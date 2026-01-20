import streamlit as st
import os
import json
import pdfplumber
import google.generativeai as genai
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# --- 頁面設定 ---
st.set_page_config(page_title="OT 排程助理", layout="wide")

# --- 1. 資安核心：從 Secrets 讀取鑰匙 ---
# 我們不讀取檔案，而是讀取 Streamlit 的環境變數
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    # 將 secrets 裡的 token 字串轉回字典物件
    TOKEN_DICT = json.loads(st.secrets["GOOGLE_TOKEN_JSON"])
    # 將 secrets 裡的 client config 轉回字典 (如果需要重新授權才用得到，這邊主要靠 token)
    CLIENT_CONFIG = json.loads(st.secrets["GOOGLE_CLIENT_JSON"])
except Exception as e:
    st.error("❌ 尚未設定 Secrets 金鑰！請至 Streamlit 後台設定。")
    st.stop()

genai.configure(api_key=API_KEY)
SCOPES = ['https://www.googleapis.com/auth/calendar']

# --- 2. 核心功能函式 ---
def extract_text_from_pdf(file):
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted: text += extracted + "\n"
    except Exception as e:
        return None
    return text

def get_calendar_service():
    """取得 Google Calendar 服務權限 (雲端版)"""
    creds = None
    # 直接從 secrets 載入 token
    if TOKEN_DICT:
        creds = Credentials.from_authorized_user_info(TOKEN_DICT, SCOPES)
    
    # 檢查是否有效
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                st.error("❌ 憑證過期且無法自動更新，請聯絡管理員更新 Token。")
                return None
        else:
            st.error("❌ 找不到有效的憑證，請檢查 Secrets 設定。")
            return None
            
    return build('calendar', 'v3', credentials=creds)

def analyze_and_schedule(content):
    model = genai.GenerativeModel('gemini-flash-latest') # 或 gemini-1.5-flash
    
    with st.spinner('🧠 AI 正在分析並聯絡 Google 日曆...'):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt = f"""
        現在時間：{now}
        請分析內容，提取「行事曆活動」。
        【規則】
        1. 相對時間(明天、週五)請轉為 ISO 8601 日期 (YYYY-MM-DDTHH:MM:SS)。
        2. 若無結束時間，預設為開始後 1 小時。
        3. 回傳純 JSON。
        
        【範例】
        {{ "events": [ {{ "summary": "標題", "start_time": "2026-01-20T10:00:00", "end_time": "2026-01-20T11:00:00" }} ] }}

        內容：{content[:5000]}
        """
        
        try:
            response = model.generate_content(prompt)
            clean = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
        except Exception as e:
            st.error(f"AI 解析失敗: {e}")
            return

        if not data or "events" not in data:
            st.warning("⚠️ AI 沒找到任何活動。")
            return

        # 寫入日曆
        service = get_calendar_service()
        if not service: return

        success_count = 0
        for event in data['events']:
            try:
                body = {
                    'summary': event.get('summary', '新活動'),
                    'start': {'dateTime': event['start_time'], 'timeZone': 'Asia/Taipei'},
                    'end': {'dateTime': event.get('end_time', event['start_time']), 'timeZone': 'Asia/Taipei'},
                }
                service.events().insert(calendarId='primary', body=body).execute()
                st.toast(f"✅ 已建立：{event['summary']}")
                success_count += 1
            except Exception as e:
                st.error(f"建立失敗: {e}")
        
        if success_count > 0:
            st.success(f"🎉 成功加入 {success_count} 個行程到日曆！")
            st.balloons()

# --- 3. 前端介面 ---
st.title("🏥 職能治療排程助理")
st.markdown("---")

tab1, tab2 = st.tabs(["📝 指令/語音輸入", "📂 上傳公文 PDF"])

with tab1:
    st.info("💡 提示：手機開啟時，鍵盤上的「麥克風」按鈕可直接語音輸入。")
    user_input = st.text_area("請輸入行程指令：", height=150, placeholder="例如：幫我安排下週三早上八點開科務會議")
    if st.button("送出分析", key="txt_btn", use_container_width=True):
        if user_input:
            analyze_and_schedule(user_input)
        else:
            st.warning("請輸入內容")

with tab2:
    uploaded_file = st.file_uploader("請選擇 PDF 檔案", type="pdf")
    if uploaded_file:
        if st.button("開始讀取並分析", key="pdf_btn", use_container_width=True):
            text = extract_text_from_pdf(uploaded_file)
            if text:
                analyze_and_schedule(text)
            else:
                st.error("無法讀取 PDF 文字")