import os
import json
import discord
from discord.ui import View, Modal, Select, TextInput, Button
from web3 import Account, Web3

from utils.contract_utils import transfer_tokens, get_transaction_details
from bot.bot import users, referral_codes, bot
from utils.embed_utils import generate_wallet_embed, generate_settings_embed
from utils.encryption_utils import decrypt, encrypt, generate_random_password

TX_CHANNEL_ID = int(os.getenv("DISCORD_TX_CHANNEL_ID", "0"))

class WalletNavigationView(View):
    def __init__(self, user_id, wallet_index=0):
        super().__init__()
        self.user_id = user_id
        self.wallet_index = wallet_index

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_wallet(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.wallet_index = (self.wallet_index - 1) % len(users[self.user_id]['wallets'])
        await interaction.response.edit_message(embed=generate_wallet_embed(self.user_id, self.wallet_index), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_wallet(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.wallet_index = (self.wallet_index + 1) % len(users[self.user_id]['wallets'])
        await interaction.response.edit_message(embed=generate_wallet_embed(self.user_id, self.wallet_index), view=self)

    @discord.ui.button(label="Rename", style=discord.ButtonStyle.primary)
    async def rename_wallet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RenameWalletModal(self.user_id, self.wallet_index))

    @discord.ui.button(label="Import Wallet", style=discord.ButtonStyle.success)
    async def import_wallet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ImportWalletModal(self.user_id))

    @discord.ui.button(label="🔑", style=discord.ButtonStyle.danger)
    async def show_private_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=generate_private_key_warning_embed(self.user_id, self.wallet_index),
            view=ShowPrivateKeyView(self.user_id, self.wallet_index),
            ephemeral=True
        )

class ShowPrivateKeyView(View):
    def __init__(self, user_id, wallet_index):
        super().__init__()
        self.user_id = user_id
        self.wallet_index = wallet_index

    @discord.ui.button(label="Show", style=discord.ButtonStyle.danger)
    async def show(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ShowPrivateKeyModal(self.user_id, self.wallet_index))

    @discord.ui.button(label="Close", style=discord.ButtonStyle.secondary)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Action canceled.", embed=None, view=None)

class ShowPrivateKeyModal(Modal, title="Show Private Key"):
    password = TextInput(label="Password", style=discord.TextStyle.short, required=True)

    def __init__(self, user_id, wallet_index):
        super().__init__()
        self.user_id = user_id
        self.wallet_index = wallet_index

    async def on_submit(self, interaction: discord.Interaction):
        private_key_encrypted = users[self.user_id]['wallets'][self.wallet_index]['private_key']
        stored_password = users[self.user_id]['wallets'][self.wallet_index]['password']
        if self.password.value == stored_password:
            private_key = decrypt(private_key_encrypted, stored_password)
            if private_key:
                await interaction.response.edit_message(content=f"Private key: ||{private_key}||", embed=None, view=None)
            else:
                await interaction.response.send_message("Failed to decrypt the private key.", ephemeral=True)
        else:
            await interaction.response.send_message("Incorrect password.", ephemeral=True)

class ImportWalletModal(Modal, title="Import Wallet"):
    private_key = TextInput(label="Private Key", style=discord.TextStyle.short)

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            account = Account.from_key(self.private_key.value)
            password = generate_random_password()
            if self.user_id not in users:
                users[self.user_id] = {'email': None, 'ip': None, 'wallets': []}
            wallet_name = f"Wallet {len(users[self.user_id]['wallets']) + 1}"
            users[self.user_id]['wallets'].append({
                "private_key": encrypt(self.private_key.value, password),
                "address": account.address,
                "name": wallet_name,
                "referrer": None,
                "password": password
            })
            with open("data/users.json", "w") as file:
                json.dump(users, file, indent=4)

            await interaction.response.send_message(
                f"Wallet imported successfully!\nAddress: {account.address}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error importing wallet: {e}", ephemeral=True)

