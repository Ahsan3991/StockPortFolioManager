import streamlit as st
import sqlite3
import time
import json
import os
from trade_receipt import clean_stock_name, display_trades

def load_psx_data():
    """Load the PSX stock data from JSON file"""
    try:
        # Check if the file exists first
        if os.path.exists("psx_stocks.json"):
            with open("psx_stocks.json", "r") as f:
                return json.load(f)
        else:
            # If file doesn't exist, show a message and return empty dict
            st.error("File psx_stocks.json does not exist. Please create it with your PSX stock data.")
            return {}
    except Exception as e:
        st.error(f"Error loading PSX stock data: {e}")
        return {}

def get_all_stock_symbols():
    """Extract all stock symbols from the PSX data"""
    psx_data = load_psx_data()
    all_symbols = {}
    
    for sector, stocks in psx_data.items():
        for symbol, name in stocks.items():
            all_symbols[symbol] = {"name": name, "sector": sector}
    
    return all_symbols

def get_stock_display_options():
    """Generate stock display options for dropdown showing ticker symbol and company name"""
    all_stocks = get_all_stock_symbols()
    
    # Create display options in format "TICKER - Company Name"
    display_options = [""]  # Empty option for default/unselected state
    ticker_to_display = {"": ""}  # Mapping from ticker to display string
    
    for symbol, details in all_stocks.items():
        display = f"{symbol} - {details['name']}"
        display_options.append(display)
        ticker_to_display[display] = symbol  # Store mapping to retrieve ticker later
    
    return display_options, ticker_to_display

