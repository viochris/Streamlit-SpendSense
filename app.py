import streamlit as st
import pandas as pd
import plotly.express as px
import json
from datetime import datetime, timedelta
from PIL import Image
from google import genai

# Import custom functions from local module
from function import (
    init_state, 
    change_on_upload, 
    send_expense, 
    send_income, 
    get_expense, 
    get_income
)

# ==========================================
# 1. INITIALIZATION & SETUP
# ==========================================
# Initialize session state for data persistence
init_state()

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
    ### 🤖 AI Financial Assistant
    **Welcome to SpendSense!** Your intelligent financial companion. 
    Track your **Income 💰**, manage **Expenses 💸**, and visualize your **Financial Health 📊** effortlessly.
    """
)

# ==========================================
# 3. SIDEBAR CONFIGURATION
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuration")

    # Mapping dictionary to display user-friendly labels with icons 
    # while maintaining valid backend string values for logic control.
    mode_icons = {
        "Income": "💰 Record Income",
        "Expense": "💸 Track Expense",
        "Dashboard": "📊 Dashboard Analytics"
    }

    # Navigation menu using the mapping dictionary for display
    part = st.selectbox(
        "🗂️ Navigation Mode",
        options=["Income", "Expense", "Dashboard"],
        format_func=lambda option: mode_icons.get(option),
        index=0,
        help="Select the module you want to access."
    )

# ==========================================
# 4. APPLICATION LOGIC
# ==========================================
# Initialize Google Gemini Client
# Uses session state key if available, otherwise relies on .env fallback
client = genai.Client()

# Set current timezone (UTC+7 for WIB)
current_time = (datetime.utcnow() + timedelta(hours=7))

# ------------------------------------------
# MODULE: EXPENSE TRACKER
# ------------------------------------------
if part == "Expense":
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

# ------------------------------------------
# MODULE: DASHBOARD ANALYTICS
# ------------------------------------------
elif part == "Dashboard":
    
    # 1. Control Panel
    # Button to force reload data from Google Sheets
    if st.button("🔄 Refresh Data", help="Click here to reload the latest data from the database."):
        st.rerun()

    # 2. Data Retrieval
    # Fetching latest dataframes from helper functions
    df_expense = get_expense()
    df_income = get_income()

    # 3. Key Metrics Display
    # displaying total income summary
    if len(df_income) > 0:
        total_income = df_income["Total"].sum()
        st.metric(label="💰 Total Income", value=f"{total_income:,.0f}")
    else:
        st.info("ℹ️ No Income Data Recorded Yet")

    # 4. Raw Data Visualization
    # Displaying raw tables for user reference
    st.subheader("📋 Transaction History")

    # Expense Table Rendering logic
    # Checks if expense dataframe is not empty
    if len(df_expense) > 0:
        st.dataframe(df_expense, use_container_width=True, hide_index=True)
    else:
        # Fallback message when no expense data is available
        st.info("ℹ️ No expense records found yet.")

    # Income Table Rendering logic
    # Checks if income dataframe is not empty
    if len(df_income) > 0: 
        st.dataframe(df_income, use_container_width=True, hide_index=True)
    else:
        # Fallback message when no income data is available
        st.info("ℹ️ No income records found yet.")

    # 5. Comparative Analysis (Income vs Expense)
    # Tagging data for merged visualization
    df_expense["Type"] = "Expense" 
    df_income["Type"] = "Income"

    if len(df_expense) > 0 and len(df_income) > 0:
        # Merge datasets to create a comparative bar chart
        df_all = pd.concat([df_expense, df_income], axis=0)
        
        total_by_type = df_all.groupby("Type")["Total"].sum()
        st.bar_chart(x=total_by_type.index, y=total_by_type.values)
    else:
        st.warning("⚠️ **Insufficient Data:** Both Income and Expense records are required to generate the comparison chart.")

    # 6. Category Breakdown (Pie Charts)
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

    # 7. Behavioral Insight: Most Visited Places
    if len(df_expense) > 0:
        most_visited_store = df_expense["Place Name"].value_counts().head(3).index
        total_visited_store = len(most_visited_store)

        st.markdown("### 🏆 Top 3 Most Visited Places")
        
        if total_visited_store == 3:
            for i, store in enumerate(most_visited_store, 1):
                st.markdown(f"{i}. 🏪 **{store}**")
        elif total_visited_store > 0 and total_visited_store < 3:
            for store in most_visited_store:
                st.markdown(f"- 🏪 {store}")
            st.info(f"ℹ️ You have only visited **{total_visited_store}** distinct locations: **{', '.join(most_visited_store)}**.")
        else:
            st.info("ℹ️ Not enough data to generate store ranking.")