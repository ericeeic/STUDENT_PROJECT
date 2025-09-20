import streamlit as st
import requests
import math
import folium
from streamlit.components.v1 import html

st.title("🏠 房屋比較 + Google Places 雙地圖 + 顏色標記 + 半徑顯示")

# ===============================
# Google Places 類別
# ===============================
PLACE_TYPES = {
    "交通": ["bus_station", "subway_station", "train_station"],
    "超商": ["convenience_store"],
    "餐廳": ["restaurant", "cafe"],
    "學校": ["school", "university", "primary_school", "secondary_school"],
    "醫院": ["hospital"],
    "藥局": ["pharmacy"],
}

CATEGORY_COLORS = {
    "交通": "#800080",
    "超商": "#FF8C00",
    "餐廳": "#FF0000",
    "學校": "#1E90FF",
    "醫院": "#32CD32",
    "藥局": "#008080",
    "關鍵字": "#000000"
}

# ===============================
# 工具函式
# ===============================
def geocode_address(address: str, api_key: str):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key, "language": "zh-TW"}
    r = requests.get(url, params=params, timeout=10).json()
    if r.get("status") == "OK" and r["results"]:
        loc = r["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    return None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(d_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def query_google_places(lat, lng, api_key, selected_categories, keyword="", radius=500):
    results = {k: [] for k in selected_categories}
    if keyword:
        results["關鍵字"] = []
    for label in selected_categories:
        for t in PLACE_TYPES[label]:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": f"{lat},{lng}",
                "radius": radius,
                "type": t,
                "keyword": keyword if keyword else "",
                "language": "zh-TW",
                "key": api_key,
            }
            r = requests.get(url, params=params, timeout=10).json()
            for place in r.get("results", []):
                p_lat = place["geometry"]["location"]["lat"]
                p_lng = place["geometry"]["location"]["lng"]
                dist = int(haversine(lat, lng, p_lat, p_lng))
                results[label].append((place.get("name", "未命名"), p_lat, p_lng, dist))
    # 關鍵字單獨搜尋
    if keyword and "關鍵字" in results:
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {"location": f"{lat},{lng}", "radius": radius, "keyword": keyword, "key": api_key, "language": "zh-TW"}
        r = requests.get(url, params=params, timeout=10).json()
        for place in r.get("results", []):
            p_lat = place["geometry"]["location"]["lat"]
            p_lng = place["geometry"]["location"]["lng"]
            dist = int(haversine(lat, lng, p_lat, p_lng))
            results["關鍵字"].append((place.get("name", "未命名"), p_lat, p_lng, dist))
    return results

def add_markers(m, info_dict):
    for category, places in info_dict.items():
        color = CATEGORY_COLORS.get(category, "#000000")
        for name, lat, lng, dist in places:
            folium.Marker(
                [lat, lng],
                popup=f"{category}：{name}（{dist} 公尺）",
                icon=folium.Icon(color="blue", icon="info-sign")  # folium Icon 顏色固定，可用 CircleMarker 改顏色
            ).add_to(m)
            folium.CircleMarker(
                location=[lat, lng],
                radius=6,
                color=color,
                fill=True,
                fill_opacity=0.8
            ).add_to(m)

# ===============================
# Streamlit 介面
# ===============================
google_key = st.text_input("🔑 輸入 Google Maps API Key", type="password")

if google_key:
    col1, col2 = st.columns(2)
    with col1:
        addr_a = st.text_input("房屋 A 地址")
    with col2:
        addr_b = st.text_input("房屋 B 地址")

    radius = st.slider("搜尋半徑 (公尺)", 100, 2000, 500, 50)
    keyword = st.text_input("關鍵字搜尋（可留空）")

    st.subheader("選擇生活機能類別")
    selected_categories = []
    cols = st.columns(len(PLACE_TYPES))
    for i, cat in enumerate(PLACE_TYPES.keys()):
        color = CATEGORY_COLORS[cat]
        with cols[i]:
            st.markdown(
                f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{color};margin-right:4px"></span>',
                unsafe_allow_html=True
            )
            if st.checkbox(cat, key=f"cat_{cat}", value=True):
                selected_categories.append(cat)

    if st.button("比較房屋"):
        if not addr_a or not addr_b:
            st.warning("請輸入兩個地址")
            st.stop()
        if not selected_categories and not keyword:
            st.warning("請至少選擇一個類別或輸入關鍵字")
            st.stop()

        lat_a, lng_a = geocode_address(addr_a, google_key)
        lat_b, lng_b = geocode_address(addr_b, google_key)
        if not lat_a or not lat_b:
            st.error("❌ 無法解析其中一個地址")
            st.stop()

        info_a = query_google_places(lat_a, lng_a, google_key, selected_categories, keyword, radius)
        info_b = query_google_places(lat_b, lng_b, google_key, selected_categories, keyword, radius)

        # 房屋 A 地圖
        st.subheader("📍 房屋 A 周邊地圖")
        m_a = folium.Map(location=[lat_a, lng_a], zoom_start=15)
        folium.Marker([lat_a, lng_a], popup=f"房屋 A：{addr_a}", icon=folium.Icon(color="red", icon="home")).add_to(m_a)
        folium.Circle([lat_a, lng_a], radius=radius, color="red", fill=True, fill_opacity=0.1).add_to(m_a)
        add_markers(m_a, info_a)
        html(m_a._repr_html_(), height=400)

        # 房屋 B 地圖
        st.subheader("📍 房屋 B 周邊地圖")
        m_b = folium.Map(location=[lat_b, lng_b], zoom_start=15)
        folium.Marker([lat_b, lng_b], popup=f"房屋 B：{addr_b}", icon=folium.Icon(color="blue", icon="home")).add_to(m_b)
        folium.Circle([lat_b, lng_b], radius=radius, color="blue", fill=True, fill_opacity=0.1).add_to(m_b)
        add_markers(m_b, info_b)
        html(m_b._repr_html_(), height=400)
