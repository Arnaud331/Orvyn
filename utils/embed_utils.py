import discord
from utils.contract_utils import get_balances, get_total_balances
from bot.bot import users, referral_codes
import logging

def generate_wallet_embed(user_id, wallet_index):
    if user_id not in users:
        logging.error(f"User {user_id} not found in user data.")
        raise KeyError(f"User {user_id} not found in user data.")

    user_info = users[user_id]['wallets'][wallet_index]
    logging.debug(f"User {user_id} info: {user_info}")
    address = user_info["address"]
    name = user_info["name"]
    orv_balance, eth_balance = get_balances(address)
    total_orv, total_eth = get_total_balances(user_id, users)

    embed = discord.Embed(title=f"{name} — Wallet Information", color=discord.Color.blue())
    embed.add_field(name="Public Address", value=address, inline=False)
    embed.add_field(name="ORV Balance", value=f"{orv_balance} ORV", inline=False)
    embed.add_field(name="ETH Balance", value=f"{eth_balance} ETH", inline=False)
    embed.add_field(name="Total ORV", value=f"{total_orv} ORV", inline=True)
    embed.add_field(name="Total ETH", value=f"{total_eth} ETH", inline=True)
    embed.set_footer(text="Use the buttons below to navigate between wallets and show the private key.")
    return embed

def generate_settings_embed(user_id):
    if user_id not in users:
        logging.error(f"User {user_id} not found in user data.")
        raise KeyError(f"User {user_id} not found in user data.")

    user_info = users[user_id]['wallets'][0]
    referrer_code = None
    for code, uid in referral_codes.items():
        if uid == user_info["referrer"]:
            referrer_code = code
            break

    embed = discord.Embed(title=f"Settings — {user_id}", color=discord.Color.green())
    embed.add_field(name="Referrer", value=f"{referrer_code if referrer_code else 'None'}", inline=True)
    embed.set_footer(text="Use the buttons below to modify your settings.")
    return embed
