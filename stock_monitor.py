#!/usr/bin/env python3
"""
Stock Portfolio Monitor — 150-Day Moving Average Alert System
Checks each stock against its 150-day SMA and sends alerts
via Email and/or Telegram when stocks enter the red zone.

Usage:
    python3 stock_monitor.py              # Run analysis and send alerts
    python3 stock_monitor.py --dry-run    # Run analysis, print results, don't send alerts
    python3 stock_monitor.py --force      # Send report even if no alerts
"""

import sys
import os
import smtplib
import urllib.request
import urllib.parse
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path

# Add script directory to path so config can be found
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
import config

# ---------------------------------------------------------------------------
# Portfolio loader
# ---------------------------------------------------------------------------
def load_portfolio(filepath):
    """Read portfolio.txt and return list of (ticker, name, quantity)."""
    holdings = []
    path = Path(filepath)
    if not path.is_absolute():
        path = SCRIPT_DIR / path
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2:
                ticker = parts[0]
                name = parts[1]
                qty = float(parts[2]) if len(parts) >= 3 else 0
                holdings.append((ticker, name, qty))
    return holdings


# ---------------------------------------------------------------------------
# Price data fetcher (using yfinance)
# ---------------------------------------------------------------------------
def fetch_stock_data(ticker, days=250):
    """Fetch historical price data using yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. Run: pip3 install yfinance")
        sys.exit(1)

    end = datetime.now()
    start = end - timedelta(days=days)
    stock = yf.Ticker(ticker)
    hist = stock.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
    return hist


# ---------------------------------------------------------------------------
# Technical analysis
# ---------------------------------------------------------------------------
def analyze_stock(ticker, name, qty):
    """Analyze a single stock and return a result dict."""
    result = {
        "ticker": ticker,
        "name": name,
        "qty": qty,
        "status": "OK",
        "error": None,
    }

    try:
        hist = fetch_stock_data(ticker, config.DATA_LOOKBACK_DAYS)

        # Drop rows with no closing price (yfinance can return NaN for the
        # latest row before the market closes / settles), which would otherwise
        # poison the current price and all MA/percentage calculations (nan%).
        if hist is not None and "Close" in hist:
            hist = hist[hist["Close"].notna()]

        if hist is None or len(hist) < 20:
            result["status"] = "ERROR"
            result["error"] = f"Insufficient data ({0 if hist is None else len(hist)} days)"
            return result

        current_price = hist["Close"].iloc[-1]
        result["current_price"] = round(current_price, 2)

        # Moving averages
        ma_period = config.MA_PERIOD
        if len(hist) >= ma_period:
            ma150 = hist["Close"].tail(ma_period).mean()
        else:
            ma150 = hist["Close"].mean()
            result["ma_note"] = f"Only {len(hist)} days available, using full average"

        result["ma150"] = round(ma150, 2)
        result["pct_from_ma"] = round(((current_price - ma150) / ma150) * 100, 2)
        result["above_ma"] = current_price > ma150

        # 50-day MA
        if len(hist) >= 50:
            result["ma50"] = round(hist["Close"].tail(50).mean(), 2)
        # 200-day MA
        if len(hist) >= 200:
            result["ma200"] = round(hist["Close"].tail(200).mean(), 2)

        # Recent trend (10-day)
        if len(hist) >= 10:
            recent = hist["Close"].tail(10)
            result["trend_10d"] = "Declining" if recent.iloc[-1] < recent.iloc[0] else "Rising"
            result["change_10d"] = round(((recent.iloc[-1] - recent.iloc[0]) / recent.iloc[0]) * 100, 2)

        # Death cross check: 50d MA < 200d MA
        if "ma50" in result and "ma200" in result:
            result["death_cross"] = result["ma50"] < result["ma200"]

        # Determine alert level
        if not result["above_ma"]:
            if result.get("trend_10d") == "Declining":
                result["status"] = "HIGH_ALERT"
            else:
                result["status"] = "WARNING"
        elif result.get("pct_from_ma", 0) < 3 and result.get("trend_10d") == "Declining":
            result["status"] = "WATCH"

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)

    return result


# ---------------------------------------------------------------------------
# Alert formatting
# ---------------------------------------------------------------------------
def format_email_report(results, timestamp):
    """Build HTML email body."""
    alerts = [r for r in results if r["status"] in ("HIGH_ALERT", "WARNING")]
    watches = [r for r in results if r["status"] == "WATCH"]
    healthy = [r for r in results if r["status"] == "OK"]
    errors = [r for r in results if r["status"] == "ERROR"]

    html = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
    <h2 style="color: #1F4E79;">Portfolio Monitor — {config.MA_PERIOD}-Day MA Report</h2>
    <p style="color: #666;">Generated: {timestamp}</p>
    """

    if alerts:
        html += '<h3 style="color: #CC0000; background: #FFE0E0; padding: 10px; border-radius: 5px;">STOP-LOSS ALERT — Action Required</h3>'
        html += '<table style="border-collapse: collapse; width: 100%;">'
        html += '<tr style="background: #8B0000; color: white;"><th style="padding: 8px;">Stock</th><th>Price</th><th>{0}d MA</th><th>% Gap</th><th>10d Trend</th><th>Signal</th></tr>'.format(config.MA_PERIOD)
        for r in alerts:
            color = "#CC0000" if r["status"] == "HIGH_ALERT" else "#CC6600"
            bg = "#FFE0E0" if r["status"] == "HIGH_ALERT" else "#FFF3E0"
            death = " DEATH CROSS" if r.get("death_cross") else ""
            html += f'<tr style="background: {bg};"><td style="padding: 6px; border: 1px solid #ddd;"><b>{r["name"]}</b> ({r["ticker"]})</td>'
            html += f'<td style="border: 1px solid #ddd; text-align: right; color: {color};">${r.get("current_price", "N/A")}</td>'
            html += f'<td style="border: 1px solid #ddd; text-align: right;">${r.get("ma150", "N/A")}</td>'
            html += f'<td style="border: 1px solid #ddd; text-align: right; color: {color}; font-weight: bold;">{r.get("pct_from_ma", "N/A")}%</td>'
            html += f'<td style="border: 1px solid #ddd; text-align: center;">{r.get("trend_10d", "N/A")}</td>'
            html += f'<td style="border: 1px solid #ddd; text-align: center; color: {color}; font-weight: bold;">{r["status"]}{death}</td></tr>'
        html += '</table>'

    if watches:
        html += '<h3 style="color: #996600;">WATCH LIST — Monitor Closely</h3>'
        html += '<table style="border-collapse: collapse; width: 100%;"><tr style="background: #FFD93D;"><th style="padding: 8px;">Stock</th><th>Price</th><th>{0}d MA</th><th>% Gap</th><th>10d Trend</th></tr>'.format(config.MA_PERIOD)
        for r in watches:
            html += f'<tr style="background: #FFFDE0;"><td style="padding: 6px; border: 1px solid #ddd;">{r["name"]} ({r["ticker"]})</td>'
            html += f'<td style="border: 1px solid #ddd; text-align: right;">${r.get("current_price", "N/A")}</td>'
            html += f'<td style="border: 1px solid #ddd; text-align: right;">${r.get("ma150", "N/A")}</td>'
            html += f'<td style="border: 1px solid #ddd; text-align: right;">{r.get("pct_from_ma", "N/A")}%</td>'
            html += f'<td style="border: 1px solid #ddd; text-align: center;">{r.get("trend_10d", "N/A")}</td></tr>'
        html += '</table>'

    if healthy:
        html += '<h3 style="color: #006600;">HEALTHY — Above {0}-Day MA</h3>'.format(config.MA_PERIOD)
        html += '<table style="border-collapse: collapse; width: 100%;"><tr style="background: #6BCB77; color: white;"><th style="padding: 8px;">Stock</th><th>Price</th><th>{0}d MA</th><th>% Above</th><th>10d Trend</th></tr>'.format(config.MA_PERIOD)
        for r in healthy:
            html += f'<tr><td style="padding: 6px; border: 1px solid #ddd;">{r["name"]} ({r["ticker"]})</td>'
            html += f'<td style="border: 1px solid #ddd; text-align: right;">${r.get("current_price", "N/A")}</td>'
            html += f'<td style="border: 1px solid #ddd; text-align: right;">${r.get("ma150", "N/A")}</td>'
            html += f'<td style="border: 1px solid #ddd; text-align: right; color: #006600;">+{r.get("pct_from_ma", "N/A")}%</td>'
            html += f'<td style="border: 1px solid #ddd; text-align: center;">{r.get("trend_10d", "N/A")}</td></tr>'
        html += '</table>'

    if errors:
        html += '<h3 style="color: #999;">Errors</h3><ul>'
        for r in errors:
            html += f'<li>{r["name"]} ({r["ticker"]}): {r.get("error", "Unknown error")}</li>'
        html += '</ul>'

    html += '<p style="color: #999; font-size: 11px; margin-top: 20px;">This is an automated analysis. Verify data on your broker platform before making trading decisions.</p>'
    html += '</body></html>'
    return html


