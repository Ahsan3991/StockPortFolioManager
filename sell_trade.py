# sell_trade.py
import streamlit as st
import sqlite3
from datetime import datetime

def get_stock_details():
    """Fetches list of stocks with their quantities and average buying prices."""
    from db_utils import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get buy trade details
        cursor.execute("""
            SELECT 
                stock,
                SUM(quantity) as bought_qty,
                SUM(quantity * rate) / SUM(quantity) as avg_buy_price,
                SUM(total_amount) as total_investment
            FROM trades
            WHERE type = 'Buy'
            GROUP BY stock
        """)
        bought = {row[0]: {
            'quantity': row[1],
            'avg_price': row[2],
            'investment': row[3]
        } for row in cursor.fetchall()}
        
        # Get sell trade details
        cursor.execute("""
            SELECT stock, SUM(quantity) as sold_qty
            FROM sell_trades
            GROUP BY stock
        """)
        sold = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Calculate available quantities and details
        stock_details = {}
        for stock in bought:
            available_qty = bought[stock]['quantity'] - sold.get(stock, 0)
            if available_qty > 0:
                stock_details[stock] = {
                    'available_qty': available_qty,
                    'avg_buy_price': bought[stock]['avg_price'],
                    'total_investment': bought[stock]['investment']
                }
                
        return stock_details
    finally:
        conn.close()

def sell_trade():
    """Handles selling stocks and CGT calculations."""
    st.header("💹 Sell Stock")
    
    # Get stock details
    stock_details = get_stock_details()
    
    if not stock_details:
        st.warning("No stocks available to sell. Please add some buy trades first.")
        return
    
    # Create two columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Stock Selection")
        selected_stock = st.selectbox(
            "Select Stock to Sell",
            options=list(stock_details.keys()),
            help="Choose from your available stocks"
        )
        
        stock_info = stock_details[selected_stock]
        available_qty = stock_info['available_qty']
        avg_buy_price = stock_info['avg_buy_price']
        
        st.info(f"""
            Current Position:
            - Available: {available_qty:,} shares
            - Avg. Buy Price: Rs. {avg_buy_price:.2f}/share
            - Total Investment: Rs. {stock_info['total_investment']:,.2f}
        """)
        
        quantity = st.number_input(
            "Quantity to Sell",
            min_value=1,
            max_value=available_qty,
            step=1,
            help="Enter the number of shares you want to sell"
        )
    
    with col2:
        st.subheader("Sale Details")
        rate = st.number_input(
            "Selling Rate (Rs.)",
            min_value=0.01,
            step=0.01,
            format="%.2f",
            help="Enter the price per share"
        )
        
        # Show potential profit/loss
        if rate > 0:
            profit_per_share = rate - avg_buy_price
            total_profit = profit_per_share * quantity
            profit_percentage = (profit_per_share / avg_buy_price) * 100 if avg_buy_price > 0 else 0
            
            if profit_per_share > 0:
                st.success(f"""
                    Potential Profit:
                    - Per Share: Rs. {profit_per_share:.2f}
                    - Total: Rs. {total_profit:,.2f}
                    - Return: {profit_percentage:.1f}%
                """)
            else:
                st.error(f"""
                    Potential Loss:
                    - Per Share: Rs. {abs(profit_per_share):.2f}
                    - Total: Rs. {abs(total_profit):,.2f}
                    - Return: {profit_percentage:.1f}%
                """)
        
        cgt_percentage = st.number_input(
            "Capital Gains Tax (%)",
            min_value=0.0,
            max_value=100.0,
            value=15.0,  # Default CGT rate
            step=0.1,
            format="%.1f",
            help="Enter the applicable CGT percentage"
        )
    
    # Calculate values
    sale_amount = quantity * rate
    cgt_value = (cgt_percentage / 100) * sale_amount
    net_amount = sale_amount - cgt_value
    
    # Display summary
    st.subheader("Transaction Summary")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Sale Amount",
            f"Rs. {sale_amount:,.2f}",
            help="Total value before tax"
        )
    with col2:
        st.metric(
            "CGT Amount",
            f"Rs. {cgt_value:,.2f}",
            help="Capital Gains Tax"
        )
    with col3:
        st.metric(
            "Net Amount",
            f"Rs. {net_amount:,.2f}",
            help="Amount after tax"
        )

    # Add divider
    st.divider()

    # Validation and submission
    if st.button("Confirm Sale", type="primary"):
        if quantity > available_qty:
            st.error(f"Cannot sell {quantity} shares. Only {available_qty} available.")
            return
        
        from db_utils import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            # Generate unique memo number for the sale
            memo_number = f"S{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Insert sell trade record - FIXED COLUMN NAME
            cursor.execute("""
                INSERT INTO sell_trades (
                    stock,
                    quantity,
                    rate,
                    sale_amount,
                    cgt_amount,
                    cgt_percentage,
                    net_amount,
                    sell_date,
                    memo_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                selected_stock,
                quantity,
                rate,
                sale_amount,
                cgt_value,
                cgt_percentage,
                net_amount,
                datetime.now().strftime('%Y-%m-%d'),
                memo_number
            ))
            
            cursor.execute("COMMIT")
            
            st.success(f"""
                ✅ Sale completed successfully!
                
                Transaction Details:
                - Stock: {selected_stock}
                - Quantity: {quantity:,} shares
                - Rate: Rs. {rate:,.2f}
                - Total Amount: Rs. {sale_amount:,.2f}
                - CGT ({cgt_percentage}%): Rs. {cgt_value:,.2f}
                - Net Amount: Rs. {net_amount:,.2f}
                - Memo Number: {memo_number}
                
                Profit/Loss:
                - Buy Price: Rs. {avg_buy_price:.2f}/share
                - Sell Price: Rs. {rate:.2f}/share
                - P/L per Share: Rs. {profit_per_share:.2f}
                - Total P/L: Rs. {total_profit:,.2f} ({profit_percentage:.1f}%)
            """)
            
            # Show remaining position
            remaining = available_qty - quantity
            remaining_value = remaining * avg_buy_price
            st.info(f"""
                Updated Position:
                - Remaining Shares: {remaining:,}
                - Position Value: Rs. {remaining_value:,.2f}
            """)
            
        except sqlite3.Error as e:
            cursor.execute("ROLLBACK")
            st.error(f"Error recording sale: {str(e)}")
        finally:
            conn.close()
            
        # Option to sell more
        if st.button("Sell More Stocks"):
            st.rerun()