import datetime
from psx import stocks

# Set the stock symbol and date range
STOCK_SYMBOL = "HUMNL"
START_DATE = datetime.date(2025, 2, 1)  # Change this if needed
END_DATE = datetime.date.today()  # Fetch latest available data

def get_latest_eod_closing_price(symbol):
    """Fetch the latest available end-of-day closing stock price using psx-data-reader."""
    try:
        # Fetch stock data
        data = stocks(symbol, start=START_DATE, end=END_DATE)

        # Check if data is retrieved
        if data.empty:
            print(f"⚠️ No stock data found for {symbol}.")
            return None

        # Get the latest available closing price
        latest_price = data["Close"].iloc[-1]  # Last row's closing price
        return round(float(latest_price), 2)

    except Exception as e:
        print(f"❌ Error fetching stock price: {e}")
        return None

# Run the function
stock_price = get_latest_eod_closing_price(STOCK_SYMBOL)
if stock_price:
    print(f"✅ Latest available EOD closing price for {STOCK_SYMBOL}: Rs. {stock_price}")
else:
    print("Stock price data not available.")
