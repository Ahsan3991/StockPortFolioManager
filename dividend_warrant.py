import streamlit as st
import sqlite3
#import pdfplumber
import json
import re
#from gpt4all import GPT4All
from datetime import datetime
import pandas as pd  # Add this import at the top


def insert_dividend(warrant_no, payment_date, stock_name, rate_per_security, number_of_securities, amount_of_dividend, tax_deducted, amount_paid):
    """Inserts a dividend record into the database."""
    from db_utils import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        st.info(f"Processing dividend for warrant {warrant_no}")
        
        
        # First, ensure the warrant exists in the warrants table
        cursor.execute("INSERT OR IGNORE INTO warrants (warrant_no) VALUES (?)", (warrant_no,))
        
        # Normalize date format to YYYY-MM-DD format for consistent storage
        try:
            # Check what format the date is in
            if isinstance(payment_date, str):
                # Try different date formats
                try:
                    # Try DD-MM-YYYY format
                    if '-' in payment_date:
                        parts = payment_date.split('-')
                        if len(parts[0]) == 2:  # DD-MM-YYYY
                            from datetime import datetime
                            date_obj = datetime.strptime(payment_date, '%d-%m-%Y')
                            payment_date = date_obj.strftime('%Y-%m-%d')
                    # Try YYYY/MM/DD format        
                    elif '/' in payment_date:
                        parts = payment_date.split('/')
                        if len(parts[0]) == 4:  # YYYY/MM/DD
                            from datetime import datetime
                            date_obj = datetime.strptime(payment_date, '%Y/%m/%d')
                            payment_date = date_obj.strftime('%Y-%m-%d')
                except Exception as e:
                    # If date parsing fails, just use the date as is
                    st.warning(f"Date format conversion issue: {e}. Using date as provided.")
        except Exception as e:
            st.warning(f"Error handling date format: {str(e)}")
        
        # Then insert the dividend details
        from utils import normalize_date_format
        normalize_date = normalize_date_format(payment_date)
        cursor.execute("""
            INSERT INTO dividends (
                warrant_no, payment_date, stock_name, rate_per_security, 
                number_of_securities, amount_of_dividend, tax_deducted, amount_paid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (warrant_no, normalize_date, stock_name, rate_per_security, 
              number_of_securities, amount_of_dividend, tax_deducted, amount_paid))
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Database error: {str(e)}")
        st.info("Please check database connection and schema")
        return False
    finally:
        conn.close()

def display_stored_dividends():
    """Displays all stored dividends in a table format."""
    from db_utils import get_db_connection
    conn = get_db_connection()
    try:
        query = """
            SELECT 
                d.warrant_no,
                d.payment_date,
                d.stock_name,
                d.rate_per_security,
                d.number_of_securities,
                d.amount_of_dividend,
                d.tax_deducted,
                d.amount_paid
            FROM dividends d
            JOIN warrants w ON d.warrant_no = w.warrant_no
            ORDER BY d.payment_date DESC
        """
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            st.write("### Stored Dividends")
            st.dataframe(df)
        else:
            st.info("No dividend records found.")
    except Exception as e:
        st.error(f"Error fetching dividend records: {str(e)}")
    finally:
        conn.close()


def manual_dividend_entry():
    """Allows manual entry of dividend details into the database."""
    st.header("Manual Dividend Entry")
    
    # Initialize session state variables
    if 'confirm_stage' not in st.session_state:
        st.session_state.confirm_stage = False
        st.session_state.dividend_data = None
    
    # Create two columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Basic Information")
        warrant_no = st.text_input(
            "Warrant Number (Required)", 
            help="Enter the unique warrant number from your dividend warrant"
        )
        
        payment_date = st.date_input(
            "Payment Date", 
            help="Select the date when the dividend was paid"
        )
        
        stock_name = st.text_input(
            "Stock Name (Required)",
            help="Enter the name of the company that paid the dividend"
        )

    with col2:
        st.subheader("Dividend Details")
        rate_per_security = st.number_input(
            "Rate per Security (Rs.)", 
            min_value=0.0, 
            format="%.4f",
            help="Enter the dividend amount per share"
        )
        
        number_of_securities = st.number_input(
            "Number of Securities", 
            min_value=1, 
            format="%d",
            help="Enter the total number of shares"
        )
        
        tax_percentage = st.number_input(
            "Tax Rate (%)", 
            min_value=0.0, 
            max_value=100.0, 
            value=15.0,  # Default tax rate
            format="%.2f",
            help="Enter the tax rate applied to the dividend"
        )

    # Calculate values
    amount_of_dividend = rate_per_security * number_of_securities
    tax_deducted = amount_of_dividend * (tax_percentage / 100)
    amount_paid = amount_of_dividend - tax_deducted

    # Display calculated values in a nice format
    st.subheader("Calculated Values")
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    
    with metric_col1:
        st.metric(
            label="Gross Dividend",
            value=f"Rs. {amount_of_dividend:,.2f}",
            help="Total dividend amount before tax"
        )
    
    with metric_col2:
        st.metric(
            label="Tax Deducted",
            value=f"Rs. {tax_deducted:,.2f}",
            help="Tax amount to be deducted"
        )
    
    with metric_col3:
        st.metric(
            label="Net Amount",
            value=f"Rs. {amount_paid:,.2f}",
            help="Final amount after tax deduction"
        )

    # Add divider for visual separation
    st.divider()

    def reset_form():
        st.session_state.confirm_stage = False
        st.session_state.dividend_data = None

    def proceed_to_confirm():
        st.session_state.confirm_stage = True
        st.session_state.dividend_data = {
            'warrant_no': warrant_no,
            'payment_date': payment_date,
            'stock_name': stock_name,
            'rate_per_security': rate_per_security,
            'number_of_securities': number_of_securities,
            'amount_of_dividend': amount_of_dividend,
            'tax_deducted': tax_deducted,
            'amount_paid': amount_paid
        }

    if not st.session_state.confirm_stage:
        if st.button("Add Dividend", type="primary", on_click=proceed_to_confirm):
            # Validate inputs
            errors = []
            
            if not warrant_no.strip():
                errors.append("Warrant number is required")
            
            if not stock_name.strip():
                errors.append("Stock name is required")
            
            if rate_per_security <= 0:
                errors.append("Rate per security must be greater than 0")
            
            if number_of_securities <= 0:
                errors.append("Number of securities must be greater than 0")

            # Check for existing warrant
            if warrant_no.strip():
                from db_utils import get_db_connection
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM warrants WHERE warrant_no = ?", (warrant_no,))
                existing_count = cursor.fetchone()[0]
                conn.close()

                if existing_count > 0:
                    errors.append(f"Warrant number {warrant_no} already exists")

            # Display any validation errors
            if errors:
                for error in errors:
                    st.error(error)
                reset_form()
                return

    else:
        # Show confirmation
        st.info("Please verify the information before confirming:")
        dividend_data = st.session_state.dividend_data
        st.write(f"""
        - Warrant No: {dividend_data['warrant_no']}
        - Stock: {dividend_data['stock_name']}
        - Payment Date: {dividend_data['payment_date'].strftime('%d-%m-%Y')}
        - Shares: {dividend_data['number_of_securities']:,}
        - Rate/Share: Rs. {dividend_data['rate_per_security']:.4f}
        - Gross Amount: Rs. {dividend_data['amount_of_dividend']:,.2f}
        - Tax Deducted: Rs. {dividend_data['tax_deducted']:,.2f}
        - Net Amount: Rs. {dividend_data['amount_paid']:,.2f}
        """)

        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Confirm", type="primary"):
                success = insert_dividend(
                    dividend_data['warrant_no'],
                    dividend_data['payment_date'].strftime("%d-%m-%Y"),
                    dividend_data['stock_name'],
                    dividend_data['rate_per_security'],
                    dividend_data['number_of_securities'],
                    dividend_data['amount_of_dividend'],
                    dividend_data['tax_deducted'],
                    dividend_data['amount_paid']
                )

                if success:
                    st.success("✅ Dividend added successfully!")
                    reset_form()
                    # Show the updated records
                    display_stored_dividends()
                else:
                    st.error("Failed to add dividend. Please try again.")
                    
        with col2:
            if st.button("Cancel", on_click=reset_form):
                pass

    # Option to view existing records
    if st.checkbox("View Existing Dividend Records"):
        display_stored_dividends()