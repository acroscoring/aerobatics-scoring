# import streamlit as st
# from google.oauth2.service_account import Credentials
# from googleapiclient.discovery import build # type: ignore

# def check_quotas() -> None:
#     # 1. Load Secrets
#     creds_dict = dict(st.secrets["gcp_service_account"])
#     creds = Credentials.from_service_account_info(creds_dict)

#     # 2. Build Drive Service
#     service = build('drive', 'v3', credentials=creds)

#     # 3. Ask for Quota Info
#     try:
#         about = service.about().get(fields="storageQuota, user").execute()
#         quota = about.get('storageQuota', {})
#         user = about.get('user', {})

#         limit = int(quota.get('limit', 0))
#         usage = int(quota.get('usage', 0))
        
#         st.write(f"🤖 **Bot Name:** {user.get('displayName')}")
#         st.write(f"📧 **Bot Email:** {user.get('emailAddress')}")
        
#         st.divider()
        
#         st.metric("Total Storage Limit", f"{limit / (1024*1024):.2f} MB")
#         st.metric("Used Storage", f"{usage / (1024*1024):.2f} MB")
        
#         if limit == 0:
#             st.error("⚠️ Your Bot has 0 MB of storage! This is why it fails.")
#             st.info("💡 **Fix:** You likely need to enable Billing on your Google Cloud Project (don't worry, it's free for this usage, but it unlocks the storage quota).")
#         elif usage >= limit:
#             st.error("⚠️ Bot storage is full!")
#         else:
#             st.success("✅ Storage looks fine. The error might be permission-related.")

#     except Exception as e:
#         st.error(f"Error checking quota: {e}")