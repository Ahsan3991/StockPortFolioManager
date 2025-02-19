import streamlit as st
import sqlite3
import pdfplumber
import json
import re
import time
from gpt4all import GPT4All
import pandas as pd
from datetime import datetime

def clean_json_output(json_text):
    """Fixes common JSON formatting issues like misplaced commas in numbers."""
    json_text = re.sub(r'(\d+),(\d+)', r'\1\2', json_text)  # Remove commas in numbers
    
    try:
        parsed_data = json.loads(json_text)  # Try parsing after cleanup
        return parsed_data
    except json.JSONDecodeError as e:
        print("JSON Decoding Failed:", str(e))
        return None

def validate_json_structure(parsed_data):
    """Ensures the JSON has the correct structure."""
    if not isinstance(parsed_data, dict):
        return False
    
    required_keys = {"date", "memo_number", "trades"}
    if not required_keys.issubset(parsed_data.keys()):
        return False
    
    if not isinstance(parsed_data["trades"], list) or len(parsed_data["trades"]) == 0:
        return False
    
    trade_keys = {"stock", "rate", "quantity", "comm_amount", "cdc_charges", "sales_tax", "total_amount"}
    for trade in parsed_data["trades"]:
        if not isinstance(trade, dict) or not trade_keys.issubset(trade.keys()):
            return False
    
    return True

def extract_memo_number(text):
    """Extracts the memo number from the raw trade receipt text using regex."""
    match = re.search(r"Memo\s*#\s*(\d+/\w+)", text, re.IGNORECASE)
    return match.group(1) if match else None

def clean_stock_name(stock_name):
    """Cleans the stock name by removing 'Ready' suffix and extra whitespace."""
    if isinstance(stock_name, str):
        # Remove 'Ready' suffix and trim whitespace
        cleaned = stock_name.split('Ready')[0].strip()
        return cleaned
    return stock_name

def extract_trade_details_with_llm(text):
    """Extracts structured trade details from raw text using GPT4ALL with enforced JSON output."""
    try:
        memo_number = extract_memo_number(text)
        if not memo_number:
            st.error("❌ Unable to extract memo number from the trade receipt.")
            return {}

        with GPT4All("Meta-Llama-3-8B-Instruct.Q4_0.gguf", device="cuda") as model:
            prompt = (
                f"Extract stock trade details from the text in JSON format.\n\n"
                f"Ensure the response contains an object with exactly three keys: 'date', 'memo_number', and 'trades'.\n"
                f"'date' should contain the trade date, 'memo_number' should be '{memo_number}',\n"
                f"'trades' should be a list containing JSON objects with keys: 'stock', 'rate', 'quantity', 'comm_amount', 'cdc_charges', 'sales_tax', and 'total_amount'.\n\n"
                f"Strict JSON format rules:\n"
                f"- Do not add explanations or summaries.\n"
                f"- Ensure numbers do not contain commas.\n"
                f"- Return only JSON output.\n"
                f"- Each trade must have all required fields.\n"
                f"- The JSON should be properly formatted even when there are multiple trades.\n\n"
                f"Process the following trade receipt text:\n"
                f"{text}"
            )

            response = model.generate(prompt, temp=0, max_tokens=800)

            # Debugging: Show raw response
            st.write("### Raw LLM Response:")
            st.text(response[:2000])

            # Extract JSON from response
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                json_data = match.group(0)

                # Clean JSON numbers
                json_data = clean_json_output(json_data)

                if json_data and validate_json_structure(json_data):
                    parsed_data = json_data
                    parsed_data["memo_number"] = memo_number

                    # Clean stock names in the parsed data
                    if 'trades' in parsed_data:
                        for trade in parsed_data['trades']:
                            if 'stock' in trade:
                                trade['stock'] = clean_stock_name(trade['stock'])

                    return parsed_data
                else:
                    st.error("❌ JSON validation failed. Check LLM response format.")
                    return {}
            else:
                st.error("❌ No valid JSON response extracted.")
                return {}

    except json.JSONDecodeError:
        st.error("❌ JSON decoding failed. Check LLM response format.")
        return {}
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        return {}

def extract_raw_text(pdf_file):
    """Extracts raw text from a PDF file."""
    with pdfplumber.open(pdf_file) as pdf:
        return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

