# user_auth_ui.py (Part 1: Imports and Helper Functions)
import streamlit as st
import os
import time
from db_utils import get_db_path
from auth import (
    verify_credentials, hash_password, update_user_password, register_user
)
from forget_password import send_verification_email

def get_admin_password():
    """Get the admin password from environment variables or fallback"""
    if 'ADMIN_PASSWORD' in os.environ:
        return os.environ['ADMIN_PASSWORD']
    elif hasattr(st, 'secrets') and 'ADMIN_PASSWORD' in st.secrets:
        return st.secrets['ADMIN_PASSWORD']
    else:
        return "admin123"  # Default fallback for local testing

def change_password_page():
    """Display the change password form"""
    st.subheader("Change Your Password")
    
    current_password = st.text_input("Current Password", type="password")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm New Password", type="password")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Update Password", type="primary"):
            # Validate current password
            if not verify_credentials(st.session_state.username, current_password):
                st.error("Current password is incorrect.")
            elif not new_password:
                st.error("New password cannot be empty.")
            elif new_password != confirm_password:
                st.error("New passwords do not match.")
            else:
                # Update password
                if update_user_password(st.session_state.username, new_password):
                    st.success("Password updated successfully!")
                    st.session_state.reset_password_mode = False
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to update password. Please try again.")
    
    with col2:
        if st.button("Cancel"):
            st.session_state.reset_password_mode = False
            st.rerun()

