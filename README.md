# Polymarket AI Bot — Telegram

An AI-powered Polymarket crypto market analyzer bot using Claude AI.

## Commands
- `/start` — Welcome message
- `/analyze` — Analyze a Polymarket market (3-step guided flow)
- `/log` — View your last 10 trade analyses
- `/clear` — Clear your trade log
- `/help` — Show all commands

## Deploy to Railway (Free)

### Step 1 — Get your tokens
- **Telegram token**: Message @BotFather on Telegram → /newbot → copy the token
- **Anthropic API key**: Get from https://console.anthropic.com

### Step 2 — Upload to GitHub
1. Create a new GitHub repo (github.com → New repository)
2. Upload these 3 files: `bot.py`, `requirements.txt`, `Procfile`

### Step 3 — Deploy on Railway
1. Go to https://railway.app and sign up with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your repo
4. Go to **Variables** tab and add:
   - `TELEGRAM_TOKEN` = your telegram bot token
   - `ANTHROPIC_API_KEY` = your anthropic api key
5. Railway auto-deploys — your bot goes live in ~2 minutes!

### Step 4 — Test it
Open Telegram, find your bot, send `/start`

## How it works
1. User sends `/analyze`
2. Bot asks for market question, price, and asset
3. Claude AI analyzes and returns confidence score, direction, edge %, and tips
4. Results are logged per user session
