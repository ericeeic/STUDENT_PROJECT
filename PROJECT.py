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
            
            
            
with tab2:
    st.header("Gemini 聊天機器人")
    
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    chat = genai.ChatSession(model=model)
    
    user_input = st.text_input("請輸入問題")
    if user_input:
        response = chat.send_message(user_input)
        st.write(response.text)

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

        st.write("### 選擇兩個欄位來判斷相關關係")
        cols = corr.columns.tolist()
        col1 = st.selectbox("選擇欄位1", cols)
        col2 = st.selectbox("選擇欄位2", [c for c in cols if c != col1])

        if col1 and col2:
            val = corr.loc[col1, col2]
            st.write(f"{col1} 與 {col2} 的相關係數是：{val:.3f}")

            threshold = 0.5  # 可以自己調整
            if val >= threshold:
                st.success("判斷：**正相關**")
            elif val <= -threshold:
                st.error("判斷：**負相關**")
            else:
                st.info("判斷：**無明顯相關**")
    else:
        st.info("請先在「CSV 檔案分析」上傳並分析 CSV 檔案")



