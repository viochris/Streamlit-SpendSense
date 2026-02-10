import os
import json
from datetime import datetime, timedelta

# --- Third Party Libraries ---
import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
from dotenv import load_dotenv

# --- Google AI ---
from google import genai

# --- LangChain Ecosystem ---
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
from langchain_classic.memory import ConversationBufferMemory

# --- Local Modules ---
from function import (
    init_state, 
    reset_state,
    change_on_upload, 
    send_expense, 
    send_income, 
    get_expense, 
    get_income,
    send_update
)

# ==========================================
# 1. INITIALIZATION & SETUP
# ==========================================
# Initialize session state for data persistence
init_state()

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configure global page settings, including the browser tab title and icon
st.set_page_config(
    page_title="SpendSense", 
    page_icon="💸",
    layout="wide"
)

# ==========================================
# 2. MAIN UI LAYOUT
# ==========================================
# Render the main application header
st.title("💸 SpendSense")

# Render the application description and welcome message
st.markdown(
    """
    ### 💬 AI Financial Assistant
    **Welcome to SpendSense!** Your intelligent financial companion. 
    Track your **Income 💰**, manage **Expenses 💸**, and visualize your **Financial Health 📊** effortlessly.
    """
)

# ==========================================
# 3. SIDEBAR CONFIGURATION
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuration")

    # Add vertical spacing for visual separation
    st.markdown("<br>", unsafe_allow_html=True)

    # 1. Navigation Mapping
    # Dictionary to map internal logical keys (used in code) 
    # to user-friendly display labels (seen in UI).
    mode_icons = {
        "Income": "💰 Record Income",
        "Expense": "💸 Track Expense",
        "Dashboard": "📊 Dashboard Analytics",
        "Comparison": "🆚 Compare Trends",    
        "Edit & Delete": "✏️ Manage Data",
        "Ask AI": "💬 Ask AI"
    }

    # 2. Main Navigation Menu
    # Uses 'format_func' to display the nice label with icon,
    # but returns the raw key (e.g., "Income") to the variable 'part'.
    part = st.selectbox(
        "🗂️ Navigation Mode",
        options=["Income", "Expense", "Dashboard", "Comparison", "Edit & Delete", "Ask AI"],
        format_func=lambda option: mode_icons.get(option),
        index=0,
        help="Select the module you want to access."
    )

# ==========================================
# 4. APPLICATION LOGIC
# ==========================================
# Initialize Google Gemini Client
# Uses session state key if available, otherwise relies on .env fallback
client = genai.Client(api_key=GOOGLE_API_KEY)

# Set current timezone (UTC+7 for WIB)
current_time = (datetime.utcnow() + timedelta(hours=7))

