# auth.py
import streamlit as st
import os
import json
import hashlib
import smtplib
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from db_utils import initialize_user_db

# Email configuration
def get_email_config():
    """Get email configuration from environment variables or secrets"""
    email_user = os.environ.get("EMAIL_USER") or st.secrets.get("EMAIL_USER", "")
    email_password = os.environ.get("EMAIL_PASSWORD") or st.secrets.get("EMAIL_PASSWORD", "")
    email_server = os.environ.get("EMAIL_SERVER") or st.secrets.get("EMAIL_SERVER", "smtp.gmail.com")
    email_port = int(os.environ.get("EMAIL_PORT") or st.secrets.get("EMAIL_PORT", 587))
    
    return {
        "user": email_user,
        "password": email_password,
        "server": email_server,
        "port": email_port
    }

def send_email(to_email, subject, body, is_html=True):
    """Send an email using the configured email settings"""
    config = get_email_config()
    
    # Check if email credentials are configured
    if not config["user"] or not config["password"]:
        st.error("Email settings are not configured. Please set up EMAIL_USER and EMAIL_PASSWORD.")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = config["user"]
        msg['To'] = to_email
        msg['Subject'] = subject
        
        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(config["server"], config["port"])
        server.starttls()
        server.login(config["user"], config["password"])
        server.send_message(msg)
        server.quit()
        return True
    
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")
        return False

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

def get_tokens_file_path():
    """Get the path to the tokens file for password reset and email verification"""
    # For Streamlit Cloud, we need to use a writable directory
    base_dir = os.environ.get('HOME', '')
    
    # If running on Streamlit Cloud, use a subdirectory in HOME
    if os.path.exists(base_dir) and os.access(base_dir, os.W_OK):
        data_dir = os.path.join(base_dir, 'wealthwise_data')
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "tokens.json")
    else:
        # Fallback to local directory for local development
        return "tokens.json"

def hash_password(password):
    """Create a SHA-256 hash of the password"""
    return hashlib.sha256(password.encode()).hexdigest()

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

def load_tokens():
    """Load tokens from file"""
    tokens_file = get_tokens_file_path()
    if os.path.exists(tokens_file):
        with open(tokens_file, 'r') as f:
            return json.load(f)
    return {}

def save_tokens(tokens):
    """Save tokens to file"""
    tokens_file = get_tokens_file_path()
    with open(tokens_file, 'w') as f:
        json.dump(tokens, f)

def clear_expired_tokens():
    """Remove expired tokens"""
    tokens = load_tokens()
    now = datetime.now().isoformat()
    
    valid_tokens = {k: v for k, v in tokens.items() if v.get('expires', now) > now}
    
    if len(valid_tokens) != len(tokens):
        save_tokens(valid_tokens)
    
    return valid_tokens

def generate_token(token_type, username, email, expiry_hours=24):
    """Generate a unique token for email verification or password reset"""
    tokens = clear_expired_tokens()
    
    # Generate a unique token
    token = str(uuid.uuid4())
    
    # Set expiry time
    expiry = (datetime.now() + timedelta(hours=expiry_hours)).isoformat()
    
    # Store token
    tokens[token] = {
        'type': token_type,
        'username': username,
        'email': email,
        'expires': expiry,
        'used': False
    }
    
    save_tokens(tokens)
    return token

def validate_token(token, token_type):
    """Validate a token and mark it as used if valid"""
    tokens = clear_expired_tokens()
    
    if token not in tokens:
        return None
    
    token_data = tokens[token]
    
    # Check if token is of correct type and not used
    if token_data.get('type') != token_type or token_data.get('used', False):
        return None
    
    # Mark token as used
    tokens[token]['used'] = True
    save_tokens(tokens)
    
    return token_data

def register_user(username, password, email):
    """Register a new user with email"""
    users = load_users()
    
    # Convert username to lowercase for comparison
    username_lower = username.lower()
    email_lower = email.lower()
    
    # Check if username already exists
    if any(user.get('username', '').lower() == username_lower for user in users):
        return {'success': False, 'message': "Username already exists"}
    
    # Check if email already exists
    if any(user.get('email', '').lower() == email_lower for user in users):
        return {'success': False, 'message': "Email already in use"}
    
    # Generate verification token
    token = generate_token('email_verification', username, email)
    
    # Hash the password
    hashed_password = hash_password(password)
    
    # Add new user with hashed password and email (not verified yet)
    user_data = {
        'username': username,
        'password': hashed_password,
        'email': email,
        'email_verified': False,
        'created_at': datetime.now().isoformat()
    }
    users.append(user_data)
    save_users(users)
    
    # Initialize the database for this user
    initialize_user_db(username)
    
    # Return success with token
    return {
        'success': True, 
        'message': "User registered successfully",
        'token': token
    }

def verify_email(token):
    """Verify a user's email using a verification token"""
    token_data = validate_token(token, 'email_verification')
    
    if not token_data:
        return False
    
    username = token_data.get('username')
    users = load_users()
    
    # Find and update the user
    for user in users:
        if user.get('username') == username:
            user['email_verified'] = True
            user['verified_at'] = datetime.now().isoformat()
            save_users(users)
            return True
    
    return False

