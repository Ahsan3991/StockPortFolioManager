# admin_panel.py
import streamlit as st
import pandas as pd
import os
from auth import load_users, delete_user
from db_utils import get_db_path

def show_user_management():
    """Display the user management interface for admins"""
    st.subheader("User Management")
    
    # Load all users
    users = load_users()
    
    if not users:
        st.warning("No registered users found.")
    else:
        # Display all users
        st.write("### Registered Users")
        
        # Create a dataframe for better visualization
        user_list = []
        for user in users:
            if isinstance(user, dict):
                username = user.get('username', '')
                email = user.get('email', 'No email')
                email_verified = "✅" if user.get('email_verified', False) else "❌"
                created_at = user.get('created_at', 'Unknown')
                user_list.append({
                    "Username": username,
                    "Email": email,
                    "Email Verified": email_verified,
                    "Created": created_at
                })
            else:
                # Handle old format users
                user_list.append({
                    "Username": user,
                    "Email": "No email",
                    "Email Verified": "❌",
                    "Created": "Unknown"
                })
                
        user_df = pd.DataFrame(user_list)
        st.dataframe(user_df, hide_index=True)
        
        st.divider()
        
        # Delete user section
        st.subheader("Delete User")
        
        # Get usernames excluding admin
        non_admin_users = [user.get('username', user) if isinstance(user, dict) else user 
                           for user in users 
                           if (isinstance(user, dict) and user.get('username', '').lower() != 'admin') 
                           or (isinstance(user, str) and user.lower() != 'admin')]
        
        username = st.selectbox("Select user to delete:", non_admin_users)
        
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

def show_app_dashboard():
    """Display the application dashboard for admins"""
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
    
    # System information
    st.write("### System Information")
    
    # Email configuration status
    email_config = check_email_config()
    if email_config["configured"]:
        st.success("✅ Email service is configured")
        st.write(f"Email server: {email_config['server']}")
        st.write(f"Email user: {email_config['user']}")
    else:
        st.error("❌ Email service is not configured")
        st.write("Please set EMAIL_USER, EMAIL_PASSWORD, and EMAIL_SERVER environment variables or in Streamlit secrets.")
    
    # Show environment information
    st.write("### Environment")
    
    # Show Python version
    import sys
    st.write(f"Python version: {sys.version}")
    
    # Show Streamlit version 
    import streamlit as st
    st.write(f"Streamlit version: {st.__version__}")
    
    # Show environment type
    if 'HOSTNAME' in os.environ and os.environ['HOSTNAME'].endswith('.streamlit.app'):
        st.write("Running on: Streamlit Cloud")
    else:
        st.write("Running on: Local development")

def check_email_config():
    """Check if email service is configured"""
    email_user = os.environ.get("EMAIL_USER") or (st.secrets.get("EMAIL_USER", "") if hasattr(st, "secrets") else "")
    email_password = os.environ.get("EMAIL_PASSWORD") or (st.secrets.get("EMAIL_PASSWORD", "") if hasattr(st, "secrets") else "")
    email_server = os.environ.get("EMAIL_SERVER") or (st.secrets.get("EMAIL_SERVER", "smtp.gmail.com") if hasattr(st, "secrets") else "smtp.gmail.com")
    
    return {
        "configured": bool(email_user and email_password),
        "user": email_user or "Not configured",
        "server": email_server
    }