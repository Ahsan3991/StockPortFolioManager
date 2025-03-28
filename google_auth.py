# google_auth.py
import streamlit as st
import os
import json
from datetime import datetime 
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from db_utils import initialize_user_db

# Load OAuth credentials from environment or secrets
def get_oauth_config():
    client_id = os.environ.get("GOOGLE_CLIENT_ID") or st.secrets.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET") or st.secrets.get("GOOGLE_CLIENT_SECRET", "")
    
    if not client_id or not client_secret:
        st.error("Google OAuth credentials are not configured.")
        return None
    
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                "http://localhost:10000/callback",
                f"https://{os.environ.get('HOSTNAME', '')}/callback"
            ]
        }
    }

def get_users_file_path():
    # Same as in auth.py
    base_dir = os.environ.get('HOME', '')
    if os.path.exists(base_dir) and os.access(base_dir, os.W_OK):
        data_dir = os.path.join(base_dir, 'wealthwise_data')
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "registered_users.json")
    else:
        return "registered_users.json"

def load_users():
    users_file = get_users_file_path()
    if os.path.exists(users_file):
        with open(users_file, 'r') as f:
            return json.load(f)
    return []

def save_users(users):
    users_file = get_users_file_path()
    with open(users_file, 'w') as f:
        json.dump(users, f)

def start_google_auth():
    oauth_config = get_oauth_config()
    if not oauth_config:
        return
    
    # Create OAuth flow instance
    flow = Flow.from_client_config(
        oauth_config,
        scopes=["https://www.googleapis.com/auth/userinfo.email", 
                "https://www.googleapis.com/auth/userinfo.profile"],
        redirect_uri=oauth_config["web"]["redirect_uris"][0]  # Use the first redirect URI
    )
    
    # Generate authorization URL
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    
    # Store the flow in session state for later
    st.session_state.flow = flow
    
    # Redirect to Google's OAuth page
    st.markdown(f'<meta http-equiv="refresh" content="0;URL=\'{auth_url}\'">', unsafe_allow_html=True)
    st.write("Redirecting to Google Sign-In...")

def handle_oauth_callback():
    if "flow" not in st.session_state:
        st.error("Authorization flow not found. Please try again.")
        return
    
    try:
        # Get the authorization code from URL parameters
        query_params = st.experimental_get_query_params()
        code = query_params.get("code", [""])[0]
        
        if not code:
            st.error("No authorization code received.")
            return
        
        # Exchange authorization code for tokens
        flow = st.session_state.flow
        flow.fetch_token(code=code)
        
        # Get credentials and build the service
        credentials = flow.credentials
        service = build("oauth2", "v2", credentials=credentials)
        
        # Get user info
        user_info = service.userinfo().get().execute()
        email = user_info.get("email")
        name = user_info.get("name") or email.split("@")[0]
        
        # Store user info in session state
        st.session_state.google_user_info = user_info
        
        # Check if user exists or create a new one
        users = load_users()
        user = next((u for u in users if isinstance(u, dict) and u.get("email") == email), None)
        
        if user:
            # Update existing user
            st.session_state.logged_in = True
            st.session_state.username = user.get("username")
            st.session_state.is_admin = user.get("username").lower() == "admin"
            st.success(f"Welcome back, {user.get('username')}!")
        else:
            # Create new user
            username = email.split("@")[0]
            base_username = username
            
            # Ensure username is unique
            counter = 1
            while any(u.get("username", "").lower() == username.lower() for u in users if isinstance(u, dict)):
                username = f"{base_username}{counter}"
                counter += 1
            
            # Add new user
            user_data = {
                "username": username,
                "email": email,
                "email_verified": True,  # Google OAuth provides verified emails
                "created_at": datetime.now().isoformat(),
                "oauth_provider": "google"
            }
            users.append(user_data)
            save_users(users)
            
            # Initialize database for this user
            initialize_user_db(username)
            
            # Update session state
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.is_admin = False
            
            st.success(f"Welcome {username}! Your account has been created successfully.")
        
        # Remove flow from session state
        del st.session_state.flow
        
        # Redirect to home page
        st.rerun()
        
    except Exception as e:
        st.error(f"Error during Google authentication: {str(e)}")
        # Remove flow from session state
        if "flow" in st.session_state:
            del st.session_state.flow