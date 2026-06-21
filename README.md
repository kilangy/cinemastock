# Stock Portfolio Monitor

A lightweight Python script that checks each stock in your portfolio against its
**150-day moving average (SMA)** and sends you an alert by **Email** and/or
**Telegram** when a holding drops into the "red zone" (below its moving average).

It also reports the 50-day and 200-day MAs, a death-cross signal (50d MA below
200d MA), and the recent 10-day trend — so you get a quick at-a-glance health
check of your portfolio.

> ⚠️ **Disclaimer:** This is an automated technical-analysis helper for personal
> use. It is **not** financial advice. Always verify data on your broker platform
> before making any trading decision.

## Features

- 150-day SMA alert system with configurable period
- Status tiers: Healthy / Watch / Warning / High Alert
- 50d & 200d moving averages + death-cross detection
- 10-day trend direction and percentage change
- HTML email reports and Telegram messages
- Supports US tickers and Tel Aviv (TASE) tickers via the `.TA` suffix
- `--dry-run` and `--force` modes for testing

## Requirements

- Python 3.8+
- [`yfinance`](https://pypi.org/project/yfinance/) for price data

```bash
pip3 install -r requirements.txt
```

## Setup

### 1. Create your config from the template

```bash
cp config.example.py config.py
cp portfolio.example.txt portfolio.txt
```

### 2. Configure credentials in `config.py`

**Email (Gmail):**
1. Go to https://myaccount.google.com/apppasswords
2. Sign in, generate a 16-character **App Password** (regular passwords won't work).
3. Paste it into `EMAIL_PASSWORD` and set `EMAIL_SENDER` to your Gmail address.

**Telegram:**
1. Message **@BotFather** on Telegram, send `/newbot`, follow the prompts.
2. Copy the bot token into `TELEGRAM_BOT_TOKEN`.
3. Send any message to your new bot, then visit
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` and copy the
   `"chat":{"id":...}` value into `TELEGRAM_CHAT_ID`.

Set `EMAIL_ENABLED` / `TELEGRAM_ENABLED` to `False` for any channel you don't want.

### 3. Add your holdings to `portfolio.txt`

One stock per line:

```
TICKER | Display Name | Quantity
```

Examples:

```
AAPL     | Apple Inc      | 50      # US stock
SPY      | S&P 500 ETF    | 100     # US ETF
NVMI.TA  | Nova Ltd       | 15      # Tel Aviv (TASE) — note the .TA suffix
```

Lines starting with `#` are comments.

## Usage

```bash
python3 stock_monitor.py            # Analyze and send alerts only if stocks are below their MA
python3 stock_monitor.py --dry-run  # Analyze and print results, send nothing
python3 stock_monitor.py --force    # Send a full report regardless of alert status
```

## Configuration options (`config.py`)

| Setting | Default | What it does |
|---------|---------|--------------|
| `MA_PERIOD` | 150 | Moving-average period in days (try 100 or 200) |
| `ALERT_THRESHOLD` | 0 | Only alert if a stock is this % or more below its MA |
| `DATA_LOOKBACK_DAYS` | 250 | Calendar days of history to fetch |

## Scheduling (run it daily)

### macOS / Linux — cron

```bash
crontab -e
```

Add a line to run every weekday at 7:00 AM:

```
0 7 * * 1-5 cd /path/to/stock_monitor && /usr/bin/python3 stock_monitor.py >> monitor.log 2>&1
```

### macOS — launchd

See [`SETUP_GUIDE.md`](SETUP_GUIDE.md) for a ready-to-use `launchd` plist and
more detailed platform notes.

## Troubleshooting

- **"yfinance not installed"** → `pip3 install -r requirements.txt`
- **Email fails** → You need a Gmail **App Password**, not your normal password.
- **Telegram fails** → Send at least one message to your bot first; bots can't initiate chats.
- **TASE stock not found** → Verify the ticker on Yahoo Finance and confirm the `.TA` suffix.

## License

Released under the [MIT License](LICENSE).
