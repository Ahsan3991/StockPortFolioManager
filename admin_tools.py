# admin_tools.py
import streamlit as st
import os
import json
from db_utils import get_db_path

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
    # Check if user exists
    users = load_users()
    if username.lower() not in [u.lower() for u in users]:
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
    users = [u for u in users if u.lower() != username.lower()]
    save_users(users)
    
    return True

def main():
    st.title("WealthWise Admin Tools")
    
    st.header("User Management")
    
    # Load all users
    users = load_users()
    
    if not users:
        st.warning("No registered users found.")
        return
    
    # Display all users
    st.subheader("Registered Users")
    for i, user in enumerate(users, 1):
        st.text(f"{i}. {user}")
    
    st.divider()
    
    # Delete user section
    st.subheader("Delete User")
    
    username = st.selectbox("Select user to delete:", users)
    
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

if __name__ == "__main__":
    main()