import streamlit as st
import sqlite3
import pdfplumber
import json
import re
import time
from gpt4all import GPT4All
import pandas as pd

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

                # 🔹 Apply Fix: Clean JSON numbers
                json_data = clean_json_output(json_data)

                if json_data and validate_json_structure(json_data):
                    parsed_data = json_data
                    parsed_data["memo_number"] = memo_number  # Ensure memo number is included
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

    max_retries = 5  # Prevents infinite looping
    retry_delay = 1  # Wait time before retrying

    for attempt in range(max_retries):
        conn = sqlite3.connect("portfolio.db", timeout=10)
        cursor = conn.cursor()

        try:
            cursor.execute("PRAGMA journal_mode=WAL;")  # Use WAL mode to prevent locking

            # Ensure total_amount is converted properly to float (removes comma formatting errors)
            total_amount = float(str(total_amount).replace(",", ""))  

            cursor.execute("""
                INSERT INTO trades (date, memo_number, stock, quantity, rate, comm_amount, cdc_charges, sales_tax, total_amount, type) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (date, memo_number, stock, quantity, rate, comm_amount, cdc_charges, sales_tax, total_amount, trade_type))

            conn.commit()
            return  # If successful, exit function

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                st.warning(f"Database is locked. Retrying in {retry_delay} second(s)... ({attempt+1}/{max_retries})")
                time.sleep(retry_delay)  # Wait and retry
            else:
                st.error(f"Database error: {str(e)}")
                break  # Exit loop on non-lock errors

        finally:
            conn.close()  # Ensure the connection is always closed

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
    """Allows manual entry of trade details into the database with enhanced UI."""
    st.header("Manual Trade Entry")
    
    # Initialize session state variables
    if 'confirm_stage' not in st.session_state:
        st.session_state.confirm_stage = False
        st.session_state.trade_data = None
    
    # Create columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Basic Information")
        memo_number = st.text_input(
            "Memo Number (Required)", 
            help="Enter the unique memo number from your trade confirmation"
        )
        
        purchase_date = st.date_input(
            "Date of Purchase (Required)",
            help="Select the date when the trade was executed"
        )
        
        stock_name = st.text_input(
            "Stock Name (Required)",
            help="Enter the name of the company whose shares you purchased"
        )
        
        number_of_stocks = st.number_input(
            "Number of Shares (Required)", 
            min_value=1, 
            format="%d",
            help="Enter the total number of shares purchased"
        )

    with col2:
        st.subheader("Price & Charges")
        rate_per_share = st.number_input(
            "Rate per Share (Rs.)", 
            min_value=0.0, 
            format="%.4f",
            help="Enter the price per share"
        )
        
        commission_charges = st.number_input(
            "Commission Charges (Rs.)", 
            min_value=0.0, 
            format="%.2f",
            help="Enter the broker's commission"
        )
        
        cdc_charges = st.number_input(
            "CDC Charges (Rs.)", 
            min_value=0.0, 
            format="%.2f",
            help="Enter the Central Depository Company charges"
        )
        
        sales_tax = st.number_input(
            "Sales Tax (Rs.)", 
            min_value=0.0, 
            format="%.2f",
            help="Enter the sales tax amount"
        )

    # Calculate values
    stock_value = rate_per_share * number_of_stocks
    total_charges = commission_charges + cdc_charges + sales_tax
    total_amount = stock_value + total_charges

    # Display calculated values
    st.subheader("Transaction Summary")
    
    # Create three columns for metrics
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    
    with metric_col1:
        st.metric(
            label="Stock Value",
            value=f"Rs. {stock_value:,.2f}",
            help="Base value of stocks (Rate × Quantity)"
        )
    
    with metric_col2:
        st.metric(
            label="Total Charges",
            value=f"Rs. {total_charges:,.2f}",
            help="Sum of Commission, CDC Charges, and Sales Tax"
        )
    
    with metric_col3:
        st.metric(
            label="Total Amount",
            value=f"Rs. {total_amount:,.2f}",
            help="Total payment required"
        )

    # Detailed breakdown of charges
    with st.expander("View Charges Breakdown"):
        st.write(f"""
        - Commission: Rs. {commission_charges:,.2f}
        - CDC Charges: Rs. {cdc_charges:,.2f}
        - Sales Tax: Rs. {sales_tax:,.2f}
        """)

    # Add divider for visual separation
    st.divider()

    def reset_form():
        st.session_state.confirm_stage = False
        st.session_state.trade_data = None

    def proceed_to_confirm():
        st.session_state.confirm_stage = True
        st.session_state.trade_data = {
            'memo_number': memo_number,
            'purchase_date': purchase_date,
            'stock_name': stock_name,
            'number_of_stocks': number_of_stocks,
            'rate_per_share': rate_per_share,
            'commission_charges': commission_charges,
            'cdc_charges': cdc_charges,
            'sales_tax': sales_tax,
            'total_amount': total_amount
        }

    if not st.session_state.confirm_stage:
        if st.button("Add Trade", type="primary", on_click=proceed_to_confirm):
            # Validate inputs
            errors = []
            
            if not memo_number.strip():
                errors.append("Memo number is required")
            
            if not stock_name.strip():
                errors.append("Stock name is required")
            
            if rate_per_share <= 0:
                errors.append("Rate per share must be greater than 0")
            
            if number_of_stocks <= 0:
                errors.append("Number of shares must be greater than 0")

            # Check for existing memo number
            if memo_number.strip():
                conn = sqlite3.connect("portfolio.db")
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM memos WHERE memo_number = ?", (memo_number,))
                existing_count = cursor.fetchone()[0]
                conn.close()

                if existing_count > 0:
                    errors.append(f"Trade with memo number {memo_number} already exists")

            # Display any validation errors
            if errors:
                for error in errors:
                    st.error(error)
                reset_form()
                return

    else:
        # Show confirmation
        st.info("Please verify the information before confirming:")
        trade_data = st.session_state.trade_data
        st.write(f"""
        - Memo Number: {trade_data['memo_number']}
        - Date: {trade_data['purchase_date'].strftime('%d-%m-%Y')}
        - Stock: {trade_data['stock_name']}
        - Shares: {trade_data['number_of_stocks']:,}
        - Rate/Share: Rs. {trade_data['rate_per_share']:.4f}
        - Total Amount: Rs. {trade_data['total_amount']:,.2f}
        """)

        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Confirm", type="primary"):
                conn = sqlite3.connect("portfolio.db")
                cursor = conn.cursor()
                
                try:
                    # Begin transaction
                    cursor.execute("BEGIN TRANSACTION")
                    
                    # Insert memo number
                    cursor.execute("INSERT INTO memos (memo_number) VALUES (?)", 
                                 (trade_data['memo_number'],))
                    
                    # Insert trade
                    cursor.execute("""
                        INSERT INTO trades (
                            date, memo_number, stock, quantity, rate, 
                            comm_amount, cdc_charges, sales_tax, total_amount, type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trade_data['purchase_date'].strftime('%d-%m-%Y'),
                        trade_data['memo_number'],
                        trade_data['stock_name'],
                        trade_data['number_of_stocks'],
                        trade_data['rate_per_share'],
                        trade_data['commission_charges'],
                        trade_data['cdc_charges'],
                        trade_data['sales_tax'],
                        trade_data['total_amount'],
                        "Buy"
                    ))
                    
                    # Commit transaction
                    conn.commit()
                    st.success("✅ Trade added successfully!")
                    
                    # Reset form
                    reset_form()
                    
                    # Show updated trades
                    display_trades()
                    
                except sqlite3.Error as e:
                    conn.rollback()
                    st.error(f"Failed to add trade: {str(e)}")
                finally:
                    conn.close()
                    
        with col2:
            if st.button("Cancel", on_click=reset_form):
                pass

    # Option to view existing trades
    if st.checkbox("View Existing Trades"):
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