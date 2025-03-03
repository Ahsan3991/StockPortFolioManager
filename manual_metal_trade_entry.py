# manual_metal_trade_entry.py
import streamlit as st
import sqlite3
from datetime import datetime
from currency_conversion import convert_currency  # Import conversion function

def manual_metal_trade_entry():
    st.title("Manually Enter Metal Trade")
    
    # Metal trade form
    metal = st.selectbox("Select Metal", ["Gold", "Silver", "Platinum", "Palladium"])
    weight = st.number_input("Enter Weight (grams)", min_value=0.01, step=0.01)
    karat = st.selectbox("Select Karat", [24, 22, 21, 20, 18, 16, 14, 10], index=0)
    
    # Currency selection (USD or PKR)
    currency = st.selectbox("Select Currency", ["PKR", "USD"])
    purchase_price = st.number_input(f"Enter Purchase Price per Gram ({currency})", min_value=0.01, step=0.01)
    date = st.date_input("Select Purchase Date", datetime.today())
    
    # Convert price to PKR if entered in USD
    if currency == "USD":
        converted_price = convert_currency(purchase_price, "USD", "PKR")
        if converted_price is None:
            st.error("❌ Failed to fetch exchange rate. Please try again later.")
            return
        # Show the converted price to user for reference
        st.info(f"💱 Converted Price: {purchase_price} USD = {converted_price:.2f} PKR")
        purchase_price = converted_price  # Save as PKR
    
    if st.button("Add Metal Trade"):
        total_cost = round(weight * purchase_price, 2)
        save_metal_trade(metal, weight, karat, purchase_price, total_cost, date)
        st.success("✅ Metal trade recorded successfully!")
        
        # Display confirmation with details
        st.write("**Trade Details:**")
        st.write(f"Metal: {metal} ({karat}K)")
        st.write(f"Weight: {weight} grams")
        st.write(f"Purchase Price: PKR {purchase_price:.2f} per gram")
        st.write(f"Total Cost: PKR {total_cost:.2f}")
        st.write(f"Date: {date}")

def save_metal_trade(metal, weight, karat, purchase_price, total_cost, date):
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO metal_trades (date, metal, weight, karat, purchase_price, total_cost)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (date, metal, weight, karat, purchase_price, total_cost))
    
    conn.commit()
    conn.close()