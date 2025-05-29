import streamlit as st
import pandas as pd
CSV1 = st.file_uploader("CSV:", accept_multiple_files=True)
for i in CSV1:
   st.write("filename:", i.name)
   x=pd.read_csv(i ,encoding="BIG5")
   st.dataframe(x)
   
   
   