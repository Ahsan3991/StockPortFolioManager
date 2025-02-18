import streamlit as st
import pandas as pd
import sqlite3
from trade_receipt import process_trade_receipt, manual_trade_entry
from dividend_warrant import process_dividend_warrant, manual_dividend_entry
from sell_trade import sell_trade
from view_trades import view_trades
from portfolio_summary import view_portfolio_summary


def initialize_db():
    """Creates all required tables if they do not exist."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    
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
        type TEXT,
        FOREIGN KEY (memo_number) REFERENCES memos(memo_number) ON DELETE CASCADE
    )''')
    
    # Create `memos` table
    cursor.execute('''CREATE TABLE IF NOT EXISTS memos (
        memo_number TEXT PRIMARY KEY
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
    
    conn.commit()
    conn.close()

# Initialize Database at Startup
initialize_db()

st.title("Stock Portfolio Manager")

# Sidebar Options with improved organization
option = st.sidebar.selectbox(
    "Choose Action",
    [
        "Portfolio Summary",
        "Upload Trade Receipt",
        "Manually Enter Trade",
        "Upload Dividend Warrant",
        "Manually Enter Dividend",
        "Sell Stock",
        "View Trades"
    ]
)

# Call the respective functions
if option == "Upload Trade Receipt":
    process_trade_receipt()
elif option == "Manually Enter Trade":
    manual_trade_entry()
elif option == "Upload Dividend Warrant":
    process_dividend_warrant()
elif option == "Manually Enter Dividend":
    manual_dividend_entry()
elif option == "Sell Stock":
    sell_trade()
elif option == "View Trades":
    view_trades()
elif option == "Portfolio Summary":
    view_portfolio_summary()