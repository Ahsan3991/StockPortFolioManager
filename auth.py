# auth.py
import streamlit as st
import os
import json
import hashlib
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

def register_user(username, password):
    """Register a new user with password"""
    users = load_users()
    
    # Convert username to lowercase for comparison
    username_lower = username.lower()
    
    # Check if username already exists
    if any(user.get('username', '').lower() == username_lower for user in users):
        return False
    
    # Hash the password
    hashed_password = hash_password(password)
    
    # Add new user with hashed password
    user_data = {
        'username': username,
        'password': hashed_password
    }
    users.append(user_data)
    save_users(users)
    
    # Initialize the database for this user
    initialize_user_db(username)
    return True

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

def user_exists(username):
    """Check if a user exists"""
    users = load_users()
    return any(user.get('username', '').lower() == username.lower() for user in users)


def update_user_password(username, new_password):
    """Update a user's password"""
    users = load_users()
    
    # Find the user
    for user in users:
        if user.get('username', '').lower() == username.lower():
            # Update password
            user['password'] = hash_password(new_password)
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
                    # Check if any user needs migration
                    migration_needed = any(
                        not isinstance(user, dict) or 'password' not in user 
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
                        updated_users.append(user)
                    # If it's a dict with just username
                    elif isinstance(user, dict) and 'username' in user:
                        updated_users.append({
                            'username': user['username'],
                            'password': hash_password('default123')  # Temporary default password
                        })
                    # If it's just a username string
                    else:
                        username = user if isinstance(user, str) else str(user)
                        updated_users.append({
                            'username': username,
                            'password': hash_password('default123')  # Temporary default password
                        })
                
                save_users(updated_users)
                return
                
            # If it's a list of strings (old format)
            elif isinstance(existing_data, list) and all(isinstance(u, str) for u in existing_data):
                updated_users = [
                    {'username': username, 'password': hash_password('default123')}
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