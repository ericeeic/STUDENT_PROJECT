import streamlit as st
import pandas as pd
import chardet
import plotly.express as px
from sklearn.preprocessing import LabelEncoder
import google.generativeai as genai
from dotenv import load_dotenv
import os
import io

# 讀取 .env 檔案
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# 檢查 API KEY
if not API_KEY:
    st.error("API 金鑰未設定，請確認 .env 檔案或環境變數")
    st.stop()

# 設定 Gemini API
genai.configure(api_key=API_KEY)

# 初始化 Session State
if 'df_raw_dict' not in st.session_state:
    st.session_state['df_raw_dict'] = {}
if 'df_dict' not in st.session_state:
    st.session_state['df_dict'] = {}
if 'corr_dict' not in st.session_state:
    st.session_state['corr_dict'] = {}
if 'has_data' not in st.session_state:
    st.session_state['has_data'] = False

# App 標題
st.title("STREAMLIT作業")

# 四個頁籤
tab1, tab2, tab3, tab4 = st.tabs(["CSV 檔案分析", "Gemini 聊天", "資料欄位統計", "相關係數分析"])

# ---- tab1: CSV 檔案分析 ----
with tab1:
    st.header("上傳 CSV 檔案")
    uploaded_files = st.file_uploader("請上傳 CSV 檔案 (可多檔)", type=['csv'], accept_multiple_files=True)

    if uploaded_files:
        for uploaded_file in uploaded_files:
            st.subheader(f"檔案：{uploaded_file.name}")

            raw_bytes = uploaded_file.read()
            encoding = chardet.detect(raw_bytes)['encoding']
            df_raw = pd.read_csv(io.BytesIO(raw_bytes), encoding=encoding)

            st.write(f"資料筆數: {df_raw.shape[0]} 筆，欄位數: {df_raw.shape[1]} 欄")
            st.dataframe(df_raw, use_container_width=True)

            # 儲存原始資料
            st.session_state['df_raw_dict'][uploaded_file.name] = df_raw

            # 複製一份並 LabelEncoder 編碼
            df = df_raw.copy()
            cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            if cat_cols:
                le = LabelEncoder()
                for col in cat_cols:
                    try:
                        df[col] = le.fit_transform(df[col].astype(str))
                    except Exception as e:
                        st.warning(f"欄位 '{col}' 編碼失敗：{e}")

            # 儲存編碼後資料與相關係數
            st.session_state['df_dict'][uploaded_file.name] = df
            corr = df.corr()
            st.session_state['corr_dict'][uploaded_file.name] = corr
            st.session_state['has_data'] = True

# ---- tab2: Gemini 聊天 ----
with tab2:
    st.header("Gemini")
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    chat = genai.ChatSession(model=model)

    user_input = st.text_input("請輸入問題")
    if user_input:
        response = chat.send_message(user_input)
        st.markdown(f"Gemini 回答: {response.text}")

# ---- tab3: 資料欄位統計 ----
with tab3:
    st.header("資料欄位統計")

    if st.session_state.get('df_raw_dict'):
        file_options = list(st.session_state['df_raw_dict'].keys())
        selected_file = st.selectbox("選擇要分析的檔案", file_options)

        df_raw = st.session_state['df_raw_dict'][selected_file]

        selected_col = st.selectbox("資料欄位統計:選擇欄位查看比例分佈", df_raw.columns.tolist())

        value_counts = df_raw[selected_col].value_counts(dropna=False)
        percentages = value_counts / value_counts.sum() * 100

        result_df = pd.DataFrame({
            selected_col: value_counts.index,
            '數量': value_counts.values,
            '百分比 (%)': percentages.round(2)
        })

        st.write(result_df)

        fig = px.pie(
            result_df,
            names=selected_col,
            values='數量',
            title=f"{selected_col} 分佈圓餅圖",
            hole=0.3
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("請先上傳 CSV 檔案")

# ---- tab4: 相關係數分析 ----
with tab4:
    st.header("相關係數分析")

    if st.session_state.get('has_data', False):
        file_options = list(st.session_state['corr_dict'].keys())
        selected_file = st.selectbox("相關係數分析:選擇要分析的檔案", file_options)

        corr = st.session_state['corr_dict'][selected_file]

        st.write(f"檔案 {selected_file} 的相關係數矩陣")
        st.dataframe(corr, use_container_width=True)

        st.write("相關係數熱力圖 (Plotly)")
        fig = px.imshow(
            corr,
            text_auto=True,
            color_continuous_scale='RdBu_r',
            zmin=-1, zmax=1,
            aspect="auto"
        )
        st.plotly_chart(fig, use_container_width=True)

        cols = corr.columns.tolist()
        col1 = st.selectbox("選擇欄位1", cols)
        col2 = st.selectbox("選擇欄位2", [c for c in cols if c != col1])

        if col1 and col2:
            val = corr.loc[col1, col2]
            st.write(f"{col1} 與 {col2} 的相關係數是：{val:.3f}")
            threshold = 0.5
            if val >= threshold:
                st.success("判斷：正相關")
            elif val <= -threshold:
                st.error("判斷：負相關")
            else:
                st.info("判斷：無明顯相關")
    else:
        st.info("請先上傳並分析 CSV 檔案")
