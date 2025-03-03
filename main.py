# main.py
import streamlit as st
import pandas as pd
import sqlite3
import os
from trade_receipt import manual_trade_entry
from dividend_warrant import manual_dividend_entry
from sell_trade import sell_trade
from view_trades import view_trades
from portfolio_summary import view_portfolio_summary
from manual_metal_trade_entry import manual_metal_trade_entry
from auth import login_page, show_user_info
from db_utils import initialize_user_db, get_db_path

# Page Configuration
st.set_page_config(
    page_title="WealthWise",
    page_icon="📊",
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
    
    /* Logo container styling */
    .logo-container {
        text-align: center;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    
    /* App title as fallback */
    .app-title {
        text-align: center;
        width: 100%;
        margin-top: 10px;
        margin-bottom: 0;
        padding-bottom: 0;
    }
    
    .app-title h1 {
        font-size: 2.5em !important;
        color: white;
        font-weight: 600;
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
        line-height: 1.2;
    }
    
    .app-subtitle {
        text-align: center;
        width: 100%;
        margin-top: 0;
    }
    
    .app-subtitle h2 {
        font-size: 1.8em !important;
        color: #cccccc;
        font-weight: 400;
        margin-top: 0 !important;
        padding-top: 0 !important;
        line-height: 1.2;
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
    
    /* Add some space after the title section */
    .welcome-section {
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state for authentication
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if 'username' not in st.session_state:
    st.session_state.username = None

# Main application logic
if not st.session_state.logged_in:
    # Show login page if not logged in
    login_page()
else:
    # Display logo or text-based title with fallback
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    
    # Try different methods to display the logo, with fallbacks
    try:
        # Method 1: Using st.image with width parameter
        logo_path = "./assets/wealthwise-logo-zip-file/svg/logo-no-background.svg"
        if os.path.exists(logo_path):
            st.image(logo_path, width=400)
        else:
            # If main logo not found, try alternative logo
            alt_logo_path = "./assets/wealthwise-logo-zip-file/png/logo-no-background.png"
            if os.path.exists(alt_logo_path):
                st.image(alt_logo_path, width=400)
            else:
                # Fallback to text-based title
                raise FileNotFoundError("Logo files not found")
    except Exception as e:
        # Fallback to text-based title if image doesn't work
        st.markdown('<div class="app-title"><h1>WealthWise</h1></div>', unsafe_allow_html=True)
        st.markdown('<div class="app-subtitle"><h2>Portfolio Manager</h2></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Welcome message with current portfolio name
    st.markdown('<div class="welcome-section"></div>', unsafe_allow_html=True)
    st.markdown(f"## Welcome to your personal portfolio tracker, {st.session_state.username}!")
    st.caption(f"Your portfolio data is stored in: {get_db_path()}")

    # Sidebar Navigation
    with st.sidebar:
        # Show user info and logout button
        show_user_info()
        
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
    if option == "Manually Enter Trade":
        manual_trade_entry()
    elif option == "Manually Enter Metal Trade":
        manual_metal_trade_entry()
    elif option == "Manually Enter Dividend":
        manual_dividend_entry()
    elif option == "Sell Stock":
        sell_trade()
    elif option == "View Trades":
        view_trades()
    elif option == "Portfolio Summary":
        view_portfolio_summary()