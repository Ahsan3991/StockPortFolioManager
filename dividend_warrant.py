import streamlit as st
import sqlite3
import pdfplumber
import json
import re
from gpt4all import GPT4All
from datetime import datetime
import pandas as pd  # Add this import at the top

def extract_dividend_details_with_llm(text):
    """Extracts structured dividend details from raw text using GPT4ALL with enforced JSON output."""
    try:
        st.info("Initializing GPT4All model...")
        with GPT4All("Meta-Llama-3-8B-Instruct.Q4_0.gguf", device="cuda") as model:
            prompt = (
                "Extract structured dividend details from the provided text in **JSON format ONLY**.\n"
                "The response must be a single valid JSON object with exactly two keys: 'warrant_no' and 'dividends'.\n\n"

                "### **Expected JSON Output Format:**\n"
                "{\n"
                '  "warrant_no": "7012014544",\n'
                '  "dividends": [\n'
                '    {\n'
                '      "payment_date": "01-11-2024",\n'
                '      "stock_name": "Nishat Power Limited",\n'
                '      "rate_per_security": 5.00,\n'
                '      "number_of_securities": 2000,\n'
                '      "amount_of_dividend": 10000.00,\n'
                '      "tax_deducted": 750.00,\n'
                '      "amount_paid": 9250.00\n'
                '    }\n'
                '  ]\n'
                "}\n\n"

                "### **Strict JSON Rules:**\n"
                "- **DO NOT** include any text outside the JSON.\n"
                "- **DO NOT** add explanations, comments, or summary messages.\n"
                "- **DO NOT** repeat responses or include multiple JSON blocks.\n"
                "- **Ensure correct JSON formatting** with no missing brackets.\n"
                "- **Numbers must not contain commas** (use 10000.00, not 10,000.00).\n\n"

                "**Extract the data now:**\n"
            )

            st.info("Processing text with GPT4All...")
            response = model.generate(prompt + "\n" + text, temp=0, max_tokens=500)

            st.write("### Raw LLM Response:")
            st.text(response[:2000])

            json_pattern = r'\{[\s\S]*\}'
            match = re.search(json_pattern, response)
            
            if match:
                json_str = match.group(0)
                
                # Clean up the JSON string
                json_str = re.sub(r'[\n\r\t]', '', json_str)
                json_str = re.sub(r'\s+', ' ', json_str)
                json_str = re.sub(r'(\d),(\d)', r'\1\2', json_str)
                json_str = json_str.replace('**', '')
                json_str = json_str.strip()
                
                try:
                    parsed_json = json.loads(json_str)
                    
                    if "warrant_no" in parsed_json and "dividends" in parsed_json:
                        st.write("### Extracted JSON Data:")
                        st.json(parsed_json)
                        return parsed_json
                    else:
                        st.error("❌ Invalid JSON structure: missing required keys")
                        return {}
                        
                except json.JSONDecodeError as e:
                    st.error(f"❌ JSON parsing error: {str(e)}")
                    st.text(f"Problematic JSON string: {json_str}")
                    return {}
            else:
                st.error("❌ No JSON data found in the response")
                return {}

    except FileNotFoundError:
        st.error("❌ Model file not found. Please ensure the model is properly installed.")
        return {}
    except Exception as e:
        st.error(f"❌ Error initializing model: {str(e)}")
        return {}

def extract_raw_text(pdf_file):
    """Extracts raw text from a PDF file."""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            if not text:
                st.warning("No text could be extracted from the PDF.")
            return text
    except Exception as e:
        st.error(f"❌ Error extracting text from PDF: {str(e)}")
        return ""

def insert_dividend(warrant_no, payment_date, stock_name, rate_per_security, number_of_securities, amount_of_dividend, tax_deducted, amount_paid):
    """Inserts a dividend record into the database."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    
    try:
        st.info(f"Processing dividend for warrant {warrant_no}")
        
        # First, ensure the warrant exists in the warrants table
        cursor.execute("INSERT OR IGNORE INTO warrants (warrant_no) VALUES (?)", (warrant_no,))
        
        # Then insert the dividend details
        cursor.execute("""
            INSERT INTO dividends (
                warrant_no, payment_date, stock_name, rate_per_security, 
                number_of_securities, amount_of_dividend, tax_deducted, amount_paid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (warrant_no, payment_date, stock_name, rate_per_security, 
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
    conn = sqlite3.connect("portfolio.db")
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

def process_dividend_warrant():
    """Handles the Streamlit UI for dividend warrant uploads."""
    st.header("Upload Dividend Warrant")
    uploaded_file = st.file_uploader("Upload your Dividend Warrant (PDF)", type=["pdf"])

    if uploaded_file is not None:
        raw_text = extract_raw_text(uploaded_file)
        if raw_text:
            st.write("### Extracted Raw Text from PDF:")
            st.text(raw_text[:2000])

            extracted_data = extract_dividend_details_with_llm(raw_text)

            if extracted_data and 'warrant_no' in extracted_data and 'dividends' in extracted_data:
                warrant_no = extracted_data['warrant_no']
                dividends = extracted_data['dividends']

                if not dividends:
                    st.error("Failed to extract dividend details.")
                    return

                # Check if warrant exists
                conn = sqlite3.connect("portfolio.db")
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT COUNT(*) FROM warrants WHERE warrant_no = ?", (warrant_no,))
                    existing_count = cursor.fetchone()[0]
                
                    if existing_count > 0:
                        overwrite = st.radio(
                            f"Dividend warrant {warrant_no} already exists. Overwrite?",
                            ["No", "Yes"],
                            key=f"overwrite_{warrant_no}"
                        )

                        if overwrite == "No":
                            st.warning(f"Dividend warrant {warrant_no} was not added.")
                            return

                        # Delete existing records
                        cursor.execute("DELETE FROM dividends WHERE warrant_no = ?", (warrant_no,))
                        cursor.execute("DELETE FROM warrants WHERE warrant_no = ?", (warrant_no,))
                        conn.commit()
                        st.info(f"Existing dividend warrant {warrant_no} deleted.")

                except sqlite3.Error as e:
                    st.error(f"Database error: {str(e)}")
                    return
                finally:
                    conn.close()

                # Insert all dividends
                success = True
                for dividend in dividends:
                    if not insert_dividend(
                        warrant_no,
                        dividend.get("payment_date", "N/A"),
                        dividend.get("stock_name", "UNKNOWN"),
                        dividend.get("rate_per_security", 0.0),
                        dividend.get("number_of_securities", 0),
                        dividend.get("amount_of_dividend", 0.0),
                        dividend.get("tax_deducted", 0.0),
                        dividend.get("amount_paid", 0.0)
                    ):
                        success = False
                        break

                if success:
                    st.success("Dividend warrant added successfully!")
                    display_stored_dividends()
                else:
                    st.error("Failed to add dividend warrant.")
            else:
                st.error("Failed to extract dividend details.")

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
                conn = sqlite3.connect("portfolio.db")
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