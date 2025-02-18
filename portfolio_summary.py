# portfolio_summary.py
import streamlit as st
import sqlite3
import pandas as pd
import json
import plotly.express as px
from streamlit.components.v1 import html

def get_portfolio_positions():
    """Gets current position for all stocks."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    
    try:
        # Get buy positions
        cursor.execute("""
            SELECT 
                stock,
                SUM(quantity) as total_bought,
                SUM(quantity * rate) / SUM(quantity) as avg_price,
                SUM(total_amount) as total_investment
            FROM trades
            WHERE type = 'Buy'
            GROUP BY stock
        """)
        buy_positions = {row[0]: {
            'total_bought': row[1],
            'avg_price': row[2],
            'investment': row[3]
        } for row in cursor.fetchall()}
        
        # Get sell positions
        cursor.execute("""
            SELECT 
                stock,
                SUM(quantity) as total_sold,
                SUM(sale_amount) as total_sales,
                SUM(cgt_amount) as total_tax
            FROM sell_trades
            GROUP BY stock
        """)
        sell_positions = {row[0]: {
            'total_sold': row[1],
            'total_sales': row[2],
            'total_tax': row[3]
        } for row in cursor.fetchall()}
        
        # Calculate current positions
        positions = []
        for stock in buy_positions:
            buy_data = buy_positions[stock]
            sell_data = sell_positions.get(stock, {
                'total_sold': 0,
                'total_sales': 0,
                'total_tax': 0
            })
            
            remaining = buy_data['total_bought'] - sell_data['total_sold']
            if remaining > 0:
                positions.append({
                    'Stock': stock,
                    'Total Bought': buy_data['total_bought'],
                    'Total Sold': sell_data['total_sold'],
                    'Remaining': remaining,
                    'Avg. Buy Price': buy_data['avg_price'],
                    'Current Value': remaining * buy_data['avg_price'],
                    'Total Investment': buy_data['investment'],
                    'Total Sales': sell_data['total_sales'],
                    'Total Tax': sell_data['total_tax']
                })
        
        return positions
    finally:
        conn.close()

def calculate_realized_pl():
    """Calculates realized profit/loss from completed sales."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    
    try:
        # Get buy prices for all sold stocks
        cursor.execute("""
            SELECT 
                stock,
                quantity,
                rate as buy_rate,
                total_amount as buy_amount
            FROM trades
            WHERE type = 'Buy'
        """)
        buy_trades = cursor.fetchall()
        
        # Get all sell trades
        cursor.execute("""
            SELECT 
                stock,
                quantity,
                rate as sell_rate,
                sale_amount,
                cgt_amount,
                net_amount,
                sell_date
            FROM sell_trades
            ORDER BY sell_date
        """)
        sell_trades = cursor.fetchall()
        
        # Calculate P/L for each stock
        realized_pl = {}
        for sell in sell_trades:
            stock = sell[0]
            sell_qty = sell[1]
            sell_rate = sell[2]
            sell_amount = sell[3]
            tax = sell[4]
            
            # Find matching buy trades for this stock
            matching_buys = [t for t in buy_trades if t[0] == stock]
            if matching_buys:
                # Calculate average buy price for this stock
                total_buy_qty = sum(t[1] for t in matching_buys)
                total_buy_amount = sum(t[3] for t in matching_buys)
                avg_buy_price = total_buy_amount / total_buy_qty
                
                # Calculate P/L
                buy_value = avg_buy_price * sell_qty
                pl_before_tax = sell_amount - buy_value
                pl_after_tax = pl_before_tax - tax
                
                # Add to realized P/L
                if stock not in realized_pl:
                    realized_pl[stock] = {
                        'total_sold': 0,
                        'total_buy_value': 0,
                        'total_sell_value': 0,
                        'total_tax': 0,
                        'net_pl': 0
                    }
                
                realized_pl[stock]['total_sold'] += sell_qty
                realized_pl[stock]['total_buy_value'] += buy_value
                realized_pl[stock]['total_sell_value'] += sell_amount
                realized_pl[stock]['total_tax'] += tax
                realized_pl[stock]['net_pl'] += pl_after_tax
        
        return realized_pl
    finally:
        conn.close()

