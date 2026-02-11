# 💸 SpendSense | AI-Powered Financial Assistant

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Gemini](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-8E75B2?logo=google&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-Pandas%20Agent-1C3C3C?logo=langchain&logoColor=white)
![Google Sheets](https://img.shields.io/badge/Google%20Sheets-Database-34A853?logo=googlesheets&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-success)

## 📌 Overview
**SpendSense** is an intelligent **Financial Tracking & Analytics Platform** designed to simplify personal finance management through the power of Generative AI.

It combines traditional expense tracking with **Google Gemini 2.5 Flash** to offer features like **OCR Receipt Scanning**, **Natural Language Data Querying**, and **Automated Insights**. Built on Streamlit, it uses Google Sheets as a real-time, cloud-based backend, ensuring your financial data is accessible and secure.

## ✨ Key Features

### 📸 AI Receipt Scanner (OCR)
* **Smart Extraction:** Upload an image of a receipt or take a photo directly. The system uses **Gemini 2.5 Flash** to automatically identify the *Merchant Name*, *Transaction Date*, *Total Amount*, and categorize the expense (e.g., Food, Transport).
* **Validation Layer:** Includes a verification step where users can review and edit the AI-extracted data before saving it to the database, ensuring 100% accuracy.

### 💬 Conversational Finance (Pandas Agent)
* **Ask Your Data:** Instead of complex filters, just ask: *"How much did I spend on food last month?"* or *"What is my biggest expense?"*.
* **LangChain Integration:** Utilizes a **Pandas DataFrame Agent** to convert natural language questions into executable Python code, analyzing your Income and Expense datasets in real-time.
* **Context-Aware:** The AI understands context (e.g., "savings", "wasteful") and provides actionable financial advice based on your spending habits.

### 📊 Interactive Dashboard
* **Dynamic Filtering:** Toggle between **Monthly** (Day-by-Day) and **Yearly** (Month-by-Month) views to analyze trends at different granularities.
* **KPI Cards:** Instantly view **Total Income**, **Total Expense**, and **Net Balance** with color-coded delta indicators (Green for profit, Red for loss).
* **Visual Analytics:**
    * **Trend Lines:** Interactive Plotly line charts showing financial movement over time.
    * **Category Breakdown:** Pie charts visualizing the percentage share of each expense/income category.
    * **Ranking System:** Automatically identifies your "Top 3 Most Visited Places" and "Top 3 Income Sources".

### 🛡️ Robust Data Management (ETL)
* **Google Sheets Backend:** Acts as a lightweight, reliable database. Data is fetched in real-time (`gspread`) and processed into Pandas DataFrames.
* **Safe Updates:** Implements an **Auto-Backup & Rollback** mechanism. Before any edit/delete operation, the system creates a backup of the current sheet. If the update fails, it automatically restores the original data to prevent corruption.
* **Edit & Delete:** A dedicated interface using `st.data_editor` allows users to modify or remove records directly from the app, with changes syncing instantly to the cloud.

## 🛠️ Tech Stack
* **Frontend:** Streamlit
* **AI Engine:** Google GenAI SDK (`gemini-2.5-flash`)
* **Orchestration:** LangChain (Pandas DataFrame Agent)
* **Database:** Google Sheets API (`gspread`)
* **Data Processing:** Pandas, NumPy
* **Visualization:** Plotly Express, Matplotlib, Seaborn
* **Utilities:** Python-Dotenv, Pillow (Image Processing)

## ⚙️ Configuration (Environment Variables)
Create a `.secrets.toml` file in the `.streamlit` directory for local development, or set these in your deployment platform's secrets management:

```toml
[files]
gcp_json = """
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
  "client_email": "your-service-account-email",
  "client_id": "your-client-id",
  "auth_uri": "[https://accounts.google.com/o/oauth2/auth](https://accounts.google.com/o/oauth2/auth)",
  "token_uri": "[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)",
  "auth_provider_x509_cert_url": "[https://www.googleapis.com/oauth2/v1/certs](https://www.googleapis.com/oauth2/v1/certs)",
  "client_x509_cert_url": "[https://www.googleapis.com/robot/v1/metadata/x509/your-service-account-email](https://www.googleapis.com/robot/v1/metadata/x509/your-service-account-email)"
}
"""
```

Create a `.env` file for the API Key:
```ini
GOOGLE_API_KEY=your_gemini_api_key
```

## 📦 Installation

1. **Clone the Repository**
```bash
git clone https://github.com/viochris/Streamlit-SpendSense.git
cd Streamlit-SpendSense
```


2. **Install Dependencies**
```bash
pip install -r requirements.txt
# Requires: streamlit, pandas, plotly, google-genai, langchain-google-genai, gspread, python-dotenv
```


3. **Run the Application**
```bash
streamlit run app.py
```


## 🚀 Usage Guide

### 1. Tracking Finances
* **Income/Expense Tabs:** Choose between "Scan Receipt" (AI) or "Manual Entry".
* **AI Scan:** Upload an image. The AI will extract the *Place*, *Date*, *Category*, and *Total*. Review the pre-filled form and click "Save".
* **Manual:** Fill in the details yourself if you don't have a receipt.

### 2. Dashboard & Analytics
* Navigate to **"Dashboard"** to see your financial health.
* Use the **"View Mode"** toggle to switch between daily tracking (Monthly view) or high-level trends (Yearly view).
* Check the **"Comparison"** tab to overlay data from different months or years to spot spending patterns.

### 3. Ask AI (Chat Mode)
* Go to **"Ask AI"**.
* Type natural questions like: *"Show me a bar chart of my expenses by category"* or *"Did I save money this month?"*.
* The AI will generate Python code to calculate the answer or plot the chart directly in the chat interface.

### 4. Data Management
* Use **"Edit & Delete"** to fix mistakes.
* The system automatically backs up data before saving changes, ensuring safety.

---

**Author:** [Silvio Christian, Joe](https://www.linkedin.com/in/silvio-christian-joe)
*"Master your money, don't let it master you."*
