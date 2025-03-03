# main.py
import streamlit as st
import pandas as pd
import sqlite3
from trade_receipt import manual_trade_entry
from dividend_warrant import manual_dividend_entry
from sell_trade import sell_trade
from view_trades import view_trades
from portfolio_summary import view_portfolio_summary
from manual_metal_trade_entry import manual_metal_trade_entry


# Page Configuration
st.set_page_config(
    page_title="WealthWise",
    page_icon="./assets/wealthwise-logo-zip-file/png/logo-color.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for overall app styling
st.markdown("""
    <style>
    /* Content container styling */
    [data-testid="stAppViewContainer"] {
        background-color: #191a16;  /* Background color, greenish-black */
    }
            
    /* Base styling for metrics */
    .metric-container {
        padding: 1rem;
        border-radius: 0.5rem;
        background: #262624;
        margin-bottom: 1rem;
    }
    
    /* Logo styling */
    .centered-logo {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 1rem 0;
        margin: auto;
        width: 100%;  /* This controls how much of the container width to use */
    }

    .centered-logo img {
        max-width: 100%;
        height: auto;
    }
    
    .stMetric {
        background-color:#262624 ;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    
    /* Font sizes for metrics */
    .stMetric label {
        font-size: 0.875rem !important;
    }
    
    .stMetric .css-1xarl3l {
        font-size: 1.25rem !important;
    }
    
    .stMetric .css-1wivap2 {
        font-size: 1rem !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.875rem !important;
    }
    
    /* Make content use full width */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 85% !important;
    }

    /* Sidebar styling */
    .css-1d391kg {
        padding-top: 1rem;
    }
    
    /* Headers styling */
    h1 {
        font-size: 2rem !important;
        padding-bottom: 1rem;
    }
    
    h2 {
        font-size: 1.5rem !important;
        padding-bottom: 0.5rem;
    }
    
    /* Add sidebar background color */
    [data-testid="stSidebar"] {
        background-color: #8a6d17;
    }
    
    /* Make text in sidebar white */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: white;
    }
    
    /* Target the subheader specifically */
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] .sidebar-content h3,
    [data-testid="stSidebar"] .st-emotion-cache-16idsys h3,
    [data-testid="stSidebar"] .st-bq,
    [data-testid="stSidebar"] .st-af,
    [data-testid="stSidebar"] .st-ae {
        font-size: 2.5rem !important;
        font-weight: bold !important;
        margin-top: 1rem !important;
        margin-bottom: 1rem !important;
    }
    
    /* Increase font size for "Choose Action" label */
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stSelectbox .st-bs,
    [data-testid="stSidebar"] .stSelectbox .st-bq {
        font-size: 1.8rem !important;
        font-weight: 500 !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Ensure dropdown options are also larger */
    [data-testid="stSidebar"] select option {
        font-size: 1.2rem !important;
    }
    </style>
""", unsafe_allow_html=True)


def initialize_db():

    conn = sqlite3.connect("portfolio.db")
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

        conn.commit()
        
    except sqlite3.Error as e:
        st.error(f"Database initialization error: {str(e)}")
        
    finally:
        conn.close()


def recreate_metal_trades_table():
    """
    Drops the existing metal_trades table (if any) and recreates it so 'id' is AUTOINCREMENT.
    WARNING: This will delete all existing metal trades data!
    """
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    try:
        cursor.execute("DROP TABLE IF EXISTS metal_trades")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metal_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                metal TEXT NOT NULL,
                weight REAL NOT NULL CHECK (weight > 0),
                karat INTEGER DEFAULT 24 CHECK (karat IN (10, 14, 16, 18, 20, 21, 22, 24)),
                purchase_price REAL NOT NULL CHECK (purchase_price > 0),
                total_cost REAL NOT NULL CHECK (total_cost > 0)
            )
        ''')
        conn.commit()
        st.success("metal_trades table recreated (all existing metal data removed).")
    except sqlite3.Error as e:
        conn.rollback()
        st.error(f"Error recreating metal_trades table: {e}")
    finally:
        conn.close()


# Initialize Database at Startup
initialize_db()
#recreate_metal_trades_table()  # NOTE: This will wipe existing metal trades


# Display logo in the second column
container = st.container()

with container:
    st.markdown('<div class="centered-logo">', unsafe_allow_html=True)
    st.image(
        "./assets/wealthwise-logo-zip-file/svg/logo-no-background.svg",
        use_container_width=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

# Sidebar Navigation
with st.sidebar:
    st.subheader("Navigation")
    st.markdown('<p style="font-size: 1.5rem; font-weight: 500; color: #1E4020; margin-bottom: 0.2rem;">Choose Your Action</p>', unsafe_allow_html=True)
    option = st.selectbox(
        "Choose Your Action",
        [
            "Portfolio Summary",
            "Manually Enter Trade",
            "Manually Enter Metal Trade",
            "Manually Enter Dividend",
            "Sell Stock",
            "View Trades"
        ],
         label_visibility="collapsed"  # This hides the label but keeps it accessible
    )

# Route to appropriate function based on selection
#if option == "Upload Trade Receipt":
 #   process_trade_receipt()
if option == "Manually Enter Trade":
    manual_trade_entry()
elif option == "Manually Enter Metal Trade":
    manual_metal_trade_entry()
#elif option == "Upload Dividend Warrant":
 #   process_dividend_warrant()
elif option == "Manually Enter Dividend":
    manual_dividend_entry()
elif option == "Sell Stock":
    sell_trade()
elif option == "View Trades":
    view_trades()
elif option == "Portfolio Summary":
    view_portfolio_summary()