# ------------------------------------------
# MODULE: EXPENSE TRACKER
# ------------------------------------------
if part == "Expense":
    # Add visual separation and main title
    st.divider()
    st.subheader("💸 Track New Expense")

    # Defined categories for expense tracking (Standardized in English)
    category_list = ["Food", "Beverage", "Electronics", "Transportation", "Insurance", "Entertainment", "Investment", "Unknown"]

    # Initialize tabs for different input methods
    scan, manual = st.tabs(["📸 Scan Receipt", "📝 Manual Entry"])

    # ==========================================
    # TAB 1: AI SCANNING (OCR & EXTRACTION)
    # ==========================================
    with scan:
        # 1. Image Input Section
        uploaded_image = st.file_uploader(
            "📂 Upload Receipt Image", 
            type=["jpg", "jpeg", "png", "webp"],
            on_change=change_on_upload,
            help="Supported formats: JPG, PNG, WEBP."
        )

        st.markdown("<div style='text-align: center;'><b>— OR —</b></div>", unsafe_allow_html=True)

        enable = st.checkbox("📸 Enable Camera Input")
        catched_image = st.camera_input(
            "Capture Receipt",
            disabled=not enable,
            on_change=change_on_upload,
            help="Take a clear photo of your receipt."
        )

        # Priority logic for image selection
        if uploaded_image is not None:
            img = uploaded_image
        elif catched_image is not None:
            img = catched_image
        else:
            img = None

        # 2. Process Button
        process_btn = st.button(
            "✨ Process Image",
            use_container_width=True,
            help="Extract transaction details using Gemini AI."
        )        
        
        # 3. AI Processing Logic
        if img is not None and process_btn:
            # Display source image
            st.image(img, caption="Source Image", use_container_width=True)

            img = Image.open(img)
            
            # Prompt Engineering (English):
            # strict instructions for dictionary output and category matching.
            prompt = """
                Please provide the output as a clean dictionary (JSON format).
                The output must ONLY include these 3 keys:
                1. Place name -> "Place"
                2. Category -> "Category" (Select ONLY from: Food, Beverage, Electronics, Transportation, Insurance, Entertainment, Investment, Unknown)
                3. Total amount (integer) -> "Total"

                If the uploaded image is NOT a receipt or invoice, return exactly: "Please upload a valid receipt".
                If the image is too blurry or unclear, return exactly: "Image is unclear, please retake".
            """
            
            model_id = 'gemini-2.5-flash'
            
            # Execute API Call
            response = client.models.generate_content(
                model=model_id,
                contents=[img, prompt]
            )

            # 4. Response Parsing & Error Handling
            if response.text and not response.text.strip() == "":
                # Check for specific error phrases defined in the prompt
                if "Please upload a valid receipt".lower() in response.text.lower():
                    st.error("⚠️ Invalid Image: Please upload a valid receipt or invoice.")
                    st.stop()
                elif "Image is unclear, please retake".lower() in response.text.lower():
                    st.error("⚠️ Low Quality: The image is blurry. Please retake the photo.")
                    st.stop()
                else:
                    # Clean markdown formatting to get raw JSON string
                    processed_response = response.text.replace("```json", "").replace("```", "").strip()
                    st.session_state.scanned_data = json.loads(processed_response)

        # UI Feedback for empty state
        if st.session_state.scanned_data is None:
            st.info("ℹ️ Upload an image and click 'Process' to extract data.")

        # ==========================================
        # EDIT FORM (POST-SCANNING)
        # ==========================================
        if st.session_state.scanned_data is not None:
            # Re-display image if persistence check passes
            if img and not process_btn:
                st.image(img, caption="Source Image", use_container_width=True)

            if img:
                data_dict = st.session_state.scanned_data

                with st.expander("📝 Verify & Edit Details", expanded=True):
                    with st.form("edit_scanned_form"):
                        st.markdown("### 🔍 Review Results\nPlease check the extracted details below and correct any errors.")

                        # Form Inputs (Pre-filled with AI Data)
                        datetime_val = st.datetime_input(
                            "📅 Transaction Date", 
                            current_time,
                            help="Select the exact date and time of transaction.",
                        )

                        place_name = st.text_input(
                            "📍 Place / Merchant",
                            value=data_dict.get("Place", None),
                            help="Name of the store or merchant."
                        )

                        # Logic to map AI category to the list index safely
                        current_category = data_dict.get("Category", "Unknown")
                        # Default to last index ("Unknown") if category is not found
                        category_index = category_list.index(current_category) if current_category in category_list else 7
                        
                        category = st.selectbox(
                            "🏷️ Category",
                            options=category_list,
                            index=category_index,
                            help="Select the expense category."
                        )

                        total = st.number_input(
                            "💰 Total Amount",
                            value=data_dict.get("Total", 0),
                            help="Total expense amount."
                        )

                        submitted = st.form_submit_button("✅ Confirm Details")

                # 5. Validation & Submission Logic
                if (datetime_val and place_name and category and total) or submitted:
                    st.success(
                        f"**Preview:**\n"
                        f"- 📅 Date: `{datetime_val}`\n"
                        f"- 📍 Place: `{place_name}`\n"
                        f"- 🏷️ Category: `{category}`\n"
                        f"- 💰 Total: `{total}`"
                    )

                send_btn = st.button("💾 Save to Google Sheets", use_container_width=True, help="Save this record to Google Sheets.")

                if datetime_val and place_name and category and total and send_btn:
                    send_expense(datetime_val, place_name, category, total)
                    st.toast("✅ Record saved successfully!", icon="🎉")
                    st.success("✅ **Success:** Expense data has been pushed to the spreadsheet.")
                    
                elif not datetime_val or not place_name or not category or not total:
                    if send_btn:
                        st.warning("⚠️ **Missing Information:** Please ensure all fields are filled before saving.")
                    else:
                        st.warning("⚠️ Please complete all fields.")

                elif datetime_val and place_name and category and total and not send_btn:
                    st.info("ℹ️ Data is ready. Click **Save to Database** to finish.")

    # ==========================================
    # TAB 2: MANUAL ENTRY
    # ==========================================
    with manual:
        with st.form("manual_input_form"):
            st.markdown("### 📝 Manual Entry Form")
            
            datetime_val = st.datetime_input(
                "📅 Transaction Date", 
                current_time,
                help="When did this transaction happen?"
            )

            place_name = st.text_input(
                "📍 Place / Merchant",
                value="Indomaret", # Default value example
                help="Where did you spend the money?"
            )

            category = st.selectbox(
                "🏷️ Category",
                options=category_list,
                index=0,
                help="Classify your expense."
            )

            total = st.number_input(
                "💰 Total Amount",
                value=10000,
                help="How much did you spend?"
            )

            submitted = st.form_submit_button("✅ Submit Expense")

        # Submission Logic for Manual Entry
        if submitted:
            if datetime_val and place_name and category and total:
                send_expense(datetime_val, place_name, category, total)
                st.toast("✅ Record saved successfully!", icon="🎉")
                st.success("✅ **Success:** Manual entry saved.")
            elif not datetime_val or not place_name or not category or not total:
                st.warning("⚠️ **Missing Information:** Please fill in all fields.")
        
        # Display warning if fields are incomplete but not yet submitted
        elif not datetime_val or not place_name or not category or not total:
            st.info("ℹ️ Please fill in the form above.")

