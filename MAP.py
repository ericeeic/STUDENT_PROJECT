import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_echarts import st_echarts
import json
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
import os

# 載入 .env（如有）
load_dotenv()

# 頁面設定
st.set_page_config(page_title="台灣不動產與 Gemini 聊天室", layout="wide")

# 頁面選擇
page = st.sidebar.selectbox("選擇頁面", ["不動產分析", "Gemini 聊天室"], key="page")

# 共用 Session State 初始化
def init_state(defaults):
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# 驗證 API 並初始化 Gemini 模型
def verify_gemini_api():
    if not st.session_state.api_key:
        st.info("⚠️ 請在左側輸入 API 金鑰後開始使用。")
        st.stop()

    try:
        genai.configure(api_key=st.session_state.api_key)
        MODEL_NAME = "models/gemini-2.0-flash"
        model = genai.GenerativeModel(MODEL_NAME)
        test_response = model.generate_content("Hello")
        if not test_response.text.strip():
            raise ValueError("API 回應為空，可能是無效金鑰")
        return model
    except Exception as e:
        st.error(f"❌ API 金鑰驗證失敗或無效：{e}")
        st.stop()

# ✨ 你的不動產分析邏輯（請接續保留）
# ... 這裡保留你完整的不動產分析程式碼 ...
# 你只需要：
# - 把原本的 `model = genai.GenerativeModel(...)` 改成 `model = verify_gemini_api()`
# - 只在需要 Gemini 的區塊呼叫即可

# ---------------- Gemini 聊天室頁 ----------------
    elif page == "Gemini 聊天室":
        st.title("🤖 Gemini AI 聊天室")

        init_state({
            "api_key": "",
            "remember_api": False,
            "conversations": {},
            "topic_ids": [],
            "current_topic": "new",
            "uploaded_df": None
        })

        with st.sidebar:
            st.markdown("## 🔐 API 設定")
            st.session_state.remember_api = st.checkbox("記住 API 金鑰", value=st.session_state.remember_api)
            if st.session_state.remember_api and st.session_state.api_key:
                api_key_input = st.session_state.api_key
                st.success("✅ 已使用儲存的 API Key")
            else:
                api_key_input = st.text_input("請輸入 Gemini API 金鑰", type="password")
            if api_key_input and api_key_input != st.session_state.api_key:
                st.session_state.api_key = api_key_input

    # 初始化模型
    model = verify_gemini_api()

    uploaded_file = st.file_uploader("📁 上傳 CSV 檔案（Gemini 可讀取）", type="csv")
    if uploaded_file:
        try:
            st.session_state.uploaded_df = pd.read_csv(uploaded_file)
            st.success("✅ 上傳成功，前幾列資料如下：")
            st.dataframe(st.session_state.uploaded_df.head())
        except Exception as e:
            st.error(f"❌ 上傳錯誤：{e}")

    with st.sidebar:
        st.markdown("---")
        st.header("🗂️ 聊天紀錄")
        if st.button("🆕 新對話"):
            st.session_state.current_topic = "new"
        for tid in st.session_state.topic_ids:
            label = ("✔️ " if tid == st.session_state.current_topic else "") + st.session_state.conversations[tid]["title"]
            if st.button(label, key=f"btn_{tid}"):
                st.session_state.current_topic = tid
        if st.button("🧹 清除所有紀錄"):
            st.session_state.conversations.clear()
            st.session_state.topic_ids.clear()
            st.session_state.current_topic = "new"

    with st.form("user_input_form", clear_on_submit=True):
        user_input = st.text_input("你想問什麼？")
        submitted = st.form_submit_button("🚀 送出")

    if submitted and user_input:
        is_new = st.session_state.current_topic == "new"
        if is_new:
            topic_id = f"topic_{len(st.session_state.topic_ids)+1}"
            st.session_state.conversations[topic_id] = {"title": "（產生主題中...）", "history": []}
            st.session_state.topic_ids.append(topic_id)
            st.session_state.current_topic = topic_id
        else:
            topic_id = st.session_state.current_topic

        st.session_state.conversations[topic_id]["history"].append({"user": user_input, "bot": "⏳ 回覆生成中..."})

        with st.spinner("Gemini 回覆中..."):
            try:
                if is_new:
                    title_prompt = f"請為以下句子產生主題：「{user_input}」(不超過10字)"
                    topic_title = model.generate_content(title_prompt).text.strip()[:10]
                    st.session_state.conversations[topic_id]["title"] = topic_title
                else:
                    topic_title = st.session_state.conversations[topic_id]["title"]

                prompt = f"主題為「{topic_title}」。\n使用者問題：「{user_input}」"
                if st.session_state.uploaded_df is not None:
                    csv_preview = st.session_state.uploaded_df.head(10).to_csv(index=False)
                    prompt += f"\nCSV 資料：\n{csv_preview}"

                answer = model.generate_content(prompt).text.strip()
            except Exception as e:
                answer = f"⚠️ 錯誤：{e}"
                if is_new:
                    st.session_state.conversations[topic_id]["title"] = "錯誤主題"

        st.session_state.conversations[topic_id]["history"][-1]["bot"] = answer

    if st.session_state.current_topic != "new":
        conv = st.session_state.conversations[st.session_state.current_topic]
        for msg in reversed(conv["history"]):
            st.markdown(f"**👤 你：** {msg['user']}")
            st.markdown(f"**🤖 Gemini：** {msg['bot']}")
            st.markdown("---")
