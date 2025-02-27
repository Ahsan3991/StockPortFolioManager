#manual metal entry
import streamlit as st
import sqlite3
from datetime import datetime

def manual_metal_trade_entry():
    st.title("Manually Enter Metal Trade")
    
    # Metal trade form
    metal = st.selectbox("Select Metal", ["Gold", "Silver", "Platinum", "Palladium"])
    weight = st.number_input("Enter Weight (grams)", min_value=0.01, step=0.01)
    karat = st.selectbox("Select Karat", [24, 22, 21, 20, 18, 16, 14, 10], index=0)
    purchase_price = st.number_input("Enter Purchase Price per Gram (USD)", min_value=0.01, step=0.01)
    date = st.date_input("Select Purchase Date", datetime.today())
    
    if st.button("Add Metal Trade"):
        total_cost = round(weight * purchase_price, 2)
        save_metal_trade(metal, weight, karat, purchase_price, total_cost, date)
        st.success("Metal trade recorded successfully!")

def save_metal_trade(metal, weight, karat, purchase_price, total_cost, date):
    conn = sqlite3.connect("portfolio.db")
    cursor = conn.cursor()
    
    # (Remove the CREATE TABLE statement here)
    
    cursor.execute('''
        INSERT INTO metal_trades (date, metal, weight, karat, purchase_price, total_cost)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (date, metal, weight, karat, purchase_price, total_cost))
    
    conn.commit()
    conn.close()
