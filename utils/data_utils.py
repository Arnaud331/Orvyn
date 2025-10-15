# utils/data_utils.py
import os
import json
from pathlib import Path
from utils.encryption_utils import encrypt, decrypt

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

USERS_FILE = os.getenv("USERS_FILE", "data/users.json")
REFERRAL_CODES_FILE = os.getenv("REFERRAL_CODES_FILE", "data/referral_codes.json")
TRANSACTIONS_FILE = os.getenv("TRANSACTIONS_FILE", "data/transactions.json")
NOTIFICATIONS_FILE = os.getenv("NOTIFICATIONS_FILE", "data/notifications.json")
REFERRAL_CODES_DEFAULT = os.getenv("REFERRAL_CODES_DEFAULT", "{}")

def _ensure_parent(path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def load_users(filepath: str = None):
    fp = filepath or USERS_FILE
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as f:
            encrypted_users = json.load(f)
        users = {}
        for user_id, user_data in encrypted_users.items():
            user_info = {"email": user_data.get("email"), "ip": user_data.get("ip"), "wallets": []}
            for wallet in user_data.get("wallets", []):
                decrypted_private_key = decrypt(wallet["private_key"], wallet["password"])
                w = wallet.copy()
                w["private_key"] = decrypted_private_key
                user_info["wallets"].append(w)
            users[user_id] = user_info
        return users
    return {}

def save_users(users, filepath: str = None):
    fp = filepath or USERS_FILE
    _ensure_parent(fp)
    encrypted_users = {}
    for user_id, user_info in users.items():
        encrypted_wallets = []
        for wallet in user_info.get("wallets", []):
            encrypted_private_key = encrypt(wallet["private_key"], wallet["password"])
            wallet_copy = wallet.copy()
            wallet_copy["private_key"] = encrypted_private_key
            encrypted_wallets.append(wallet_copy)
        encrypted_users[user_id] = {
            "email": user_info.get("email"),
            "ip": user_info.get("ip"),
            "wallets": encrypted_wallets,
        }
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(encrypted_users, f, indent=4)

def reload_users():
    global users
    users = load_users()

def _parse_referral_default():
    try:
        return json.loads(REFERRAL_CODES_DEFAULT) if REFERRAL_CODES_DEFAULT else {}
    except Exception:
        return {}

def load_referral_codes(filepath: str = None):
    fp = filepath or REFERRAL_CODES_FILE
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    return _parse_referral_default()

def load_transactions(filepath: str = None):
    fp = filepath or TRANSACTIONS_FILE
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def log_transaction(user_id, tx_details, filepath: str = None):
    fp = filepath or TRANSACTIONS_FILE
    _ensure_parent(fp)
    transactions = load_transactions(fp)
    transactions.setdefault(str(user_id), []).append(tx_details)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(transactions, f, indent=4)

def get_user_id_by_address(address, users):
    for user_id, user_info in users.items():
        for wallet in user_info.get("wallets", []):
            if wallet.get("address") == address:
                return user_id
    return None

def has_user_been_notified(user_id, tx_hash, filepath: str = None):
    fp = filepath or NOTIFICATIONS_FILE
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as f:
            notifications = json.load(f)
            return tx_hash in notifications.get(str(user_id), [])
    return False

def log_notification(user_id, tx_hash, filepath: str = None):
    fp = filepath or NOTIFICATIONS_FILE
    _ensure_parent(fp)
    notifications = {}
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as f:
            notifications = json.load(f)
    notifications.setdefault(str(user_id), [])
    if tx_hash not in notifications[str(user_id)]:
        notifications[str(user_id)].append(tx_hash)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(notifications, f, indent=4)
