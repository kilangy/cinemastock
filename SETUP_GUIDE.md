# Stock Portfolio Monitor — Setup Guide (Mac)

## Quick Start (5 minutes)

### Step 1: Install Python dependency

Open Terminal and run:

```bash
pip3 install yfinance
```

### Step 2: Configure your credentials

Open `config.py` and fill in your details:

#### Email (Gmail)
1. Go to https://myaccount.google.com/apppasswords
2. Sign in, select "Mail" → "Mac" → Generate
3. Copy the 16-character app password
4. Paste it into `config.py` as `EMAIL_PASSWORD`
5. Set `EMAIL_SENDER` to your Gmail address

#### Telegram
1. Open Telegram, search for **@BotFather**
2. Send `/newbot`, follow the prompts to name your bot
3. Copy the bot token → paste into `TELEGRAM_BOT_TOKEN`
4. Send any message to your new bot
5. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
6. Find `"chat":{"id":123456789}` → paste that number into `TELEGRAM_CHAT_ID`

### Step 3: Test it

```bash
cd /path/to/stock_monitor
python3 stock_monitor.py --dry-run
```

This runs the analysis and prints results without sending alerts.

To send a full report (even if no alerts):

```bash
python3 stock_monitor.py --force
```

### Step 4: Schedule it to run daily

#### Option A: Using cron (simple)

Open Terminal and run:

```bash
crontab -e
```

Add this line to run every weekday at 7:00 AM (before US market opens):

```
0 7 * * 1-5 cd /path/to/stock_monitor && /usr/bin/python3 stock_monitor.py >> monitor.log 2>&1
```

Replace `/path/to/stock_monitor` with the actual folder path.

Save and exit. Verify with:

```bash
crontab -l
```

#### Option B: Using launchd (more Mac-native)

Create the file `~/Library/LaunchAgents/com.stockmonitor.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.stockmonitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/stock_monitor/stock_monitor.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/stock_monitor</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/path/to/stock_monitor/monitor.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/stock_monitor/monitor_error.log</string>
</dict>
</plist>
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.stockmonitor.plist
```

---

## Updating Your Portfolio

Edit `portfolio.txt` — one stock per line:

```
TICKER | Display Name | Quantity
```

Examples:
- US stock: `AAPL     | Apple Inc            | 50`
- TASE stock: `NVMI.TA  | Nova Ltd             | 15`
- US ETF: `SPY      | S&P 500 ETF          | 100`

Lines starting with `#` are comments (ignored).

---

## Customization

In `config.py` you can adjust:

| Setting | Default | What it does |
|---------|---------|--------------|
| `MA_PERIOD` | 150 | Moving average period (try 100 or 200) |
| `ALERT_THRESHOLD` | 0 | Only alert if stock is this % below MA |
| `DATA_LOOKBACK_DAYS` | 250 | Calendar days of history to fetch |

---

## Command Reference

| Command | What it does |
|---------|-------------|
| `python3 stock_monitor.py` | Run and send alerts only if stocks are in red zone |
| `python3 stock_monitor.py --dry-run` | Analyze only, don't send any notifications |
| `python3 stock_monitor.py --force` | Send full report regardless of alert status |

---

## Troubleshooting

**"yfinance not installed"** → Run `pip3 install yfinance`

**Email fails** → Check your Gmail App Password. Regular passwords won't work — you need an App Password.

**Telegram fails** → Make sure you sent at least one message to your bot before running the script. The bot can't initiate conversations.

**TASE stock not found** → Verify the ticker on Yahoo Finance (search for the company, check the .TA suffix).

**Cron not running** → On Mac, grant Terminal "Full Disk Access" in System Preferences → Privacy & Security.
