# portfolio_summary.py
import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
from psx import stocks
from real_time_stock_prices import get_psx_stock_price

def migrate_stock_prices_buffer():
    """Adds buffer_price column to stock_prices table if it doesn't exist."""
    from db_utils import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if we need to add the buffer_price column
        cursor.execute("PRAGMA table_info(stock_prices)")
        columns = {col[1] for col in cursor.fetchall()}
        
        if 'buffer_price' not in columns:
            cursor.execute("ALTER TABLE stock_prices ADD COLUMN buffer_price REAL")
            
        conn.commit()
        
    except sqlite3.Error as e:
        print(f"Migration error: {str(e)}")
        
    finally:
        conn.close()

# Run migration when initializing the app
migrate_stock_prices_buffer()

def get_portfolio_positions():
    """Gets current position for all stocks with real-time previous close price and calculates P/L."""
    from db_utils import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get buy positions with proper grouping
        cursor.execute("""
            SELECT 
                UPPER(TRIM(stock)) as stock_name,
                SUM(quantity) as total_bought,
                CAST(SUM(quantity * rate) AS FLOAT) / CAST(SUM(quantity) AS FLOAT) as avg_price,
                SUM(total_amount) as total_investment
            FROM trades
            WHERE type = 'Buy'
            GROUP BY stock_name
        """)
        
        buy_positions = {row[0]: {
            'total_bought': row[1],
            'avg_price': row[2],
            'investment': row[3]
        } for row in cursor.fetchall()}

        # Get sell positions with proper grouping
        cursor.execute("""
            SELECT 
                UPPER(TRIM(stock)) as stock_name,
                SUM(quantity) as total_sold,
                SUM(sale_amount) as total_sales,
                SUM(cgt_amount) as total_tax
            FROM sell_trades
            GROUP BY stock_name
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
                # Fetch previous close price (NO ".KAR" suffix)
                previous_close = get_psx_stock_price(stock)

                # Calculate P/L if price is available
                if previous_close is not None:
                    open_pl = (previous_close - buy_data["avg_price"]) * remaining
                    current_value = previous_close * remaining
                else:
                    open_pl, current_value = None, None

                positions.append({
                    'Stock': stock,
                    'Total Bought': buy_data['total_bought'],
                    'Total Sold': sell_data['total_sold'],
                    'Remaining': remaining,
                    'Avg. Buy Price': buy_data['avg_price'],
                    'Previous Close': previous_close if isinstance(previous_close, (int, float)) else None,
                    'Current Value': current_value if current_value is not None else None,
                    'Total Investment': buy_data['investment'],
                    'Total Sales': sell_data['total_sales'],
                    'Total Tax': sell_data['total_tax'],
                    'Open P/L': round(open_pl, 2) if open_pl is not None else None,
                })

        return positions
    finally:
        conn.close()

def portfolio_distribution():
    """Displays the portfolio distribution with multiple options (Shares vs Wealth)."""
    positions = get_portfolio_positions()

    if not positions:
        st.warning("No active positions found in portfolio.")
        return

    df = pd.DataFrame(positions)
    df.rename(columns={'Remaining': 'Shares'}, inplace=True)

    total_shares = df['Shares'].sum()
    total_investment = df['Total Investment'].sum()

    # Dropdown menu for selecting distribution type
    distribution_type = st.selectbox(
        "Select Distribution Type",
        ["Share Distribution", "Wealth Distribution"]
    )

    df = df.copy()  # Avoids SettingWithCopyWarning
    if distribution_type == "Share Distribution":
        df['Percentage'] = (df['Shares'] / total_shares * 100) if total_shares > 0 else 0
        values_column = "Shares"
        title = f"Portfolio Distribution (Total Shares: {total_shares:,})"
    else:
        df['Percentage'] = (df['Total Investment'] / total_investment * 100) if total_investment > 0 else 0
        values_column = "Total Investment"
        title = f"Wealth Distribution (Total Investment: Rs. {total_investment:,.2f})"

    df['Percentage'] = df['Percentage'].astype(float)  # Ensures float before formatting

    # Create Pie Chart
    fig = px.pie(
        df,
        values=values_column,
        names="Stock",
        title=title,
        hover_data={'Percentage': ':.2f'},
        custom_data=['Percentage']
    )

    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>" +
                     "Value: %{value:,.2f}<br>" +
                     "Percentage: %{customdata[0]:.2f}%<br>" +
                     "<extra></extra>"
    )

    # Increase pie chart size for better visibility
    fig.update_layout(
        showlegend=True,
        height=500,  
        width=800,   
        margin=dict(t=50, b=0, l=0, r=0)
    )

    # Show Pie Chart
    st.plotly_chart(fig, use_container_width=True)

    # Display Table Below Pie Chart
    st.subheader("Distribution Details")
    distribution_df = df[['Stock', values_column, 'Percentage']].copy()
    distribution_df[values_column] = distribution_df[values_column].apply(
        lambda x: f"Rs. {x:,.2f}" if distribution_type == "Wealth Distribution" else f"{int(x):,}"
    )
    distribution_df['Percentage'] = distribution_df['Percentage'].apply(lambda x: f"{x:.2f}%")

    st.dataframe(distribution_df, hide_index=True)


def calculate_realized_pl():
    """Calculates realized profit/loss from completed sales."""
    from db_utils import get_db_connection
    conn = get_db_connection()
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
    from db_utils import get_db_connection
    conn = get_db_connection()
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

# Fix for view_dividend_income function in portfolio_summary.py
def view_dividend_income():
    """Displays dividend income summary along with a line chart of dividends over time."""
    st.subheader("📈 Dividend Income Over Time")
    
    from db_utils import get_db_connection
    conn = get_db_connection()
    
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
        # Try to convert dates without dropping rows
        try:
            # Try parsing dates with flexible approach
            dividend_df['Date_Parsed'] = pd.to_datetime(dividend_df['Date'], errors='coerce')
            
            # Create a dataframe that only includes rows with successfully parsed dates for the chart
            chart_df = dividend_df.dropna(subset=['Date_Parsed']).copy()
            
            if chart_df.empty:
                st.warning("Could not parse any date values for the chart visualization.")
            else:
                # Create line chart with the parsed dates
                fig = px.line(chart_df, x='Date_Parsed', y='Net Dividend', 
                            markers=True, title="Dividend Income Over Time",
                            labels={'Net Dividend': 'Net Dividend (Rs.)', 'Date_Parsed': 'Payment Date'})
                st.plotly_chart(fig, use_container_width=True)
            
            # Show all data in the table view with original dates
            st.write("### Dividend Details")
            display_df = dividend_df[['Date', 'Net Dividend']].copy()  # Use original dates for display
            st.dataframe(display_df.style.format({"Net Dividend": "Rs. {:.2f}"}), hide_index=True)
            
        except Exception as e:
            st.error(f"Error parsing dates: {str(e)}")
            
            # Still show the raw data even if chart fails
            st.write("### Dividend Details")
            st.dataframe(dividend_df.style.format({"Net Dividend": "Rs. {:.2f}"}), hide_index=True)
        

def get_metal_portfolio():
    """Gets current position for all metals with real-time pricing and calculates P/L."""
    from db_utils import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Import the metal pricing function at runtime to avoid circular imports
        from real_time_metal_pricing import get_latest_metal_prices
        from real_time_metal_pricing import get_metal_price_in_currency
        
        # Get latest metal prices (now in PKR)
        metal_prices = get_latest_metal_prices()
        
        # Get all metal trades
        cursor.execute("""
            SELECT 
                metal,
                SUM(weight) as total_weight,
                CAST(SUM(weight * purchase_price) AS FLOAT) / CAST(SUM(weight) AS FLOAT) as avg_price,
                SUM(total_cost) as total_investment,
                karat,
                MIN(date) as first_purchase,
                MAX(date) as latest_purchase
            FROM metal_trades
            GROUP BY metal, karat
        """)
        
        positions = []
        for row in cursor.fetchall():
            metal_name = row[0]
            total_weight = row[1]
            avg_price = row[2]
            total_investment = row[3]
            karat = row[4]
            
            # Map the database metal names to API metal codes
            metal_code_map = {
                "Gold": "XAU",
                "Silver": "XAG", 
                "Platinum": "XPT",
                "Palladium": "XPD"
            }
            
            metal_code = metal_code_map.get(metal_name)
            current_price = None
            # Ensure we get the price in PKR
            current_price = get_metal_price_in_currency(metal_code, karat, "PKR")
            
            # Calculate current value and P/L if price is available
            if current_price is not None:
                current_value = current_price * total_weight
                open_pl = (current_price - avg_price) * total_weight
                pl_percentage = (current_price / avg_price - 1) * 100 if avg_price > 0 else 0
            else:
                current_value, open_pl, pl_percentage = None, None, None
                
            positions.append({
                'Metal': f"{metal_name} ({karat}K)",
                'Total Weight (g)': total_weight,
                'Avg. Purchase Price': avg_price,
                'Current Price': current_price,
                'Current Value': current_value,
                'Total Investment': total_investment,
                'Open P/L': open_pl,
                'P/L %': pl_percentage,
                'First Purchase': row[5],
                'Latest Purchase': row[6]
            })
            
        return positions
    finally:
        conn.close()

def metal_distribution():
    """Displays the metal portfolio distribution with multiple options (Weight vs Value)."""
    positions = get_metal_portfolio()

    if not positions:
        st.warning("No metal positions found in portfolio.")
        return

    df = pd.DataFrame(positions)
    
    # Extract total weight and investment
    total_weight = df['Total Weight (g)'].sum()
    total_investment = df['Total Investment'].sum()

    # Dropdown menu for selecting distribution type
    distribution_type = st.selectbox(
        "Select Distribution Type",
        ["Weight Distribution", "Value Distribution"],
        key="metal_dist_type"
    )

    df = df.copy()  # Avoids SettingWithCopyWarning
    if distribution_type == "Weight Distribution":
        df['Percentage'] = (df['Total Weight (g)'] / total_weight * 100) if total_weight > 0 else 0
        values_column = "Total Weight (g)"
        title = f"Metal Portfolio Distribution (Total Weight: {total_weight:,.2f}g)"
    else:
        df['Percentage'] = (df['Total Investment'] / total_investment * 100) if total_investment > 0 else 0
        values_column = "Total Investment"
        title = f"Metal Value Distribution (Total Investment: PKR {total_investment:,.2f})"

    # Create Pie Chart with custom color scheme for metals
    color_map = {
        "Gold": "#FFD700",
        "Silver": "#C0C0C0",
        "Platinum": "#E5E4E2", 
        "Palladium": "#CEC3B6"
    }
    
    # Extract base metal from the Metal column (removing the karat info)
    df['Base Metal'] = df['Metal'].apply(lambda x: x.split(" ")[0])
    
    # Create custom color list based on the metals in the dataframe
    colors = [color_map.get(metal, "#1f77b4") for metal in df['Base Metal']]
    
    fig = px.pie(
        df,
        values=values_column,
        names="Metal",
        title=title,
        hover_data={'Percentage': ':.2f'},
        custom_data=['Percentage']
    )
    
    # Apply custom colors
    fig.update_traces(
        marker=dict(colors=colors),
        hovertemplate="<b>%{label}</b><br>" +
                     f"{values_column}: %{{value:,.2f}}<br>" +
                     "Percentage: %{customdata[0]:.2f}%<br>" +
                     "<extra></extra>"
    )

    # Increase pie chart size
    fig.update_layout(
        showlegend=True,
        height=500,  
        width=800,   
        margin=dict(t=50, b=0, l=0, r=0)
    )

    # Show Pie Chart
    st.plotly_chart(fig, use_container_width=True)

    # Display Table Below Pie Chart
    st.subheader("Distribution Details")
    distribution_df = df[['Metal', values_column, 'Percentage']].copy()
    distribution_df[values_column] = distribution_df[values_column].apply(
        lambda x: f"PKR {x:,.2f}" if distribution_type == "Value Distribution" else f"{x:,.2f}g"
    )
    distribution_df['Percentage'] = distribution_df['Percentage'].apply(lambda x: f"{x:.2f}%")
    
    st.dataframe(distribution_df, hide_index=True)

def create_metal_price_history_chart():
    """Create a chart showing the price history of metals over time based on purchases."""
    from db_utils import get_db_connection
    conn = get_db_connection()
    
    # Query to get purchase dates and prices for each metal
    price_query = """
        SELECT 
            date as 'Purchase Date', 
            metal as 'Metal',
            karat as 'Karat',
            purchase_price as 'Price per Gram'
        FROM metal_trades
        ORDER BY date ASC
    """
    
    price_df = pd.read_sql(price_query, conn)
    conn.close()
    
    if price_df.empty:
        st.warning("No metal trade records found.")
        return
        
    # Create a unique identifier for each metal+karat combination
    price_df['Metal Type'] = price_df['Metal'] + " (" + price_df['Karat'].astype(str) + "K)"
    
    # Convert date column to datetime
    price_df['Purchase Date'] = pd.to_datetime(price_df['Purchase Date'])
    
    # Create line chart with a separate line for each metal type
    fig = px.line(
        price_df, 
        x='Purchase Date', 
        y='Price per Gram',
        color='Metal Type',
        markers=True,
        title="Metal Purchase Price History",
        labels={'Price per Gram': 'Price per Gram (PKR)', 'Purchase Date': 'Date'}
    )
    
    # Customize layout
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Price per Gram (PKR)",
        legend_title="Metal",
        hovermode="closest"
    )
    
    # Display chart
    st.plotly_chart(fig, use_container_width=True)

def view_metal_portfolio_summary():
    """Displays comprehensive metal portfolio summary with P/L."""
    st.subheader("🥇 Precious Metals Portfolio")
    
    positions = get_metal_portfolio()
    
    if not positions:
        st.warning("No metal positions found in portfolio.")
        return
        
    df = pd.DataFrame(positions)
    
    # Convert columns to numeric
    df["Open P/L"] = pd.to_numeric(df["Open P/L"], errors="coerce")
    df["Current Value"] = pd.to_numeric(df["Current Value"], errors="coerce")
    
    # Calculate totals
    total_investment = df["Total Investment"].sum()
    total_open_pl = df["Open P/L"].sum(skipna=True)
    total_current_value = df["Current Value"].sum(skipna=True)
    
    # Format for display
    formatted_df = df.copy()
    formatted_df['Total Weight (g)'] = formatted_df['Total Weight (g)'].apply(lambda x: f"{x:,.2f}")
    formatted_df['Avg. Purchase Price'] = formatted_df['Avg. Purchase Price'].apply(lambda x: f"PKR {x:,.2f}")
    formatted_df['Current Price'] = formatted_df['Current Price'].apply(lambda x: f"PKR {x:,.2f}" if isinstance(x, (int, float)) else "N/A")
    formatted_df['Current Value'] = formatted_df['Current Value'].apply(lambda x: f"PKR {x:,.2f}" if isinstance(x, (int, float)) else "N/A")
    formatted_df['Total Investment'] = formatted_df['Total Investment'].apply(lambda x: f"PKR {x:,.2f}")
    formatted_df['Open P/L'] = formatted_df['Open P/L'].apply(lambda x: f"PKR {x:,.2f}" if isinstance(x, (int, float)) else "N/A")
    formatted_df['P/L %'] = formatted_df['P/L %'].apply(lambda x: f"{x:,.2f}%" if isinstance(x, (int, float)) else "N/A")
    
    # Display the data table
    st.dataframe(formatted_df, hide_index=True)
    
    # Portfolio Metrics Section
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.subheader("📈 Metals Portfolio Metrics")
    
    # Create three columns for metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Investment",
            f"PKR {total_investment:,.2f}",
            help="Total amount invested in metals"
        )
    
    with col2:
        st.metric(
            "Total Open P/L",
            f"PKR {total_open_pl:,.2f}",
            delta=f"{'↑' if total_open_pl > 0 else '↓'} {abs(total_open_pl):,.2f}",
            help="Unrealized profit/loss based on current metal prices"
        )
    
    with col3:
        st.metric(
            "Portfolio Value",
            f"PKR {total_current_value:,.2f}",
            delta=f"{((total_current_value/total_investment - 1) * 100):,.2f}%" if total_investment > 0 else "0%",
            help="Current total value of your metals portfolio"
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Add Portfolio Distribution Pie Chart
    st.subheader("📊 Metals Portfolio Distribution")
    metal_distribution()
    
    # Add price history chart
    st.subheader("📈 Metal Price History")
    create_metal_price_history_chart()

def view_portfolio_summary():
    """Displays comprehensive portfolio summary with P/L and dividends."""
    st.subheader("📝 Holdings Table")
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Current Positions", "Realized P/L", "Dividend Income", "Metals Portfolio"])
    
    with tab1:
        positions = get_portfolio_positions()
        
        if not positions:
            st.warning("No active positions found in portfolio.")
        else:
            df = pd.DataFrame(positions)

            # Convert "Open P/L" to numeric while handling None values
            df["Open P/L"] = pd.to_numeric(df["Open P/L"], errors="coerce")
            
            # Calculate total Open P/L (ignoring None values)
            total_open_pl = df["Open P/L"].sum(skipna=True)
            
            # Calculate total investment
            total_investment = df["Total Investment"].sum()
            
            # Calculate total portfolio value
            total_portfolio_value = total_investment + total_open_pl

            # Format numeric columns
            df['Total Bought'] = df['Total Bought'].apply(lambda x: f"{x:,}")
            df['Total Sold'] = df['Total Sold'].apply(lambda x: f"{x:,}")
            df['Remaining'] = df['Remaining'].apply(lambda x: f"{x:,}")
            df['Avg. Buy Price'] = df['Avg. Buy Price'].apply(lambda x: f"Rs. {x:,.2f}")
            df['Previous Close'] = df['Previous Close'].apply(lambda x: f"Rs. {x:,.2f}" if isinstance(x, (int, float)) else "N/A")
            df['Current Value'] = df['Current Value'].apply(lambda x: f"Rs. {x:,.2f}" if isinstance(x, (int, float)) else "N/A")
            df['Total Investment'] = df['Total Investment'].apply(lambda x: f"Rs. {x:,.2f}")
            df['Total Sales'] = df['Total Sales'].apply(lambda x: f"Rs. {x:,.2f}")
            df['Total Tax'] = df['Total Tax'].apply(lambda x: f"Rs. {x:,.2f}")
            df['Open P/L'] = df['Open P/L'].apply(lambda x: f"Rs. {x:,.2f}" if isinstance(x, (int, float)) else "N/A")

            st.dataframe(df, hide_index=True)

            # Portfolio Metrics Section
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.subheader("📈 Portfolio Metrics")
            
            # Create three columns for metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Total Investment",
                    f"Rs. {total_investment:,.2f}",
                    help="Total amount invested in current positions"
                )
            
            with col2:
                st.metric(
                    "Total Open P/L",
                    f"Rs. {total_open_pl:,.2f}",
                    delta=f"{'↑' if total_open_pl > 0 else '↓'} {abs(total_open_pl):,.2f}",
                    help="Unrealized profit/loss based on current market prices"
                )
            
            with col3:
                st.metric(
                    "Portfolio Value",
                    f"Rs. {total_portfolio_value:,.2f}",
                    delta=f"{((total_portfolio_value/total_investment - 1) * 100):,.2f}%" if total_investment > 0 else "0%",
                    help="Current total value of your portfolio including unrealized P/L"
                )

            st.markdown('</div>', unsafe_allow_html=True)

            # Add Portfolio Distribution Pie Chart with Dropdown Options
            st.subheader("📊 Portfolio Distribution")
            portfolio_distribution()
    
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
            
            # Add metric container styling
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "Total Realized P/L",
                    f"Rs. {total_pl:,.2f}",
                    delta=f"{'↑' if total_pl > 0 else '↓'} {abs(total_pl):,.2f}",
                    help="Total profit/loss from completed trades"
                )
            with col2:
                st.metric(
                    "Total Tax Paid",
                    f"Rs. {total_tax:,.2f}",
                    help="Total capital gains tax paid on sales"
                )
            st.markdown('</div>', unsafe_allow_html=True)
    
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
            
            # Add metric container styling
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Total Dividends",
                    f"Rs. {total_dividend:,.2f}",
                    help="Total dividend income before tax"
                )
            with col2:
                st.metric(
                    "Tax Deducted",
                    f"Rs. {total_tax:,.2f}",
                    help="Total tax deducted from dividends"
                )
            with col3:
                st.metric(
                    "Net Dividend Income",
                    f"Rs. {net_dividend:,.2f}",
                    help="Total dividend income after tax"
                )
            st.markdown('</div>', unsafe_allow_html=True)
    
    with tab4:
        # New tab for metal portfolio
        view_metal_portfolio_summary()

    # Overall Portfolio Performance
    st.divider()
    st.subheader("📈 Overall Portfolio Performance")

    
    
    try:
         # Get stock data
        realized_pl = calculate_realized_pl()
        dividends = calculate_total_dividends()
        total_stock_pl = sum(data['net_pl'] for data in realized_pl.values()) if realized_pl else 0
        net_dividend = sum(data['net_amount'] for data in dividends.values()) if dividends else 0
        
        # Get metal data
        metal_positions = get_metal_portfolio()
        metal_df = pd.DataFrame(metal_positions) if metal_positions else pd.DataFrame()
        total_metal_pl = metal_df["Open P/L"].sum(skipna=True) if not metal_df.empty else 0
        
        # Calculate combined returns
        total_return = total_stock_pl + net_dividend + total_metal_pl
        
        # Add metric container styling
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Stock Trading P/L",
                f"Rs. {total_stock_pl:,.2f}",
                delta=f"{'↑' if total_stock_pl > 0 else '↓'} {abs(total_stock_pl):,.2f}",
                help="Total profit/loss from stock trades"
            )
        
        with col2:
            st.metric(
                "Dividend Income",
                f"Rs. {net_dividend:,.2f}",
                help="Total dividend income after tax"
            )
            
        with col3:
            st.metric(
                "Metals Portfolio P/L",
                f"PKR {total_metal_pl:,.2f}",
                delta=f"{'↑' if total_metal_pl > 0 else '↓'} {abs(total_metal_pl):,.2f}",
                help="Unrealized profit/loss from metals portfolio"
            )
        
        with col4:
            st.metric(
                "Total Returns",
                f"PKR {total_return:,.2f}",
                delta=f"{'↑' if total_return > 0 else '↓'} {abs(total_return):,.2f}",
                help="Combined returns from stocks and metals (all in PKR)"
            )
            
        st.markdown('</div>', unsafe_allow_html=True)
        
    except Exception as e:
        st.info("Insufficient data to calculate overall performance.")
        st.exception(e)