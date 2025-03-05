import streamlit as st
import sqlite3
import pdfplumber
import json
import re
import time
import pandas as pd
from datetime import datetime

def clean_stock_name(stock_name):
    if isinstance(stock_name, str):
        cleaned = stock_name.split('Ready')[0].strip()
        return cleaned
    return stock_name

def insert_trade(date, memo_number, stock, quantity, rate, comm_amount, cdc_charges, sales_tax, total_amount, trade_type):
    max_retries = 5
    retry_delay = 1

    stock = clean_stock_name(stock)

    for attempt in range(max_retries):
        from db_utils import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("PRAGMA journal_mode=WAL;")

            total_amount = float(str(total_amount).replace(",", ""))
            from utils import normalize_date_format
            normalize_date = normalize_date_format(date)

            cursor.execute("""
                INSERT INTO trades (date, memo_number, stock, quantity, rate, comm_amount, cdc_charges, sales_tax, total_amount, type) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (normalize_date, memo_number, stock, quantity, rate, comm_amount, cdc_charges, sales_tax, total_amount, trade_type))

            conn.commit()
            return

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                st.warning(f"Database is locked. Retrying in {retry_delay} second(s)... ({attempt+1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                st.error(f"Database error: {str(e)}")
                break

        finally:
            conn.close()

    st.error("❌ Could not insert trade after multiple attempts due to database locking.")

def display_trades():
    from db_utils import get_db_connection
    conn = get_db_connection()
    try:
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
        
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            st.write("### Trade History")
            
            numeric_cols = ['Rate', 'Commission', 'CDC Charges', 'Sales Tax', 'Total Amount']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].round(2)
            
            st.dataframe(
                df,
                column_config={
                    "Rate": st.column_config.NumberColumn(format="%.2f"),
                    "Commission": st.column_config.NumberColumn(format="%.2f"),
                    "CDC Charges": st.column_config.NumberColumn(format="%.2f"),
                    "Sales Tax": st.column_config.NumberColumn(format="%.2f"),
                    "Total Amount": st.column_config.NumberColumn(format="%.2f")
                },
                hide_index=True
            )
            
            st.write("### Summary")
            total_invested = df['Total Amount'].sum()
            total_shares = df['Shares'].sum()
            total_commission = df['Commission'].sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Investment", f"Rs. {total_invested:,.2f}")
            with col2:
                st.metric("Total Shares", f"{total_shares:,}")
            with col3:
                st.metric("Total Commission", f"Rs. {total_commission:,.2f}")
                
        else:
            st.info("No trade records found.")
            
    except Exception as e:
        st.error(f"Error fetching trade records: {str(e)}")
        st.info("If you just created the database, this is normal. Add some trades first.")
    finally:
        conn.close()

def parse_trade_pdf(pdf_file):
    st.warning("PDF parsing functionality is not currently implemented.")
    return None