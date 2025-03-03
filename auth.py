# auth.py
import streamlit as st
import os
import json
from db_utils import initialize_user_db

# File to store registered usernames
USERS_FILE = "registered_users.json"

def load_users():
    """Load registered users from file"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_users(users):
    """Save registered users to file"""
    with open(USERS_FILE, 'w') as f:
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
    This application allows you to track your investment portfolio. Each user 
    gets their own private database, so your data won't be mixed with others.
    
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
    import os
    
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

# Add this function for admin usage
def admin_delete_user():
    """Admin interface to delete a user"""
    st.title("🔒 Admin: Delete User")
    
    # Load all users
    users = load_users()
    
    if not users:
        st.warning("No registered users found.")
        return
    
    # Select user to delete
    username = st.selectbox("Select user to delete:", users)
    
    # Confirmation
    if st.button("Delete User"):
        confirm = st.text_input("Type the username again to confirm deletion:")
        
        if confirm.lower() == username.lower():
            if delete_user(username):
                st.success(f"User '{username}' and all their data have been deleted.")
            else:
                st.error(f"Failed to delete user '{username}'.")
        elif confirm:
            st.error("Username confirmation doesn't match. Please try again.")