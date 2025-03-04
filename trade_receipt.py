#trade receipt
import streamlit as st
import sqlite3
import pdfplumber
import json
import re
import time
#from gpt4all import GPT4All
import pandas as pd
from datetime import datetime


def clean_stock_name(stock_name):
    """Cleans the stock name by removing 'Ready' suffix and extra whitespace."""
    if isinstance(stock_name, str):
        # Remove 'Ready' suffix and trim whitespace
        cleaned = stock_name.split('Ready')[0].strip()
        return cleaned
    return stock_name


def insert_trade(date, memo_number, stock, quantity, rate, comm_amount, cdc_charges, sales_tax, total_amount, trade_type):
    """Inserts a trade record into the database with retry logic to handle locked database issues."""
    max_retries = 5
    retry_delay = 1

    # Clean the stock name before insertion
    stock = clean_stock_name(stock)

    for attempt in range(max_retries):
        from db_utils import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("PRAGMA journal_mode=WAL;")

            total_amount = float(str(total_amount).replace(",", ""))
            from utils import normalize_date_format
            normalize_date = normalize_date_format(date)

            cursor.execute("""
                INSERT INTO trades (date, memo_number, stock, quantity, rate, comm_amount, cdc_charges, sales_tax, total_amount, type) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (normalize_date, memo_number, stock, quantity, rate, comm_amount, cdc_charges, sales_tax, total_amount, trade_type))

            conn.commit()
            return

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                st.warning(f"Database is locked. Retrying in {retry_delay} second(s)... ({attempt+1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                st.error(f"Database error: {str(e)}")
                break

        finally:
            conn.close()

    st.error("❌ Could not insert trade after multiple attempts due to database locking.")


# ✅ **Manual Entry UI**
def manual_trade_entry():
    """Allows manual entry of multiple trades under an optional memo number."""
    st.header("Manual Trade Entry")
    
    # Initialize session state variables
    if 'trades_list' not in st.session_state:
        st.session_state.trades_list = []
    if 'current_memo' not in st.session_state:
        st.session_state.current_memo = None

    st.subheader("Enter Trade Details")

    # Memo Number (Optional)
    if st.session_state.current_memo is None:
        raw_memo_number = st.text_input(
            "Memo Number (Optional)",
            help="Enter the memo number if you have it; leave blank otherwise."
        )
        # Default to "UNKNOWN" if blank
        if not raw_memo_number.strip():
            raw_memo_number = "UNKNOWN"
        st.session_state.current_memo = raw_memo_number
    else:
        st.success(f"📌 Adding trades under Memo: {st.session_state.current_memo}")

    memo_number = st.session_state.current_memo

    # Trade Details Input
    col1, col2 = st.columns(2)
    with col1:
        purchase_date = st.date_input("Date of Purchase (Required)", help="Select the date when the trade was executed")
        formatted_date = purchase_date.strftime('%B %d, %Y')
        stock_name = st.text_input("Stock Name (Required)", help="Enter the name of the stock")
        number_of_stocks = st.number_input("Number of Shares (Required)", min_value=1, format="%d",
                                          help="Enter the total number of shares")
    with col2:
        rate_per_share = st.number_input("Rate per Share (Rs.)", min_value=0.0, format="%.4f",
                                         help="Enter the price per share")
        commission_charges = st.number_input("Commission Charges (Rs.)", min_value=0.0, format="%.2f",
                                             help="Enter broker's commission")
        cdc_charges = st.number_input("CDC Charges (Rs.)", min_value=0.0, format="%.2f",
                                      help="Enter CDC charges")
        sales_tax = st.number_input("Sales Tax (Rs.)", min_value=0.0, format="%.2f",
                                    help="Enter the sales tax amount")

    # Calculate summary
    stock_value = rate_per_share * number_of_stocks
    total_charges = commission_charges + cdc_charges + sales_tax
    total_amount = stock_value + total_charges

    st.subheader("Transaction Summary")
    col_sum1, col_sum2, col_sum3 = st.columns(3)
    with col_sum1:
        st.metric("Stock Value", f"Rs. {stock_value:,.2f}")
    with col_sum2:
        st.metric("Total Charges", f"Rs. {total_charges:,.2f}")
    with col_sum3:
        st.metric("Total Amount", f"Rs. {total_amount:,.2f}")

    # Action buttons
    button_col1, button_col2, button_col3 = st.columns([1, 1, 1])

    with button_col1:
        # Add Another Trade button
        if st.button("➕ Add Another Trade"):
            # Validate current trade data
            if not stock_name or rate_per_share <= 0:
                st.error("Please fill in all required fields before adding another trade.")
                return

            trade_data = {
                'memo_number': memo_number,
                'purchase_date': formatted_date,
                'stock_name': stock_name,
                'number_of_stocks': number_of_stocks,
                'rate_per_share': rate_per_share,
                'commission_charges': commission_charges,
                'cdc_charges': cdc_charges,
                'sales_tax': sales_tax,
                'total_amount': total_amount
            }
            st.session_state.trades_list.append(trade_data)
            st.success(f"✅ Added {stock_name} to memo: {memo_number}")

    with button_col2:
        # Submit button
        if st.button("✅ Submit Trade(s)", type="primary"):
            # Validate current trade
            if not stock_name or rate_per_share <= 0:
                st.error("Please fill in all required fields.")
                return

            # Add current trade to list if not empty
            if stock_name and rate_per_share > 0:
                current_trade = {
                    'memo_number': memo_number,
                    'purchase_date': formatted_date,
                    'stock_name': stock_name,
                    'number_of_stocks': number_of_stocks,
                    'rate_per_share': rate_per_share,
                    'commission_charges': commission_charges,
                    'cdc_charges': cdc_charges,
                    'sales_tax': sales_tax,
                    'total_amount': total_amount
                }
                if current_trade not in st.session_state.trades_list:
                    st.session_state.trades_list.append(current_trade)

            # Insert trades into the database
            from db_utils import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("BEGIN TRANSACTION")

                # Insert all trades
                trades_to_insert = st.session_state.trades_list or [current_trade]
                for trade in trades_to_insert:
                    cursor.execute("""
                        INSERT INTO trades (
                            date, memo_number, stock, quantity, rate, 
                            comm_amount, cdc_charges, sales_tax, total_amount, type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade['purchase_date'],
                        trade['memo_number'],
                        clean_stock_name(trade['stock_name']),
                        trade['number_of_stocks'],
                        trade['rate_per_share'],
                        trade['commission_charges'],
                        trade['cdc_charges'],
                        trade['sales_tax'],
                        trade['total_amount'],
                        "Buy"
                    ))

                cursor.execute("COMMIT")
                st.success(f"✅ Trade(s) under Memo {memo_number} have been saved!")

                # Reset session state and form
                st.session_state.trades_list = []
                st.session_state.current_memo = None

                # Clear all form inputs by resetting their keys in session state
                for key in list(st.session_state.keys()):
                    if key.startswith(('stock_name_', 'rate_', 'shares_', 'commission_', 'cdc_', 'tax_')):
                        del st.session_state[key]

                # Add a button to start a new trade
                if st.button("➕ Add New Trade", type="primary"):
                    st.rerun()

                # (Optional) Show Updated Trades
                if st.session_state.get('show_trades', False):
                    display_trades()

                # Automatically rerun to clear the form
                time.sleep(1)
                st.rerun()

            except sqlite3.Error as e:
                cursor.execute("ROLLBACK")
                st.error(f"❌ Failed to save trades: {str(e)}")
            finally:
                conn.close()

    with button_col3:
        # Cancel button
        if st.button("❌ Cancel"):
            st.session_state.trades_list = []
            st.session_state.current_memo = None
            st.warning("Trade entry canceled.")
            st.rerun()

    # Show number of trades added so far
    if st.session_state.trades_list:
        st.info(f"🔄 {len(st.session_state.trades_list)} trade(s) ready to submit under memo {memo_number}")

    # Option to View Trades
    show_trades = st.checkbox("📜 View Existing Trades", value=st.session_state.get('show_trades', False))
    st.session_state.show_trades = show_trades
    if show_trades:
        display_trades()

