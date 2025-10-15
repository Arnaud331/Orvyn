from solcx import compile_standard, install_solc, set_solc_version
from web3 import Web3
from pathlib import Path
import json
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def require_env(name: str, allow_empty: bool = False) -> str:
    val = os.getenv(name)
    if (val is None) or (not allow_empty and val.strip() == ""):
        sys.exit(f"[CONFIG] Missing env var: {name}")
    return val

def as_int(name: str, default: int = None) -> int:
    s = os.getenv(name)
    if s is None or s.strip() == "":
        if default is None:
            sys.exit(f"[CONFIG] Missing env var: {name}")
        return default
    try:
        return int(s)
    except ValueError:
        sys.exit(f"[CONFIG] {name} must be an integer. Got: {s}")

def checksum_addr(val: str) -> str:
    try:
        return Web3.to_checksum_address(val)
    except Exception:
        sys.exit(f"[CONFIG] Invalid Ethereum address for value: {val}")

def normalize_privkey(pk: str) -> str:
    pk = pk.strip()
    if not pk.startswith("0x"):
        pk = "0x" + pk
    if len(pk) != 66:
        sys.exit("[CONFIG] SENDER_PRIVATE_KEY must be a 32-byte hex string (64 hex chars), with or without 0x.")
    return pk


SOLC_VERSION         = os.getenv("SOLC_VERSION", "0.8.20")
GANACHE_URL          = os.getenv("GANACHE_URL", "http://127.0.0.1:7545")
CHAIN_ID             = as_int("CHAIN_ID", default=1337)
GAS_LIMIT_DEPLOY     = as_int("GAS_LIMIT_DEPLOY", default=5_000_000)
GAS_LIMIT_TRANSFER   = as_int("GAS_LIMIT_TRANSFER", default=500_000)
GAS_PRICE_GWEI       = as_int("GAS_PRICE_GWEI", default=50)
TOKEN_SUPPLY         = as_int("TOKEN_SUPPLY", default=7_000_000)
TRANSFER_AMOUNT      = as_int("TRANSFER_AMOUNT", default=1_000)
SENDER_ADDRESS       = checksum_addr(require_env("SENDER_ADDRESS"))
SENDER_PRIVATE_KEY   = normalize_privkey(require_env("SENDER_PRIVATE_KEY"))
RECIPIENT_ADDRESS    = checksum_addr(require_env("RECIPIENT_ADDRESS"))

COMPILED_CODE_PATH   = Path(os.getenv("COMPILED_CODE_PATH", "abi/compiled_code.json"))
COMPILED_CODE_PATH.parent.mkdir(parents=True, exist_ok=True)

CONTRACT_FILENAME    = os.getenv("CONTRACT_FILENAME", "OrvynToken.sol")
CONTRACT_PATH        = Path(CONTRACT_FILENAME)

NODE_MODULES_PATH    = Path(os.getenv("NODE_MODULES_PATH", Path.cwd() / "node_modules")).resolve()

OPENZEPPELIN_PATHS = {
    "@openzeppelin/contracts/token/ERC20/ERC20.sol": "contracts/token/ERC20/ERC20.sol",
    "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol": "contracts/token/ERC20/extensions/IERC20Metadata.sol",
    "@openzeppelin/contracts/token/ERC20/IERC20.sol": "contracts/token/ERC20/IERC20.sol",
    "@openzeppelin/contracts/utils/Context.sol": "contracts/utils/Context.sol",
    "@openzeppelin/contracts/interfaces/draft-IERC6093.sol": "contracts/interfaces/draft-IERC6093.sol",
}


print(f"[INFO] Using solc {SOLC_VERSION}")
install_solc(SOLC_VERSION)
set_solc_version(SOLC_VERSION)

if not CONTRACT_PATH.is_file():
    sys.exit(f"[FS] Solidity contract not found: {CONTRACT_PATH}")
token_source_code = CONTRACT_PATH.read_text(encoding="utf-8")

