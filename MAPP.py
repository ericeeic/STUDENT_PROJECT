import streamlit as st
import requests
import folium
import time
from streamlit.components.v1 import html

PLACE_TAGS = {
    "交通": '["public_transport"="stop_position"]',
    "醫院": '["amenity"="hospital"]',
    "超商": '["shop"="convenience"]',
    "餐廳": '["amenity"="restaurant"]',
    "學校": '["amenity"="school"]'
}

st.title("🌍 地址周邊400公尺查詢 (OSM)")

address = st.text_input("輸入地址", "台北101")
selected_types = st.multiselect("選擇要查詢的類別", PLACE_TAGS.keys(), default=["超商", "交通"])

if st.button("查詢"):
    # 暫停 1 秒，避免被 Nominatim 封鎖
    time.sleep(1)

    geo_url = f"https://nominatim.openstreetmap.org/search?format=json&q={address}"
    headers = {
        "User-Agent": "StreamlitApp/1.0 (your_email@example.com)",  # 官方建議包含 App 名稱和 email
        "From": "your_email@example.com"
    }
    
    try:
        geo_res = requests.get(geo_url, headers=headers, timeout=10).json()
    except requests.exceptions.RequestException as e:
        st.error(f"無法連線到 Nominatim: {e}")
        geo_res = None
    
    if geo_res:
        lat, lng = float(geo_res[0]["lat"]), float(geo_res[0]["lon"])
        
        m = folium.Map(location=[lat, lng], zoom_start=16)
        folium.Marker([lat, lng], popup="查詢中心", icon=folium.Icon(color="red")).add_to(m)
        
        all_places = []
        for t in selected_types:
            tag = PLACE_TAGS[t]
            query = f"""
            [out:json];
            (
              node{tag}(around:400,{lat},{lng});
              way{tag}(around:400,{lat},{lng});
              relation{tag}(ar