def format_telegram_message(results, timestamp):
    """Build Telegram message (plain text with emoji)."""
    alerts = [r for r in results if r["status"] in ("HIGH_ALERT", "WARNING")]
    watches = [r for r in results if r["status"] == "WATCH"]

    lines = [f"📊 *Portfolio {config.MA_PERIOD}-Day MA Report*", f"🕐 {timestamp}", ""]

    if alerts:
        lines.append("🔴 *STOP-LOSS ALERTS:*")
        for r in alerts:
            icon = "🚨" if r["status"] == "HIGH_ALERT" else "⚠️"
            death = " ☠️ DEATH CROSS" if r.get("death_cross") else ""
            lines.append(
                f"{icon} *{r['name']}* ({r['ticker']}): "
                f"${r.get('current_price', '?')} | "
                f"MA: ${r.get('ma150', '?')} | "
                f"Gap: {r.get('pct_from_ma', '?')}% | "
                f"{r.get('trend_10d', '?')}{death}"
            )
        lines.append("")

    if watches:
        lines.append("🟡 *WATCH LIST:*")
        for r in watches:
            lines.append(
                f"👀 *{r['name']}* ({r['ticker']}): "
                f"${r.get('current_price', '?')} | "
                f"Gap: {r.get('pct_from_ma', '?')}%"
            )
        lines.append("")

    ok_count = len([r for r in results if r["status"] == "OK"])
    lines.append(f"🟢 {ok_count} stocks healthy (above {config.MA_PERIOD}d MA)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Alert senders
# ---------------------------------------------------------------------------
def send_email(subject, html_body):
    """Send HTML email via SMTP."""
    if not config.EMAIL_ENABLED:
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_SENDER
    msg["To"] = ", ".join(config.EMAIL_RECIPIENTS)
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"  ✅ Email sent to {', '.join(config.EMAIL_RECIPIENTS)}")
    except Exception as e:
        print(f"  ❌ Email failed: {e}")


