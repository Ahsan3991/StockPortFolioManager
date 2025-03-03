# real_time_stock_prices.py
import sqlite3
import datetime as dt
from psx import stocks

def get_psx_stock_price(stock_symbol):
    """
    Fetches previous close price with a graceful fallback:
    1. Try scraping PSX data
    2. Use today's cached price if available
    3. Use previous day's buffer price if scraping fails
    4. Return None if all attempts fail
    """

    stock_symbol = stock_symbol.upper().strip()
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()

    try:
        # Ensure stock_prices table exists with proper schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                stock TEXT PRIMARY KEY,
                previous_close REAL,
                last_updated TEXT,
                buffer_price REAL
            )
        """)

        today_date = dt.date.today().strftime('%Y-%m-%d')

       # print(f"Fetching PSX stock price for: {stock_symbol}")
        #print(f"Today's date: {today_date}")

        # Check for cached price
        cursor.execute("""
            SELECT previous_close, last_updated, buffer_price 
            FROM stock_prices WHERE stock = ?
        """, (stock_symbol,))
        result = cursor.fetchone()

        cached_price = None
        buffer_price = None

        if result:
            cached_price, last_updated, buffer_price = result
          #  print(f"Cached Price: {cached_price}, Last Updated: {last_updated}, Buffer Price: {buffer_price}")

            # If we have today's price, return it immediately
            if last_updated == today_date:
              #  print(f"✅ Returning cached price for {stock_symbol}: {cached_price}")
                return cached_price

        # Scrape stock price from PSX
        try:
            start_date = dt.date(2024, 1, 1)
            end_date = dt.date.today()
           # print(f"Scraping PSX data from {start_date} to {end_date}")

            data = stocks(stock_symbol, start=start_date, end=end_date)
            
            if not data.empty:
                print(f"Scraped data:\n{data.tail()}")  # Print last few rows for debugging
                previous_close = round(float(data["Close"].iloc[-1]), 2)

                # Update cache with new price, moving current price to buffer
                cursor.execute("""
                    INSERT INTO stock_prices (stock, previous_close, buffer_price, last_updated) 
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(stock) DO UPDATE SET 
                        buffer_price = stock_prices.previous_close,
                        previous_close = excluded.previous_close,
                        last_updated = excluded.last_updated
                """, (
                    stock_symbol,
                    previous_close,
                    cached_price if cached_price is not None else previous_close,  # Maintain buffer
                    today_date
                ))

                conn.commit()
                print(f"✅ Successfully updated price for {stock_symbol}: {previous_close}")
                return previous_close

        except Exception as e:
            print(f"❌ Scraping failed for {stock_symbol}: {e}")

        # If scraping fails, try cached price
        if cached_price is not None:
           # print(f"⚠️ Returning cached price for {stock_symbol} (Scraping failed): {cached_price}")
            return cached_price

        # If no cached price, try buffer price
        if buffer_price is not None:
          #  print(f"⚠️ Returning buffer price for {stock_symbol} (Scraping & Cache failed): {buffer_price}")
            return buffer_price

        # If all else fails, return None
        print(f"❌ No price available for {stock_symbol}")
        return None

    finally:
        conn.close()
