import discord
from discord.ext import commands
from bot.bot import bot, users, referral_codes
from utils.data_utils import load_users, save_users, load_referral_codes, log_notification, has_user_been_notified

@bot.event
async def on_ready():
    global users, referral_codes
    users = load_users()
    referral_codes = load_referral_codes()
    await bot.tree.sync()
    print(f"Bot connected as {bot.user}")

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Unknown command. Use `/help` to see the list of available commands.")
    else:
        await ctx.send(f"An error occurred: {str(error)}")

@bot.event
async def on_transaction_complete(tx_hash: str, sender_id: int, recipient_id: int, amount: float):
    recipient = bot.get_user(recipient_id)
    if recipient and not has_user_been_notified(recipient_id, tx_hash):
        await recipient.send(f"You received {amount} ORV.")
        log_notification(recipient_id, tx_hash)
