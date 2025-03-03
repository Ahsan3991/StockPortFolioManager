import requests
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load API key from environment variables
API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")

def initialize_exchange_rates_table():
    """Create the exchange_rates table if it doesn't exist."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS exchange_rates (
            base_currency TEXT,
            target_currency TEXT,
            rate REAL,
            last_updated TEXT,
            PRIMARY KEY (base_currency, target_currency)
        )''')
        conn.commit()
    finally:
        conn.close()

def fetch_usd_to_pkr_rate():
    """Fetch the latest USD to PKR exchange rate and store it in a variable."""
    print("\n=== FETCHING USD TO PKR EXCHANGE RATE ===")
    
    if not API_KEY:
        print("❌ Exchange Rate API key is missing. Using cached rate if available.")
        return get_cached_rate("USD", "PKR")
    
    url = f"https://v6.exchangerate-api.com/v6/{API_KEY}/pair/USD/PKR"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("result") == "success":
            rate = data.get("conversion_rate")
            print(f"✅ Successfully fetched USD to PKR exchange rate: {rate}")
            store_exchange_rate("USD", "PKR", rate)
            return rate
        else:
            print(f"❌ API Error: {data}")
            return get_cached_rate("USD", "PKR")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch exchange rate: {e}")
        return get_cached_rate("USD", "PKR")

def store_exchange_rate(base_currency, target_currency, rate):
    """Store a specific exchange rate in the database."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    try:
        initialize_exchange_rates_table()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO exchange_rates (base_currency, target_currency, rate, last_updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(base_currency, target_currency)
            DO UPDATE SET rate=excluded.rate, last_updated=excluded.last_updated
        ''', (base_currency, target_currency, rate, timestamp))
        conn.commit()
    finally:
        conn.close()

def get_cached_rate(base_currency, target_currency):
    """Get cached exchange rate from the database."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT rate FROM exchange_rates
            WHERE base_currency = ? AND target_currency = ?
        ''', (base_currency, target_currency))
        result = cursor.fetchone()
        
        if result:
            print(f"⚠️ Using cached rate for {base_currency} to {target_currency}: {result[0]}")
            return result[0]
        
        # Fallback rates
        fallbacks = {"USD_PKR": 278.50}
        return fallbacks.get(f"{base_currency}_{target_currency}")
    finally:
        conn.close()

def convert_currency(amount, from_currency, to_currency):
    """Convert an amount from one currency to another using stored exchange rates."""
    if from_currency == to_currency:
        return amount

    # Get exchange rate from the database or fetch if not available
    exchange_rate = get_cached_rate(from_currency, to_currency)

    if exchange_rate is None:
        print(f"❌ Exchange rate not available for {from_currency} to {to_currency}.")
        return None

    return round(amount * exchange_rate, 2)
