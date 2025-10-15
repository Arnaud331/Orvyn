import json
import os
from utils.encryption_utils import encrypt, decrypt

class StateManager:
    def __init__(self, filepath="data/users.json"):
        self.filepath = filepath
        self.users = self.load_users()

    def load_users(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as file:
                encrypted_users = json.load(file)
                users = {}
                for user_id, user_data in encrypted_users.items():
                    user_info = {
                        "email": user_data.get("email"),
                        "ip": user_data.get("ip"),
                        "wallets": []
                    }
                    for wallet in user_data.get("wallets", []):
                        decrypted_private_key = decrypt(wallet['private_key'], wallet['password'])
                        wallet['private_key'] = decrypted_private_key
                        user_info["wallets"].append(wallet)
                    users[user_id] = user_info
                return users
        return {}

    def save_users(self):
        encrypted_users = {}
        for user_id, user_info in self.users.items():
            encrypted_wallets = []
            for wallet in user_info["wallets"]:
                encrypted_private_key = encrypt(wallet['private_key'], wallet['password'])
                wallet_copy = wallet.copy()
                wallet_copy['private_key'] = encrypted_private_key
                encrypted_wallets.append(wallet_copy)
            encrypted_users[user_id] = {
                "email": user_info["email"],
                "ip": user_info["ip"],
                "wallets": encrypted_wallets
            }
        with open(self.filepath, "w") as file:
            json.dump(encrypted_users, file, indent=4)

    def reload_users(self):
        self.users = self.load_users()

    def get_users(self):
        return self.users

    def update_users(self, new_users):
        self.users = new_users
        self.save_users()

state_manager = StateManager()

