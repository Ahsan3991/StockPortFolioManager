import streamlit as st
import sqlite3
import pandas as pd

def delete_trade(memo_number, stock):
    """Deletes a single trade record while keeping other trades under the same memo."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        # Delete only the selected trade under the memo
        cursor.execute("DELETE FROM trades WHERE memo_number = ? AND stock = ?", (memo_number, stock))
        
        # Check if the memo number still has remaining trades
        cursor.execute("SELECT COUNT(*) FROM trades WHERE memo_number = ?", (memo_number,))
        remaining_trades = cursor.fetchone()[0]

        # If no trades remain under this memo, delete the memo entry too
        if remaining_trades == 0:
            cursor.execute("DELETE FROM memos WHERE memo_number = ?", (memo_number,))
        
        cursor.execute("COMMIT")
        return True
    except sqlite3.Error as e:
        cursor.execute("ROLLBACK")
        st.error(f"Error deleting trade: {str(e)}")
        return False
    finally:
        conn.close()

def delete_dividend(warrant_no):
    """Deletes a dividend record and its associated warrant."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        # Delete dividend record
        cursor.execute("DELETE FROM dividends WHERE warrant_no = ?", (warrant_no,))
        # Delete associated warrant
        cursor.execute("DELETE FROM warrants WHERE warrant_no = ?", (warrant_no,))
        cursor.execute("COMMIT")
        return True
    except sqlite3.Error as e:
        cursor.execute("ROLLBACK")
        st.error(f"Error deleting dividend: {str(e)}")
        return False
    finally:
        conn.close()

def view_trades():
    """Displays both trade transactions and dividend warrants stored in the database with delete functionality."""
    st.header("📊 Portfolio Transactions")
    
    # Initialize session state for deletion confirmation
    if 'delete_trade_id' not in st.session_state:
        st.session_state.delete_trade_id = None
    if 'delete_trade_stock' not in st.session_state:
        st.session_state.delete_trade_stock = None
    if 'delete_dividend_id' not in st.session_state:
        st.session_state.delete_dividend_id = None
    
    conn = sqlite3.connect("portfolio.db")
    
    # Fetch and display trade transactions
    st.subheader("📌 Trade Transactions")
    trade_query = """
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
    trade_df = pd.read_sql(trade_query, conn)
    
    if trade_df.empty:
        st.warning("No trade transactions found.")
    else:
        # Format numeric columns
        numeric_cols = ['Rate', 'Commission', 'CDC Charges', 'Sales Tax', 'Total Amount']
        for col in numeric_cols:
            if col in trade_df.columns:
                trade_df[col] = trade_df[col].round(2)
                trade_df[col] = trade_df[col].apply(lambda x: f"Rs. {x:,.2f}")
        
        # Format shares column
        trade_df['Shares'] = trade_df['Shares'].apply(lambda x: f"{x:,}")
        
        # Display the dataframe
        st.dataframe(trade_df, hide_index=True)
        
        # Add delete buttons below the table
        st.write("Select a trade to delete:")
        for i, row in trade_df.iterrows():
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                st.write(f"{row['Date']} - {row['Stock']} ({row['Shares']} shares)")
            with col2:
                if st.button("🗑️", key=f"delete_trade_{row['Memo No']}_{row['Stock']}"):
                    st.session_state.delete_trade_id = row['Memo No']
                    st.session_state.delete_trade_stock = row['Stock']
                    st.rerun()
        
        # Handle delete confirmation
        if st.session_state.delete_trade_id and st.session_state.delete_trade_stock:
            st.info(f"Are you sure you want to delete **{st.session_state.delete_trade_stock}** under memo `{st.session_state.delete_trade_id}`?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirm Delete", key=f"confirm_trade"):
                    if delete_trade(st.session_state.delete_trade_id, st.session_state.delete_trade_stock):
                        st.success(f"Trade for **{st.session_state.delete_trade_stock}** deleted successfully!")
                        st.session_state.delete_trade_id = None
                        st.session_state.delete_trade_stock = None
                        st.rerun()
            with col2:
                if st.button("❌ Cancel", key=f"cancel_trade"):
                    st.session_state.delete_trade_id = None
                    st.session_state.delete_trade_stock = None
                    st.rerun()
    
    st.divider()
    
    # Fetch and display dividend warrants
    st.subheader("💰 Dividend Warrants")
    dividend_query = """
        SELECT 
            d.warrant_no as 'Warrant No',
            d.payment_date as 'Payment Date',
            d.stock_name as 'Stock',
            d.rate_per_security as 'Rate/Share',
            d.number_of_securities as 'Shares',
            d.amount_of_dividend as 'Gross Amount',
            d.tax_deducted as 'Tax',
            d.amount_paid as 'Net Amount'
        FROM dividends d
        JOIN warrants w ON d.warrant_no = w.warrant_no
        ORDER BY d.payment_date DESC
    """
    dividend_df = pd.read_sql(dividend_query, conn)
    
    if dividend_df.empty:
        st.warning("No dividend warrants found.")
    else:
        # Format numeric columns
        numeric_cols = ['Rate/Share', 'Gross Amount', 'Tax', 'Net Amount']
        for col in numeric_cols:
            if col in dividend_df.columns:
                dividend_df[col] = dividend_df[col].round(2)
                dividend_df[col] = dividend_df[col].apply(lambda x: f"Rs. {x:,.2f}")
        
        # Format shares column
        dividend_df['Shares'] = dividend_df['Shares'].apply(lambda x: f"{x:,}")
        
        # Display the dataframe
        st.dataframe(dividend_df, hide_index=True)
        
        # Add delete buttons below the table
        st.write("Select a dividend to delete:")
        for i, row in dividend_df.iterrows():
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                st.write(f"{row['Payment Date']} - {row['Stock']} ({row['Shares']} shares)")
            with col2:
                if st.button("🗑️", key=f"delete_div_{row['Warrant No']}"):
                    st.session_state.delete_dividend_id = row['Warrant No']
                    st.rerun()
        
        # Handle delete button clicks
        if st.session_state.delete_dividend_id:
            st.info(f"Are you sure you want to delete the dividend with warrant number {st.session_state.delete_dividend_id}?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirm Delete", key=f"confirm_dividend"):
                    if delete_dividend(st.session_state.delete_dividend_id):
                        st.success("Dividend deleted successfully!")
                        st.session_state.delete_dividend_id = None
                        st.rerun()
            with col2:
                if st.button("❌ Cancel", key=f"cancel_dividend"):
                    st.session_state.delete_dividend_id = None
                    st.rerun()
    
    conn.close()