def insert_trade(date, memo_number, stock, quantity, rate, comm_amount, cdc_charges, sales_tax, total_amount, trade_type):
    """Inserts a trade record into the database with retry logic to handle locked database issues."""
    max_retries = 5
    retry_delay = 1

    # Clean the stock name before insertion
    stock = clean_stock_name(stock)

    for attempt in range(max_retries):
        conn = sqlite3.connect("portfolio.db", timeout=10)
        cursor = conn.cursor()

        try:
            cursor.execute("PRAGMA journal_mode=WAL;")

            total_amount = float(str(total_amount).replace(",", ""))

            cursor.execute("""
                INSERT INTO trades (date, memo_number, stock, quantity, rate, comm_amount, cdc_charges, sales_tax, total_amount, type) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (date, memo_number, stock, quantity, rate, comm_amount, cdc_charges, sales_tax, total_amount, trade_type))

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

def process_trade_receipt():
    """Handles the Streamlit UI for trade receipt uploads."""
    st.header("Upload Trade Receipt")
    uploaded_file = st.file_uploader("Upload your Trade Confirmation (PDF)", type=["pdf"])

    if uploaded_file is not None:
        raw_text = extract_raw_text(uploaded_file)
        st.write("### Extracted Raw Text from PDF:")
        st.text(raw_text[:2000])

        extracted_data = extract_trade_details_with_llm(raw_text)

        if extracted_data:
            trade_date = extracted_data.get("date", "N/A")
            memo_number = extracted_data.get("memo_number")  # Extracted correctly
            trades = extracted_data.get("trades", [])

            if not memo_number:
                st.error("❌ No memo number found in trade receipt. Please check the file.")
                return

            if not trades:
                st.error("❌ Failed to extract trade details.")
                return

            # Insert new trades in a SINGLE TRANSACTION
            conn = sqlite3.connect("portfolio.db", timeout=10)
            cursor = conn.cursor()
            try:
                cursor.execute("BEGIN TRANSACTION")

                # Insert memo first
                cursor.execute("INSERT INTO memos (memo_number) VALUES (?)", (memo_number,))

                # Insert all trades (directly, without calling `insert_trade`)
                for trade in trades:
                    total_amount = float(str(trade.get("total_amount", 0.0)).replace(",", ""))  # Convert properly
                    cursor.execute("""
                        INSERT INTO trades (date, memo_number, stock, quantity, rate, comm_amount, cdc_charges, sales_tax, total_amount, type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade_date,
                        memo_number,
                        trade.get("stock", "UNKNOWN"),
                        trade.get("quantity", 0),
                        trade.get("rate", 0.0),
                        trade.get("comm_amount", 0.0),
                        trade.get("cdc_charges", 0.0),
                        trade.get("sales_tax", 0.0),
                        total_amount,
                        "Buy"
                    ))

                cursor.execute("COMMIT")
                st.success(f"✅ All trades added successfully under memo number {memo_number}!")

            except sqlite3.Error as e:
                cursor.execute("ROLLBACK")
                st.error(f"❌ Failed to add trades: {str(e)}")
            finally:
                conn.close()

# ✅ **Manual Entry UI**
def manual_trade_entry():
    """Allows manual entry of multiple trades under the same memo number with improved UX."""
    st.header("Manual Trade Entry")
    
    # Initialize session state variables
    if 'trades_list' not in st.session_state:
        st.session_state.trades_list = []
    
    if 'current_memo' not in st.session_state:
        st.session_state.current_memo = None

    st.subheader("Enter Trade Details")

    # Memo Number (Set Once)
    if st.session_state.current_memo is None:
        memo_number = st.text_input("Memo Number (Required)", help="Enter the unique memo number for this trade set")
        if memo_number:
            st.session_state.current_memo = memo_number
    else:
        st.success(f"📌 Adding trades under Memo: {st.session_state.current_memo}")
        memo_number = st.session_state.current_memo

    # Trade Details Input
    col1, col2 = st.columns(2)

    with col1:
        purchase_date = st.date_input("Date of Purchase (Required)", help="Select the date when the trade was executed")
        formatted_date = purchase_date.strftime('%B %d, %Y')
        stock_name = st.text_input("Stock Name (Required)", help="Enter the name of the stock")
        number_of_stocks = st.number_input("Number of Shares (Required)", min_value=1, format="%d", help="Enter the total number of shares")

    with col2:
        rate_per_share = st.number_input("Rate per Share (Rs.)", min_value=0.0, format="%.4f", help="Enter the price per share")
        commission_charges = st.number_input("Commission Charges (Rs.)", min_value=0.0, format="%.2f", help="Enter broker's commission")
        cdc_charges = st.number_input("CDC Charges (Rs.)", min_value=0.0, format="%.2f", help="Enter CDC charges")
        sales_tax = st.number_input("Sales Tax (Rs.)", min_value=0.0, format="%.2f", help="Enter the sales tax amount")

    # Calculate summary
    stock_value = rate_per_share * number_of_stocks
    total_charges = commission_charges + cdc_charges + sales_tax
    total_amount = stock_value + total_charges

    st.subheader("Transaction Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Stock Value", f"Rs. {stock_value:,.2f}")
    with col2:
        st.metric("Total Charges", f"Rs. {total_charges:,.2f}")
    with col3:
        st.metric("Total Amount", f"Rs. {total_amount:,.2f}")

    # Action buttons container
    button_col1, button_col2, button_col3 = st.columns([1, 1, 1])

    with button_col1:
        # Add Another Trade button
        if st.button("➕ Add Another Trade"):
            # Validate current trade data
            if not memo_number or not stock_name or rate_per_share <= 0:
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
            st.success(f"✅ Added {stock_name} to the memo {memo_number}")

    with button_col2:
        # Submit button - always visible
        if st.button("✅ Submit Trade(s)", type="primary"):
            # Validate current trade
            if not memo_number or not stock_name or rate_per_share <= 0:
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

            conn = sqlite3.connect("portfolio.db")
            cursor = conn.cursor()

            try:
                cursor.execute("BEGIN TRANSACTION")

                # Ensure memo is added only once
                cursor.execute("INSERT INTO memos (memo_number) VALUES (?)", (memo_number,))

                # Insert all trades under this memo
                trades_to_insert = st.session_state.trades_list if st.session_state.trades_list else [current_trade]
                
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
                for key in st.session_state.keys():
                    if key.startswith(('stock_name_', 'rate_', 'shares_', 'commission_', 'cdc_', 'tax_')):
                        del st.session_state[key]
                
                # Add a button to start a new trade
                if st.button("➕ Add New Trade", type="primary"):
                    st.rerun()
                
                # Show Updated Trades
                if st.session_state.get('show_trades', False):
                    display_trades()
                    
                # Automatically rerun to clear the form
                time.sleep(1)  # Give user time to see success message
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

def display_trades():
    """Displays all stored trades in a table format."""
    conn = sqlite3.connect("portfolio.db")
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