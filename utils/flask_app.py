# oauth_server.py
import os
import requests
from flask import Flask, request
from utils.contract_utils import generate_user_account
from utils.state_manager import state_manager

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

DISCORD_API_BASE = os.getenv("DISCORD_API_BASE", "https://discord.com/api/v10")
CLIENT_ID = require_env("DISCORD_CLIENT_ID")
CLIENT_SECRET = require_env("DISCORD_CLIENT_SECRET")
REDIRECT_URI = require_env("DISCORD_REDIRECT_URI")
DISCORD_CHANNEL_ID = require_env("DISCORD_CHANNEL_ID")
BOT_TOKEN = require_env("DISCORD_BOT_TOKEN")

app = Flask(__name__)

def send_embed_to_discord(user_info, ip_address: str):
    url = f"{DISCORD_API_BASE}/channels/{DISCORD_CHANNEL_ID}/messages"
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    embed = {
        "title": "New Sign-in",
        "fields": [
            {"name": "User ID", "value": user_info.get("id", "Unavailable"), "inline": False},
            {"name": "Username", "value": f"{user_info.get('username', 'Unknown')}#{user_info.get('discriminator', '0000')}", "inline": False},
            {"name": "IP Address", "value": ip_address, "inline": False},
            {"name": "Email", "value": user_info.get("email", "Not provided"), "inline": False},
            {"name": "MFA Enabled", "value": str(user_info.get("mfa_enabled", "Unavailable")), "inline": False}
        ],
        "color": 0x2C2F33
    }
    payload = {"content": "", "embeds": [embed]}
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    if not (200 <= r.status_code < 300):
        print(f"Failed to send embed to Discord: {r.status_code}, {r.text}")

@app.route("/")
def home():
    return "Bot OAuth2"

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Missing authorization code", 400

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_res = requests.post(f"{DISCORD_API_BASE}/oauth2/token", data=data, headers=headers, timeout=20)

    if token_res.status_code != 200:
        return f"Error obtaining token: {token_res.status_code}", 400

    access_token = token_res.json().get("access_token")
    if not access_token:
        return "Access token not found", 400

    user_res = requests.get(f"{DISCORD_API_BASE}/users/@me", headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
    if user_res.status_code != 200:
        return f"Error fetching user info: {user_res.status_code}", 400
    user_info = user_res.json()

    ip_res = requests.get("https://httpbin.org/ip", timeout=10)
    if ip_res.status_code != 200:
        return f"Error fetching IP: {ip_res.status_code}", 400
    user_ip = ip_res.json().get("origin", "unknown")

    send_embed_to_discord(user_info, user_ip)

    user_id = user_info.get("id")
    if user_id:
        users = state_manager.get_users()
        if user_id not in users or len(users[user_id].get("wallets", [])) == 0:
            account = generate_user_account(user_id, users, email=user_info.get("email"), ip=user_ip)
            state_manager.update_users(users)
            state_manager.reload_users()
            print(f"Generated account for user {user_id}: Address: {account['address']}")

    return "Authorization complete. You can close this window."
