# utils/eth_utils.py
import os
from web3 import Web3

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

WEB3_PROVIDER_URL = os.getenv("WEB3_PROVIDER_URL", "http://127.0.0.1:7545")
CHAIN_ID = int(os.getenv("CHAIN_ID", "1337"))
GAS_PRICE_GWEI = int(os.getenv("GAS_PRICE_GWEI", "50"))
GAS_LIMIT_ETH_TRANSFER = int(os.getenv("GAS_LIMIT_ETH_TRANSFER", "21000"))

w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))
if not w3.is_connected():
    raise SystemExit("Connection to provider failed")

def _checksum(addr: str) -> str:
    return Web3.to_checksum_address(addr)

def _normalize_privkey(pk: str) -> str:
    pk = pk.strip()
    return pk if pk.startswith("0x") else "0x" + pk

def send_eth(sender_private_key: str, sender_address: str, recipient_address: str, amount_eth: float):
    sender_checksum = _checksum(sender_address)
    recipient_checksum = _checksum(recipient_address)
    tx = {
        "nonce": w3.eth.get_transaction_count(sender_checksum),
        "to": recipient_checksum,
        "value": w3.to_wei(amount_eth, "ether"),
        "gas": GAS_LIMIT_ETH_TRANSFER,
        "gasPrice": w3.to_wei(GAS_PRICE_GWEI, "gwei"),
        "chainId": CHAIN_ID,
    }
    signed_tx = w3.eth.account.sign_transaction(tx, _normalize_privkey(sender_private_key))
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Sent {amount_eth} ETH to {recipient_checksum}")
    return tx_hash
