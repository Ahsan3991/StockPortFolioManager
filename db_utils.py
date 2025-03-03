# db_utils.py
import os
import sqlite3
import streamlit as st

def get_db_path(username=None):
    """
    Get the database path for a specific user.
    Returns the path to the user-specific database file.
    """
    if not username and 'username' in st.session_state:
        username = st.session_state.username
    
    if not username:
        # Fallback to default if no username is set
        return "portfolio.db"
    
    # Create a db directory if it doesn't exist
    os.makedirs('db', exist_ok=True)
    
    # Return the user-specific database path
    return os.path.join('db', f"{username.lower()}_portfolio.db")

def get_db_connection(timeout=10):
    """
    Get a database connection for the current user.
    Returns a connection to the user-specific database.
    
    Args:
        timeout (int, optional): Connection timeout in seconds. Defaults to 10.
    """
    db_path = get_db_path()
    return sqlite3.connect(db_path, timeout=timeout)

def initialize_user_db(username):
    """Initialize database for a specific user"""
    db_path = get_db_path(username)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create `trades` table
        cursor.execute('''CREATE TABLE IF NOT EXISTS trades (
            date TEXT,
            memo_number TEXT,
            stock TEXT,
            quantity INTEGER,
            rate REAL,
            comm_amount REAL,
            cdc_charges REAL,
            sales_tax REAL,
            total_amount REAL,
            type TEXT
        )''')
        
        # Create `memos` table
        cursor.execute('''CREATE TABLE IF NOT EXISTS memos (
            memo_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Create `warrants` table
        cursor.execute('''CREATE TABLE IF NOT EXISTS warrants (
            warrant_no TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Create `dividends` table
        cursor.execute('''CREATE TABLE IF NOT EXISTS dividends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            warrant_no TEXT,
            payment_date TEXT,
            stock_name TEXT,
            rate_per_security REAL,
            number_of_securities INTEGER,
            amount_of_dividend REAL,
            tax_deducted REAL,
            amount_paid REAL,
            FOREIGN KEY (warrant_no) REFERENCES warrants(warrant_no) ON DELETE CASCADE
        )''')
        
        # Create `sell_trades` table
        cursor.execute('''CREATE TABLE IF NOT EXISTS sell_trades (
            sell_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sell_date TEXT NOT NULL,
            stock TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            rate REAL NOT NULL CHECK (rate > 0),
            sale_amount REAL NOT NULL,
            cgt_percentage REAL DEFAULT 0,
            cgt_amount REAL DEFAULT 0,
            net_amount REAL NOT NULL,
            memo_number TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # Create `stock_prices` table with buffer
        cursor.execute('''CREATE TABLE IF NOT EXISTS stock_prices (
            stock TEXT PRIMARY KEY,
            previous_close REAL,
            last_updated TEXT,
            last_attempt_time TEXT,
            buffer_price REAL
        )''')
        
        # Create api_calls table
        cursor.execute('''CREATE TABLE IF NOT EXISTS api_calls (
            date TEXT PRIMARY KEY,
            calls INTEGER DEFAULT 0
        )''')
        
        # Create metal_trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metal_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                metal TEXT NOT NULL,
                weight REAL NOT NULL CHECK (weight > 0),
                karat INTEGER DEFAULT NULL CHECK (karat IS NULL OR karat IN (10, 14, 16, 18, 20, 21, 22, 24)),
                purchase_price REAL NOT NULL CHECK (purchase_price > 0),
                total_cost REAL NOT NULL CHECK (total_cost > 0)
            )
        ''')
        
        # Create metal_prices table
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
        
        # Create exchange_rates table
        cursor.execute('''CREATE TABLE IF NOT EXISTS exchange_rates (
            base_currency TEXT,
            target_currency TEXT,
            rate REAL,
            last_updated TEXT,
            PRIMARY KEY (base_currency, target_currency)
        )''')

        conn.commit()
        return True
        
    except sqlite3.Error as e:
        print(f"Database initialization error: {str(e)}")
        return False
        
    finally:
        conn.close()