def manual_trade_entry():
    st.header("Manual Trade Entry")
    
    if 'trades_list' not in st.session_state:
        st.session_state.trades_list = []
    if 'current_memo' not in st.session_state:
        st.session_state.current_memo = None

    st.subheader("Enter Trade Details")

    if st.session_state.current_memo is None:
        raw_memo_number = st.text_input(
            "Memo Number (Optional)",
            help="Enter the memo number if you have it; leave blank otherwise."
        )
        if not raw_memo_number.strip():
            raw_memo_number = "UNKNOWN"
        st.session_state.current_memo = raw_memo_number
    else:
        st.success(f"📌 Adding trades under Memo: {st.session_state.current_memo}")

    memo_number = st.session_state.current_memo

    # Get all stock symbols and prepare display options
    all_stocks = get_all_stock_symbols()
    display_options, ticker_to_display = get_stock_display_options()
    
    col1, col2 = st.columns(2)
    with col1:
        purchase_date = st.date_input("Date of Purchase (Required)", help="Select the date when the trade was executed")
        formatted_date = purchase_date.strftime('%B %d, %Y')
        
        # Enhanced dropdown with ticker and company name
        selected_display = st.selectbox(
            "Stock Ticker Symbol (Required)",
            options=display_options,
            help="Select or type to search for the stock symbol",
            key="stock_symbol_select",
            index=0  # Start with the empty option selected
        )
        
        # Extract just the ticker symbol for database storage
        selected_symbol = ticker_to_display.get(selected_display, "")
        
        # Show sector information only if a valid selection is made
        if selected_symbol and selected_symbol in all_stocks:
            st.info(f"Sector: {all_stocks[selected_symbol]['sector']}")
        elif not selected_symbol:
            st.warning("Please select a stock ticker symbol")
        
        number_of_stocks = st.number_input("Number of Shares (Required)", min_value=1, format="%d",
                                          help="Enter the total number of shares")
    with col2:
        rate_per_share = st.number_input("Rate per Share (Rs.)", min_value=0.0, format="%.4f",
                                         help="Enter the price per share")
        
        # Calculate stock value here, before we need it for sales tax
        stock_value = rate_per_share * number_of_stocks
        
        commission_charges = st.number_input("Commission Charges (Rs.)", min_value=0.0, format="%.2f",
                                             help="Enter broker's commission")
        cdc_charges = st.number_input("CDC Charges (Rs.)", min_value=0.0, format="%.2f",
                                      help="Enter CDC charges")
        
        # Add option to enter sales tax as percentage or absolute value
        tax_input_type = st.radio(
            "Sales Tax Input Type:",
            options=["Amount (Rs.)", "Percentage (%)"],
            horizontal=True,
            help="Choose how you want to enter the sales tax"
        )
        
        if tax_input_type == "Amount (Rs.)":
            sales_tax = st.number_input("Sales Tax (Rs.)", min_value=0.0, format="%.2f",
                                       help="Enter the sales tax amount directly")
            sales_tax_percentage = None
        else:
            sales_tax_percentage = st.number_input("Sales Tax (%)", min_value=0.0, max_value=100.0, format="%.2f",
                                                 help="Enter the sales tax as a percentage of the stock value")
            # Calculate the sales tax amount based on the percentage and stock value
            sales_tax = (sales_tax_percentage / 100) * stock_value
            st.info(f"Calculated Sales Tax: Rs. {sales_tax:.2f} ({sales_tax_percentage}% of Rs. {stock_value:.2f})")

    # Calculate total values
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

    button_col1, button_col2, button_col3 = st.columns([1, 1, 1])

    with button_col1:
        if st.button("➕ Add Another Trade"):
            if not selected_symbol:
                st.error("Please select a stock ticker symbol.")
                return
            elif rate_per_share <= 0:
                st.error("Rate per share must be greater than zero.")
                return

            # Store only the ticker symbol for database operations
            trade_data = {
                'memo_number': memo_number,
                'purchase_date': formatted_date,
                'stock_name': selected_symbol,  # Store only the ticker symbol
                'number_of_stocks': number_of_stocks,
                'rate_per_share': rate_per_share,
                'commission_charges': commission_charges,
                'cdc_charges': cdc_charges,
                'sales_tax': sales_tax,
                'total_amount': total_amount
            }
            st.session_state.trades_list.append(trade_data)
            
            # Display success with both ticker and company name for user clarity
            company_name = all_stocks[selected_symbol]['name'] if selected_symbol in all_stocks else ""
            st.success(f"✅ Added {selected_symbol} ({company_name}) to memo: {memo_number}")

    with button_col2:
        if st.button("✅ Submit Trade(s)", type="primary"):
            if not selected_symbol:
                st.error("Please select a stock ticker symbol.")
                return
            elif rate_per_share <= 0:
                st.error("Rate per share must be greater than zero.")
                return

            if selected_symbol and rate_per_share > 0:
                current_trade = {
                    'memo_number': memo_number,
                    'purchase_date': formatted_date,
                    'stock_name': selected_symbol,  # Store only the ticker symbol
                    'number_of_stocks': number_of_stocks,
                    'rate_per_share': rate_per_share,
                    'commission_charges': commission_charges,
                    'cdc_charges': cdc_charges,
                    'sales_tax': sales_tax,
                    'total_amount': total_amount
                }
                if current_trade not in st.session_state.trades_list:
                    st.session_state.trades_list.append(current_trade)

            from db_utils import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("BEGIN TRANSACTION")

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
                        clean_stock_name(trade['stock_name']),  # Still using clean_stock_name for consistency
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

                st.session_state.trades_list = []
                st.session_state.current_memo = None

                for key in list(st.session_state.keys()):
                    if key.startswith(('stock_name_', 'rate_', 'shares_', 'commission_', 'cdc_', 'tax_')):
                        del st.session_state[key]

                if st.button("➕ Add New Trade", type="primary"):
                    st.rerun()

                if st.session_state.get('show_trades', False):
                    display_trades()

                time.sleep(1)
                st.rerun()

            except sqlite3.Error as e:
                cursor.execute("ROLLBACK")
                st.error(f"❌ Failed to save trades: {str(e)}")
            finally:
                conn.close()

    with button_col3:
        if st.button("❌ Cancel"):
            st.session_state.trades_list = []
            st.session_state.current_memo = None
            st.warning("Trade entry canceled.")
            st.rerun()

    if st.session_state.trades_list:
        st.info(f"🔄 {len(st.session_state.trades_list)} trade(s) ready to submit under memo {memo_number}")

    show_trades = st.checkbox("📜 View Existing Trades", value=st.session_state.get('show_trades', False))
    st.session_state.show_trades = show_trades
    if show_trades:
        display_trades()