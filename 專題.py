import streamlit as st
import pandas as pd
import google.generativeai as genai
genai.configure(api_key="AIzaSyAP7BSVTOBJo2CDpincq7dAlTmDG4Ix5c0")
CSV1 = st.file_uploader("FILE:", accept_multiple_files=True,type=['csv','txt','jpg','png'])
for i in CSV1:
   if i.name.endswith(('.jpg', '.jpeg', '.png')):
       st.write("filename:", i.name)
       st.image(i)
   elif i.name.endswith(('.csv','.txt')):
       st.write("filename:", i.name)
       x=pd.read_csv(i ,encoding="BIG5")
       st.dataframe(x)
st.title("Gemini")

model = genai.GenerativeModel("models/gemini-1.5-flash")
chat = genai.ChatSession(model=model)

user_input = st.text_input("請輸入問題")

if user_input:
    response = chat.send_message(user_input)
    st.write(response.text)