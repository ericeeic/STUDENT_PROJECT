import streamlit as st
import pandas as pd
CSV1 = st.file_uploader("CSV:", accept_multiple_files=True,type=['csv','txt','jpg','png'])
for i in CSV1:
   if i.name.endswith(('.jpg', '.jpeg', '.png')):
       st.write("filename:", i.name)
       st.image(i)
   elif i.name.endswith(('.csv','.txt')):
       st.write("filename:", i.name)
       x=pd.read_csv(i ,encoding="BIG5")
       st.dataframe(x)
      
