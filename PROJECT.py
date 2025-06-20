import streamlit as st
import pandas as pd
import chardet
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder
import google.generativeai as genai

API_KEY = "AIzaSyAP7BSVTOBJo2CDpincq7dAlTmDG4Ix5c0"

st.title("CSV 檔案分析與 Gemini 聊天")

tab1, tab2, tab3 = st.tabs(["CSV 檔案分析", "Gemini 聊天機器人", "相關係數分析"])

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
            
            raw_bytes = uploaded_file.read()
            encoding = chardet.detect(raw_bytes)['encoding']
            uploaded_file.seek(0)
            
            df = pd.read_csv(uploaded_file, encoding=encoding)
            st.write("資料預覽")
            st.dataframe(df.head())
            
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            if cat_cols:
                le = LabelEncoder()
                for col in cat_cols:
                    try:
                        df[col] = le.fit_transform(df[col].astype(str))
                    except Exception as e:
                        st.warning(f"欄位 '{col}' 編碼失敗：{e}")
            
            corr = df.corr()
            st.session_state['corr'] = corr
            st.session_state['has_data'] = True

with tab3:
    st.header("相關係數分析")
    if st.session_state.get('has_data', False):
        corr = st.session_state['corr']
        st.write("相關係數矩陣")
        st.dataframe(corr)
        
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
        
        # 分析相關係數矩陣，列出顯著正相關與負相關
        st.write("### 正相關與負相關對照表")
        threshold = 0.5  # 你可以調整這個閾值，代表什麼程度的相關算顯著
        
        pos_corr = []
        neg_corr = []
        for i in corr.columns:
            for j in corr.columns:
                if i != j:
                    val = corr.loc[i, j]
                    if val >= threshold:
                        pos_corr.append((i, j, val))
                    elif val <= -threshold:
                        neg_corr.append((i, j, val))
        
        if pos_corr:
            st.write("**正相關對** (相關係數 >= {:.2f}):".format(threshold))
            for i, j, val in pos_corr:
                st.write(f"{i} 與 {j} ：相關係數 = {val:.3f}")
        else:
            st.write("沒有顯著的正相關")
        
        if neg_corr:
            st.write("**負相關對** (相關係數 <= {:.2f}):".format(-threshold))
            for i, j, val in neg_corr:
                st.write(f"{i} 與 {j} ：相關係數 = {val:.3f}")
        else:
            st.write("沒有顯著的負相關")
    else:
        st.info("請先在「CSV 檔案分析」上傳並分析 CSV 檔案")

with tab2:
    st.header("Gemini 聊天機器人")
    
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    chat = genai.ChatSession(model=model)
    
    user_input = st.text_input("請輸入問題")
    if user_input:
        response = chat.send_message(user_input)
        st.write(response.text)
