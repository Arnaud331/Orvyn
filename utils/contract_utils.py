# wallet_and_token_ops.py
import os
import json
from web3 import Web3, Account
from bot.bot import users
from utils.data_utils import log_transaction, get_user_id_by_address, log_notification, has_user_been_notified
from utils.eth_utils import send_eth
from utils.encryption_utils import encrypt, decrypt, generate_random_password

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def require_env(name: str) -> str:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        raise SystemExit(f"Missing env var: {name}")
    return v

def as_int(name: str, default: int = None) -> int:
    s = os.getenv(name)
    if s is None or s.strip() == "":
        if default is None:
            raise SystemExit(f"Missing env var: {name}")
        return default
    try:
        return int(s)
    except ValueError:
        raise SystemExit(f"{name} must be an integer")

def checksum_addr(v: str) -> str:
    try:
        return Web3.to_checksum_address(v)
    except Exception:
        raise SystemExit(f"Invalid address: {v}")

def normalize_privkey(pk: str) -> str:
    pk = pk.strip()
    if not pk.startswith("0x"):
        pk = "0x" + pk
    if len(pk) != 66:
        raise SystemExit("MAIN_ACCOUNT_PRIVATE_KEY must be 32-byte hex")
    return pk

WEB3_PROVIDER_URL = os.getenv("WEB3_PROVIDER_URL", "http://127.0.0.1:7545")
CHAIN_ID = as_int("CHAIN_ID", 1337)
GAS_PRICE_GWEI = as_int("GAS_PRICE_GWEI", 50)
GAS_LIMIT_BUY = as_int("GAS_LIMIT_BUY", 210000)
GAS_LIMIT_TRANSFER = as_int("GAS_LIMIT_TRANSFER", 500000)
INITIAL_ETH_GRANT = as_int("INITIAL_ETH_GRANT", 1)
INITIAL_TOKEN_GRANT = as_int("INITIAL_TOKEN_GRANT", 1000)
TOKEN_DECIMALS = as_int("TOKEN_DECIMALS", 18)
COMPILED_CODE_PATH = os.getenv("COMPILED_CODE_PATH", "abi/compiled_code.json")
CONTRACT_SOURCE_FILE = os.getenv("CONTRACT_SOURCE_FILE", "OrvynToken.sol")
CONTRACT_NAME = os.getenv("CONTRACT_NAME", "OrvynToken")
MAIN_ACCOUNT_ADDRESS = checksum_addr(require_env("MAIN_ACCOUNT_ADDRESS"))
MAIN_ACCOUNT_PRIVATE_KEY = normalize_privkey(require_env("MAIN_ACCOUNT_PRIVATE_KEY"))
CONTRACT_ADDRESS = checksum_addr(require_env("CONTRACT_ADDRESS"))

w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))
if not w3.is_connected():
    raise SystemExit("Connection to provider failed")

with open(COMPILED_CODE_PATH, "r") as f:
    compiled_sol = json.load(f)
try:
    abi = compiled_sol["contracts"][CONTRACT_SOURCE_FILE][CONTRACT_NAME]["abi"]
except Exception:
    raise SystemExit("ABI not found in compiled output; check CONTRACT_SOURCE_FILE and CONTRACT_NAME")

Token = w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

def send_eth_to_contract(sender_private_key, sender_address, amount_eth, referrer_address=None):
    tx = Token.functions.buyTokens(referrer_address).build_transaction({
        "nonce": w3.eth.get_transaction_count(sender_address),
        "value": w3.to_wei(amount_eth, "ether"),
        "gas": GAS_LIMIT_BUY,
        "gasPrice": w3.to_wei(GAS_PRICE_GWEI, "gwei"),
        "chainId": CHAIN_ID
    })
    signed = w3.eth.account.sign_transaction(tx, sender_private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Sent {amount_eth} ETH to contract {CONTRACT_ADDRESS}")
    return tx_hash

def generate_user_account(user_id, users_dict, email=None, ip=None):
    account = Account.create()
    password = generate_random_password()
    user_data = {
        "private_key": encrypt("0x" + account.key.hex(), password),
        "address": account.address,
        "name": "Wallet 1",
        "referrer": None,
        "password": password
    }
    if user_id not in users_dict:
        users_dict[user_id] = {"email": email, "ip": ip, "wallets": []}
    users_dict[user_id]["wallets"].append(user_data)
    send_eth(MAIN_ACCOUNT_PRIVATE_KEY, MAIN_ACCOUNT_ADDRESS, account.address, INITIAL_ETH_GRANT)
    send_initial_orv(account.address)
    return user_data

def send_initial_orv(recipient_address):
    tx = Token.functions.transfer(recipient_address, INITIAL_TOKEN_GRANT * (10 ** TOKEN_DECIMALS)).build_transaction({
        "chainId": CHAIN_ID,
        "gas": GAS_LIMIT_TRANSFER,
        "gasPrice": w3.to_wei(GAS_PRICE_GWEI, "gwei"),
        "nonce": w3.eth.get_transaction_count(MAIN_ACCOUNT_ADDRESS),
    })
    signed = w3.eth.account.sign_transaction(tx, MAIN_ACCOUNT_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Sent {INITIAL_TOKEN_GRANT} tokens to {recipient_address}, tx: {receipt.transactionHash.hex()}")

def get_balances(address):
    orv = Token.functions.balanceOf(address).call() / (10 ** TOKEN_DECIMALS)
    eth = w3.eth.get_balance(address) / (10 ** 18)
    return orv, eth

def get_total_balances(user_id, users_dict):
    total_orv = 0.0
    total_eth = 0.0
    for wallet in users_dict[user_id]["wallets"]:
        o, e = get_balances(wallet["address"])
        total_orv += o
        total_eth += e
    return total_orv, total_eth

def transfer_tokens(interaction, sender_private_key, sender_address, recipient_address, amount, bot):
    tx = Token.functions.transfer(recipient_address, int(amount * (10 ** TOKEN_DECIMALS))).build_transaction({
        "chainId": CHAIN_ID,
        "gas": GAS_LIMIT_TRANSFER,
        "gasPrice": w3.to_wei(GAS_PRICE_GWEI, "gwei"),
        "nonce": w3.eth.get_transaction_count(sender_address),
    })
    signed = w3.eth.account.sign_transaction(tx, sender_private_key)
    try:
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transfer successful: {receipt.transactionHash.hex()}")
        details = get_transaction_details(receipt.transactionHash.hex(), bot, users)
        log_transaction(str(interaction.user.id), details)
        return receipt.transactionHash.hex()
    except ValueError as e:
        print(f"Transfer error: {e}")
        return None

def get_transaction_details(tx_hash, bot, users_dict):
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    logs = Token.events.Transfer().process_receipt(receipt)
    value = logs[0]["args"]["value"] / (10 ** TOKEN_DECIMALS) if logs else 0
    from_address = logs[0]["args"]["from"] if logs else ""
    to_address = logs[0]["args"]["to"] if logs else ""
    recipient_user_id = get_user_id_by_address(to_address, users_dict)
    if recipient_user_id:
        recipient = bot.get_user(int(recipient_user_id))
        if recipient:
            bot.loop.create_task(send_notification(recipient, from_address, value, tx_hash))
    return {"from": from_address, "to": to_address, "value": value, "hash": receipt.transactionHash.hex()}

async def send_notification(user, from_address, amount, tx_hash):
    try:
        if not has_user_been_notified(user.id, tx_hash):
            await user.send(f"You received {amount} ORV from {from_address}.")
            log_notification(user.id, tx_hash)
    except Exception as e:
        print(f"DM failed for {user}: {e}")
