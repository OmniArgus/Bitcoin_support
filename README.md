# Bitcoin Price Notification Bot

A Telegram bot (like [t.me/bitcoin_price](https://t.me/bitcoin_price)) that shows
the current Bitcoin price and **notifies you whenever the price moves by $500**
(configurable). Prices come from the free [CoinGecko](https://www.coingecko.com/) API.

## Commands

| Command | What it does |
| --- | --- |
| `/start` | Subscribe this chat to price-move alerts |
| `/price` | Show the current Bitcoin price |
| `/threshold <usd>` | View or change the move size that triggers an alert (e.g. `/threshold 1000`) |
| `/stop` | Unsubscribe |

## Setup

1. **Create a bot** — message [@BotFather](https://t.me/BotFather), send `/newbot`,
   and copy the token it gives you.

2. **Configure** — copy the example env file and paste your token:

   ```powershell
   copy .env.example .env
   ```

   Then edit `.env` and set `BOT_TOKEN=...`.

3. **Install dependencies** (Python 3.10+):

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. **Run it:**

   ```powershell
   python bot.py
   ```

5. In Telegram, open your bot and send `/start`.

## How the alert works

Every `POLL_SECONDS` (default 60) the bot fetches the BTC price. It remembers the
price at which it last alerted you; when the price has moved up or down by at least
the threshold since then, it sends a notification and resets the baseline to the
new price. So with a $500 threshold you get one message per $500 move, not a flood.

## Deploy to the cloud (run 24/7, no Python on your PC)

A notification bot needs to run all the time, so a cloud host is the right home.
The repo already includes everything needed: `Procfile`, `runtime.txt`,
`Dockerfile`, and `render.yaml`.

### Option A — Railway (easiest)

1. Push this folder to a **GitHub repo** (see "Push to GitHub" below).
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**.
3. Pick your repo. Railway auto-detects the `Procfile` and builds it.
4. Open the service → **Variables** → add `BOT_TOKEN` = your BotFather token.
   (The other settings have sensible defaults; add `THRESHOLD`, `COIN_ID`, etc. to override.)
5. Deploy. Watch the **Logs** tab for `Bot started.` — then send `/start` in Telegram.

### Option B — Any Docker host (Fly.io, Koyeb, a VPS…)

```bash
docker build -t btc-price-bot .
docker run -d --restart=always \
  -e BOT_TOKEN=your-token-here \
  -v btc_state:/data \
  btc-price-bot
```

The `-v btc_state:/data` volume keeps your subscriber list across restarts.

### Option C — Render

Use the included `render.yaml` (New → Blueprint). Note Render runs bots as a
**background worker**, which is on a paid plan.

> **Note on persistence:** the bot stores subscribers in `state.json`. On hosts
> with an ephemeral filesystem (Railway, Render without a disk) this resets on
> redeploy, so users would need to `/start` again. For Docker, the volume above
> keeps it. For a small bot this is usually fine.

## Push to GitHub

```powershell
git init
git add .
git commit -m "Bitcoin price notification bot"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

`.gitignore` already excludes `.env` and `state.json`, so your token never gets
committed.

## Track a different coin

Set `COIN_ID` in `.env` to any [CoinGecko id](https://api.coingecko.com/api/v3/coins/list)
— e.g. `ethereum`, or `bittensor` for TAO — and adjust `THRESHOLD` to suit that
coin's price range.
