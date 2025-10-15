
<h1 align="center">🪙 Orvyn — Tokenized Discord Economy</h1>
<p align="center">
  <b>Full-stack prototype for gaming prize payouts, built for speed and YC-proof-of-work.</b><br/>
  <sub>Discord + Flask + Web3 + Solidity • ERC‑20 from Discord • OAuth2 onboarding • Wallets • Purchases • Transfers</sub>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white">
  <img alt="Solidity" src="https://img.shields.io/badge/Solidity-0.8.20-363636?logo=solidity&logoColor=white">
  <img alt="Discord.py" src="https://img.shields.io/badge/discord.py-2.x-5865F2?logo=discord&logoColor=white">
  <img alt="Web3.py" src="https://img.shields.io/badge/Web3.py-6.x-333?logo=ethereum&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-0aa36e">
</p>

> Originally used during **gaming competitions** where players received **cash‑prize–style rewards** as tokens.  
> This repo is a **compact proof‑of‑work** for YC: end‑to‑end shipping across bot, backend, chain, and storage.

---

## 🧭 Table of Contents
- [🎯 Goals](#-goals)
- [✨ Key Features](#-key-features)
- [🏗️ Architecture](#%EF%B8%8F-architecture)
- [🧰 Tech Stack](#-tech-stack)
- [📁 Folder Structure](#-folder-structure)
- [📝 Smart Contract](#-smart-contract)
- [🤖 Discord Bot Commands](#-discord-bot-commands)
- [🗃️ Data Model](#%EF%B8%8F-data-model)
- [🔐 Security & Privacy](#-security--privacy)
- [🚀 Setup & Run](#-setup--run)
- [⚙️ Environment Variables](#%EF%B8%8F-environment-variables)
- [🧪 Common Workflows](#-common-workflows)
- [🛠️ Troubleshooting](#%EF%B8%8F-troubleshooting)
- [🗺️ Roadmap](#%EF%B8%8F-roadmap)
- [📜 License](#-license)

---

## 🎯 Goals
- Ship a **working product**, not slides: bot + backend + blockchain + persistence.  
- Demonstrate practical **Discord OAuth2 onboarding**, wallet creation, **token sales**, and **on‑chain transfers**.  
- Provide a **runnable artifact** for YC reviewers & engineers.

---

## ✨ Key Features
- 🔐 **Per‑user wallets**: generate or import; persisted with local encryption helpers.
- 💸 **Initial grants** (ETH + token) to reduce onboarding friction.
- 🛒 **Token purchase** via `/buy_tokens` → calls `buyTokens(referrer)` on the ERC‑20.
- 🔁 **On‑chain transfers** between users, with embeds and DM notifications.
- 📊 **Balances**: per wallet + aggregated across all wallets.
- 🧑‍🤝‍🧑 **Referrals**: simple code → user ID mapping.
- 🔗 **OAuth2 flow** (`/authorize`) through Flask; posts a nice login embed to a channel.
- ⚙️ **.env‑driven config** and a **.gitignore** that keeps secrets & data out of Git.

---

## 🏗️ Architecture

```
+------------------------+            +------------------+            +----------------------+
|        Discord         | <------->  |   Discord Bot    |  ------->  |     Web3 Provider    |
|  (Guild, Users, cmds) |   API/GW   | (discord.py app) |  HTTP/RPC  |  (Ganache/Node/etc.) |
+-----------^------------+            +---------^--------+            +-----------^----------+
            |                                  |                                 |
            |                                  |                                 |
            |                       +----------+----------+                      |
            |                       |   Flask OAuth App  |                      |
            |                       |  (/authorize flow) |                      |
            |                       +----------^----------+                      |
            |                                  |                                 |
            v                                  |                                 |
+------------------------+                     |                                 |
|      Discord OAuth     | <-------------------+                                 |
|    (authorize/token)   |                                                       |
+------------------------+                                                       |
                                                                                 |
                                                             +-------------------+-----------------+
                                                             |            Local Persistence        |
                                                             |         data/*.json (encrypted)     |
                                                             +-------------------------------------+
```

**Bot**: slash commands, views/modals, transfers, history.  
**Flask**: OAuth callback + channel embed.  
**Contract**: ERC‑20 with `buyTokens(referrer)` and standard methods.  
**Storage**: JSON files for users/tx/notifications/referrals (encrypted keys supported).

---

## 🧰 Tech Stack
**Languages**: Python 3.10+, Solidity 0.8.20  
**Libs**: `discord.py`, `Flask`, `requests`, `web3`, `py‑solc‑x`, `python‑dotenv`, `cryptography`  
**Chain**: Ganache (or any EVM RPC), OpenZeppelin Contracts  
**Ops**: `.env` config, curated `.gitignore`

---

## 📁 Folder Structure
```
.
├─ abi/                         # Compiled contract artifacts (JSON)
├─ bot/
│  ├─ bot.py                    # Bot bootstrap: env, intents, /authorize URL builder
│  ├─ commands.py               # Slash commands (/wallet, /history, /settings, /transaction, /buy_tokens)
│  ├─ events.py                 # on_ready, on_command_error, on_transaction_complete
│  └─ views.py                  # Discord UI: wallet nav, show key, transaction modal, settings
├─ data/
│  ├─ users.json                # Local user store (encrypted private keys when persisted)
│  ├─ transactions.json         # Logged tx history per user
│  ├─ notifications.json        # Delivery-dedup for DM notifications
│  └─ referral_codes.json       # Simple referral mapping
├─ deploy/                      # (optional) compile/deploy helpers
├─ utils/
│  ├─ contract_utils.py         # Web3 helpers: balances, buyTokens, transfers, generate wallet, etc.
│  ├─ data_utils.py             # load/save users, tx log, notifications, referrals
│  ├─ embed_utils.py            # embed builders
│  ├─ encryption_utils.py       # encrypt/decrypt/password helpers
│  ├─ eth_utils.py              # raw ETH sends
│  ├─ flask_app.py              # OAuth2 endpoints + Discord embed posting
│  └─ state_manager.py          # in‑memory state
├─ OrvynToken.sol               # ERC‑20 token with buyTokens/referral
├─ main.py                      # Launch Flask (thread) + Bot
├─ .env.example                 # Example env → copy to .env
├─ .gitignore
└─ README.md
```

---

## 📝 Smart Contract
- **Name**: `OrvynToken` (ERC‑20) • **Solidity**: `0.8.20`  
- **Key method**: `buyTokens(address referrer)` — fixed‑rate purchase + optional referral.  
- Standard ERC‑20: `transfer`, `balanceOf`, `totalSupply`, etc.  
- **Artifacts**: `abi/compiled_code.json` consumed by the bot/backend.

---

## 🤖 Discord Bot Commands
- `/authorize` → OAuth link; on success, auto‑bootstrap wallet + optional initial grants.  
- `/wallet` → navigable wallet embed (address, ORV/ETH, totals), rename/import/show‑key UI.  
- `/history` → transaction history (from local log).  
- `/settings` → view/update referrer code.  
- `/transaction` → pick wallet → send ORV to an address.  
- `/buy_tokens amount_eth:<float>` → call `buyTokens` with provided ETH amount.

---

## 🗃️ Data Model
**`data/users.json`**
```json
{
  "discord_user_id": {
    "email": "optional@email",
    "ip": "optional ip",
    "wallets": [
      {
        "private_key": "<encrypted or plaintext depending on mode>",
        "address": "0x...",
        "name": "Wallet 1",
        "referrer": "discord_user_id_of_referrer_or_null",
        "password": "<random per-wallet password if encryption is used>"
      }
    ]
  }
}
```
Also:
- `data/transactions.json` → `{ "<discord_user_id>": [{ "from": "...", "to": "...", "value": 0, "hash": "0x..." }] }`
- `data/notifications.json` → per‑user delivered tx hashes
- `data/referral_codes.json` → `{ "CODE": "discord_user_id" }`

---

## 🔐 Security & Privacy
- Secrets live in **`.env`**. Never commit them.  
- Local data (`data/*.json`) is **gitignored**.  
- Keys can be **encrypted** and decrypted only on use.  
- OAuth `state` can be added for CSRF hardening if pushing toward prod.  
- Prototype quality: perfect for demos/POCs/competitions; **not** production custody.

---

## 🚀 Setup & Run

### 1) Prereqs
- Python 3.10+ • Ganache (or any EVM RPC) • Discord App & Bot token

### 2) Install
```bash
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3) Configure
```bash
cp .env.example .env
# edit .env with your tokens, RPC URL, addresses, contract address, etc.
```

### 4) Compile & Deploy (if needed)
- Deploy `OrvynToken.sol` and set `CONTRACT_ADDRESS` in `.env`,  
  or place ABI at `abi/compiled_code.json`.

### 5) Run
```bash
python main.py
```
The bot will register slash commands. Use `/authorize` to create a wallet and get initial grants (if configured).

---

## ⚙️ Environment Variables
See **`.env.example`** (copy → `.env`). Highlights:

```dotenv
# Discord
DISCORD_TOKEN=your-bot-token
DISCORD_CLIENT_ID=123456789012345678
DISCORD_REDIRECT_URI=https://xxxx.ngrok-free.app/callback
DISCORD_OAUTH_SCOPES=identify guilds.join email
DISCORD_COMMAND_PREFIX=!

# Flask (optional)
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false

# Web3 / Chain
WEB3_PROVIDER_URL=http://127.0.0.1:7545
CHAIN_ID=1337
GAS_PRICE_GWEI=50
GAS_LIMIT_ETH_TRANSFER=21000
GAS_LIMIT_BUY=210000
GAS_LIMIT_TRANSFER=500000

# Contract
SOLC_VERSION=0.8.20
CONTRACT_SOURCE_FILE=OrvynToken.sol
CONTRACT_NAME=OrvynToken
COMPILED_CODE_PATH=abi/compiled_code.json
CONTRACT_ADDRESS=0xYourDeployedContract

# Funding / Token
INITIAL_ETH_GRANT=1
INITIAL_TOKEN_GRANT=1000
TOKEN_DECIMALS=18

# Faucet
MAIN_ACCOUNT_ADDRESS=0xYourMainAccount
MAIN_ACCOUNT_PRIVATE_KEY=0xyour32bytehexprivatekey

# Channels
DISCORD_TX_CHANNEL_ID=123456789012345678

# Local data
USERS_FILE=data/users.json
TRANSACTIONS_FILE=data/transactions.json
NOTIFICATIONS_FILE=data/notifications.json
REFERRAL_CODES_FILE=data/referral_codes.json
REFERRAL_CODES_DEFAULT={"code":"11111111111111"}
```

---

## 🧪 Common Workflows
- **Create wallet**: `/authorize` → OAuth → wallet + optional grants.  
- **Buy tokens**: `/buy_tokens amount_eth:0.1` → on‑chain purchase.  
- **Send tokens**: `/transaction` → choose wallet → recipient + amount → broadcast → log & embed.  
- **View wallets**: `/wallet` → navigate, rename, import, reveal key (guarded).  
- **History**: `/history` → list past tx (local log).

---

## 🛠️ Troubleshooting
- **No slash commands?** Ensure bot invited with `applications.commands`. First sync may take a minute.  
- **RPC errors?** Check `WEB3_PROVIDER_URL` and `CHAIN_ID`. Make sure Ganache is running.  
- **Nonces/funds?** Reset Ganache or bump faucet grants in `.env`.  
- **OAuth issues?** `DISCORD_REDIRECT_URI` must match your Discord app settings.

---

## 🗺️ Roadmap
- Add OAuth `state` for CSRF hardening.  
- Decrypt‑on‑use only; keep encrypted keys in memory.  
- Atomic writes & locks for `data/*.json`.  
- DB backend (SQLite/Postgres).  
- Admin dashboard (stats, payouts, users).  
- CI to compile & test contracts.

---

## 📜 License
MIT. This repo is a **demo/POC** for YC & competitions. Use responsibly.