# ------------------------------------------
# MODULE: INCOME TRACKER
# ------------------------------------------
elif part == "Income":
    # Add visual separation and main title
    st.divider()
    st.subheader("💰 Record New Income")
    
    # Defined categories for income sources (Standardized in English)
    category_list = ["Salary", "Allowance", "Bonus", "Freelance", "Investment", "Gift", "Other"]

    # Initialize tabs for different input methods
    scan, manual = st.tabs(["📸 Scan Proof", "📝 Manual Entry"])

    # ==========================================
    # TAB 1: AI SCANNING (OCR & EXTRACTION)
    # ==========================================
    with scan:
        # 1. Image Input Section
        uploaded_image = st.file_uploader(
            "📂 Upload Proof of Income", 
            type=["jpg", "jpeg", "png", "webp"],
            on_change=change_on_upload,
            help="Supported formats: JPG, PNG, WEBP (e.g., Transfer screenshot, Payslip)."
        )

        st.markdown("<div style='text-align: center;'><b>— OR —</b></div>", unsafe_allow_html=True)

        enable = st.checkbox("📸 Enable Camera Input")
        catched_image = st.camera_input(
            "Capture Proof",
            disabled=not enable,
            on_change=change_on_upload,
            help="Take a clear photo of your payslip or proof."
        )

        # Priority logic for image selection
        if uploaded_image is not None:
            img = uploaded_image
        elif catched_image is not None:
            img = catched_image
        else:
            img = None

        # 2. Process Button
        process_btn = st.button(
            "✨ Process Image",
            use_container_width=True,
            help="Extract income details using Gemini AI."
        )        
        
        # 3. AI Processing Logic
        if img is not None and process_btn:
            # Display source image
            st.image(img, caption="Source Image", use_container_width=True)

            img = Image.open(img)
            
            # Prompt Engineering (Adapted for Income):
            # Instructs Gemini to extract Source/Payer instead of Merchant.
            prompt = """
                Please provide the output as a clean dictionary (JSON format).
                The output must ONLY include these 3 keys:
                1. Source Name / Payer -> "Place" 
                2. Category -> "Category" (Select ONLY from: Salary, Allowance, Bonus, Freelance, Investment, Gift, Other)
                3. Total amount (integer) -> "Total"

                If the uploaded image is NOT a valid proof of income (like payslip, transfer screenshot), return exactly: "Please upload a valid proof".
                If the image is too blurry or unclear, return exactly: "Image is unclear, please retake".
            """
            
            model_id = 'gemini-2.5-flash'
            
            # Execute API Call
            response = client.models.generate_content(
                model=model_id,
                contents=[img, prompt]
            )

            # 4. Response Parsing & Error Handling
            if response.text and not response.text.strip() == "":
                # Check for specific error phrases defined in the prompt
                if "Please upload a valid proof".lower() in response.text.lower():
                    st.error("⚠️ Invalid Image: Please upload a valid transfer proof or payslip.")
                    st.stop()
                elif "Image is unclear, please retake".lower() in response.text.lower():
                    st.error("⚠️ Low Quality: The image is blurry. Please retake the photo.")
                    st.stop()
                else:
                    # Clean markdown formatting to get raw JSON string
                    processed_response = response.text.replace("```json", "").replace("```", "").strip()
                    st.session_state.scanned_data = json.loads(processed_response)

        # UI Feedback for empty state
        if st.session_state.scanned_data is None:
            st.info("ℹ️ Upload an image and click 'Process' to extract data.")

        # ==========================================
        # EDIT FORM (POST-SCANNING)
        # ==========================================
        if st.session_state.scanned_data is not None:
            # Re-display image if persistence check passes
            if img and not process_btn:
                st.image(img, caption="Source Image", use_container_width=True)

            if img:
                data_dict = st.session_state.scanned_data

                with st.expander("📝 Verify & Edit Details", expanded=True):
                    with st.form("edit_scanned_income_form"):
                        st.markdown("### 🔍 Review Results\nPlease check the extracted details below and correct any errors.")

                        # Form Inputs (Pre-filled with AI Data)
                        datetime_val = st.datetime_input(
                            "📅 Date Received", 
                            current_time,
                            help="Select the exact date and time the income was received.",
                        )

                        from_where = st.text_input(
                            "📍 Source / Payer",
                            value=data_dict.get("Place", None),
                            help="Who sent this money? (e.g., Office, Parents, Client)."
                        )

                        # Logic to map AI category to the list index safely
                        current_category = data_dict.get("Category", "Other")
                        # Default to last index ("Other") if category is not found
                        category_index = category_list.index(current_category) if current_category in category_list else 6
                        
                        category = st.selectbox(
                            "🏷️ Category",
                            options=category_list,
                            index=category_index,
                            help="Classify the income source."
                        )

                        total = st.number_input(
                            "💰 Total Amount",
                            value=data_dict.get("Total", 0),
                            help="Total income amount."
                        )

                        submitted = st.form_submit_button("✅ Confirm Details")

                # 5. Validation & Submission Logic
                if (datetime_val and from_where and category and total) or submitted:
                    st.success(
                        f"**Preview:**\n"
                        f"- 📅 Date: `{datetime_val}`\n"
                        f"- 📍 Source: `{from_where}`\n"
                        f"- 🏷️ Category: `{category}`\n"
                        f"- 💰 Total: `{total}`"
                    )

                send_btn = st.button("💾 Save to Google Sheets", use_container_width=True, help="Save this record to Google Sheets.")

                if datetime_val and from_where and category and total and send_btn:
                    # IMPORTANT: Calling send_income instead of send_expense
                    send_income(datetime_val, from_where, category, total)
                    st.toast("✅ Income saved successfully!", icon="🎉")
                    st.success("✅ **Success:** Income data has been pushed to the spreadsheet.")
                    
                elif not datetime_val or not from_where or not category or not total:
                    if send_btn:
                        st.warning("⚠️ **Missing Information:** Please ensure all fields are filled before saving.")
                    else:
                        st.warning("⚠️ Please complete all fields.")

                elif datetime_val and from_where and category and total and not send_btn:
                    st.info("ℹ️ Data is ready. Click **Save to Google Sheets** to finish.")

    # ==========================================
    # TAB 2: MANUAL ENTRY
    # ==========================================
    with manual:
        with st.form("manual_income_input_form"):
            st.markdown("### 📝 Manual Entry Form")
            
            datetime_val = st.datetime_input(
                "📅 Date Received", 
                current_time,
                help="When did you receive this money?"
            )

            from_where = st.text_input(
                "📍 Source / Payer",
                value="Office", # Default value example
                help="Where did this money come from?"
            )

            category = st.selectbox(
                "🏷️ Category",
                options=category_list,
                index=0,
                help="Classify your income."
            )

            total = st.number_input(
                "💰 Total Amount",
                value=1000000,
                help="How much did you receive?"
            )

            submitted = st.form_submit_button("✅ Submit Income")

        # Submission Logic for Manual Entry
        if submitted:
            if datetime_val and from_where and category and total:
                # IMPORTANT: Calling send_income instead of send_expense
                send_income(datetime_val, from_where, category, total)
                st.toast("✅ Income saved successfully!", icon="🎉")
                st.success("✅ **Success:** Manual entry saved.")
            elif not datetime_val or not from_where or not category or not total:
                st.warning("⚠️ **Missing Information:** Please fill in all fields.")
        
        # Display warning if fields are incomplete but not yet submitted
        elif not datetime_val or not from_where or not category or not total:
            st.info("ℹ️ Please fill in the form above.")

