# ============================================================
# CONFIGURATION TEMPLATE
# Copy this file to "config.py" and fill in your own values.
#   cp config.example.py config.py
# config.py is git-ignored so your secrets never get committed.
# ============================================================

# --- Email Settings (Gmail recommended) ---
# To use Gmail, enable 2FA and create an App Password:
# https://myaccount.google.com/apppasswords
EMAIL_ENABLED = True
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "you@example.com"                 # Your Gmail address
EMAIL_PASSWORD = "YOUR_16_CHAR_APP_PASSWORD"     # Gmail App Password (NOT your login password)
EMAIL_RECIPIENTS = ["you@example.com"]           # Who receives alerts

# --- Telegram Settings ---
# 1. Message @BotFather on Telegram, send /newbot, follow steps
# 2. Copy the bot token
# 3. Send any message to your bot, then visit:
#    https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
#    to find your chat_id
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# --- Analysis Settings ---
MA_PERIOD = 150           # Moving average period (days)
DATA_LOOKBACK_DAYS = 250  # How many calendar days to fetch (buffer for trading days)
ALERT_THRESHOLD = 0       # Alert when stock is this % or more below MA (0 = any amount below)

# --- Portfolio File ---
PORTFOLIO_FILE = "portfolio.txt"  # Path relative to this script
