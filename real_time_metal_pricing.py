import requests
import sqlite3
from datetime import datetime
import os
from dotenv import load_dotenv
from currency_conversion import fetch_usd_to_pkr_rate  # Import exchange rate function
from currency_conversion import fetch_usd_to_pkr_rate, convert_currency


# Load environment variables
load_dotenv()

# Retrieve API key from .env file
API_KEY = os.getenv("GOLDAPI_KEY")

def fetch_metal_prices():
    """Fetch real-time metal prices, convert to PKR, and store them in the database."""
    metals = ["XAU", "XAG", "XPT", "XPD"]  # Gold, Silver, Platinum, Palladium
    currency = "USD"
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    
    try:
        # Ensure the metal_prices table exists with the required columns
        cursor.execute("PRAGMA table_info(metal_prices)")
        columns = {col[1] for col in cursor.fetchall()}
        
        if not columns:
            cursor.execute('''CREATE TABLE IF NOT EXISTS metal_prices (
                metal TEXT PRIMARY KEY,
                price_gram_24k REAL,
                price_gram_22k REAL,
                price_gram_21k REAL,
                price_gram_20k REAL,
                price_gram_18k REAL,
                price_gram_16k REAL,
                price_gram_14k REAL,
                price_gram_10k REAL,
                price_usd_gram_24k REAL,
                last_updated TEXT
            )''')
        elif 'price_usd_gram_24k' not in columns:
            cursor.execute("ALTER TABLE metal_prices ADD COLUMN price_usd_gram_24k REAL")
        
        conn.commit()

        # Fetch the latest USD to PKR exchange rate
        usd_to_pkr_rate = fetch_usd_to_pkr_rate()
        if usd_to_pkr_rate is None:
            print("❌ Failed to fetch USD to PKR rate. Using cached rate if available.")
            usd_to_pkr_rate = 278.50  # Fallback rate

        for metal in metals:
            url = f"https://www.goldapi.io/api/{metal}/{currency}"
            headers = {
                "x-access-token": API_KEY,
                "Content-Type": "application/json"
            }
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                # Debug: Print the raw response from GoldAPI before conversion
                print(f"🔍 Raw API Response for {metal}: {data}")

                if "price_gram_24k" in data:
                    # Store original USD price
                    price_usd_24k = data["price_gram_24k"]
                    
                    # Convert all prices from USD to PKR
                    price_pkr_24k = round(price_usd_24k * usd_to_pkr_rate, 2)
                    price_pkr_22k = round(data["price_gram_22k"] * usd_to_pkr_rate, 2)
                    price_pkr_21k = round(data["price_gram_21k"] * usd_to_pkr_rate, 2)
                    price_pkr_20k = round(data["price_gram_20k"] * usd_to_pkr_rate, 2)
                    price_pkr_18k = round(data["price_gram_18k"] * usd_to_pkr_rate, 2)
                    price_pkr_16k = round(data["price_gram_16k"] * usd_to_pkr_rate, 2)
                    price_pkr_14k = round(data["price_gram_14k"] * usd_to_pkr_rate, 2)
                    price_pkr_10k = round(data["price_gram_10k"] * usd_to_pkr_rate, 2)
                    
                    if None in [price_pkr_24k, price_pkr_22k, price_pkr_21k, price_pkr_20k, 
                            price_pkr_18k, price_pkr_16k, price_pkr_14k, price_pkr_10k]:
                        print(f"⚠️ Failed to convert {metal} prices to PKR. Skipping update.")
                        continue
                    
                    cursor.execute('''INSERT INTO metal_prices (
                        metal, price_gram_24k, price_gram_22k, price_gram_21k,
                        price_gram_20k, price_gram_18k, price_gram_16k, price_gram_14k, 
                        price_gram_10k, price_usd_gram_24k, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(metal) DO UPDATE SET
                        price_gram_24k=excluded.price_gram_24k,
                        price_gram_22k=excluded.price_gram_22k,
                        price_gram_21k=excluded.price_gram_21k,
                        price_gram_20k=excluded.price_gram_20k,
                        price_gram_18k=excluded.price_gram_18k,
                        price_gram_16k=excluded.price_gram_16k,
                        price_gram_14k=excluded.price_gram_14k,
                        price_gram_10k=excluded.price_gram_10k,
                        price_usd_gram_24k=excluded.price_usd_gram_24k,
                        last_updated=excluded.last_updated''',
                        (metal, price_pkr_24k, price_pkr_22k, price_pkr_21k,
                        price_pkr_20k, price_pkr_18k, price_pkr_16k,
                        price_pkr_14k, price_pkr_10k, price_usd_24k, 
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    
                    conn.commit()
                    print(f"✅ Updated {metal} prices: ${price_usd_24k} USD = {price_pkr_24k} PKR per gram (24k)")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Failed to fetch {metal} price: {e}")
                
    finally:
        conn.close()

def get_latest_metal_prices():
    """Retrieve the latest stored metal prices from the database (already in PKR)."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(metal_prices)")
        columns = {row[1]: idx for idx, row in enumerate(cursor.fetchall())}
        
        if not columns:
            print("❌ No metal price data found in database.")
            return {}
            
        cursor.execute("SELECT * FROM metal_prices")
        metals = cursor.fetchall()
        
        metal_prices = {}
        for metal in metals:
            metal_code = metal[columns['metal']]
            
            metal_data = {
                "price_gram_24k": metal[columns['price_gram_24k']],
                "price_gram_22k": metal[columns['price_gram_22k']],
                "price_gram_21k": metal[columns['price_gram_21k']],
                "price_gram_20k": metal[columns['price_gram_20k']],
                "price_gram_18k": metal[columns['price_gram_18k']],
                "price_gram_16k": metal[columns['price_gram_16k']],
                "price_gram_14k": metal[columns['price_gram_14k']],
                "price_gram_10k": metal[columns['price_gram_10k']],
                "last_updated": metal[columns['last_updated']],
                "currency": "PKR"
            }
            
            if 'price_usd_gram_24k' in columns:
                metal_data["price_usd_gram_24k"] = metal[columns['price_usd_gram_24k']]
            
            metal_prices[metal_code] = metal_data

       # print(f"🔍 Retrieved Metal Prices from DB: {metal_prices}")
            
        return metal_prices
    except Exception as e:
        print(f"❌ Error retrieving metal prices: {e}")
        return {}
    finally:
        conn.close()


def get_metal_price_in_currency(metal_code, karats=24, currency="PKR"):
    """
    Get the price of a specific metal in the desired currency.
    If currency is USD and we have the original price, return that.
    Otherwise, convert from PKR to the desired currency.
    """
    metal_prices = get_latest_metal_prices()
    
    if metal_code not in metal_prices:
        print(f"No data available for {metal_code}")
        return None
    
    karat_key = f"price_gram_{karats}k"
    if karat_key not in metal_prices[metal_code]:
        print(f"No {karats}k data available for {metal_code}")
        return None
    
    # Default: return price in PKR
    if currency == "PKR":
        return metal_prices[metal_code][karat_key]
    
    # If USD is requested and we have the original USD price
    if currency == "USD" and karats == 24 and "price_usd_gram_24k" in metal_prices[metal_code]:
        return metal_prices[metal_code]["price_usd_gram_24k"]
    
    # For other currencies or karats, convert from PKR
    return convert_currency(
        metal_prices[metal_code][karat_key], 
        from_currency="PKR", 
        to_currency=currency
    )

if __name__ == "__main__":
    fetch_metal_prices()