#Display the trade information        
def display_trades():
    """Displays all stored trades in a table format."""
    from db_utils import get_db_connection
    conn = get_db_connection()
    try:
        query = """
            SELECT 
                date as 'Date',
                memo_number as 'Memo No',
                stock as 'Stock',
                quantity as 'Shares',
                rate as 'Rate',
                comm_amount as 'Commission',
                cdc_charges as 'CDC Charges',
                sales_tax as 'Sales Tax',
                total_amount as 'Total Amount',
                type as 'Type'
            FROM trades
            ORDER BY date DESC
        """
        
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            st.write("### Trade History")
            
            # Format numeric columns
            numeric_cols = ['Rate', 'Commission', 'CDC Charges', 'Sales Tax', 'Total Amount']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].round(2)
            
            # Display the dataframe
            st.dataframe(
                df,
                column_config={
                    "Rate": st.column_config.NumberColumn(format="%.2f"),
                    "Commission": st.column_config.NumberColumn(format="%.2f"),
                    "CDC Charges": st.column_config.NumberColumn(format="%.2f"),
                    "Sales Tax": st.column_config.NumberColumn(format="%.2f"),
                    "Total Amount": st.column_config.NumberColumn(format="%.2f")
                },
                hide_index=True
            )
            
            # Display summary
            st.write("### Summary")
            total_invested = df['Total Amount'].sum()
            total_shares = df['Shares'].sum()
            total_commission = df['Commission'].sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Investment", f"Rs. {total_invested:,.2f}")
            with col2:
                st.metric("Total Shares", f"{total_shares:,}")
            with col3:
                st.metric("Total Commission", f"Rs. {total_commission:,.2f}")
                
        else:
            st.info("No trade records found.")
            
    except Exception as e:
        st.error(f"Error fetching trade records: {str(e)}")
        st.info("If you just created the database, this is normal. Add some trades first.")
    finally:
        conn.close()