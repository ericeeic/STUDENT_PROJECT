import streamlit as st
import requests
import folium
import time
from streamlit_folium import st_folium

# 支援類別 (OSM tag)
PLACE_TAGS = {
    "交通": '["public_transport"="stop_position"]',
    "醫院": '["amenity"="hospital"]',
    "超商": '["shop"="convenience"]',
    "餐廳": '["amenity"="restaurant"]',
    "學校": '["amenity"="school"]'
}

st.set_page_config(page_title="周邊地點查詢 (OSM)", layout="wide")
st.title("🌍 地址周邊400公尺地點查詢 (OpenStreetMap)")

# 初始化 Session State
if 'all_places' not in st.session_state:
    st.session_state['all_places'] = []
if 'map' not in st.session_state:
    st.session_state['map'] = None

address = st.text_input("輸入地址", "台北101")
selected_types = st.multiselect("選擇要查詢的類別", PLACE_TAGS.keys(), default=["超商", "交通"])

if st.button("查詢"):
    # 暫停 1 秒，避免被 Nominatim 封鎖
    time.sleep(1)

    # Nominatim 地址轉經緯度
    geo_url = f"https://nominatim.openstreetmap.org/search?format=json&q={address}"
    headers = {
        "User-Agent": "StreamlitApp/1.0 (your_email@example.com)",
        "From": "your_email@example.com"
    }
    
    try:
        geo_res = requests.get(geo_url, headers=headers, timeout=10).json()
    except requests.exceptions.RequestException as e:
        st.error(f"無法連線到 Nominatim: {e}")
        geo_res = None

    if geo_res:
        lat, lng = float(geo_res[0]["lat"]), float(geo_res[0]["lon"])
        
        # 建立 Folium 地圖
        m = folium.Map(location=[lat, lng], zoom_start=16)
        folium.Marker([lat, lng], popup="查詢中心", icon=folium.Icon(color="red")).add_to(m)
        
        all_places = []

        for t in selected_types:
            tag = PLACE_TAGS[t]
            overpass_query = f"""
            [out:json];
            (
              node{tag}(around:400,{lat},{lng});
              way{tag}(around:400,{lat},{lng});
              relation{tag}(around:400,{lat},{lng});
            );
            out center;
            """
            try:
                res = requests.post("https://overpass-api.de/api/interpreter",
                                    data=overpass_query.encode("utf-8"),
                                    headers=headers,
                                    timeout=20)
                data = res.json()
            except requests.exceptions.RequestException as e:
                st.warning(f"無法查詢 {t} 類別: {e}")
                continue

            for el in data.get("elements", []):
                # 使用 node 或 center
                lat_el = el.get("lat") or el.get("center", {}).get("lat")
                lon_el = el.get("lon") or el.get("center", {}).get("lon")
                if lat_el and lon_el:
                    name = el.get("tags", {}).get("name", "未命名")
                    all_places.append((t, name))
                    folium.Marker(
                        [lat_el, lon_el],
                        popup=f"{t}: {name}",
                        icon=folium.Icon(color="blue" if t != "醫院" else "green")
                    ).add_to(m)

        # 儲存結果到 Session State
        st.session_state['all_places'] = all_places
        st.session_state['map'] = m
    else:
        st.error("無法解析該地址，請確認輸入正確。")

# 顯示查詢結果
if st.session_state.get('all_places'):
    st.subheader("查詢結果")
    for t, name in st.session_state['all_places']:
        st.write(f"**{t}** - {name}")

if st.session_state.get('map'):
    st_folium(st.session_state['map'], width=700, height=500)