def send_telegram(message):
    """Send message via Telegram Bot API."""
    if not config.TELEGRAM_ENABLED:
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }).encode()

    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                print(f"  ✅ Telegram message sent to chat {config.TELEGRAM_CHAT_ID}")
            else:
                print(f"  ❌ Telegram API error: {result}")
    except Exception as e:
        print(f"  ❌ Telegram failed: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    print(f"\n{'='*60}")
    print(f"  Stock Portfolio Monitor — {config.MA_PERIOD}-Day Moving Average")
    print(f"  {timestamp}")
    print(f"{'='*60}\n")

    # Load portfolio
    holdings = load_portfolio(config.PORTFOLIO_FILE)
    print(f"📋 Loaded {len(holdings)} stocks from {config.PORTFOLIO_FILE}\n")

    # Analyze each stock
    results = []
    for ticker, name, qty in holdings:
        print(f"  Analyzing {name} ({ticker})...", end=" ", flush=True)
        result = analyze_stock(ticker, name, qty)
        status_icon = {
            "OK": "🟢", "WATCH": "🟡", "WARNING": "🟠",
            "HIGH_ALERT": "🔴", "ERROR": "❌"
        }.get(result["status"], "❓")
        extra = f" | {result.get('pct_from_ma', '?')}% from MA" if result.get("pct_from_ma") is not None else ""
        print(f"{status_icon} {result['status']}{extra}")
        results.append(result)

    # Summary
    alerts = [r for r in results if r["status"] in ("HIGH_ALERT", "WARNING")]
    watches = [r for r in results if r["status"] == "WATCH"]
    healthy = [r for r in results if r["status"] == "OK"]
    errors = [r for r in results if r["status"] == "ERROR"]

    print(f"\n{'='*60}")
    print(f"  SUMMARY: {len(alerts)} alerts | {len(watches)} watch | {len(healthy)} healthy | {len(errors)} errors")
    print(f"{'='*60}\n")

    # Send alerts
    should_send = len(alerts) > 0 or force
    if dry_run:
        print("  🔇 DRY RUN — no alerts sent\n")
        if alerts:
            print("  Would have sent alerts for:")
            for r in alerts:
                print(f"    🔴 {r['name']} ({r['ticker']}): {r.get('pct_from_ma', '?')}% from {config.MA_PERIOD}d MA")
    elif should_send:
        subject_prefix = "🚨" if alerts else "📊"
        alert_names = ", ".join(r["ticker"] for r in alerts) if alerts else "All Clear"
        subject = f"{subject_prefix} Portfolio Alert: {alert_names} below {config.MA_PERIOD}d MA" if alerts else f"📊 Portfolio Report — All Clear"

        print("  Sending alerts...")
        send_email(subject, format_email_report(results, timestamp))
        send_telegram(format_telegram_message(results, timestamp))
    else:
        print("  ✅ No alerts needed — all stocks above their moving averages.\n")
        print("  (Use --force to send a full report anyway)")


if __name__ == "__main__":
    main()
