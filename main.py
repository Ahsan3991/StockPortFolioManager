# main.py (Part 1: Imports, Configuration, and Session State Initialization)
import streamlit as st
import os
import time
from dotenv import load_dotenv

# Load modules for authentication and user interface
from user_auth_ui import login_page, change_password_page, show_user_info
from admin_panel import show_user_management, show_app_dashboard
from forget_password import (
    forgot_password_page, reset_password_page, verify_email_page,
    resend_verification_email
)
from auth import (
    migrate_users_to_password_system, register_user, check_email_verified,
    load_users
)

# Load application modules
from manual_trade_entry import manual_trade_entry
from dividend_warrant import manual_dividend_entry
from sell_trade import sell_trade
from view_trades import view_trades
from portfolio_summary import view_portfolio_summary
from manual_metal_trade_entry import manual_metal_trade_entry

# For .env file support
try:
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use hardcoded fallback

# ADMIN_PASSWORD is needed in user_auth_ui.py but we'll keep it here for consistency
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 
                             st.secrets.get('ADMIN_PASSWORD', 'admin123') if hasattr(st, 'secrets') else 'admin123')

# Page Configuration with theme explicitly set to dark
st.set_page_config(
    page_title="WealthWise",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state variables
def init_session_state():
    """Initialize all session state variables"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if 'username' not in st.session_state:
        st.session_state.username = None

    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False

    if 'admin_view' not in st.session_state:
        st.session_state.admin_view = "User Management"

    if 'selected_option' not in st.session_state:
        st.session_state.selected_option = "Portfolio Summary"

    if 'reset_password_mode' not in st.session_state:
        st.session_state.reset_password_mode = False

    if 'forgot_password' not in st.session_state:
        st.session_state.forgot_password = False

    if 'reset_token' not in st.session_state:
        st.session_state.reset_token = None

    if 'verify_token' not in st.session_state:
        st.session_state.verify_token = None

    if 'base_url' not in st.session_state:
        # Try to determine the base URL
        if 'HOSTNAME' in os.environ and os.environ['HOSTNAME'].endswith('.streamlit.app'):
            st.session_state.base_url = f"https://{os.environ['HOSTNAME']}"
        else:
            st.session_state.base_url = "http://localhost:10000"  # Fallback for local dev

# main.py (Part 2: Helper Functions and CSS Styling)


# Check for URL parameters
def check_url_params():
    """Check for URL parameters for password reset or email verification"""
    try:
        query_params = st.experimental_get_query_params()
        
        # Handle email verification
        if "verify_email" in query_params and query_params["verify_email"]:
            token = query_params["verify_email"][0]
            st.session_state.verify_token = token
            
        # Handle password reset
        if "reset_password" in query_params and query_params["reset_password"]:
            token = query_params["reset_password"][0]
            st.session_state.reset_token = token
            
        # Handle OAuth callback
        if "code" in query_params and "scope" in query_params:
            from google_auth import handle_oauth_callback
            handle_oauth_callback()
            
    except:
        # Older Streamlit versions might not have this function
        pass

# Function to display the logo and welcome message
def display_app_header():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Display logo or text-based title with fallback
        try:
            # Method 1: Using st.image with width parameter - much larger now
            logo_path = "./assets/wealthwise-logo-zip-file/svg/logo-no-background.svg"
            if os.path.exists(logo_path):
                st.image(logo_path, width=600)
            else:
                # If main logo not found, try alternative logo
                alt_logo_path = "./assets/wealthwise-logo-zip-file/png/logo-no-background.png"
                if os.path.exists(alt_logo_path):
                    st.image(alt_logo_path, width=600)
                else:
                    # Fallback to text-based title
                    raise FileNotFoundError("Logo files not found")
        except Exception as e:
            # Fallback to text-based title if image doesn't work
            st.markdown('<div class="app-title"><h1>WealthWise</h1></div>', unsafe_allow_html=True)
            st.markdown('<div class="app-subtitle"><h2>Portfolio Manager</h2></div>', unsafe_allow_html=True)

# Custom CSS for the application
def load_css():
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
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 30px auto;
            text-align: center;
            width: 100%;
        }
        
        /* Center the image in Streamlit */
        .stImage {
            display: block;
            margin-left: auto;
            margin-right: auto;
            text-align: center;
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
            background-color:#262624;
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
            font-size: 2rem !important;
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
            font-size: 1rem !important;
        }
        
        /* Add some space after the title section */
        .welcome-section {
            margin-top: 30px;
        }
        
        /* Admin panel styling */
        .admin-header {
            color: #ff5555;
            font-weight: bold;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 5px solid #ff5555;
            background-color: rgba(255, 85, 85, 0.1);
        }
        </style>
    """, unsafe_allow_html=True)