def calculate_total_dividends():
    """Calculates total dividends earned per stock."""
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                stock_name,
                SUM(amount_of_dividend) as total_dividend,
                SUM(tax_deducted) as total_tax,
                SUM(amount_paid) as net_amount,
                COUNT(*) as num_payments
            FROM dividends
            GROUP BY stock_name
        """)
        
        return {row[0]: {
            'total_dividend': row[1],
            'total_tax': row[2],
            'net_amount': row[3],
            'num_payments': row[4]
        } for row in cursor.fetchall()}
    finally:
        conn.close()

def view_dividend_income():
    """Displays dividend income summary along with a line chart of dividends over time."""
    st.subheader("📈 Dividend Income Over Time")
    
    conn = sqlite3.connect("portfolio.db")
    
    # Query to fetch dividend data
    dividend_query = """
        SELECT payment_date as 'Date', amount_paid as 'Net Dividend'
        FROM dividends
        ORDER BY payment_date ASC
    """
    dividend_df = pd.read_sql(dividend_query, conn)
    conn.close()
    
    if dividend_df.empty:
        st.warning("No dividend records found.")
    else:
        # Convert date column to datetime
        dividend_df['Date'] = pd.to_datetime(dividend_df['Date'])

        # Create line chart
        fig = px.line(dividend_df, x='Date', y='Net Dividend', 
                      markers=True, title="Dividend Income Over Time",
                      labels={'Net Dividend': 'Net Dividend (Rs.)', 'Date': 'Payment Date'})

        # Display chart
        st.plotly_chart(fig, use_container_width=True)

        # Display raw dividend data
        st.write("### Dividend Details")
        st.dataframe(dividend_df.style.format({"Net Dividend": "Rs. {:.2f}"}), hide_index=True)

def view_portfolio_summary():
    """Displays comprehensive portfolio summary with P/L and dividends."""
    st.header("📊 Portfolio Summary")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Current Positions", "Realized P/L", "Dividend Income"])
    
    with tab1:
        positions = get_portfolio_positions()
        
        if not positions:
            st.warning("No active positions found in portfolio.")
        else:
            df = pd.DataFrame(positions)
            
            # Format numeric columns
            df['Total Bought'] = df['Total Bought'].apply(lambda x: f"{x:,}")
            df['Total Sold'] = df['Total Sold'].apply(lambda x: f"{x:,}")
            df['Remaining'] = df['Remaining'].apply(lambda x: f"{x:,}")
            df['Avg. Buy Price'] = df['Avg. Buy Price'].apply(lambda x: f"Rs. {x:,.2f}")
            df['Current Value'] = df['Current Value'].apply(lambda x: f"Rs. {x:,.2f}")
            df['Total Investment'] = df['Total Investment'].apply(lambda x: f"Rs. {x:,.2f}")
            df['Total Sales'] = df['Total Sales'].apply(lambda x: f"Rs. {x:,.2f}")
            df['Total Tax'] = df['Total Tax'].apply(lambda x: f"Rs. {x:,.2f}")
            
            st.dataframe(df, hide_index=True)
            
            # Add Portfolio Distribution Pie Chart
            st.subheader("Portfolio Distribution")
            
            # Prepare data for pie chart
            pie_data = []
            total_shares = 0
            
            # Convert string numbers back to numeric for calculations
            for pos in positions:
                shares = pos['Remaining']  # This is already numeric from your query
                total_shares += shares
                pie_data.append({
                    'Stock': pos['Stock'],
                    'Shares': shares,
                    'Percentage': 0  # Will calculate after getting total
                })
            
            # Calculate percentages
            for item in pie_data:
                item['Percentage'] = (item['Shares'] / total_shares * 100) if total_shares > 0 else 0
            
            # Create pie chart using plotly
            fig = px.pie(
                pie_data,
                values='Shares',
                names='Stock',
                title=f'Portfolio Distribution (Total Shares: {total_shares:,})',
                hover_data=['Percentage'],
                custom_data=['Percentage']
            )
            
            # Update hover template to show shares and percentage
            fig.update_traces(
                hovertemplate="<b>%{label}</b><br>" +
                             "Shares: %{value:,.0f}<br>" +
                             "Percentage: %{customdata[0]:.2f}%<br>" +
                             "<extra></extra>"
            )
            
            # Update layout
            fig.update_layout(
                showlegend=True,
                height=500,
                margin=dict(t=50, b=0, l=0, r=0)
            )
            
            # Display the chart
            st.plotly_chart(fig, use_container_width=True)
            
            # Show distribution details in a table
            st.subheader("Distribution Details")
            distribution_df = pd.DataFrame([{
                'Stock': d['Stock'],
                'Shares': f"{int(d['Shares']):,}",
                'Percentage': f"{d['Percentage']:.2f}%"
            } for d in pie_data])
            st.dataframe(distribution_df, hide_index=True)
            
            # Position Summary
            total_value = sum(pos['Current Value'] for pos in positions)
            total_investment = sum(pos['Total Investment'] for pos in positions)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Portfolio Value", f"Rs. {total_value:,.2f}")
            with col2:
                st.metric("Total Investment", f"Rs. {total_investment:,.2f}")
    
    with tab2:
        realized_pl = calculate_realized_pl()
        
        if not realized_pl:
            st.warning("No realized profits/losses found.")
        else:
            # Create P/L DataFrame
            pl_data = []
            for stock, data in realized_pl.items():
                pl_data.append({
                    'Stock': stock,
                    'Shares Sold': f"{data['total_sold']:,}",
                    'Total Buy Value': f"Rs. {data['total_buy_value']:,.2f}",
                    'Total Sell Value': f"Rs. {data['total_sell_value']:,.2f}",
                    'Tax Paid': f"Rs. {data['total_tax']:,.2f}",
                    'Net P/L': f"Rs. {data['net_pl']:,.2f}"
                })
            
            pl_df = pd.DataFrame(pl_data)
            st.dataframe(pl_df, hide_index=True)
            
            # P/L Summary
            total_pl = sum(data['net_pl'] for data in realized_pl.values())
            total_tax = sum(data['total_tax'] for data in realized_pl.values())
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "Total Realized P/L",
                    f"Rs. {total_pl:,.2f}",
                    delta=f"{'↑' if total_pl > 0 else '↓'} {abs(total_pl):,.2f}"
                )
            with col2:
                st.metric("Total Tax Paid", f"Rs. {total_tax:,.2f}")
    
    with tab3:
        view_dividend_income()
        dividends = calculate_total_dividends()
        
        if not dividends:
            st.warning("No dividend income found.")
        else:
            # Create Dividends DataFrame
            div_data = []
            for stock, data in dividends.items():
                div_data.append({
                    'Stock': stock,
                    'Total Dividend': f"Rs. {data['total_dividend']:,.2f}",
                    'Tax Deducted': f"Rs. {data['total_tax']:,.2f}",
                    'Net Amount': f"Rs. {data['net_amount']:,.2f}",
                    'Number of Payments': data['num_payments']
                })
            
            div_df = pd.DataFrame(div_data)
            st.dataframe(div_df, hide_index=True)
            
            # Dividend Summary
            total_dividend = sum(data['total_dividend'] for data in dividends.values())
            total_tax = sum(data['total_tax'] for data in dividends.values())
            net_dividend = sum(data['net_amount'] for data in dividends.values())
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Dividends", f"Rs. {total_dividend:,.2f}")
            with col2:
                st.metric("Tax Deducted", f"Rs. {total_tax:,.2f}")
            with col3:
                st.metric("Net Dividend Income", f"Rs. {net_dividend:,.2f}")

    # Overall Portfolio Performance
    st.divider()
    st.subheader("📈 Overall Portfolio Performance")
    
    try:
        total_pl = sum(data['net_pl'] for data in realized_pl.values()) if realized_pl else 0
        net_dividend = sum(data['net_amount'] for data in dividends.values()) if dividends else 0
        total_return = total_pl + net_dividend
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Total Realized P/L",
                f"Rs. {total_pl:,.2f}",
                delta=f"{'↑' if total_pl > 0 else '↓'} {abs(total_pl):,.2f}"
            )
        with col2:
            st.metric("Total Dividend Income", f"Rs. {net_dividend:,.2f}")
        with col3:
            st.metric(
                "Total Returns",
                f"Rs. {total_return:,.2f}",
                delta=f"{'↑' if total_return > 0 else '↓'} {abs(total_return):,.2f}"
            )
    except:
        st.info("Insufficient data to calculate overall performance.")