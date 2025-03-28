# forget_password.py
import streamlit as st
import os
from auth import (
    get_user_email, send_email, generate_token, verify_email,
    request_password_reset, reset_password, check_email_verified
)

def get_base_url():
    """Get the base URL of the application"""
    # Try to get from Streamlit, fallback to localhost
    if hasattr(st, 'session_state') and 'base_url' in st.session_state:
        return st.session_state.base_url
    
    # Check if running on Streamlit Cloud
    if os.environ.get('HOSTNAME', '').endswith('.streamlit.app'):
        return f"https://{os.environ.get('HOSTNAME')}"
    
    # Local development fallback
    return "http://localhost:10000"

def forgot_password_page():
    """Display the forgot password form"""
    # Custom CSS similar to login page
    st.markdown(
        f"""
        <style>
        /* Center alignment */
        .center-column {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        /* Form container */
        .form-container {{
            background-color: rgba(25, 26, 22, 0.7);
            padding: 30px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        
        /* Page header */
        .page-header {{
            text-align: center;
            margin: 1rem 0;
            color: #cfcfcc;
            font-size: 1.8rem;
            font-weight: 450;
        }}
        
        .stButton button {{
            background-color: #8a6d17 !important;
            color: white !important;
            width: 100%;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown('<div class="center-column">', unsafe_allow_html=True)
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    
    st.markdown('<h2 class="page-header">Reset Your Password</h2>', unsafe_allow_html=True)
    
    email = st.text_input("Enter your email address")
    
    if st.button("Reset Password"):
        if not email:
            st.error("Please enter your email address.")
        else:
            # Check if email exists and send reset link
            reset_info = request_password_reset(email)
            
            if reset_info:
                # Generate reset URL
                reset_url = f"{get_base_url()}/reset_password/{reset_info['token']}"
                
                # Prepare email
                email_subject = "WealthWise - Password Reset"
                email_body = f"""
                <html>
                <body>
                    <h2>WealthWise Password Reset</h2>
                    <p>Hello {reset_info['username']},</p>
                    <p>We received a request to reset your password. Click the link below to reset your password:</p>
                    <p><a href="{reset_url}">{reset_url}</a></p>
                    <p>This link will expire in 1 hour.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                    <p>Regards,<br>The WealthWise Team</p>
                </body>
                </html>
                """
                
                # Send email
                if send_email(email, email_subject, email_body):
                    st.success("Password reset link has been sent to your email address. Please check your inbox.")
                else:
                    st.error("Failed to send password reset email. Please try again later or contact support.")
            else:
                # Don't reveal if email exists for security
                st.info("If this email is registered, you will receive a password reset link. Please check your inbox.")
    
    if st.button("Back to Login"):
        st.session_state.forgot_password = False
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def reset_password_page(token):
    """Display the password reset form"""
    # Custom CSS similar to login page
    st.markdown(
        f"""
        <style>
        /* Center alignment */
        .center-column {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        /* Form container */
        .form-container {{
            background-color: rgba(25, 26, 22, 0.7);
            padding: 30px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        
        /* Page header */
        .page-header {{
            text-align: center;
            margin: 1rem 0;
            color: #cfcfcc;
            font-size: 1.8rem;
            font-weight: 450;
        }}
        
        .stButton button {{
            background-color: #8a6d17 !important;
            color: white !important;
            width: 100%;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown('<div class="center-column">', unsafe_allow_html=True)
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    
    st.markdown('<h2 class="page-header">Set New Password</h2>', unsafe_allow_html=True)
    
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm New Password", type="password")
    
    if st.button("Update Password", type="primary"):
        if not new_password:
            st.error("Please enter a new password.")
        elif new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            if reset_password(token, new_password):
                st.success("Your password has been reset successfully! You can now log in with your new password.")
                # Add a button to return to login
                if st.button("Go to Login"):
                    # Reset the token and return to login page
                    st.session_state.reset_token = None
                    st.rerun()
            else:
                st.error("Invalid or expired password reset link. Please request a new password reset.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def verify_email_page(token):
    """Display the email verification page"""
    # Custom CSS similar to login page
    st.markdown(
        f"""
        <style>
        /* Center alignment */
        .center-column {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        /* Form container */
        .form-container {{
            background-color: rgba(25, 26, 22, 0.7);
            padding: 30px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        
        /* Page header */
        .page-header {{
            text-align: center;
            margin: 1rem 0;
            color: #cfcfcc;
            font-size: 1.8rem;
            font-weight: 450;
        }}
        
        .stButton button {{
            background-color: #8a6d17 !important;
            color: white !important;
            width: 100%;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown('<div class="center-column">', unsafe_allow_html=True)
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    
    st.markdown('<h2 class="page-header">Email Verification</h2>', unsafe_allow_html=True)
    
    if verify_email(token):
        st.success("Your email has been verified successfully! You can now log in to your account.")
    else:
        st.error("Invalid or expired verification link. Please request a new verification email.")
    
    if st.button("Go to Login"):
        # Reset the token and return to login page
        st.session_state.verify_token = None
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def resend_verification_email():
    """Resend verification email"""
    username = st.session_state.username
    email = get_user_email(username)
    
    if not email:
        st.error("Could not find your email address. Please contact support.")
        return
    
    # Generate verification token
    token = generate_token('email_verification', username, email)
    
    # Generate verification URL
    verification_url = f"{get_base_url()}/verify_email/{token}"
    
    # Prepare email
    email_subject = "WealthWise - Email Verification"
    email_body = f"""
    <html>
    <body>
        <h2>WealthWise Email Verification</h2>
        <p>Hello {username},</p>
        <p>Thank you for registering with WealthWise. Please click the link below to verify your email:</p>
        <p><a href="{verification_url}">{verification_url}</a></p>
        <p>If you didn't register for WealthWise, please ignore this email.</p>
        <p>Regards,<br>The WealthWise Team</p>
    </body>
    </html>
    """
    
    # Send email
    if send_email(email, email_subject, email_body):
        st.success("Verification email has been sent. Please check your inbox.")
    else:
        st.error("Failed to send verification email. Please try again later or contact support.")

def send_verification_email(username, email):
    """Send verification email to a newly registered user"""
    # Generate verification token
    token = generate_token('email_verification', username, email)
    
    # Generate verification URL
    verification_url = f"{get_base_url()}/verify_email/{token}"
    
    # Prepare email
    email_subject = "WealthWise - Email Verification"
    email_body = f"""
    <html>
    <body>
        <h2>WealthWise Email Verification</h2>
        <p>Hello {username},</p>
        <p>Thank you for registering with WealthWise. Please click the link below to verify your email:</p>
        <p><a href="{verification_url}">{verification_url}</a></p>
        <p>If you didn't register for WealthWise, please ignore this email.</p>
        <p>Regards,<br>The WealthWise Team</p>
    </body>
    </html>
    """
    
    # Send email
    return send_email(email, email_subject, email_body)