# main.py (Part 3: Main Application Flow)

# Initialize session state and load CSS
init_session_state()
load_css()

# Migrate existing users to the password-based system
migrate_users_to_password_system()

# Create admin user if not exists
users = load_users()
if not any(user.get('username', '').lower() == 'admin' for user in users):
    register_user('admin', ADMIN_PASSWORD, "admin@example.com")
    st.info("Admin user created on first run")

# Check for URL parameters for email verification or password reset
check_url_params()

# Main application flow
if st.session_state.verify_token:
    # Email verification page
    verify_email_page(st.session_state.verify_token)
elif st.session_state.reset_token:
    # Password reset page
    reset_password_page(st.session_state.reset_token)
elif st.session_state.forgot_password:
    # Forgot password page
    forgot_password_page()
elif not st.session_state.logged_in:
    # Login page
    login_page()
else:
    # User is logged in - handle password reset mode
    if not st.session_state.is_admin and st.session_state.reset_password_mode:
        change_password_page()
    else:
        # Regular application flow for logged-in users
        
        # First define the sidebar to collect user choice
        with st.sidebar:
            # Show user info and logout button
            show_user_info()
            
            st.subheader("Navigation")
            st.markdown('<p style="font-size: 1.5rem; font-weight: 500; color: #1E4020; margin-bottom: 0.2rem;">Choose Your Action</p>', unsafe_allow_html=True)
            
            # Different navigation options for admin vs regular users
            if st.session_state.is_admin:
                option = st.selectbox(
                    "Choose Your Action",
                    [
                        "User Management",
                        "App Dashboard"
                    ],
                    label_visibility="collapsed"
                )
                
                # Update admin view based on selection
                if option != st.session_state.admin_view:
                    st.session_state.admin_view = option
                    st.rerun()
            else:
                # Store the selection in session state to preserve it between reruns
                selected_option = st.selectbox(
                    "Choose Your Action",
                    [
                        "Portfolio Summary",
                        "Manually Enter Trade",
                        "Manually Enter Metal Trade",
                        "Manually Enter Dividend",
                        "Sell Stock",
                        "View Trades"
                    ],
                    label_visibility="collapsed"
                )
                # Store selection in session state
                st.session_state.selected_option = selected_option
        
        # Check if user email is verified for regular users
        if not st.session_state.is_admin and not check_email_verified(st.session_state.username):
            st.warning("Your email is not verified. Please check your inbox for a verification email or click below to resend it.")
            if st.button("Resend Verification Email"):
                resend_verification_email()
                
        # Now define the main content area OUTSIDE the sidebar
        if st.session_state.is_admin:
            # Admin interface
            st.markdown('<div class="admin-header">🔒 ADMIN CONTROL PANEL</div>', unsafe_allow_html=True)
            
            # Admin tabs without using .select()
            admin_option = st.radio("Admin View", ["User Management", "App Dashboard"], horizontal=True)
            st.session_state.admin_view = admin_option
            
            # Display the selected admin view
            if st.session_state.admin_view == "User Management":
                show_user_management()
            else:
                show_app_dashboard()                
        else:
            # Regular user interface - display application header
            display_app_header()
            
            # Welcome message with current portfolio name
            st.markdown('<div class="welcome-section"></div>', unsafe_allow_html=True)
            st.markdown(f"## Welcome to your personal portfolio tracker, {st.session_state.username}!")
            
            # IMPORTANT: Function calls must be OUTSIDE the sidebar context
            # This is what fixes the layout issue
            if st.session_state.selected_option == "Manually Enter Trade":
                manual_trade_entry()
            elif st.session_state.selected_option == "Manually Enter Metal Trade":
                manual_metal_trade_entry()
            elif st.session_state.selected_option == "Manually Enter Dividend":
                manual_dividend_entry()
            elif st.session_state.selected_option == "Sell Stock":
                sell_trade()
            elif st.session_state.selected_option == "View Trades":
                view_trades()
            elif st.session_state.selected_option == "Portfolio Summary":
                view_portfolio_summary()