class RenameWalletModal(Modal, title="Rename Wallet"):
    new_name = TextInput(label="New name", style=discord.TextStyle.short)

    def __init__(self, user_id, wallet_index):
        super().__init__()
        self.user_id = user_id
        self.wallet_index = wallet_index

    async def on_submit(self, interaction: discord.Interaction):
        new_name = self.new_name.value
        users[self.user_id]['wallets'][self.wallet_index]['name'] = new_name
        with open("data/users.json", "w") as file:
            json.dump(users, file, indent=4)
        await interaction.response.send_message(f"Wallet renamed to: {new_name}", ephemeral=True)

class TransactionModal(Modal, title="Make a Transaction"):
    recipient = TextInput(label="Recipient Address", style=discord.TextStyle.short)
    amount = TextInput(label="Amount to Send (ORV)", style=discord.TextStyle.short)

    def __init__(self, wallet_index):
        super().__init__()
        self.wallet_index = wallet_index

    async def on_submit(self, interaction: discord.Interaction):
        sender_id = str(interaction.user.id)
        if sender_id not in users:
            await interaction.response.send_message(
                "You don't have an account. Use `/generate_account` to create one.",
                ephemeral=True
            )
            return

        sender_info = users[sender_id]['wallets'][self.wallet_index]
        sender_private_key = decrypt(sender_info["private_key"], sender_info["password"])
        sender_address = sender_info["address"]
        recipient_address = self.recipient.value
        amount = float(self.amount.value)

        try:
            tx_hash = transfer_tokens(
                interaction,
                sender_private_key,
                Web3.to_checksum_address(sender_address),
                Web3.to_checksum_address(recipient_address),
                amount,
                bot
            )
            if tx_hash:
                tx_details = get_transaction_details(tx_hash, bot, users)
                embed = discord.Embed(title="Transaction Successful", color=discord.Color.green())
                embed.add_field(name="Transaction Hash", value=tx_details['hash'], inline=False)
                embed.add_field(name="From", value=tx_details['from'], inline=True)
                embed.add_field(name="To", value=tx_details['to'], inline=True)
                embed.add_field(name="Value", value=f"{tx_details['value']} ORV", inline=False)

                if TX_CHANNEL_ID:
                    channel = bot.get_channel(TX_CHANNEL_ID)
                else:
                    channel = None

                if channel:
                    await channel.send(embed=embed)
                else:
                    await interaction.followup.send("Transaction succeeded, but the target channel was not found.", ephemeral=True)

                await interaction.response.send_message("Transaction succeeded and was posted to the channel.", ephemeral=True)
            else:
                await interaction.response.send_message("Transaction failed.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

class SelectWalletView(View):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.select = Select(
            placeholder="Select a wallet",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=wallet['name'], value=str(index))
                for index, wallet in enumerate(users[self.user_id]['wallets'])
            ],
            custom_id="select_wallet"
        )
        self.select.callback = self.select_wallet
        self.add_item(self.select)

    async def select_wallet(self, interaction: discord.Interaction):
        selected_wallet_index = int(self.select.values[0])
        await interaction.response.send_modal(TransactionModal(selected_wallet_index))

class SettingsNavigationView(View):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    @discord.ui.button(label="Change Referrer", style=discord.ButtonStyle.primary)
    async def modify_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UpdateReferrerModal(self.user_id))

class UpdateReferrerModal(Modal, title="Update Referrer"):
    new_referrer = TextInput(label="New Referrer Code", style=discord.TextStyle.short)

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        new_referrer_code = self.new_referrer.value
        if new_referrer_code in referral_codes:
            new_referrer_id = referral_codes[new_referrer_code]
            users[self.user_id]['wallets'][0]['referrer'] = new_referrer_id
            with open("data/users.json", "w") as file:
                json.dump(users, file, indent=4)
            await interaction.response.send_message("Referrer successfully updated.", ephemeral=True)
        else:
            await interaction.response.send_message("The provided referrer code is invalid.", ephemeral=True)

def generate_private_key_warning_embed(user_id, wallet_index):
    embed = discord.Embed(
        title="Warning!",
        description="Are you sure you want to display the private key? Never show your private key publicly.",
        color=discord.Color.red()
    )
    return embed
