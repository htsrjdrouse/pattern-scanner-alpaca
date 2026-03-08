import json
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import pytz
import yfinance as yf
import pandas_ta as ta

TRACKED_FILE = '/app/data/tracked_stocks.json'
EMAIL_FROM = 'your-email@gmail.com'  # Replace with your Gmail
EMAIL_PASS = 'your-app-password'  # Replace with Gmail app password

def load_tracked_stocks():
    if os.path.exists(TRACKED_FILE):
        with open(TRACKED_FILE, 'r') as f:
            return json.load(f)
    return []

def save_tracked_stocks(stocks):
    os.makedirs(os.path.dirname(TRACKED_FILE), exist_ok=True)
    with open(TRACKED_FILE, 'w') as f:
        json.dump(stocks, f, indent=2, default=str)

def is_market_hours():
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    return now.weekday() < 5 and 9.5 <= now.hour + now.minute / 60 <= 16

def send_email(to, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM
    msg['To'] = to

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASS)
        server.sendmail(EMAIL_FROM, to, msg.as_string())

def main():
    if not is_market_hours():
        print("Outside market hours, skipping.")
        return

    stocks = load_tracked_stocks()
    updated = False

    for stock in stocks:
        if stock['notified']:
            continue

        try:
            ticker = yf.Ticker(stock['ticker'])
            hist = ticker.history(period='60d')
            if hist.empty:
                continue

            current_price = hist['Close'].iloc[-1]
            rsi = ta.rsi(hist['Close'], length=14).iloc[-1] if len(hist) > 14 else None
            avg_volume = hist['Volume'].tail(50).mean()
            current_volume = hist['Volume'].iloc[-1]

            conditions = (
                current_price > stock['buy_point'] and
                stock['rsi_min'] <= rsi <= stock['rsi_max'] and
                current_volume >= avg_volume * stock['volume_multiple']
            )

            if conditions:
                subject = f"Breakout Alert: {stock['ticker']}"
                body = f"""
Stock: {stock['ticker']}
Buy Point: ${stock['buy_point']}
Current Price: ${current_price:.2f}
RSI: {rsi:.1f} (range {stock['rsi_min']}-{stock['rsi_max']})
Volume: {int(current_volume)} (avg {int(avg_volume)} * {stock['volume_multiple']} = {int(avg_volume * stock['volume_multiple'])})
                """.strip()
                send_email(stock['email'], subject, body)
                stock['notified'] = True
                updated = True
                print(f"Alert sent for {stock['ticker']}")

        except Exception as e:
            print(f"Error checking {stock['ticker']}: {e}")

    if updated:
        save_tracked_stocks(stocks)

if __name__ == '__main__':
    main()