import os
import discord
from discord.ext import commands
from urllib.parse import urlencode, quote

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from utils.data_utils import load_referral_codes
from utils.state_manager import state_manager

def require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing env var: {name}")
    return val

DISCORD_TOKEN        = require_env("DISCORD_TOKEN")
DISCORD_CLIENT_ID    = require_env("DISCORD_CLIENT_ID")
DISCORD_REDIRECT_URI = require_env("DISCORD_REDIRECT_URI")
DISCORD_OAUTH_SCOPES = os.getenv("DISCORD_OAUTH_SCOPES", "identify guilds.join email")
COMMAND_PREFIX       = os.getenv("DISCORD_COMMAND_PREFIX", "!")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

users = state_manager.get_users()
referral_codes = load_referral_codes()

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot connected as {bot.user}")

@bot.tree.command(name="authorize")
async def authorize(interaction: discord.Interaction):
    base = "https://discord.com/oauth2/authorize"
    query = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
    }
    oauth2_url = f"{base}?{urlencode(query)}&scope={quote(DISCORD_OAUTH_SCOPES)}"

    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        style=discord.ButtonStyle.link,
        label="Authorize",
        url=oauth2_url
    ))

    await interaction.response.send_message(
        "Click the button below to authenticate via OAuth2.",
        view=view,
        ephemeral=True
    )

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