# user_auth_ui.py (Part 2: Login Page Function - First Half)
def login_page():
    """Display the enhanced login/registration page with Google Sign-In"""
    page_bg_img = f"""
    <style>
    .st-emotion-cache-uf99v8 {{
        background-image: url("https://raw.githubusercontent.com/Ahsan3991/StockPortFolioManager/refs/heads/testing/assets/wealthwise-logo-zip-file/background-image.png");
        background-size: cover;
        background-position: center;
        position: relative;
    }}

    .st-emotion-cache-uf99v8::before {{
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.4);  /* Dark transparent overlay */
        z-index: -1;  /* Places it behind content */
    }}
    </style>
    """

    # Custom CSS for the login page with better centering for radio buttons
    st.markdown(
        f"""
        <style>
        /* Remove unwanted elements and boxes */
        .element-container:has(.stTextArea) {{
            display: none !important;
        }}
        
        /* Center alignment */
        .center-column {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 5px 10px;
            position: relative; 
            z-index: 1;
            
        }}
        /* Increasing opaqueness in the center for better viewing */
        .st-emotion-cache-1wmy9hl {{
            position: relative; 
            z-index: 1;
            background-color: rgba(25, 26, 22, 0.8);
        }}
        
        /* Logo */
        .logo {{
            text-align: center;
            margin: 2rem auto 1rem auto;
            width: 100%;
            
        }}
        
        /* Page header */
        .page-header {{
            text-align: center;
            margin: 1rem 0;
            color: #cfcfcc;
            font-size: 2rem;
            font-weight: 450;
        }}
        
        /* Form elements */
        .form-control {{
            max-width: 300px;
            margin: 1rem auto;
        }}
        
        /* Center the radio buttons */
        .radio-wrapper {{
            display: flex;
            justify-content: center !important;
            text-align: center !important;
            margin: 1rem auto;
        }}
        
        /* Style the radio buttons container */
        .stRadio > div {{
            display: flex;
            justify-content: center !important;
        }}
        
        /* Submit button */
        .submit-button {{
            max-width: 150px;
            margin: 1.5rem auto;
            text-align: center;
            font-weight: bold;
        }}
        
        /* About section */
        .about-section {{
            margin-top: 1rem;
            padding: 1rem;
            border-radius: 5px;
            border: 1px solid rgba(140, 122, 49, 0.2);
            text-align: center;
            background-color: rgba(25, 26, 22, 0.5);
        }}
        
        .about-section h2 {{
            text-align: center;
            color: #cfcfcc;
            margin-bottom: 1rem;
        }}
        
        /* Hide sidebar */
        [data-testid="stSidebar"] {{
            visibility: hidden;
            width: 0 !important;
        }}
        
        /* Other elements */
        .stButton button {{
            background-color: #8a6d17 !important;
            color: white !important;
            width: 100%;
        }}
        
        /* Override Streamlit defaults */
        div[data-testid="stVerticalBlock"] > div:empty {{
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        
        /* Remove the 'Choose an option' text */
        [data-testid="stRadio"] > label {{
            display: none !important;
        }}
        
        .stTextInput {{
            max-width: 400px !important;
            margin: 0 auto !important;
        }}
        
        .stButton {{
            max-width: 400px !important;
            margin: 0 auto !important;
        }}
        
        /* Google Sign-In styling */
        .divider {{
            text-align: center;
            margin: 1rem 0;
            font-size: 0.9rem;
            color: #aaa;
            position: relative;
        }}
        .divider:before, .divider:after {{
            content: "";
            display: block;
            height: 1px;
            background-color: #4a4a4a;
            position: absolute;
            top: 50%;
            width: 35%;
        }}
        .divider:before {{
            left: 0;
        }}
        .divider:after {{
            right: 0;
        }}
        .social-login {{
            text-align: center;
            margin: 1rem auto;
        }}
        .social-login button {{
            background-color: #4285F4 !important;
            color: white !important;
            max-width: 240px !important;
            margin: 0 auto !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# user_auth_ui.py (Part 3: Login Page Function - Second Half and Show User Info)
    
    # Add overlay div
    st.markdown('<div class="overlay"></div>', unsafe_allow_html=True)
    
    # Start the centered column layout
    st.markdown('<div class="center-column">', unsafe_allow_html=True)

    # Add background image
    st.markdown(page_bg_img, unsafe_allow_html=True)
    
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
            st.image(logo_path, width=800, use_column_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        # Page header
        st.markdown('<h2 class="page-header">Please Login or Register</h2>', unsafe_allow_html=True)

        # Login/Register radio buttons - centered
        st.markdown('<div class="radio-wrapper">', unsafe_allow_html=True)
        # Using label_visibility="collapsed" to hide the "Choose an option" text
        auth_mode = st.radio("", ["Login", "Register"], horizontal=True, label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Username field
        st.markdown('<div class="form-control">', unsafe_allow_html=True)
        username = st.text_input("Username").strip()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Password field
        st.markdown('<div class="form-control">', unsafe_allow_html=True)
        password = st.text_input("Password", type="password")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Confirm password field (only for registration)
        if auth_mode == "Register":
            st.markdown('<div class="form-control">', unsafe_allow_html=True)
            confirm_password = st.text_input("Confirm Password", type="password")
            email = st.text_input("Email")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Submit button
        st.markdown('<div class="submit-button">', unsafe_allow_html=True)
        submit_button = st.button("**Submit**")
        st.markdown('</div>', unsafe_allow_html=True)

        # Google Sign-In button
        st.markdown('<div class="divider">OR</div>', unsafe_allow_html=True)
        st.markdown('<div class="social-login">', unsafe_allow_html=True)
        if st.button("Sign in with Google", key="google_login"):
            try:
                from google_auth import start_google_auth
                start_google_auth()
            except ImportError:
                st.error("Google authentication is not configured properly. Contact the administrator.")
        st.markdown('</div>', unsafe_allow_html=True)

        # Forgot password link (only for login)
        if auth_mode == "Login":
            if st.button("Forgot Password?"):
                st.session_state.forgot_password = True
                st.rerun()
        
        col1, col2, col3 = st.columns([1, 5, 1])
        with col1: st.write(" ")
        with col2:
            # About Section
            st.markdown('<div class="about-section">', unsafe_allow_html=True)
            st.markdown("<h2>About WealthWise</h2>", unsafe_allow_html=True)
            st.write("A comprehensive web application built with Streamlit for managing your portfolio, tracking trades, monitoring dividends and keeping track of precious metal investments.")
            st.write("This tool helps investors maintain a clear record of their investments and analyze their portfolio performance.")
           
            st.markdown('</div>', unsafe_allow_html=True)
        with col3: st.write(" ")
             
    with col3: 
        st.write(" ")

    # Process form submission
    if submit_button:
        if not username.strip():
            st.error("Username is required.")
            return
            
        if not password:
            st.error("Password is required.")
            return
            
        if auth_mode == "Login":
            # Special admin login
            if username.lower() == "admin":
                admin_password = get_admin_password()
                if password == admin_password:
                    st.session_state.logged_in = True
                    st.session_state.username = "admin"
                    st.session_state.is_admin = True
                    st.success("Welcome, Administrator!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Incorrect admin password.")
                    time.sleep(1)
            # Regular user login
            elif verify_credentials(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.is_admin = False
                st.success(f"Welcome back, {username}!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Invalid username or password. Please try again.")
        else:  # Register
            # Validate registration
            if username.lower() == "admin":
                st.error("Cannot register with reserved username 'admin'.")
            elif auth_mode == "Register" and password != confirm_password:
                st.error("Passwords do not match. Please try again.")
            elif not email and auth_mode == "Register":
                st.error("Email is required for registration.")
            elif auth_mode == "Register" and "@" not in email:
                st.error("Please enter a valid email address.")
            elif register_user(username, password, email):
                # Send verification email
                send_success = send_verification_email(username, email)
                
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.is_admin = False
                
                if send_success:
                    st.success(f"Account created for {username}! Please check your email to verify your account.")
                else:
                    st.warning(f"Account created for {username} but failed to send verification email. Please contact support.")
                
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Username '{username}' already exists. Please choose another.")
    
    # Close the centered column
    st.markdown('</div>', unsafe_allow_html=True)

def show_user_info():
    """Show current user information in the sidebar"""
    if 'username' in st.session_state and st.session_state.username:
        if st.session_state.is_admin:
            st.sidebar.markdown(f"**Logged in as:** {st.session_state.username} 🔑")
        else:
            st.sidebar.markdown(f"**Logged in as:** {st.session_state.username}")
        
        # Add a password change option
        if not st.session_state.is_admin:
            if st.sidebar.button("Change Password"):
                st.session_state.reset_password_mode = True
            
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.is_admin = False
            st.session_state.reset_password_mode = False
            st.rerun()