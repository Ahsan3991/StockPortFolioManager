#real time stock prices
import requests
import sqlite3
from datetime import datetime

API_KEY = "67b64ca5b01ac7.83846801"  # Replace with your actual EODHD API key

def get_daily_api_calls():
    """Get the number of API calls made today."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_calls (
                date TEXT PRIMARY KEY,
                calls INTEGER DEFAULT 0
            )
        """)
        today = datetime.today().strftime('%Y-%m-%d')
        cursor.execute("SELECT calls FROM api_calls WHERE date = ?", (today,))
        result = cursor.fetchone()
        if result:
            return result[0]
        cursor.execute("INSERT INTO api_calls (date, calls) VALUES (?, 0)", (today,))
        conn.commit()
        return 0
    finally:
        conn.close()

def increment_api_calls():
    """Increment the API call counter for today."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    try:
        today = datetime.today().strftime('%Y-%m-%d')
        cursor.execute("""
            INSERT INTO api_calls (date, calls) 
            VALUES (?, 1)
            ON CONFLICT(date) DO UPDATE SET calls = calls + 1
        """, (today,))
        conn.commit()
    finally:
        conn.close()

def migrate_stock_prices_buffer():
    """Ensure `buffer_price` column exists in `stock_prices` table."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(stock_prices)")
        columns = {col[1] for col in cursor.fetchall()}
        if 'buffer_price' not in columns:
            cursor.execute("ALTER TABLE stock_prices ADD COLUMN buffer_price REAL")
        conn.commit()
    finally:
        conn.close()

def get_psx_stock_price(stock_symbol):
    """
    Fetches previous close price with graceful fallback:
    1. Try API if daily limit not reached
    2. Use today's cached price if available
    3. Use previous day's price from buffer
    4. Return None if all attempts fail
    """
    stock_symbol = stock_symbol.upper().strip()
    if not stock_symbol.endswith(".KAR"):
        stock_symbol += ".KAR"
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                stock TEXT PRIMARY KEY,
                previous_close REAL,
                last_updated TEXT,
                last_attempt_time TEXT,
                buffer_price REAL
            )
        """)
        today_date = datetime.today().strftime('%Y-%m-%d')
        cursor.execute("SELECT previous_close, last_updated, buffer_price FROM stock_prices WHERE stock = ?", (stock_symbol,))
        result = cursor.fetchone()
        cached_price, last_updated, buffer_price = (result or (None, None, None))
        if last_updated == today_date:
            return cached_price
        if get_daily_api_calls() >= 10:
            return cached_price or buffer_price
        try:
            url = f"https://eodhd.com/api/real-time/{stock_symbol}"
            params = {"api_token": API_KEY, "fmt": "json"}
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            increment_api_calls()
            if "previousClose" in data and data["previousClose"] not in ["NA", None]:
                previous_close = round(float(data["previousClose"]), 2)
                cursor.execute("""
                    INSERT INTO stock_prices (stock, previous_close, buffer_price, last_updated, last_attempt_time)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(stock) DO UPDATE SET 
                        buffer_price = previous_close,
                        previous_close = excluded.previous_close,
                        last_updated = excluded.last_updated,
                        last_attempt_time = excluded.last_attempt_time
                """, (stock_symbol, previous_close, cached_price, today_date, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                return previous_close
        except requests.RequestException:
            pass
        return cached_price or buffer_price
    finally:
        conn.close()

migrate_stock_prices_buffer()