openzeppelin_sources = {}
for import_path, rel_file in OPENZEPPELIN_PATHS.items():
    full_path = NODE_MODULES_PATH / "@openzeppelin" / rel_file
    if not full_path.is_file():
        print(f"[WARN] File not found: {full_path}")
    else:
        print(f"[OK] Found: {full_path}")
        openzeppelin_sources[import_path] = {"content": full_path.read_text(encoding="utf-8")}

openzeppelin_sources[CONTRACT_PATH.name] = {"content": token_source_code}

print("[INFO] Compiling…")
compiled_sol = compile_standard(
    {
        "language": "Solidity",
        "sources": openzeppelin_sources,
        "settings": {
            "outputSelection": {
                "*": {
                    "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                }
            }
        },
    },
    solc_version=SOLC_VERSION
)

COMPILED_CODE_PATH.write_text(json.dumps(compiled_sol), encoding="utf-8")
print(f"[INFO] Compiled code saved to: {COMPILED_CODE_PATH}")

w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
if w3.is_connected():
    print(f"[INFO] Connected to provider: {GANACHE_URL}")
else:
    sys.exit("[NET] Connection to provider failed")

try:
    CONTRACT_NAME = os.getenv("CONTRACT_NAME", "OrvynToken")
    bytecode = compiled_sol['contracts'][CONTRACT_PATH.name][CONTRACT_NAME]['evm']['bytecode']['object']
    abi = compiled_sol['contracts'][CONTRACT_PATH.name][CONTRACT_NAME]['abi']
except KeyError:
    sys.exit("[BUILD] Could not find ABI/bytecode in compiled output — check CONTRACT_NAME and file names.")

Token = w3.eth.contract(abi=abi, bytecode=bytecode)
initial_supply_wei = TOKEN_SUPPLY * (10 ** 18)

print("[TX] Building deployment tx…")
deploy_tx = Token.constructor(initial_supply_wei).build_transaction({
    "chainId": CHAIN_ID,
    "gas": GAS_LIMIT_DEPLOY,
    "gasPrice": w3.to_wei(GAS_PRICE_GWEI, "gwei"),
    "nonce": w3.eth.get_transaction_count(SENDER_ADDRESS),
})

print("[TX] Signing…")
signed_deploy = w3.eth.account.sign_transaction(deploy_tx, SENDER_PRIVATE_KEY)
print("[TX] Sending…")
tx_hash = w3.eth.send_raw_transaction(signed_deploy.raw_transaction)
print(f"[TX] Deploy hash: {tx_hash.hex()}")

print("[TX] Waiting for receipt…")
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
contract_address = tx_receipt.contractAddress
print(f"[OK] Contract deployed at: {contract_address}")

Token = w3.eth.contract(address=contract_address, abi=abi)

try:
    total_supply = Token.functions.totalSupply().call()
    print(f"[INFO] Total Supply: {total_supply / (10 ** 18)} tokens")
except Exception as e:
    print(f"[WARN] Could not read totalSupply: {e}")

def transfer_tokens(sender_private_key: str, sender_address: str, recipient_address: str, amount_tokens: int):
    amount_wei = amount_tokens * (10 ** 18)
    tx = Token.functions.transfer(recipient_address, amount_wei).build_transaction({
        "chainId": CHAIN_ID,
        "gas": GAS_LIMIT_TRANSFER,
        "gasPrice": w3.to_wei(GAS_PRICE_GWEI, "gwei"),
        "nonce": w3.eth.get_transaction_count(sender_address),
    })
    signed = w3.eth.account.sign_transaction(tx, sender_private_key)
    sent = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(sent)
    print(f"[OK] Transfer tx: {receipt.transactionHash.hex()}")

try:
    transfer_tokens(SENDER_PRIVATE_KEY, SENDER_ADDRESS, RECIPIENT_ADDRESS, TRANSFER_AMOUNT)
except Exception as e:
    print(f"[WARN] Transfer failed: {e}")
