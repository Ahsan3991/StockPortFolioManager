import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

def edit_trade(trade_data):
    """
    Enhanced edit trade function with improved UI and validation
    """
    st.subheader("✏️ Edit Trade")
    
    # Create two columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Basic Information
        # Convert date string to datetime object, handling multiple formats
        try:
            # First try the SQL format
            date_obj = datetime.strptime(trade_data['Date'], '%Y-%m-%d')
        except ValueError:
            try:
                # Then try the displayed format
                date_obj = datetime.strptime(trade_data['Date'], '%B %d, %Y')
            except ValueError:
                # If all else fails, use today's date
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
    
    # Display summary of changes
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
    
    # Add divider for visual separation
    st.divider()
    
    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Changes", type="primary"):
            # Validate changes
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
                st.success("✅ Trade updated successfully!")
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

def view_trades():
    """Enhanced view trades function with improved edit functionality"""
    st.header("📊 View Trades")
    
    # Initialize session state for editing
    if 'editing_trade' not in st.session_state:
        st.session_state.editing_trade = None
    
    # Fetch trades from database
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
        
        if df.empty:
            st.warning("No trades found in the database.")
            return
            
        # Format numeric columns
        df['Shares'] = df['Shares'].apply(lambda x: f"{int(x):,}")
        numeric_cols = ['Rate', 'Commission', 'CDC Charges', 'Sales Tax', 'Total Amount']
        for col in numeric_cols:
            df[col] = df[col].apply(lambda x: f"Rs. {x:,.2f}")
        
        # If not editing, show the table with edit buttons
        if st.session_state.editing_trade is None:
            st.write("### Trade History")
            
            # Display each trade with action buttons
            for idx, row in df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
                    
                    with col1:
                        st.write(f"{row['Date']} - {row['Stock']} ({row['Shares']} shares @ {row['Rate']})")
                    
                    with col2:
                        if st.button("✏️ Edit", key=f"edit_{idx}"):
                            st.session_state.editing_trade = row.to_dict()
                            st.rerun()
                    
                    with col3:
                        if st.button("🗑️ Delete", key=f"delete_{idx}"):
                            st.session_state.confirm_delete = f"{row['Memo No']}_{row['Stock']}"
                            st.rerun()
                    
                    # Show delete confirmation if this is the row being deleted
                    if st.session_state.get('confirm_delete') == f"{row['Memo No']}_{row['Stock']}":
                        st.warning(f"Are you sure you want to delete this trade for **{row['Stock']}**?")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Yes, Delete", key=f"confirm_delete_{idx}"):
                                if delete_trade(row['Memo No'], row['Stock']):
                                    st.success(f"Successfully deleted trade for {row['Stock']}")
                                    st.session_state.confirm_delete = None
                                    st.rerun()
                        with col2:
                            if st.button("❌ No, Cancel", key=f"cancel_delete_{idx}"):
                                st.session_state.confirm_delete = None
                                st.rerun()
                
                st.divider()
            
            # Add summary metrics
            st.subheader("Portfolio Summary")
            total_investment = sum(float(str(val).replace('Rs. ', '').replace(',', '')) 
                                 for val in df['Total Amount'])
            total_shares = sum(int(str(val).replace(',', '')) for val in df['Shares'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Investment", f"Rs. {total_investment:,.2f}")
            with col2:
                st.metric("Total Shares", f"{total_shares:,}")
        
        # If editing, show the edit form
        else:
            if edit_trade(st.session_state.editing_trade):
                st.session_state.editing_trade = None
                st.rerun()
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
    
    finally:
        conn.close()

def delete_trade(memo_number, stock):
    """Delete a trade from the database"""
    
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute(
            "DELETE FROM trades WHERE memo_number = ? AND stock = ?",
            (memo_number, stock)
        )
        
        # Check if any trades remain for this memo
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
        st.session_state.confirm_delete = None
        return True
        
    except sqlite3.Error as e:
        cursor.execute("ROLLBACK")
        st.error(f"Error deleting trade: {str(e)}")
        return False
        
    finally:
        conn.close()