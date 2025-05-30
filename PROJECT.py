import streamlit as st
import google.generativeai as genai

genai.configure(api_key="AIzaSyAP7BSVTOBJo2CDpincq7dAlTmDG4Ix5c0")

st.title("Gemini Chatbot")

model = genai.GenerativeModel("models/gemini-1.5-flash")
chat = genai.ChatSession(model=model)

user_input = st.text_input("請輸入問題")

if user_input:
    response = chat.send_message(user_input)
    st.write(response.text)