def verify_credentials(username, password):
    """Verify username and password"""
    users = load_users()
    
    # Convert username to lowercase for case-insensitive comparison
    username_lower = username.lower()
    
    # Find user
    user = next((user for user in users if user.get('username', '').lower() == username_lower), None)
    
    if user:
        # Hash the provided password and compare with stored hash
        hashed_password = hash_password(password)
        return hashed_password == user.get('password', '')
    
    return False

def check_email_verified(username):
    """Check if a user's email is verified"""
    users = load_users()
    
    # Find user
    user = next((user for user in users if user.get('username', '').lower() == username.lower()), None)
    
    if user:
        return user.get('email_verified', False)
    
    return False

def user_exists(username):
    """Check if a user exists"""
    users = load_users()
    return any(user.get('username', '').lower() == username.lower() for user in users)

def get_user_email(username):
    """Get a user's email address"""
    users = load_users()
    
    # Find user
    user = next((user for user in users if user.get('username', '').lower() == username.lower()), None)
    
    if user:
        return user.get('email')
    
    return None

def request_password_reset(email):
    """Generate a password reset token for a given email"""
    users = load_users()
    email_lower = email.lower()
    
    # Find user by email
    user = next((user for user in users if user.get('email', '').lower() == email_lower), None)
    
    if not user:
        return None
    
    username = user.get('username')
    
    # Generate reset token
    token = generate_token('password_reset', username, email, expiry_hours=1)
    
    return {
        'username': username,
        'token': token
    }

def reset_password(token, new_password):
    """Reset a user's password using a valid token"""
    token_data = validate_token(token, 'password_reset')
    
    if not token_data:
        return False
    
    username = token_data.get('username')
    users = load_users()
    
    # Find and update the user
    for user in users:
        if user.get('username') == username:
            user['password'] = hash_password(new_password)
            user['password_reset_at'] = datetime.now().isoformat()
            save_users(users)
            return True
    
    return False

def update_user_password(username, new_password):
    """Update a user's password"""
    users = load_users()
    
    # Find the user
    for user in users:
        if user.get('username', '').lower() == username.lower():
            # Update password
            user['password'] = hash_password(new_password)
            user['password_updated_at'] = datetime.now().isoformat()
            save_users(users)
            return True
    
    return False

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
    users = [user for user in users if user.get('username', '').lower() != username.lower()]
    save_users(users)
    
    return True

# Function to migrate existing users to new format with passwords
def migrate_users_to_password_system():
    """Migrate existing users to the new password format"""
    users_file = get_users_file_path()
    
    # Check if file exists first
    if not os.path.exists(users_file):
        # Create an empty users file
        save_users([])
        return
    
    try:
        with open(users_file, 'r') as f:
            data = f.read().strip()
            # Check if the file is empty
            if not data:
                save_users([])
                return
                
            # Try to parse existing data
            existing_data = json.loads(data)
            
            # If it's already a list of dicts, check if migration is needed
            if isinstance(existing_data, list):
                if all(isinstance(user, dict) for user in existing_data):
                    # Check if any user needs migration to include email
                    migration_needed = any(
                        not isinstance(user, dict) or 
                        'password' not in user or
                        'email' not in user
                        for user in existing_data
                    )
                    
                    if not migration_needed:
                        # No migration needed
                        return
                        
                # Update format for users
                updated_users = []
                
                for user in existing_data:
                    # If it's already a dict with username and password
                    if isinstance(user, dict) and 'username' in user and 'password' in user:
                        # Add email field if missing
                        if 'email' not in user:
                            user['email'] = f"{user['username']}@example.com"
                            user['email_verified'] = False
                        updated_users.append(user)
                    # If it's a dict with just username
                    elif isinstance(user, dict) and 'username' in user:
                        updated_users.append({
                            'username': user['username'],
                            'password': hash_password('default123'),  # Temporary default password
                            'email': f"{user['username']}@example.com",
                            'email_verified': False
                        })
                    # If it's just a username string
                    else:
                        username = user if isinstance(user, str) else str(user)
                        updated_users.append({
                            'username': username,
                            'password': hash_password('default123'),  # Temporary default password
                            'email': f"{username}@example.com",
                            'email_verified': False
                        })
                
                save_users(updated_users)
                return
                
            # If it's a list of strings (old format)
            elif isinstance(existing_data, list) and all(isinstance(u, str) for u in existing_data):
                updated_users = [
                    {
                        'username': username, 
                        'password': hash_password('default123'),
                        'email': f"{username}@example.com",
                        'email_verified': False
                    }
                    for username in existing_data
                ]
                save_users(updated_users)
                return
    except json.JSONDecodeError:
        # File exists but isn't valid JSON, create a new one
        save_users([])
    except Exception as e:
        print(f"Error during migration: {e}")
        # In case of any error, create a new users file
        save_users([])