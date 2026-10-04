# Alpha Bot - paper-trading alert engine (free, ~20 min setup)

**What it does:** every 30 min on weekdays it scans your watchlist (Stage 1 India equity/ETFs, Stage 2 crypto,
Stage 3 commodities/global indices), sends ENTER / EXIT alerts to Telegram, logs the trades you report, compares
predicted vs actual return, and updates a live dashboard. Fake money only. You place every order yourself.

**What it is not:** a predictor of "100% accuracy". It runs one simple, testable rule (buy pullbacks inside an uptrend,
stop = 2x ATR, target = 3x ATR) and shows that rule's own historical win rate with every alert. Judge it by the
30-day paper results, not by promises.

## Setup
1. **Telegram bot.** In Telegram open @BotFather -> `/newbot` -> copy the token. Send any message to your new bot.
   Then open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy `"chat":{"id": NUMBER}`.
2. **GitHub.** Create a free account and a new repository (public, so the free Pages dashboard works). Upload all
   files from this folder (keep the folder structure, including `.github/workflows/scan.yml`).
3. **Secrets.** Repo -> Settings -> Secrets and variables -> Actions -> New secret:
   `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. (Secrets are never shown publicly.)
4. **Dashboard.** Repo -> Settings -> Pages -> Source: "Deploy from a branch" -> `main` / `/docs`.
5. **First run.** Repo -> Actions -> "scan" -> Run workflow. Check the Actions log, your Telegram, and the Pages URL.

## Using it
- Alert arrives -> you decide -> place a *paper* order in any demo app/TradingView paper account.
- Tell the bot: `bought ITC.NS 412.5 10` (symbol, price, qty). Later: `sold ITC.NS 430`.
  Replies are read on the next scan (up to 30 min later).
- Edit `config.yaml` to change symbols, paper size, rule thresholds, or switch stages on/off.
- Run `python run.py backtest` on any computer to see the rule's multi-year history per symbol.

## Known limits (be aware)
- Data is yfinance (free, unofficial, delayed). Fine for daily-bar rules, NOT for tick/intraday/options.
  Stage 4 (options/intraday) is switched off until Stages 1-3 prove anything. Reliable live options data is not free.
- GitHub's scheduler can run several minutes late, and your `bought/sold` replies are processed per scan.
- Backtests ignore costs, taxes and slippage. Treat them as a filter, not a promise.
- Dashboard shows STALE if no heartbeat for 3x the interval, so a silent failure is visible.
