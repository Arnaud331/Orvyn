import discord
from discord import app_commands
from bot.bot import bot, users, referral_codes
from utils.contract_utils import transfer_tokens, send_eth_to_contract, get_balances, get_total_balances
from utils.data_utils import log_transaction, load_transactions, save_users, load_users, reload_users
from bot.views import WalletNavigationView, SettingsNavigationView, RenameWalletModal, ImportWalletModal, TransactionModal, SelectWalletView
from utils.embed_utils import generate_wallet_embed, generate_settings_embed
from utils.encryption_utils import decrypt

import logging

logging.basicConfig(level=logging.DEBUG)

def update_user_info(user_id):
    global users
    if user_id not in users or len(users[user_id]['wallets']) == 0:
        reload_users()
        logging.debug(f"Users loaded: {users}")
        if user_id not in users or len(users[user_id]['wallets']) == 0:
            return False
    return True

@bot.tree.command(name="buy_tokens")
async def buy_tokens_command(interaction: discord.Interaction, amount_eth: float):
    user_id = str(interaction.user.id)
    if update_user_info(user_id):
        user_info = users[user_id]['wallets'][0]
        sender_private_key = decrypt(user_info["private_key"], user_info["password"])
        sender_address = user_info["address"]
        referrer_id = user_info["referrer"]
        referrer_address = users.get(referrer_id, {'wallets': [{'address': '0x0000000000000000000000000000000000000000'}]})['wallets'][0]['address']
        try:
            tx_hash = send_eth_to_contract(sender_private_key, sender_address, amount_eth, referrer_address)
            if tx_hash:
                await interaction.response.send_message(
                    f"You sent {amount_eth} ETH to purchase ORV. Transaction hash: {tx_hash.hex()}",
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
    else:
        await interaction.response.send_message(
            "No account found. Please authenticate via OAuth2 to create an account.",
            ephemeral=True
        )

@bot.tree.command(name="history")
async def history_command(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if update_user_info(user_id):
        transactions = load_transactions()
        if user_id in transactions:
            embed = discord.Embed(title="Transaction History", color=discord.Color.blue())
            for tx in transactions[user_id]:
                embed.add_field(
                    name=f"Transaction {tx['hash']}",
                    value=f"From: {tx['from']}\nTo: {tx['to']}\nValue: {tx['value']} ORV",
                    inline=False
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("No transactions found.", ephemeral=True)
    else:
        await interaction.response.send_message(
            "No account found. Please authenticate via OAuth2 to create an account.",
            ephemeral=True
        )

@bot.tree.command(name="wallet")
async def wallet_command(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    logging.debug(f"User ID: {user_id}")
    if update_user_info(user_id):
        try:
            logging.debug(f"User {user_id} found in data: {users[user_id]}")
            embed = generate_wallet_embed(user_id, 0)
            view = WalletNavigationView(user_id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except KeyError as e:
            logging.error(f"Error: Unable to find wallet information. {e}")
            await interaction.response.send_message(
                f"Error: Unable to find wallet information. {e} Please contact the administrator.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            await interaction.response.send_message(
                f"Unexpected error: {e}. Please contact the administrator.",
                ephemeral=True
            )
    else:
        logging.warning(f"No account found for user {user_id}.")
        await interaction.response.send_message(
            "No account found. Please authenticate via OAuth2 to create an account.",
            ephemeral=True
        )

@bot.tree.command(name="transaction")
async def transaction_command(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if update_user_info(user_id) and len(users[user_id]['wallets']) > 0:
        view = SelectWalletView(user_id)
        await interaction.response.send_message("Select the wallet for the transaction:", view=view, ephemeral=True)
    else:
        await interaction.response.send_message(
            "No account or wallet found. Please authenticate via OAuth2 to create an account.",
            ephemeral=True
        )

@bot.tree.command(name="settings")
async def settings_command(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if update_user_info(user_id):
        embed = generate_settings_embed(user_id)
        view = SettingsNavigationView(user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await interaction.response.send_message(
            "No account found. Please authenticate via OAuth2 to create an account.",
            ephemeral=True
        )
