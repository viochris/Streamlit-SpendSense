import streamlit as st
import pandas as pd
import numpy as np
import gspread
import datetime
import json
import time

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
    Ensures key variables exist to prevent KeyErrors during app startup.
    """
    
    # 1. Chat History
    # Stores the conversation log between User and AI.
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 2. Scanned Data Placeholder
    # Used for OCR or camera input data storage.
    if "scanned_data" not in st.session_state:
        st.session_state.scanned_data = None

    # 3. Language Model Instance
    # Singleton pattern to avoid reloading the LLM on every rerun.
    if "llm" not in st.session_state:
        st.session_state.llm = None
    
    # 4. Agent Memory
    # Stores context/history for the LangChain agent.
    if "agent_memory" not in st.session_state:
        st.session_state.agent_memory = None

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

def send_update(edited_df, type_name):
    """
    Handles safe updates to Google Sheets with Auto-Backup and Rollback features.
    
    Args:
        edited_df (DataFrame): The modified data from Streamlit Data Editor.
        type_name (str): The target sheet name ("Income" or "Expense").
    """
    
    # Initialize worksheet connections
    ws_main = sh.worksheet(type_name)
    ws_backup = sh.worksheet("Backup")

    # ==========================================
    # STEP 1: AUTO-BACKUP (SAFETY FIRST)
    # ==========================================
    try:
        # Retrieve existing data before modification
        old_data = ws_main.get_all_values()
        
        # Clear the backup sheet to remove old artifacts
        ws_backup.clear() 
        
        # Save the current state to the backup sheet
        if len(old_data) > 0:
            ws_backup.append_rows(old_data)
            time.sleep(1) # Pause to prevent API rate limiting
            
    except Exception as e:
        # If backup fails, stop the process immediately to prevent data loss
        st.error(f"Backup Failed: {e}")
        return False 

    # ==========================================
    # STEP 2: MAIN UPDATE EXECUTION
    # ==========================================
    try:
        # Clear the main sheet to prepare for new data
        ws_main.clear()
        
        # 1. Upload Header (Column Names)
        ws_main.append_row(edited_df.columns.tolist())

        # 2. Prepare Data Body
        # CRITICAL: Convert all data to STRING to avoid JSON serialization errors
        # (e.g., Timestamp objects causing API crashes)
        clean_df = edited_df.astype(str) 
        body_data = clean_df.values.tolist()
        
        # 3. Batch Upload
        # Upload data in chunks of 1000 rows to ensure stability
        total_data = len(body_data)
        if total_data > 0:
            for i in range(0, total_data, 1000):
                chunk = body_data[i : i + 1000]
                ws_main.append_rows(chunk)
                time.sleep(1)

        # 4. Cleanup & Success
        # Clear backup since the operation was successful
        ws_backup.clear()
        
        st.success(f"✅ Successfully updated {type_name}!")
        time.sleep(1)
        st.rerun() # Refresh the app to show new data
        return True

    # ==========================================
    # STEP 3: EMERGENCY RESTORE (ROLLBACK)
    # ==========================================
    except Exception as e:
        st.error(f"⚠️ Update Error: {e}. Restoring previous data...")
        
        # Retrieve data from the backup sheet
        backup_data = ws_backup.get_all_values()
        
        # Clear the corrupted main sheet
        ws_main.clear()
        
        # Restore original data in batches
        if len(backup_data) > 0:
            for i in range(0, len(backup_data), 1000):
                chunk = backup_data[i : i + 1000]
                ws_main.append_rows(chunk)
                time.sleep(1)
        
        # Clean up backup sheet
        ws_backup.clear()
        return False