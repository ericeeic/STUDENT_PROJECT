import streamlit as st
import pandas as pd
import chardet
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder
import google.generativeai as genai

# Gemini API Key 設定（請換成你自己的）
API_KEY = "AIzaSyAP7BSVTOBJo2CDpincq7dAlTmDG4Ix5c0"

# Streamlit 標題
st.title("CSV 檔案分析與 Gemini 聊天")

# 建立兩個 tab
tab1, tab2 = st.tabs(["CSV 檔案分析", "Gemini 聊天機器人"])

with tab1:
    st.header("上傳 CSV 檔案並分析")
    uploaded_files = st.file_uploader(
        "請上傳 CSV 檔案 (可多檔)", 
        type=['csv'], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            st.subheader(f"檔案：{uploaded_file.name}")
            
            # 讀取檔案二進位資料判斷編碼
            raw_bytes = uploaded_file.read()
            encoding = chardet.detect(raw_bytes)['encoding']
            uploaded_file.seek(0)  # 重置指標
            
            # 讀取 DataFrame
            df = pd.read_csv(uploaded_file, encoding=encoding)
            st.write("資料預覽")
            st.dataframe(df.head())
            
            # 類別欄位轉數字
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            if cat_cols:
                le = LabelEncoder()
                for col in cat_cols:
                    try:
                        df[col] = le.fit_transform(df[col].astype(str))
                    except Exception as e:
                        st.warning(f"欄位 '{col}' 編碼失敗：{e}")
            
            # 計算相關係數
            corr = df.corr()
            
            st.write("相關係數矩陣")
            st.dataframe(corr)
            
            # 畫熱力圖
            st.write("相關係數熱力圖")
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(
                corr,
                annot=True,
                cmap='coolwarm',
                vmin=-1,
                vmax=1,
                square=True,
                linewidths=0.5,
                ax=ax
            )
            st.pyplot(fig)

with tab2:
    st.header("Gemini 聊天機器人")
    
    # 設定 Gemini API
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    chat = genai.ChatSession(model=model)
    
    user_input = st.text_input("請輸入問題")
    if user_input:
        response = chat.send_message(user_input)
        st.write(response.text)
