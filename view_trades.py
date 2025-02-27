import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

def view_trades():
    """
    Enhanced view trades function with improved edit functionality, search,
    and separate tabs for Stocks, Metals, and Dividends.
    """
    st.header("📊 View All Trades & Dividends")

    # Create tabs for different types
    tab_stocks, tab_metals, tab_dividends = st.tabs(["Stock Trades", "Metal Trades", "Dividends"])

    with tab_stocks:
        view_stock_trades()

    with tab_metals:
        view_metal_trades()

    with tab_dividends:
        view_dividends()

# =========================
#    STOCK TRADES
# =========================

def view_stock_trades():
    """Displays and manages edits/deletions for stock trades in the 'trades' table."""
    st.subheader("📝 Stock Trades")

    # Add search functionality
    search_col1, search_col2 = st.columns([0.3, 0.7])
    with search_col1:
        search_type = st.selectbox(
            "Search By",
            ["Stock Name", "Memo Number", "Date"],
            help="Select search criteria"
        )
    with search_col2:
        search_text = st.text_input(
            "🔍 Search Stocks...",
            placeholder=f"Enter {search_type.lower()} to search",
            help=f"Enter {search_type.lower()} to filter trades"
        )

    # Initialize session state for editing
    if 'editing_trade' not in st.session_state:
        st.session_state.editing_trade = None
    
    conn = sqlite3.connect("portfolio.db")
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
    
    try:
        df = pd.read_sql_query(query, conn)
        
        # Apply search filter if search text is provided
        if search_text:
            search_text = search_text.strip().lower()
            if search_type == "Stock Name":
                df = df[df['Stock'].str.lower().str.contains(search_text, na=False)]
            elif search_type == "Memo Number":
                df = df[df['Memo No'].str.lower().str.contains(search_text, na=False)]
            elif search_type == "Date":
                df = df[df['Date'].str.lower().str.contains(search_text, na=False)]
                
        # Show search results summary
        if search_text:
            if len(df) > 0:
                st.success(f"Found {len(df)} matching stock trades for '{search_text}'")
            else:
                st.warning(f"No stock trades found matching '{search_text}'")
                return
        
        if df.empty:
            st.warning("No stock trades found in the database.")
            return
            
        # Format numeric columns
        df['Shares'] = df['Shares'].apply(lambda x: f"{int(x):,}")
        numeric_cols = ['Rate', 'Commission', 'CDC Charges', 'Sales Tax', 'Total Amount']
        for col in numeric_cols:
            df[col] = df[col].apply(lambda x: f"Rs. {x:,.2f}")
        
        # If not editing, show the table with edit buttons
        if st.session_state.editing_trade is None:
            st.write("### Trade History (Stocks)")
            
            # Display each trade with action buttons
            for idx, row in df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
                    
                    with col1:
                        st.write(f"{row['Date']} - {row['Stock']} ({row['Shares']} shares @ {row['Rate']})")
                    
                    with col2:
                        if st.button("✏️ Edit", key=f"edit_stock_{idx}"):
                            st.session_state.editing_trade = row.to_dict()
                            st.session_state.table_type = "stocks"
                            st.rerun()
                    
                    with col3:
                        if st.button("🗑️ Delete", key=f"delete_stock_{idx}"):
                            st.session_state.confirm_delete = ("stocks", row['Memo No'], row['Stock'])
                            st.rerun()
                    
                    # Show delete confirmation if this is the row being deleted
                    if st.session_state.get('confirm_delete') == ("stocks", row['Memo No'], row['Stock']):
                        st.warning(f"Are you sure you want to delete this STOCK trade for **{row['Stock']}**?")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Yes, Delete", key=f"confirm_delete_stock_{idx}"):
                                if delete_stock_trade(row['Memo No'], row['Stock']):
                                    st.success(f"Successfully deleted stock trade for {row['Stock']}")
                                    st.session_state.confirm_delete = None
                                    st.rerun()
                        with col2:
                            if st.button("❌ No, Cancel", key=f"cancel_delete_stock_{idx}"):
                                st.session_state.confirm_delete = None
                                st.rerun()
                
                st.divider()
            
            # Add summary metrics
            st.subheader("Portfolio Summary (Stocks)")
            total_investment = sum(float(str(val).replace('Rs. ', '').replace(',', '')) 
                                 for val in df['Total Amount'])
            total_shares = sum(int(str(val).replace(',', '')) for val in df['Shares'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Investment", f"Rs. {total_investment:,.2f}")
            with col2:
                st.metric("Total Shares", f"{total_shares:,}")
        
        else:
            # Editing trade
            if st.session_state.table_type == "stocks":
                if edit_stock_trade(st.session_state.editing_trade):
                    st.session_state.editing_trade = None
                    st.rerun()
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
    
    finally:
        conn.close()


def edit_stock_trade(trade_data):
    """
    Enhanced edit trade function (Stocks) with improved UI and validation
    """
    st.subheader("✏️ Edit Stock Trade")
    
    # Create two columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Basic Information
        try:
            date_obj = datetime.strptime(trade_data['Date'], '%Y-%m-%d')
        except ValueError:
            try:
                date_obj = datetime.strptime(trade_data['Date'], '%B %d, %Y')
            except ValueError:
                date_obj = datetime.now()
                st.warning(f"Could not parse date '{trade_data['Date']}'. Using current date instead.")
        
        new_date = st.date_input(
            "Trade Date",
            value=date_obj,
            help="Date of the trade"
        )
        
        new_stock = st.text_input(
            "Stock Name",
            value=trade_data['Stock'],
            help="Name of the stock"
        )
        
        new_shares = st.number_input(
            "Number of Shares",
            min_value=1,
            value=int(str(trade_data['Shares']).replace(',', '')),
            help="Number of shares traded"
        )
        
        new_rate = st.number_input(
            "Rate per Share (Rs.)",
            min_value=0.01,
            value=float(str(trade_data['Rate']).replace('Rs. ', '').replace(',', '')),
            format="%.2f",
            help="Price per share"
        )
    
    with col2:
        # Charges and Taxes
        new_commission = st.number_input(
            "Commission (Rs.)",
            min_value=0.0,
            value=float(str(trade_data['Commission']).replace('Rs. ', '').replace(',', '')),
            format="%.2f",
            help="Broker's commission"
        )
        
        new_cdc = st.number_input(
            "CDC Charges (Rs.)",
            min_value=0.0,
            value=float(str(trade_data['CDC Charges']).replace('Rs. ', '').replace(',', '')),
            format="%.2f",
            help="CDC charges"
        )
        
        new_tax = st.number_input(
            "Sales Tax (Rs.)",
            min_value=0.0,
            value=float(str(trade_data['Sales Tax']).replace('Rs. ', '').replace(',', '')),
            format="%.2f",
            help="Sales tax amount"
        )
    
    # Calculate new total
    new_total = (new_rate * new_shares) + new_commission + new_cdc + new_tax
    
    # Display summary
    st.subheader("Transaction Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Total Shares",
            f"{new_shares:,}",
            delta=f"{new_shares - int(str(trade_data['Shares']).replace(',', ''))}"
        )
    with col2:
        st.metric(
            "Rate",
            f"Rs. {new_rate:,.2f}",
            delta=f"Rs. {new_rate - float(str(trade_data['Rate']).replace('Rs. ', '').replace(',', '')):,.2f}"
        )
    with col3:
        st.metric(
            "Total Amount",
            f"Rs. {new_total:,.2f}",
            delta=f"Rs. {new_total - float(str(trade_data['Total Amount']).replace('Rs. ', '').replace(',', '')):,.2f}"
        )
    
    st.divider()
    
    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Stock Changes", type="primary"):
            if not new_stock.strip():
                st.error("Stock name cannot be empty!")
                return False
                
            # Update database
            conn = sqlite3.connect("portfolio.db")
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    UPDATE trades
                    SET date = ?,
                        stock = ?,
                        quantity = ?,
                        rate = ?,
                        comm_amount = ?,
                        cdc_charges = ?,
                        sales_tax = ?,
                        total_amount = ?
                    WHERE memo_number = ? AND stock = ?
                """, (
                    new_date.strftime('%Y-%m-%d'),
                    new_stock,
                    new_shares,
                    new_rate,
                    new_commission,
                    new_cdc,
                    new_tax,
                    new_total,
                    trade_data['Memo No'],
                    trade_data['Stock']
                ))
                
                conn.commit()
                st.success("✅ Stock trade updated successfully!")
                return True
                
            except sqlite3.Error as e:
                conn.rollback()
                st.error(f"Database error: {str(e)}")
                return False
                
            finally:
                conn.close()
    
    with col2:
        if st.button("❌ Cancel"):
            return True
    
    return False

def delete_stock_trade(memo_number, stock):
    """Delete a stock trade from the 'trades' table."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute(
            "DELETE FROM trades WHERE memo_number = ? AND stock = ?",
            (memo_number, stock)
        )
        
        # If no trades remain for this memo, remove from memos
        cursor.execute(
            "SELECT COUNT(*) FROM trades WHERE memo_number = ?",
            (memo_number,)
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "DELETE FROM memos WHERE memo_number = ?",
                (memo_number,)
            )
        
        cursor.execute("COMMIT")
        return True
        
    except sqlite3.Error as e:
        cursor.execute("ROLLBACK")
        st.error(f"Error deleting trade: {str(e)}")
        return False
        
    finally:
        conn.close()


# =========================
#    METAL TRADES
# =========================

def view_metal_trades():
    """Displays and manages edits/deletions for metal trades in the 'metal_trades' table."""
    st.subheader("🪙 Metal Trades")

    # Search fields
    search_col1, search_col2 = st.columns([0.3, 0.7])
    with search_col1:
        search_type = st.selectbox(
            "Search By",
            ["Metal", "Date"],
            help="Select search criteria"
        )
    with search_col2:
        search_text = st.text_input(
            "🔍 Search Metals...",
            placeholder=f"Enter {search_type.lower()} to search",
            help=f"Enter {search_type.lower()} to filter metal trades"
        )

    if 'editing_metal_trade' not in st.session_state:
        st.session_state.editing_metal_trade = None

    conn = sqlite3.connect("portfolio.db")
    query = """
        SELECT
            id as 'ID',
            date as 'Date',
            metal as 'Metal',
            weight as 'Weight (g)',
            karat as 'Karat',
            purchase_price as 'Purchase Price',
            total_cost as 'Total Cost'
        FROM metal_trades
        ORDER BY date DESC
    """

    try:
        df = pd.read_sql_query(query, conn)

        # Filter if search text
        if search_text:
            search_text = search_text.strip().lower()
            if search_type == "Metal":
                df = df[df['Metal'].str.lower().str.contains(search_text, na=False)]
            elif search_type == "Date":
                df = df[df['Date'].str.lower().str.contains(search_text, na=False)]

        if search_text:
            if len(df) > 0:
                st.success(f"Found {len(df)} matching metal trades for '{search_text}'")
            else:
                st.warning(f"No metal trades found matching '{search_text}'")
                return

        if df.empty:
            st.warning("No metal trades found in the database.")
            return

        # Format columns for display
        df['Weight (g)'] = df['Weight (g)'].apply(lambda x: f"{float(x):,.2f}")
        df['Purchase Price'] = df['Purchase Price'].apply(lambda x: f"USD {float(x):,.2f}")
        df['Total Cost'] = df['Total Cost'].apply(lambda x: f"USD {float(x):,.2f}")

        # If not editing, show the table with edit buttons
        if st.session_state.editing_metal_trade is None:
            st.write("### Metal Trades History")

            for idx, row in df.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([0.7, 0.15, 0.15])
                    with c1:
                        st.write(f"{row['Date']} - {row['Metal']} {row['Karat']}K "
                                 f"({row['Weight (g)']}g @ {row['Purchase Price']})")
                    with c2:
                        if st.button("✏️ Edit", key=f"edit_metal_{idx}"):
                            st.session_state.editing_metal_trade = row.to_dict()
                            st.rerun()
                    with c3:
                        if st.button("🗑️ Delete", key=f"delete_metal_{idx}"):
                            st.session_state.confirm_delete = ("metal", row['ID'])
                            st.rerun()

                    # Confirmation
                    if st.session_state.get('confirm_delete') == ("metal", row['ID']):
                        st.warning(f"Are you sure you want to delete this METAL trade for ID={row['ID']}?")
                        cdel1, cdel2 = st.columns(2)
                        with cdel1:
                            if st.button("✅ Yes, Delete", key=f"confirm_delete_metal_{idx}"):
                                if delete_metal_trade(row['ID']):
                                    st.success(f"Successfully deleted metal trade ID={row['ID']}")
                                    st.session_state.confirm_delete = None
                                    st.rerun()
                        with cdel2:
                            if st.button("❌ No, Cancel", key=f"cancel_delete_metal_{idx}"):
                                st.session_state.confirm_delete = None
                                st.rerun()

                st.divider()

        else:
            # Editing a metal trade
            if edit_metal_trade(st.session_state.editing_metal_trade):
                st.session_state.editing_metal_trade = None
                st.rerun()

    except Exception as e:
        st.error(f"Error: {str(e)}")

    finally:
        conn.close()


def edit_metal_trade(trade_data):
    """Edit a single record in metal_trades."""
    st.subheader("✏️ Edit Metal Trade")

    col1, col2 = st.columns(2)
    with col1:
        # Date
        try:
            date_obj = datetime.strptime(trade_data['Date'], '%Y-%m-%d')
        except ValueError:
            try:
                date_obj = datetime.strptime(trade_data['Date'], '%B %d, %Y')
            except ValueError:
                date_obj = datetime.now()
                st.warning(f"Could not parse date '{trade_data['Date']}'. Using current date instead.")

        new_date = st.date_input("Trade Date", value=date_obj)
        new_metal = st.text_input("Metal Name", value=trade_data['Metal'])
        new_karat = st.number_input("Karat", min_value=1, max_value=24, value=int(trade_data['Karat']))
    with col2:
        new_weight = st.number_input("Weight (g)", min_value=0.01, value=float(str(trade_data['Weight (g)']).replace(',', '')))
        new_purchase_price = st.number_input("Purchase Price (USD/g)", min_value=0.01, value=float(str(trade_data['Purchase Price']).replace('USD ', '').replace(',', '')))
    
    # Recalc total cost
    new_total_cost = new_weight * new_purchase_price

    st.subheader("Updated Summary")
    c1, c2 = st.columns(2)
    with c1:
        st.metric(
            "Weight (g)",
            f"{new_weight:,.2f}",
            help="New weight"
        )
    with c2:
        st.metric(
            "Total Cost (USD)",
            f"{new_total_cost:,.2f}",
            help="New total cost"
        )

    st.divider()

    cc1, cc2 = st.columns(2)
    with cc1:
        if st.button("💾 Save Metal Changes", type="primary"):
            if not new_metal.strip():
                st.error("Metal name cannot be empty!")
                return False

            conn = sqlite3.connect("portfolio.db")
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE metal_trades
                    SET date = ?,
                        metal = ?,
                        weight = ?,
                        karat = ?,
                        purchase_price = ?,
                        total_cost = ?
                    WHERE id = ?
                """, (
                    new_date.strftime('%Y-%m-%d'),
                    new_metal,
                    new_weight,
                    new_karat,
                    new_purchase_price,
                    new_total_cost,
                    trade_data['ID']
                ))
                conn.commit()
                st.success("✅ Metal trade updated successfully!")
                return True
            except sqlite3.Error as e:
                conn.rollback()
                st.error(f"Database error: {e}")
                return False
            finally:
                conn.close()

    with cc2:
        if st.button("❌ Cancel"):
            return True

    return False

def delete_metal_trade(row_id):
    """Deletes one metal trade record by 'id' from 'metal_trades'."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute("DELETE FROM metal_trades WHERE id = ?", (row_id,))
        cursor.execute("COMMIT")
        return True
    except sqlite3.Error as e:
        cursor.execute("ROLLBACK")
        st.error(f"Error deleting metal trade: {e}")
        return False
    finally:
        conn.close()


# =========================
#    DIVIDENDS
# =========================

def view_dividends():
    """Displays, edits, and deletes dividend records in 'dividends' table."""
    st.subheader("💸 Dividends")

    search_col1, search_col2 = st.columns([0.3, 0.7])
    with search_col1:
        search_type = st.selectbox(
            "Search By",
            ["Stock Name", "Warrant No", "Date"],
            help="Select search criteria"
        )
    with search_col2:
        search_text = st.text_input(
            "🔍 Search Dividends...",
            placeholder=f"Enter {search_type.lower()} to search",
            help=f"Enter {search_type.lower()} to filter dividends"
        )

    if 'editing_dividend' not in st.session_state:
        st.session_state.editing_dividend = None

    conn = sqlite3.connect("portfolio.db")
    query = """
        SELECT
            id as 'ID',
            warrant_no as 'Warrant No',
            payment_date as 'Payment Date',
            stock_name as 'Stock',
            rate_per_security as 'Rate/Security',
            number_of_securities as 'Shares',
            amount_of_dividend as 'Gross Dividend',
            tax_deducted as 'Tax Deducted',
            amount_paid as 'Net Dividend'
        FROM dividends
        ORDER BY payment_date DESC
    """

    try:
        df = pd.read_sql_query(query, conn)
        if search_text:
            s = search_text.strip().lower()
            if search_type == "Stock Name":
                df = df[df['Stock'].str.lower().str.contains(s, na=False)]
            elif search_type == "Warrant No":
                df = df[df['Warrant No'].str.lower().str.contains(s, na=False)]
            elif search_type == "Date":
                df = df[df['Payment Date'].str.lower().str.contains(s, na=False)]

        if search_text:
            if len(df) > 0:
                st.success(f"Found {len(df)} matching dividends for '{search_text}'")
            else:
                st.warning(f"No dividends found matching '{search_text}'")
                return

        if df.empty:
            st.warning("No dividend records found.")
            return

        # Format columns
        df['Gross Dividend'] = df['Gross Dividend'].apply(lambda x: f"Rs. {float(x):,.2f}")
        df['Tax Deducted'] = df['Tax Deducted'].apply(lambda x: f"Rs. {float(x):,.2f}")
        df['Net Dividend'] = df['Net Dividend'].apply(lambda x: f"Rs. {float(x):,.2f}")

        if st.session_state.editing_dividend is None:
            st.write("### Dividend Records")

            for idx, row in df.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([0.7, 0.15, 0.15])
                    with c1:
                        st.write(f"{row['Payment Date']} - {row['Stock']} => {row['Net Dividend']}")
                    with c2:
                        if st.button("✏️ Edit", key=f"edit_div_{idx}"):
                            st.session_state.editing_dividend = row.to_dict()
                            st.rerun()
                    with c3:
                        if st.button("🗑️ Delete", key=f"delete_div_{idx}"):
                            st.session_state.confirm_delete = ("dividend", row['ID'])
                            st.rerun()

                    # Confirm
                    if st.session_state.get('confirm_delete') == ("dividend", row['ID']):
                        st.warning(f"Are you sure you want to delete Dividend ID={row['ID']}?")
                        cd1, cd2 = st.columns(2)
                        with cd1:
                            if st.button("✅ Yes, Delete", key=f"confirm_delete_div_{idx}"):
                                if delete_dividend(row['ID']):
                                    st.success(f"Successfully deleted dividend record (ID={row['ID']})")
                                    st.session_state.confirm_delete = None
                                    st.rerun()
                        with cd2:
                            if st.button("❌ No, Cancel", key=f"cancel_delete_div_{idx}"):
                                st.session_state.confirm_delete = None
                                st.rerun()
                st.divider()
        else:
            # Edit
            if edit_dividend(st.session_state.editing_dividend):
                st.session_state.editing_dividend = None
                st.rerun()

    except Exception as e:
        st.error(f"Error: {str(e)}")
    finally:
        conn.close()


def edit_dividend(div_data):
    """Edit a single dividend record in 'dividends' table."""
    st.subheader("✏️ Edit Dividend Record")

    col1, col2 = st.columns(2)
    with col1:
        try:
            date_obj = datetime.strptime(div_data['Payment Date'], '%Y-%m-%d')
        except ValueError:
            try:
                date_obj = datetime.strptime(div_data['Payment Date'], '%B %d, %Y')
            except ValueError:
                date_obj = datetime.now()
        new_date = st.date_input("Payment Date", value=date_obj)
        new_stock = st.text_input("Stock Name", value=div_data['Stock'])
        new_warrant = st.text_input("Warrant No", value=div_data['Warrant No'])

    with col2:
        new_rate = st.number_input("Rate/Security (Rs.)", min_value=0.0, value=float(str(div_data['Rate/Security']).replace(',', '').replace('Rs. ', '')))
        new_shares = st.number_input("Number of Shares", min_value=1, value=int(div_data['Shares']))
        new_tax = st.number_input("Tax Deducted (Rs.)", min_value=0.0, value=float(str(div_data['Tax Deducted']).replace('Rs. ', '').replace(',', '')))

    gross_dividend = new_rate * new_shares
    net_dividend = gross_dividend - new_tax

    st.subheader("Updated Dividend Summary")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Gross Dividend", f"Rs. {gross_dividend:,.2f}")
    with c2:
        st.metric("Tax Deducted", f"Rs. {new_tax:,.2f}")
    with c3:
        st.metric("Net Dividend", f"Rs. {net_dividend:,.2f}")

    st.divider()
    cbtn1, cbtn2 = st.columns(2)
    with cbtn1:
        if st.button("💾 Save Dividend Changes", type="primary"):
            if not new_stock.strip():
                st.error("Stock name cannot be empty!")
                return False
            if not new_warrant.strip():
                st.error("Warrant No cannot be empty!")
                return False

            conn = sqlite3.connect("portfolio.db")
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE dividends
                    SET 
                        payment_date = ?,
                        stock_name = ?,
                        warrant_no = ?,
                        rate_per_security = ?,
                        number_of_securities = ?,
                        amount_of_dividend = ?,
                        tax_deducted = ?,
                        amount_paid = ?
                    WHERE id = ?
                """, (
                    new_date.strftime('%Y-%m-%d'),
                    new_stock,
                    new_warrant,
                    new_rate,
                    new_shares,
                    gross_dividend,
                    new_tax,
                    net_dividend,
                    div_data['ID']
                ))
                conn.commit()
                st.success("✅ Dividend record updated successfully!")
                return True
            except sqlite3.Error as e:
                conn.rollback()
                st.error(f"Database error: {e}")
                return False
            finally:
                conn.close()

    with cbtn2:
        if st.button("❌ Cancel"):
            return True

    return False

def delete_dividend(row_id):
    """Deletes a single dividend record by 'id' from the 'dividends' table."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute("DELETE FROM dividends WHERE id = ?", (row_id,))
        cursor.execute("COMMIT")
        return True
    except sqlite3.Error as e:
        cursor.execute("ROLLBACK")
        st.error(f"Error deleting dividend record: {e}")
        return False
    finally:
        conn.close()
