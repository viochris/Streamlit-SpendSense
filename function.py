import streamlit as st
import pandas as pd
import numpy as np
import gspread
import datetime
import json

# ==========================================
# GOOGLE SHEETS AUTHENTICATION & SETUP
# ==========================================

# 1. Retrieve the raw JSON string from Streamlit secrets
# Accessing the 'gcp_json' key nested under '[files]' in secrets.toml
raw_json_string = st.secrets["files"]["gcp_json"]

# 2. Parse the string into a Python dictionary
# Converts the raw string format back into a valid JSON object
credentials = json.loads(raw_json_string)

# 3. Authenticate with Google Sheets API
# Establishes connection using the parsed credentials dictionary
gc = gspread.service_account_from_dict(credentials)

# Open the main spreadsheet named "Report"
sh = gc.open("Report")

# Initialize specific worksheets for data storage
ws_expense = sh.worksheet("Expense")
ws_income = sh.worksheet("Income")

# ==========================================
# STATE MANAGEMENT FUNCTIONS
# ==========================================
def init_state():
    """
    Initialize Streamlit session state variables.
    Ensures 'scanned_data' exists to prevent KeyErrors during app startup.
    """
    if "scanned_data" not in st.session_state:
        st.session_state.scanned_data = None

def change_on_upload():
    """
    Callback function triggered when a new image is uploaded or captured.
    Resets the 'scanned_data' state to None to clear previous results.
    """
    st.session_state.scanned_data = None

# ==========================================
# DATA SUBMISSION FUNCTIONS
# ==========================================
def send_expense(datetime, place_name, category, total):
    """
    Formats and appends a new expense record to the 'Expense' worksheet.
    
    Parameters:
    - datetime: Date object to be formatted as string.
    - place_name: String, will be converted to Title Case.
    - category: String, expense category.
    - total: Integer/Float, amount spent.
    """
    if datetime and place_name and category and total:
        datetime = datetime.strftime("%Y-%m-%d %H:%M:%S")
        ws_expense.append_row([datetime, place_name.title(), category, total])

def send_income(datetime, from_where, category, total):
    """
    Formats and appends a new income record to the worksheet.
    
    Parameters:
    - datetime: Date object to be formatted as string.
    - from_where: String, source of income (Title Case).
    - category: String, income category.
    - total: Integer/Float, amount received.
    """
    if datetime and from_where and category and total:
        datetime = datetime.strftime("%Y-%m-%d %H:%M:%S")
        ws_income.append_row([datetime, from_where.title(), category, total])

# ==========================================
# DATA RETRIEVAL FUNCTIONS
# ==========================================
def get_expense():
    """
    Fetches all expense records from the 'Expense' worksheet.
    Returns a pandas DataFrame containing the formatted data.
    """
    df = pd.DataFrame()

    # Check if the worksheet has data (row count > 1 means header + data exists)
    if len(ws_expense.col_values(1)) > 1:
        data = ws_expense.get_all_records()
        df = pd.DataFrame(data)
        # Convert string timestamp to datetime objects for analysis
        df["DateTime"] = pd.to_datetime(df["DateTime"])
    else:
        # Notify user via Streamlit if the sheet is empty
        st.info("No Report for Expense")

    return df

def get_income():
    """
    Fetches all income records from the 'Income' worksheet.
    Returns a pandas DataFrame containing the formatted data.
    """
    df = pd.DataFrame()

    # Check if the worksheet has data (row count > 1 means header + data exists)
    if len(ws_income.col_values(1)) > 1:
        data = ws_income.get_all_records()
        df = pd.DataFrame(data)
        # Convert string timestamp to datetime objects for analysis
        df["DateTime"] = pd.to_datetime(df["DateTime"])
        
    else:
        # Notify user via Streamlit if the sheet is empty
        st.info("No Report for Income")

    return df