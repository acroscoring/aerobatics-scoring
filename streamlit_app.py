import streamlit as st
import gspread
import pandas as pd
from datetime import datetime

st.title("🔌 Database Connection Test")

# 1. Setup Credentials securely from Streamlit Secrets
try:
    # We access the secrets we defined in .streamlit/secrets.toml
    credentials_dict = dict(st.secrets["gcp_service_account"])
    
    # Authenticate with Google
    gc = gspread.service_account_from_dict(credentials_dict)
    
    st.success("✅ Authenticated with Google Cloud!")
except Exception as e:
    st.error(f"❌ Authentication Failed: {e}")
    st.stop()

# 2. Connect to the Sheet
SHEET_NAME = "Scoring Template Sheet" # Make sure this matches your Google Sheet Name exactly

try:
    sh = gc.open(SHEET_NAME)
    worksheet = sh.sheet1
    st.success(f"✅ Connected to Sheet: '{SHEET_NAME}'")
except Exception as e:
    st.error(f"❌ Could not find Sheet '{SHEET_NAME}'. Did you share it with the bot email?")
    st.stop()

# 3. Test Write Operation
if st.button("Test Write Operation"):
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Append a row: [Date, Action, Status]
        worksheet.append_row([current_time, "Connection Test", "Success"])
        st.toast("Data written to Google Sheets!", icon="🚀")
    except Exception as e:
        st.error(f"Write failed: {e}")

# 4. Test Read Operation
st.divider()
st.subheader("Current Data in Sheet:")

if st.button("Test Read Operation"):
    try:
        # Get all records
        data = worksheet.get_all_records()
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df)
        else:
            st.info("Sheet is connected but empty. Click 'Test Write' above!")
    except Exception as e:
        st.warning("Could not read data. (If the sheet is empty, add a header row like 'Time', 'Action', 'Status' manually in Google Sheets first).")