elif part == "Dashboard":
    # Add visual separation and main title
    st.divider()
    st.subheader("🚀 Financial Dashboard")

    # ==========================================
    # 1. Control Panel & Data Initialization
    # ==========================================
    # Create a 2-column layout to organize controls side-by-side.
    # Left column for Refresh, Right column for Mode selection.
    refresh, mode = st.columns(2)

    # --- Column 1: Refresh Logic ---
    with refresh:
        # Button to force a fresh data reload from the database (Google Sheets)
        if st.button("🔄 Refresh Data", help="Reload latest transactions from Google Sheets."):
            st.rerun()

    # --- Column 2: View Mode Selection ---
    with mode:
        # Toggle between Monthly (Detailed) and Yearly (Overview) views.
        # 'horizontal=True' renders buttons side-by-side for a cleaner look.
        chosed_filter_mode = st.radio(
            "📅 View Mode",
            ["Monthly", "Yearly"],
            index=0,
            horizontal=True,
            help="Select the time granularity: Monthly (Day-by-Day) or Yearly (Month-by-Month)."
        )

    st.markdown("---") # Add a divider line

    # Fetch latest dataframes
    df_expense = get_expense()
    df_income = get_income()

    # Pre-process: Extract Date Components for filtering and grouping
    for df in [df_expense, df_income]:
        if not df.empty:
            df["Date"] = df["DateTime"].dt.day
            df["Month"] = df["DateTime"].dt.month_name()
            df["Year"] = df["DateTime"].dt.year

    # Define standard month order for sorting logic
    month_order = [
        "January", "February", "March", "April", "May", "June", 
        "July", "August", "September", "October", "November", "December"
    ]

    # ==========================================
    # 2. Dynamic Filtering Logic
    # ==========================================
    # Note: 'chosed_filter_mode' must be defined in the Sidebar (e.g., st.sidebar.radio)
    
    # Calculate available Date ranges for dropdowns
    raw_month_list = set(df_expense["Month"].unique()).union(set(df_income["Month"].unique()))
    ordered_month_list = sorted(list(raw_month_list), key=lambda m: month_order.index(m))
    
    # Determine default Month index (Current Month)
    current_month_name = datetime.now().strftime("%B")
    current_month_idx = ordered_month_list.index(current_month_name) if current_month_name in ordered_month_list else 0

    raw_year_list = set(df_expense["Year"].unique()).union(set(df_income["Year"].unique()))
    ordered_year_list = sorted(list(raw_year_list), reverse=True)
    
    # Determine default Year index (Current Year)
    current_year_val = datetime.now().year
    current_year_idx = ordered_year_list.index(current_year_val) if current_year_val in ordered_year_list else 0

    # --- FILTER OPTION A: MONTHLY VIEW ---
    if chosed_filter_mode == "Monthly":
        col_month, col_year = st.columns(2)

        with col_month:
            selected_month = st.selectbox(
                "Select Month",
                ordered_month_list,
                index=current_month_idx,
                help="Filter data by specific month."
            )

        with col_year:
            selected_year = st.selectbox(
                "Select Year",
                ordered_year_list,
                index=current_year_idx,
                help="Filter data by specific year."
            )

        # Apply Filter to DataFrames
        df_expense = df_expense[(df_expense["Month"] == selected_month) & (df_expense["Year"] == selected_year)]
        df_income = df_income[(df_income["Month"] == selected_month) & (df_income["Year"] == selected_year)]
        
        # Set X-Axis to 'Date' (1-31) for line charts
        col_for_lineplot_x = "Date"

    # --- FILTER OPTION B: YEARLY VIEW ---
    elif chosed_filter_mode == "Yearly":
        selected_year = st.selectbox(
            "Select Year",
            ordered_year_list,
            index=current_year_idx,
            help="Filter data by specific year."
        )

        # Apply Filter to DataFrames
        df_expense = df_expense[df_expense["Year"] == selected_year]
        df_income = df_income[df_income["Year"] == selected_year]  

        # Set X-Axis to 'Month' (Jan-Dec) for line charts
        col_for_lineplot_x = "Month"

    # ==========================================
    # 3. Key Performance Indicators (KPIs)
    # ==========================================
    # Calculate totals safely (handle empty dataframes)
    total_inc = df_income["Total"].sum() if not df_income.empty else 0
    total_exp = df_expense["Total"].sum() if not df_expense.empty else 0
    
    # Net Balance Calculation
    remaining = total_inc - total_exp

    # Layout for KPI Cards
    m1, m2, m3 = st.columns(3)

    # --- KPI 1: Income ---
    with m1:
        st.metric(
            label="💰 Total Income", 
            value=f"Rp {total_inc:,.0f}",
            help="Total cumulative income for the selected period."
        )

    # --- KPI 2: Expense ---
    with m2:
        st.metric(
            label="💸 Total Expense", 
            value=f"Rp {total_exp:,.0f}",
            delta=f"-Rp {total_exp:,.0f}", # Negative delta shows red arrow (outflow)
            help="Total cumulative expenses for the selected period."
        )

    # --- KPI 3: Net Balance ---
    with m3:
        st.metric(
            label="📊 Net Balance", 
            value=f"Rp {remaining:,.0f}", 
            delta=f"{remaining:,.0f}", # Positive=Green, Negative=Red
            help="Net profit or loss (Income - Expense)."
        )
    
    st.markdown("---")

    # ==========================================
    # 4. Raw Data Preview
    # ==========================================
    st.subheader("📋 Transaction Details")
    
    col_exp_table, col_inc_table = st.columns(2)

    with col_exp_table:
        st.caption("🔻 Expense Records")
        if not df_expense.empty:
            view_df_expense = df_expense[["DateTime", "Place Name", "Category", "Total"]]
            st.dataframe(view_df_expense, use_container_width=True, hide_index=True)
        else:
            st.info("No expense records found.")

    with col_inc_table:
        st.caption("💹 Income Records")
        if not df_income.empty: 
            view_df_income = df_income[["DateTime", "Place Name", "Category", "Total"]]
            st.dataframe(view_df_income, use_container_width=True, hide_index=True)
        else:
            st.info("No income records found.")

    # ==========================================
    # 5. Visualization & Charts
    # ==========================================
    st.markdown("### 📈 Visual Analysis")

    # Tag data for merging
    df_expense["Type"] = "Expense"
    df_income["Type"] = "Income"

    # Only proceed if we have data to compare
    if not df_expense.empty or not df_income.empty:
        # Merge datasets vertically
        df_all = pd.concat([df_expense, df_income], axis=0)
        
        # --- CHART A: TOTAL COMPARISON (BAR) ---
        total_by_type = df_all.groupby("Type")["Total"].sum().reset_index()

        fig_type = px.bar(
            total_by_type,
            x="Type",
            y="Total",
            color="Type",
            title="Total Income vs Total Expense",
            color_discrete_map={"Income": "#2ecc71", "Expense": "#e74c3c"}, # Custom Green/Red
            text_auto='.2s' # Auto-format text on bars
        )
        st.plotly_chart(fig_type, use_container_width=True)
       
        # --- CHART B: TREND MOVEMENT (LINE) ---
        # Group by Time Unit (Date/Month) and Type
        daily_trend = df_all.groupby([col_for_lineplot_x, "Type"])["Total"].sum().reset_index()

        fig_trend = px.line(
            daily_trend, 
            x=col_for_lineplot_x, 
            y="Total", 
            color="Type",
            markers=True,
            title="Income & Expense Trend Over Time",
            color_discrete_map={"Income": "#2ecc71", "Expense": "#e74c3c"}
        )

        # Format Tooltip & Axis
        fig_trend.update_layout(yaxis_tickformat=",.0f")
        fig_trend.update_traces(hovertemplate='%{y:,.0f}') 

        # X-Axis Formatting based on mode
        if chosed_filter_mode == "Monthly":
            # Show every day (1, 2, 3...)
            fig_trend.update_xaxes(dtick=1, title="Day of Month")
        else:
            # Show Month Names in correct order
            fig_trend.update_xaxes(
                dtick=None,
                type='category',
                categoryorder='array',
                categoryarray=month_order,
                title="Month"
            )
        
        st.plotly_chart(fig_trend, use_container_width=True)

    else:
        st.warning("⚠️ **Insufficient Data:** Please add both Income and Expense records to view charts.")

    # ==========================================    
    # 6. Category Breakdown (Pie Charts)
    # ==========================================
    col_expense, col_income = st.columns(2)
    
    # -- Left Column: Expense Analysis --
    with col_expense:
        if len(df_expense) > 0:
            # Calculate percentage share per category
            total_expense_by_category = round((df_expense.groupby("Category")["Total"].sum() / df_expense["Total"].sum()) * 100, 2)

            # Generate Pie Chart using Plotly
            fig = px.pie(
                total_expense_by_category, 
                names=total_expense_by_category.index, 
                values=total_expense_by_category.values, 
                title="💸 Expense Breakdown"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Automated Insight
            st.info(f"💡 **Insight:** You spent **{total_expense_by_category.max()}%** of your money on **{total_expense_by_category.idxmax()}**.")
        else:
            st.info("ℹ️ No expense data available for analysis.")   

    # -- Right Column: Income Analysis --
    with col_income:
        if len(df_income) > 0:
            # Calculate percentage share per category
            total_income_by_category = round((df_income.groupby("Category")["Total"].sum() / df_income["Total"].sum()) * 100, 2)

            # Generate Pie Chart using Plotly
            fig = px.pie(
                total_income_by_category, 
                names=total_income_by_category.index, 
                values=total_income_by_category.values, 
                title="💰 Income Sources"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Automated Insight
            st.info(f"💡 **Insight:** You receive **{total_income_by_category.max()}%** of your income from **{total_income_by_category.idxmax()}**.")
        else:
            st.info("ℹ️ No income data available for analysis.")   

    # ==========================================
    # 7. Behavioral Insight: Top Ranking (Expenses vs Income)
    # ==========================================
    # Split the layout into two columns
    col_expense, col_income = st.columns(2)

    # --- LEFT COLUMN: EXPENSE RANKING ---
    with col_expense:
        if len(df_expense) > 0:
            # Calculate top 3 most frequent places visited
            most_visited_store = df_expense["Place Name"].value_counts().head(3).index
            total_visited_store = len(most_visited_store)

            st.markdown("### 🏆 Top 3 Most Visited Places")
            
            # Scenario A: User has visited exactly 3 or more unique places
            if total_visited_store == 3:
                for i, store in enumerate(most_visited_store, 1):
                    st.markdown(f"{i}. 🏪 **{store}**")
            
            # Scenario B: User has visited less than 3 unique places
            elif total_visited_store > 0 and total_visited_store < 3:
                for store in most_visited_store:
                    st.markdown(f"- 🏪 {store}")
                
                # Insight message
                st.info(f"ℹ️ You have only visited **{total_visited_store}** distinct locations: **{', '.join(most_visited_store)}**.")
            
            # Scenario C: Data exists but list is empty (Safety fallback)
            else:
                st.info("ℹ️ Not enough data to generate store ranking.")

    # --- RIGHT COLUMN: INCOME RANKING ---
    with col_income:
        if len(df_income) > 0:
            # Calculate top 3 most frequent income sources
            top_money_source = df_income["Place Name"].value_counts().head(3).index
            total_money_source = len(top_money_source)

            st.markdown("### 💰 Top 3 Income Sources")
            
            # Scenario A: User has exactly 3 or more unique income sources
            if total_money_source == 3:
                for i, source in enumerate(top_money_source, 1):
                    st.markdown(f"{i}. 🏦 **{source}**")
            
            # Scenario B: User has less than 3 unique income sources
            elif total_money_source > 0 and total_money_source < 3:
                for source in top_money_source:
                    st.markdown(f"- 🏦 {source}")
                
                # Insight message (Corrected context from 'visited' to 'received from')
                st.info(f"ℹ️ You have received money from **{total_money_source}** distinct sources: **{', '.join(top_money_source)}**.")
            
            # Scenario C: Safety fallback
            else:
                st.info("ℹ️ Not enough data to generate income ranking.")

elif part == "Comparison":
    # Add visual separation and main title
    st.divider()
    st.subheader("📊 Data Comparison & Trends")

    # ==========================================
    # 1. Control Panel & Data Loading
    # ==========================================
    # Button to force reload data from Google Sheets
    if st.button("🔄 Refresh Data", help="Click here to reload the latest data from the database."):
        st.rerun()

    # Fetch latest dataframes from helper functions
    df_expense = get_expense()
    df_income = get_income()

    # Pre-process Data: Extract Date Components for Analysis
    # We add 'Day', 'Month', and 'Year' columns to facilitate grouping.
    for df in [df_expense, df_income]:
        if not df.empty:
            df["Day"] = df["DateTime"].dt.day
            df["Month"] = df["DateTime"].dt.month_name()
            df["Year"] = df["DateTime"].dt.year

    # Define standard month order for sorting
    month_order = [
        "January", "February", "March", "April", "May", "June", 
        "July", "August", "September", "October", "November", "December"
    ]

    # Get unique years and months from both datasets for filter options
    all_years = sorted(list(set(df_expense["Year"]).union(set(df_income["Year"]))), reverse=True)
    all_months = sorted(list(set(df_expense["Month"]).union(set(df_income["Month"]))), key=lambda m: month_order.index(m))

    # ==========================================
    # 2. Filter Configuration
    # ==========================================
    col_type, col_mode = st.columns(2)
    
    with col_type:
        target_type = st.selectbox(
            "1. Analyze What?", 
            ["Expense", "Income"],
            help="Select the financial metric to analyze."
        )
    
    with col_mode:
        filter_mode = st.selectbox(
            "2. Comparison Mode", 
            ["Monthly (Month vs Month)", "Yearly (Year vs Year)"],
            help="Choose between comparing different months in a specific year, or different years side-by-side."
        )

    # Set data source and color palette based on selection
    if target_type == "Expense":
        df_target = df_expense.copy()
        # Use Red shades for Expenses
        line_color = px.colors.sequential.Reds[3:] 
    else:
        df_target = df_income.copy()
        # Use Green shades for Income
        line_color = px.colors.sequential.Greens[3:]

    # ==========================================
    # 3. Visualization Logic
    # ==========================================
    
    # --- OPTION A: MONTHLY COMPARISON (Within a Year) ---
    if filter_mode == "Monthly (Month vs Month)":
        col_month, col_year = st.columns(2)

        with col_year:
            selected_year = st.selectbox(
                "Select Year",
                all_years,
                index=all_years.index(datetime.now().year) if datetime.now().year in all_years else 0,
                help="Pick the year for the monthly breakdown."
            )

        with col_month:
            selected_months = st.multiselect(
                "Select Months to Compare",
                all_months,
                default=all_months[:3] if len(all_months) >= 3 else all_months,
                help="Compare daily trends across these months."
            )

        if selected_months and selected_year:
            # Filter data: Match selected months AND the specific year
            df_viz = df_target[
                (df_target["Month"].isin(selected_months)) & 
                (df_target["Year"] == selected_year)
            ]

            # Aggregate data: Sum total per Day and Month
            # We group by 'Day' (1-31) to overlay different months on the same X-axis
            df_grouped = df_viz.groupby(["Day", "Month"])["Total"].sum().reset_index()

            # Plot Line Chart
            fig = px.line(
                df_grouped, 
                x="Day", 
                y="Total", 
                color="Month", 
                markers=True,
                title=f"Daily {target_type} Trends: {' vs '.join(selected_months)} ({selected_year})",
                color_discrete_sequence=line_color
            )

            # Ensure X-axis shows all days (1-31) clearly
            fig.update_xaxes(dtick=1, title="Day of Month")

    # --- OPTION B: YEARLY COMPARISON (Year vs Year) ---
    elif filter_mode == "Yearly (Year vs Year)":
        selected_years = st.multiselect(
            "Select Years to Compare",
            all_years,
            default=all_years[:2] if len(all_years) >= 2 else all_years,
            help="Compare monthly performance across different years."
        )

        if selected_years:
            # Filter data: Match selected years
            df_viz = df_target[df_target["Year"].isin(selected_years)]

            # Aggregate data: Sum total per Month and Year
            df_grouped = df_viz.groupby(["Month", "Year"])["Total"].sum().reset_index()

            # Plot Line Chart
            fig = px.line(
                df_grouped, 
                x="Month", 
                y="Total", 
                color="Year", 
                markers=True,
                title=f"Yearly {target_type} Comparison ({', '.join(map(str, selected_years))})",
                color_discrete_sequence=line_color
            )
            
            # Ensure X-axis follows standard calendar order (Jan -> Dec)
            fig.update_xaxes(categoryorder='array', categoryarray=month_order, title="Month")

    # ==========================================
    # 4. Final Chart Rendering
    # ==========================================
    if "fig" in locals():
        # Format Y-axis with commas (e.g., 1,000,000)
        fig.update_layout(yaxis_tickformat=",.0f")
        # Format tooltip hover
        fig.update_traces(hovertemplate='%{y:,.0f}')
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Please select data parameters above to generate the chart.", icon="👆")

elif part == "Edit & Delete":
    # Add visual separation and main title
    st.divider()
    st.subheader("✏️ Manage Data (Edit & Delete)")

    # ==========================================
    # 1. UI Setup & Data Loading
    # ==========================================
    # Create separate tabs for Income and Expense management
    income, expense = st.tabs(["Income", "Expense"])

    # Fetch the latest dataframes from the data source
    df_expense = get_expense()
    df_income = get_income()

    # ==========================================
    # 2. Income Tab Logic
    # ==========================================
    with income:
        # Render the interactive data editor
        # 'num_rows="dynamic"' enables Add/Delete row functionality
        edited_df_income = st.data_editor(
            df_income, 
            num_rows="dynamic", 
            use_container_width=True,
            key="editor_income" # Unique key to prevent conflict
        )

        # Save Button
        accept = st.button(
            "💾 Save to Google Sheets", 
            use_container_width=True, 
            help="Click to commit changes to the database", 
            key="btn_save_income"
        )
        
        # Trigger update function if button is clicked
        if accept:
            send_update(edited_df_income, "Income")
        
    # ==========================================
    # 3. Expense Tab Logic
    # ==========================================
    with expense:
        # Render the interactive data editor for expenses
        edited_df_expense = st.data_editor(
            df_expense, 
            num_rows="dynamic", 
            use_container_width=True,
            key="editor_expense" # Unique key is critical here
        )

        # Save Button
        accept = st.button(
            "💾 Save to Google Sheets", 
            use_container_width=True, 
            help="Click to commit changes to the database", 
            key="btn_save_expense"
        )
        
        # Trigger update function if button is clicked
        if accept:
            send_update(edited_df_expense, "Expense")
    
elif part == "Ask AI":
    # Add visual separation and main title
    st.divider()
    st.subheader("✨ Smart Financial Assistant")

    st.button(
        "🔴 Reset AI & Chat Memory", 
        type="primary", 
        on_click=reset_state, 
        use_container_width=True, 
        help="Clears the current conversation and forces SpendSense to re-read your data from scratch. Use this if the AI gets confused."
    )

    # ==========================================
    # 1. Data Loading
    # ==========================================
    # Fetch the latest data from Google Sheets
    df_expense = get_expense()
    df_income = get_income()

    # ==========================================
    # 2. LLM Initialization (Singleton Pattern)
    # ==========================================
    # Only initialize the LLM if it hasn't been created yet to save resources.
    if st.session_state.llm is None:
        try: 
            # Initialize Google Gemini Model
            st.session_state.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash", 
                google_api_key=GOOGLE_API_KEY,
                # Temperature 0.3 ensures focused and deterministic output,
                # which is critical for accurate Python/Pandas code generation.
                temperature=0.3 
            )
            
            # Notify user upon successful connection
            st.toast("AI Engine Online & Ready!", icon="🧠")

        except Exception as e:
            # --- Smart Error Handling ---
            # Reset LLM state to allow retrying without page refresh
            st.session_state.llm = None
            error_str = str(e).lower()

            # Case 1: Authentication Issues
            if "api_key" in error_str or "403" in error_str or "permission denied" in error_str:
                 st.error("🔑 **Authentication Failed.** Invalid API Key. Please check your credentials.", icon="🚫")

            # Case 2: Model Unavailability
            elif "not found" in error_str or "404" in error_str:
                 st.error("🤖 **Model Error.** 'gemini-2.5-flash' not found. Check your API access.", icon="❓")

            # Case 3: Network/Connection Issues
            elif "connection" in error_str or "failed to connect" in error_str:
                 st.error("🌐 **Connection Error.** Cannot reach Google Servers.", icon="📡")
            
            # Case 4: Quota Limits
            elif "429" in error_str or "quota" in error_str:
                 st.error("⏳ **Quota Exceeded.** You have hit the rate limit.", icon="🛑")

            # Case 5: Unknown Errors
            else:
                 st.error(f"❌ **Initialization Failed:** {str(e)}", icon="🚨")

    # ==========================================
    # 3. Memory & Context Setup
    # ==========================================
    # Initialize conversation memory if not present
    if st.session_state.agent_memory is None:
        st.session_state.agent_memory = ConversationBufferMemory(
            memory_key="chat_history", 
            return_messages=True
        )   

    # Check if data contains valid records before starting the agent
    data_ready = (df_expense is not None) and (not df_expense.empty) and \
                 (df_income is not None) and (not df_income.empty)

    # ==========================================
    # 4. Agent Creation
    # ==========================================
    # Create the Pandas Agent if it doesn't exist and data is ready
    if "agent_executor" not in st.session_state and data_ready:
        with st.spinner("Waking up AI..."):
            try:
                # ------------------------------------------
                # System Prompt Definition (STRICT FORMATTING)
                # ------------------------------------------
                custom_prefix = """
                You are **SpendSense AI**, a smart financial advisor.

                ### 📂 DATA MAPPING
                **1. `df1` = EXPENSE (Money Out)**
                - Cols: `DateTime`, `Place Name`, `Category`, `Total`
                - Cats: ["Food", "Beverage", "Electronics", "Transportation", "Insurance", "Entertainment", "Investment" (Buying), "Unknown"]
                
                **2. `df2` = INCOME (Money In)**
                - Cols: `DateTime`, `Place Name`, `Category`, `Total`
                - Cats: ["Salary", "Allowance", "Bonus", "Freelance", "Investment" (Selling/Div), "Gift", "Other"]

                ### ⚡ RULES
                1. **Net:** Savings = `Sum(df2['Total']) - Sum(df1['Total'])`.
                2. **Format:** "Rp X.XXX.XXX".
                3. **Language:** Adapt to User (Indo/Eng/Slang).
                4. **Explanation:** GIVE CONTEXT. "Total Food is Rp 500k" is BAD. "Wah, Food abis Rp 500k, ati-ati ya" is GOOD.
                5. **Advice Logic:** IF asked for "Saran/Advice":
                   - **MUST** calculate `Top Expense Category` first via Python.
                   - **OUTPUT:** Conversational insight. Example: "Waduh, kamu boros banget di **[Category]** dengan total **[Amount]**. Saran saya..."

                ### 🛡️ OUTPUT FORMAT (ABSOLUTE RULE)
                You have TWO allowed formats. YOU MUST USE ONE OF THEM.

                **FORMAT A: NEED CALCULATION**
                Thought: I need to calculate sum of...
                Action: python_repl_ast
                Action Input: df1['Total'].sum()
                Observation: 500000
                Final Answer: Total pengeluaranmu adalah Rp 500.000.

                **FORMAT B: NO CALCULATION / JUST TALKING**
                (DO NOT USE 'Thought' OR 'Action')
                Final Answer: Halo! Ada yang bisa dibantu?

                **⚠️ CRITICAL ERROR PREVENTION:**
                - IF you write a response, YOU MUST START IT WITH "Final Answer:".
                - NEVER write text without "Final Answer:" prefix.
                - NEVER write "Thought:" without "Action:".
                
                ### MEMORY
                {chat_history}
                """

                # ------------------------------------------
                # Initialize Pandas Dataframe Agent
                # ------------------------------------------
                st.session_state.agent_executor = create_pandas_dataframe_agent(
                    llm=st.session_state.llm,
                    df=[df_expense, df_income],
                    allow_dangerous_code=True,       # Required for code execution
                    handle_parsing_errors=True,      # Auto-fix formatting errors
                    prefix=custom_prefix,            # Inject custom rules
                    agent_executor_kwargs={
                        "memory": st.session_state.agent_memory,
                        "handle_parsing_errors": True
                    }
                )

            except Exception as e:
                # --- Agent Initialization Error Handling ---
                error_str = str(e).lower()

                if "dataframe" in error_str or "index" in error_str:
                    st.error("📊 **Data Error.** Complex dataframe structure detected.", icon="📉")
                
                elif "llm" in error_str or "none" in error_str:
                    st.error("🧠 **AI Error.** LLM not initialized properly.", icon="🚫")

                elif "module" in error_str or "import" in error_str:
                    st.error("📦 **Dependency Error.** Missing required libraries.", icon="📦")

                else:
                    st.error(f"❌ **Agent Creation Failed:** {str(e)}", icon="🚨")

    # ==========================================
    # 5. Chat Interface & Logic
    # ==========================================
    # ------------------------------------------
    # A. Display Chat History
    # ------------------------------------------
    # Render previous messages from session state
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            # If message contains a plot/image, display it first
            if "image" in msg:
                st.image(msg["image"])
        
                # Add Download Button for the plot
                st.download_button(
                    label="📥 Download Plot",
                    data=msg["image"],
                    file_name="analysis_chart.png",
                    mime="image/png",
                    key=f"download_btn_{i}"
                )
            
            # Display text content
            st.markdown(msg["content"])

    # ------------------------------------------
    # B. Capture User Input
    # ------------------------------------------
    if prompt_text := st.chat_input("💬 Ask questions about your data..."):
        
        # Validation: Check if data exists
        if not data_ready:
            st.warning("⚠️ No data found! Please upload a file first.", icon="🚫")
        
        else:
            # 1. Save and Display User Message
            st.session_state.messages.append({"role": "human", "content": prompt_text})
            st.chat_message("human").write(prompt_text)

            # 2. Generate AI Response
            with st.chat_message("ai"):
                try:
                    # Enable "Thinking..." animation via Callback
                    st_callback = StreamlitCallbackHandler(st.container())

                    # Invoke Agent
                    response = st.session_state.agent_executor.invoke(
                        {"input": prompt_text},
                        {"callbacks": [st_callback]}
                    )

                    # ------------------------------------------
                    # C. Handle Visualizations (Plots)
                    # ------------------------------------------
                    # Check if Matplotlib has an active figure
                    if plt.get_fignums():
                        
                        # Capture the plot
                        fig = plt.gcf() 
                        st.pyplot(fig) 

                        # Save plot to buffer
                        img_buffer = io.BytesIO()
                        plt.savefig(img_buffer, format="png")
                        img_buffer.seek(0)

                        # Provide Download Button
                        st.download_button(
                            label="📥 Download Plot",
                            data=img_buffer,
                            file_name="analysis_chart.png",
                            mime="image/png",
                            key=f"download_btn_{len(st.session_state.messages)}"
                        )

                        # Display Text Response
                        if "output" in response and len(response["output"]) > 0:
                            st.markdown(response["output"])

                        # Save Text + Image to History
                        st.session_state.messages.append({
                            "role": "ai", 
                            "content": response["output"], 
                            "image": img_buffer
                        })
                        
                        # Clear plot to prevent overlapping
                        plt.clf()
                        plt.close()
                        
                    else:
                        # ------------------------------------------
                        # D. Handle Text-Only Responses
                        # ------------------------------------------
                        if "output" in response and len(response["output"]) > 0:
                            st.markdown(response["output"])

                        # Save Text to History
                        st.session_state.messages.append({
                            "role": "ai", 
                            "content": response["output"]
                        })

                except Exception as e:
                    # ------------------------------------------
                    # E. Runtime Error Handling
                    # ------------------------------------------
                    error_str = str(e).lower()

                    if "429" in error_str or "quota" in error_str:
                        st.error("⏳ **API Quota Exceeded.** Please wait.", icon="🛑")

                    elif "api_key" in error_str or "403" in error_str:
                        st.error("🔑 **Auth Failed.** Check API Key.", icon="🚫")

                    elif "not found" in error_str:
                        st.error("🤖 **Model Error.** Model not found.", icon="❓")

                    elif "parsing" in error_str:
                        st.error("🧩 **Parsing Error.** Please rephrase.", icon="😵‍💫")

                    elif "nameerror" in error_str or "syntaxerror" in error_str:
                        st.error(f"🐍 **Code Error.** Invalid Python generated.\n`{error_str}`", icon="📉")

                    else:
                        st.error(f"❌ **Error:** {str(e)}", icon="🚨")