import streamlit as st
import google.generativeai as genai
import pandas as pd
import chardet
genai.configure(api_key="AIzaSyAP7BSVTOBJo2CDpincq7dAlTmDG4Ix5c0")
st.title("Gemini Chatbot")
model = genai.GenerativeModel("models/gemini-1.5-flash")
chat = genai.ChatSession(model=model)
user_input = st.text_input("請輸入問題")
if user_input:
    response = chat.send_message(user_input)
    st.write(response.text)
    
    
    
    
CSV1 = st.file_uploader("上傳檔案:", accept_multiple_files=True, type=['csv', 'txt', 'jpg', 'png'])

if CSV1:
    for i in CSV1:
        st.write("檔名:", i.name)

        if i.name.endswith(('.jpg', '.jpeg', '.png')):
            st.image(i)
        elif i.name.endswith(('.csv', '.txt')):
            # 讀取檔案內容並偵測編碼
            file_contents = i.read()
            encoding_result = chardet.detect(file_contents)['encoding']
            i.seek(0)  # 重置指標
            df = pd.read_csv(i, encoding=encoding_result)
            st.dataframe(df)
   