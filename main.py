# main.py
import streamlit as st
import pandas as pd
import sqlite3
import os
import time  # Added import for sleep functionality
from manual_trade_entry import manual_trade_entry
from dividend_warrant import manual_dividend_entry
from sell_trade import sell_trade
from view_trades import view_trades
from portfolio_summary import view_portfolio_summary
from manual_metal_trade_entry import manual_metal_trade_entry
from auth import load_users, delete_user, register_user
from db_utils import initialize_user_db, get_db_path

# For .env file support (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use hardcoded fallback

# ADMIN CONFIGURATION
# Get admin password from environment variables or Streamlit secrets
if 'ADMIN_PASSWORD' in os.environ:
    ADMIN_PASSWORD = os.environ['ADMIN_PASSWORD']
elif hasattr(st, 'secrets') and 'ADMIN_PASSWORD' in st.secrets:
    ADMIN_PASSWORD = st.secrets['ADMIN_PASSWORD']

# Page Configuration with theme explicitly set to dark
st.set_page_config(
    page_title="WealthWise",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
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

# Initialize session state for authentication
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

# Create admin user if not exists
users = load_users()
if 'admin' not in [u.lower() for u in users]:
    register_user('admin')
    st.info("Admin user created on first run")

# Custom login page with admin password support
def login_page():
    """Display the enhanced login/registration page with centered elements and no rectangular box"""
    
    # Custom CSS for the login page with better centering for radio buttons
    st.markdown("""
    <style>
        /* Background color fallback */
        [data-testid="stAppViewContainer"] {
            background-color: #191a16;
        }
        
        /* Remove unwanted elements and boxes */
        .element-container:has(.stTextArea) {
            display: none !important;
        }
        
        /* Center alignment */
        .center-column {
            max-width: 650px;
            margin: 0 auto;
            padding: 10px 20px;
        }
        
        /* Logo */
        .logo {
            text-align: center;
            margin: 2rem auto 1rem auto;
        }
        
        /* Page header */
        .page-header {
            text-align: center;
            margin: 1.5rem 0;
            color: white;
            font-size: 2.5rem;
            font-weight: 600;
        }
        
        /* Form elements */
        .form-control {
            max-width: 300px;
            margin: 1rem auto;
        }
        
        /* Center the radio buttons */
        .radio-wrapper {
            display: flex;
            justify-content: center !important;
            text-align: center !important;
            margin: 1rem auto;
        }
        
        /* Style the radio buttons container */
        .stRadio > div {
            display: flex;
            justify-content: center !important;
        }
        
        /* Submit button */
        .submit-button {
            max-width: 150px;
            margin: 1.5rem auto;
            text-align: center;
        }
        
        /* About section */
        .about-section {
            margin-top: 3rem;
            padding: 1.5rem;
            background-color: rgba(30, 30, 30, 0.7);
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .about-section h2 {
            text-align: center;
            color: #8a6d17;
            margin-bottom: 1rem;
        }
        
        /* Hide sidebar */
        [data-testid="stSidebar"] {
            visibility: hidden;
            width: 0 !important;
        }
        
        /* Other elements */
        .stButton button {
            background-color: #8a6d17 !important;
            color: white !important;
            width: 100%;
        }
        
        /* Override Streamlit defaults */
        div[data-testid="stVerticalBlock"] > div:empty {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* Make form labels white */
        label {
            color: white !important;
        }
        
        /* Remove the 'Choose an option' text */
        [data-testid="stRadio"] > label {
            display: none !important;
        }
        
        .stTextInput {
            max-width: 400px !important;
            margin: 0 auto !important;
        }
        
        .stButton {
            max-width: 400px !important;
            margin: 0 auto !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Start the centered column layout
    st.markdown('<div class="center-column">', unsafe_allow_html=True)
    
    # Logo section
    logo_paths = [
        "./assets/wealthwise-logo-zip-file/svg/logo-no-background.svg",
        "./assets/wealthwise-logo-zip-file/png/logo-no-background.png",
        "./assets/logo.svg",
        "./assets/logo.png",
        "./assets/images/logo.png"
    ]
    
    logo_path = None
    for path in logo_paths:
        if os.path.exists(path):
            logo_path = path
            break
    
    # Display logo
    # Create a centered container for the logo
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1: 
        st.write(" ")
    with col2:
        st.markdown('<div class="logo">', unsafe_allow_html=True)
        if logo_path:
            st.image(logo_path, width=900)
        st.markdown('</div>', unsafe_allow_html=True)
        # Page header
        st.markdown('<h1 class="page-header">WealthWise Login</h1>', unsafe_allow_html=True)
    with col3: 
        st.write(" ")

    # Page header
   # st.markdown('<h1 class="page-header">WealthWise Login</h1>', unsafe_allow_html=True)
    
    # Login/Register radio buttons - centered
    st.markdown('<div class="radio-wrapper">', unsafe_allow_html=True)
    # Using label_visibility="collapsed" to hide the "Choose an option" text
    auth_mode = st.radio("", ["Login", "Register"], horizontal=True, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Username field
    st.markdown('<div class="form-control">', unsafe_allow_html=True)
    username = st.text_input("Username").strip()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Admin password field (conditional)
    password = ""
    if username.lower() == "admin":
        st.markdown('<div class="form-control">', unsafe_allow_html=True)
        password = st.text_input("Admin Password", type="password")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Submit button
    st.markdown('<div class="submit-button">', unsafe_allow_html=True)
    submit_button = st.button("Submit")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Process form submission
    if submit_button and username:
        if auth_mode == "Login":
            if username.lower() == "admin":
                # Special handling for admin login
                if 'ADMIN_PASSWORD' in globals() and password == ADMIN_PASSWORD:
                    st.session_state.logged_in = True
                    st.session_state.username = "admin"
                    st.session_state.is_admin = True
                    st.success("Welcome, Administrator!")
                    time.sleep(1)
                    st.rerun()
                else:
                    # Show error message for incorrect admin password
                    st.error("❌ Incorrect admin password.")
                    time.sleep(1)
                    st.rerun()
            elif user_exists(username):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.is_admin = False
                st.success(f"Welcome back, {username}!")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"User '{username}' does not exist. Please register first.")
        else:  # Register
            if username.lower() == "admin":
                st.error("Cannot register with reserved username 'admin'.")
            elif register_user(username):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.is_admin = False
                st.success(f"Account created for {username}!")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Username '{username}' already exists. Please choose another.")
    
    elif submit_button:
        st.warning("Please enter a username.")
    
    # About Section
    st.markdown('<div class="about-section">', unsafe_allow_html=True)
    st.markdown("<h2>About WealthWise</h2>", unsafe_allow_html=True)
    st.write("A comprehensive web application built with Streamlit for managing your portfolio, tracking trades, monitoring dividends and keeping track of precious metal investments.")
    st.write("This tool helps investors maintain a clear record of their investments and analyze their portfolio performance.")
    
    col1, col2, col3 = st.columns(3)
    with col1: 
        st.write(" ")
    with col2:
        st.write("**Login:** Access your existing portfolio      |     **Register:** Create a new portfolio ")
    with col3: 
        st.write(" ")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Close the centered column
    st.markdown('</div>', unsafe_allow_html=True)

# Function to check if user exists
def user_exists(username):
    """Check if a user exists"""
    users = load_users()
    return username.lower() in [u.lower() for u in users]

# Function to show user info and logout button
def show_user_info():
    """Show current user information in the sidebar"""
    if 'username' in st.session_state and st.session_state.username:
        if st.session_state.is_admin:
            st.sidebar.markdown(f"**Logged in as:** {st.session_state.username} 🔑")
        else:
            st.sidebar.markdown(f"**Logged in as:** {st.session_state.username}")
        
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.is_admin = False
            st.rerun()

# Function to show user management interface
def show_user_management():
    st.subheader("User Management")
    
    # Load all users
    users = load_users()
    
    if not users:
        st.warning("No registered users found.")
    else:
        # Display all users
        st.write("### Registered Users")
        
        # Create a dataframe for better visualization
        import pandas as pd
        user_df = pd.DataFrame({"Username": users})
        st.dataframe(user_df)
        
        st.divider()
        
        # Delete user section
        st.subheader("Delete User")
        
        username = st.selectbox("Select user to delete:", [u for u in users if u.lower() != 'admin'])
        
        # Display database path for the selected user
        if username:
            st.caption(f"Database path: {get_db_path(username)}")
        
        # Confirmation
        if username:
            st.warning(f"⚠️ WARNING: Deleting user '{username}' will permanently remove all their data!")
            confirm = st.text_input("Type the username again to confirm deletion:")
            
            if st.button("Delete User"):
                if not confirm:
                    st.error("Please confirm by typing the username.")
                elif confirm.lower() != username.lower():
                    st.error("Username confirmation doesn't match. Please try again.")
                else:
                    if delete_user(username):
                        st.success(f"✅ User '{username}' and all their data have been deleted.")
                        # Refresh the page after deletion
                        st.rerun()
                    else:
                        st.error(f"Failed to delete user '{username}'.")

# Function to show app dashboard interface
def show_app_dashboard():
    st.subheader("Application Dashboard")
    st.write("Welcome to the admin dashboard. Here you can see app statistics and manage the application.")
    
    # Load users for statistics
    users = load_users()
    
    # Stats section
    st.write("### System Statistics")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Users", len(users))
        
    with col2:
        # Get the data directory
        base_dir = os.environ.get('HOME', '')
        if os.path.exists(base_dir) and os.access(base_dir, os.W_OK):
            data_dir = os.path.join(base_dir, 'wealthwise_data')
        else:
            data_dir = 'db'
        
        if os.path.exists(data_dir):
            db_files = [f for f in os.listdir(data_dir) if f.endswith('.db')]
            st.metric("Database Files", len(db_files))
        else:
            st.metric("Database Files", "N/A")

# Main application logic
if not st.session_state.logged_in:
    # Show login page if not logged in
    login_page()
else:
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
        # Regular user interface
        # Create a centered container for the logo
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
        
        # Welcome message with current portfolio name
        st.markdown('<div class="welcome-section"></div>', unsafe_allow_html=True)
        st.markdown(f"## Welcome to your personal portfolio tracker, {st.session_state.username}!")
       # st.caption(f"Your portfolio data is stored in: {get_db_path()}")
        
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