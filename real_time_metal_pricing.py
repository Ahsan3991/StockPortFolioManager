#real_time_metal_pricing
import requests
import sqlite3
from datetime import datetime

API_KEY = "goldapi-2jph417m7lspbqz-io"  # Replace with your actual GoldAPI key

def fetch_metal_prices():
    """Fetch real-time metal prices and store them in the database."""
    metals = ["XAU", "XAG", "XPT", "XPD"]  # Gold, Silver, Platinum, Palladium
    currency = "USD"
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    
    try:
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
            last_updated TEXT
        )''')
        
        for metal in metals:
            url = f"https://www.goldapi.io/api/{metal}/{currency}"
            headers = {
                "x-access-token": API_KEY,
                "Content-Type": "application/json"
            }
            
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if "price_gram_24k" in data:
                    cursor.execute('''INSERT INTO metal_prices (metal, price_gram_24k, price_gram_22k, price_gram_21k,
                                    price_gram_20k, price_gram_18k, price_gram_16k, price_gram_14k, price_gram_10k, last_updated)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
                                    ON CONFLICT(metal) DO UPDATE SET 
                                    price_gram_24k=excluded.price_gram_24k,
                                    price_gram_22k=excluded.price_gram_22k,
                                    price_gram_21k=excluded.price_gram_21k,
                                    price_gram_20k=excluded.price_gram_20k,
                                    price_gram_18k=excluded.price_gram_18k,
                                    price_gram_16k=excluded.price_gram_16k,
                                    price_gram_14k=excluded.price_gram_14k,
                                    price_gram_10k=excluded.price_gram_10k,
                                    last_updated=excluded.last_updated''',
                                    (metal, data["price_gram_24k"], data["price_gram_22k"], data["price_gram_21k"],
                                     data["price_gram_20k"], data["price_gram_18k"], data["price_gram_16k"],
                                     data["price_gram_14k"], data["price_gram_10k"], datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    
                    conn.commit()
            except requests.exceptions.RequestException as e:
                print(f"Failed to fetch {metal} price: {e}")
    
    finally:
        conn.close()

def get_latest_metal_prices():
    """Retrieve the latest stored metal prices from the database."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM metal_prices")
    metals = cursor.fetchall()
    conn.close()
    
    metal_prices = {metal[0]: {
        "price_gram_24k": metal[1],
        "price_gram_22k": metal[2],
        "price_gram_21k": metal[3],
        "price_gram_20k": metal[4],
        "price_gram_18k": metal[5],
        "price_gram_16k": metal[6],
        "price_gram_14k": metal[7],
        "price_gram_10k": metal[8],
        "last_updated": metal[9]
    } for metal in metals}
    
    return metal_prices
