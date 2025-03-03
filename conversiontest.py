import requests
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()


# Get API keys - hardcode the exchange rate key since we know it works in the browser
GOLDAPI_KEY = os.getenv("GOLDAPI_KEY")
EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")

def test_gold_api():
    """Test fetching gold prices from GoldAPI"""
    print("\n=== TESTING GOLDAPI CONNECTION ===")
    
    url = "https://www.goldapi.io/api/XAU/USD"
    headers = {
        "x-access-token": GOLDAPI_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        print(f"Fetching gold price data...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Successfully connected to GoldAPI")
        print(f"Gold (XAU) Prices in USD:")
        print(f"- Price per gram (24K): ${data.get('price_gram_24k', 'N/A')}")
        print(f"- Price per gram (22K): ${data.get('price_gram_22k', 'N/A')}")
        print(f"- Price per gram (18K): ${data.get('price_gram_18k', 'N/A')}")
        print(f"- Price per troy ounce: ${data.get('price', 'N/A')}")
        
        return data.get('price_gram_24k')
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch gold price: {e}")
        return None

def test_pair_exchange_rate_api():
    """Test fetching exchange rates using the Pair endpoint"""
    print("\n=== TESTING EXCHANGERATE-API PAIR ENDPOINT ===")
    
    # The Pair endpoint URL format
    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_RATE_API_KEY}/pair/USD/PKR"
    
    try:
        print(f"Fetching USD to PKR exchange rate...")
        print(f"Using URL: {url}")  # Debug output
        
        response = requests.get(url, timeout=10)
        print(f"Response status code: {response.status_code}")  # Debug output
        
        response.raise_for_status()
        data = response.json()
        
        if data.get("result") == "success":
            print(f"✅ Successfully connected to ExchangeRate-API Pair endpoint")
            
            # Extract the exchange rate
            exchange_rate = data.get("conversion_rate")
            
            if exchange_rate:
                print(f"Current exchange rate: 1 USD = {exchange_rate} PKR")
                print(f"Last updated: {data.get('time_last_update_utc', 'unknown')}")
                print(f"Next update: {data.get('time_next_update_utc', 'unknown')}")
                return exchange_rate
            else:
                print(f"❌ Conversion rate not found in response: {data}")
                return None
        else:
            error_type = data.get("error-type", "unknown")
            print(f"❌ API Error: {error_type}")
            
            if error_type == "quota-reached":
                print("  You have reached your monthly API request quota.")
                print("  Consider upgrading your plan or waiting until next month.")
            elif error_type == "invalid-key":
                print("  Your API key is invalid or not activated.")
            
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch exchange rate: {e}")
        print(f"  Full error: {str(e)}")  # More detailed error
        return None

def test_conversion(gold_price_usd, exchange_rate):
    """Test currency conversion calculation"""
    print("\n=== TESTING CONVERSION CALCULATION ===")
    
    if gold_price_usd is None or exchange_rate is None:
        print("❌ Cannot perform conversion due to missing data")
        return
    
    # Calculate the converted price
    gold_price_pkr = gold_price_usd * exchange_rate
    
    print(f"Manual conversion calculation:")
    print(f"Gold price: ${gold_price_usd} USD per gram (24K)")
    print(f"Exchange rate: 1 USD = {exchange_rate} PKR")
    print(f"Converted price: PKR {gold_price_pkr:.2f} per gram (24K)")
    
    # Check if the conversion seems reasonable
    if gold_price_pkr > 50000 or gold_price_pkr < 5000:
        print(f"⚠️ Warning: Converted price (PKR {gold_price_pkr:.2f}) seems unusual")
        print(f"   Gold typically costs between PKR 15,000-40,000 per gram")
    else:
        print(f"✅ Converted price seems reasonable")
    
    return gold_price_pkr

def test_amount_endpoint():
    """Test the amount conversion endpoint"""
    print("\n=== TESTING AMOUNT CONVERSION ENDPOINT ===")
    
    test_amount = 93.00  # A typical gold price per gram
    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_RATE_API_KEY}/pair/USD/PKR/{test_amount}"
    
    try:
        print(f"Testing direct conversion of {test_amount} USD to PKR...")
        print(f"Using URL: {url}")  # Debug output
        
        response = requests.get(url, timeout=10)
        print(f"Response status code: {response.status_code}")  # Debug output
        
        response.raise_for_status()
        data = response.json()
        
        if data.get("result") == "success":
            print(f"✅ Successfully tested amount conversion endpoint")
            
            # Extract the converted amount
            conversion_result = data.get("conversion_result")
            conversion_rate = data.get("conversion_rate")
            
            if conversion_result:
                print(f"API returned: {test_amount} USD = {conversion_result} PKR")
                print(f"Using rate: 1 USD = {conversion_rate} PKR")
                return conversion_result
            else:
                print(f"❌ Conversion result not found in response: {data}")
                return None
        else:
            print(f"❌ API Error: {data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to test amount endpoint: {e}")
        print(f"  Full error: {str(e)}")  # More detailed error
        return None

if __name__ == "__main__":
    print("=" * 60)
    print(f"METAL PRICING AND PAIR CONVERSION TEST")
    print(f"Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Run the tests
    gold_price = test_gold_api()
    exchange_rate = test_pair_exchange_rate_api()
    converted_price = test_conversion(gold_price, exchange_rate)
    
    # Test the amount endpoint (with actual gold price if available)
    amount_to_test = gold_price if gold_price else 93.00
    direct_conversion = test_amount_endpoint()
    
    print("\n=== SUMMARY ===")
    if gold_price and exchange_rate and converted_price:
        print(f"✅ All tests completed successfully")
        print(f"Gold price: ${gold_price} USD per gram (24K)")
        print(f"Exchange rate: 1 USD = {exchange_rate} PKR")
        print(f"Converted price: PKR {converted_price:.2f} per gram (24K)")
        
        if direct_conversion:
            print(f"Direct API conversion: PKR {direct_conversion}")
            
            # Calculate difference between manual and direct conversion
            diff = abs(converted_price - direct_conversion)
            diff_percent = (diff / converted_price) * 100
            
            if diff_percent < 0.01:
                print(f"✅ Manual calculation matches API direct conversion")
            else:
                print(f"⚠️ Slight difference between manual calculation and API: {diff_percent:.4f}%")
        
        # Print a larger, more visible conclusion
        print("\n" + "!" * 60)
        print(f"EXPECTED GOLD PRICE IN PKR: {converted_price:.2f} PKR per gram (24K)")
        print("!" * 60)
    else:
        print(f"❌ Some tests failed. Please check the messages above.")