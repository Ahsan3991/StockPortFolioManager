# auth.py
import streamlit as st
import os
import json
from db_utils import initialize_user_db

def get_users_file_path():
    """Get the path to the users file, ensuring it's writable in Streamlit Cloud"""
    # For Streamlit Cloud, we need to use a writable directory
    base_dir = os.environ.get('HOME', '')
    
    # If running on Streamlit Cloud, use a subdirectory in HOME
    if os.path.exists(base_dir) and os.access(base_dir, os.W_OK):
        data_dir = os.path.join(base_dir, 'wealthwise_data')
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "registered_users.json")
    else:
        # Fallback to local directory for local development
        return "registered_users.json"

def load_users():
    """Load registered users from file"""
    users_file = get_users_file_path()
    if os.path.exists(users_file):
        with open(users_file, 'r') as f:
            return json.load(f)
    return []

def save_users(users):
    """Save registered users to file"""
    users_file = get_users_file_path()
    with open(users_file, 'w') as f:
        json.dump(users, f)

def register_user(username):
    """Register a new user"""
    users = load_users()
    if username.lower() not in [u.lower() for u in users]:
        users.append(username)
        save_users(users)
        # Initialize the database for this user
        initialize_user_db(username)
        return True
    return False

def user_exists(username):
    """Check if a user exists"""
    users = load_users()
    return username.lower() in [u.lower() for u in users]

def login_page():
    """Display the login/registration page"""
    st.title("🔒 WealthWise Login")
    
    # Login/register selection
    auth_mode = st.radio("Choose an option:", ["Login", "Register"], horizontal=True)
    
    username = st.text_input("Username").strip()
    submit_button = st.button("Submit")
    
    if submit_button and username:
        if auth_mode == "Login":
            if user_exists(username):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"Welcome back, {username}!")
                st.rerun()  # Reload the app to show the main interface
            else:
                st.error(f"User '{username}' does not exist. Please register first.")
        else:  # Register
            if register_user(username):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"Account created for {username}!")
                st.rerun()  # Reload the app to show the main interface
            else:
                st.error(f"Username '{username}' already exists. Please choose another.")
    
    elif submit_button:
        st.warning("Please enter a username.")
    
    # Display explanatory message
    st.markdown("""
    ### About WealthWise
    
    
    - **Login**: Access your existing portfolio
    - **Register**: Create a new portfolio
    """)
    
def logout():
    """Log out the current user"""
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

def show_user_info():
    """Show current user information in the sidebar"""
    if 'username' in st.session_state and st.session_state.username:
        st.sidebar.markdown(f"**Logged in as:** {st.session_state.username}")
        logout()

def delete_user(username):
    """
    Delete a user from the system:
    1. Removes their database file
    2. Removes them from the registered users list
    
    Args:
        username (str): The username to delete
    
    Returns:
        bool: True if user was successfully deleted, False otherwise
    """
    from db_utils import get_db_path
    
    # Check if user exists
    if not user_exists(username):
        return False
    
    # Get the user's database path
    db_path = get_db_path(username)
    
    # Delete the database file if it exists
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError as e:
            print(f"Error deleting database file: {e}")
            return False
    
    # Remove user from the registered users list
    users = load_users()
    users = [u for u in users if u.lower() != username.lower()]
    save_users(users)
    
    return True