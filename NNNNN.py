import streamlit as st
import requests
import math
import folium
from streamlit.components.v1 import html
import google.generativeai as genai

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
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def query_google_places(lat, lng, api_key, radius=500):
    results = {k: [] for k in PLACE_TYPES.keys()}
    for label, types in PLACE_TYPES.items():
        for t in types:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": f"{lat},{lng}",
                "radius": radius,
                "type": t,
                "language": "zh-TW",
                "key": api_key,
            }
            r = requests.get(url, params=params, timeout=10).json()
            for place in r.get("results", []):
                name = place.get("name", "未命名")
                p_lat = place["geometry"]["location"]["lat"]
                p_lng = place["geometry"]["location"]["lng"]
                dist = int(haversine(lat, lng, p_lat, p_lng))
                results[label].append((name, p_lat, p_lng, dist))
    return results

def format_info(address, info_dict):
    lines = [f"房屋（{address}）："]
    for k, v in info_dict.items():
        lines.append(f"- {k}: {len(v)} 個")
    return "\n".join(lines)

def add_markers(m, info_dict, color):
    for category, places in info_dict.items():
        for name, lat, lng, dist in places:
            folium.Marker(
                [lat, lng],
                popup=f"{category}：{name}（{dist} 公尺）",
                icon=folium.Icon(color=color, icon="info-sign"),
            ).add_to(m)

# ===============================
# Streamlit 介面
# ===============================
st.title("🏠 房屋比較 + Google Places 地圖 + Gemini 分析")

google_key = st.text_input("🔑 輸入 Google Maps API Key", type="password")
gemini_key = st.text_input("🔑 輸入 Gemini API Key", type="password")

if google_key and gemini_key:
    genai.configure(api_key=gemini_key)

    col1, col2 = st.columns(2)
    with col1:
        addr_a = st.text_input("房屋 A 地址")
    with col2:
        addr_b = st.text_input("房屋 B 地址")

    # ✅ 改成可拉動的連續滑條
    radius = st.slider("搜尋半徑 (公尺)", min_value=100, max_value=2000, value=500, step=50)

    if st.button("比較房屋"):
        if not addr_a or not addr_b:
            st.warning("請輸入兩個地址")
            st.stop()

        lat_a, lng_a = geocode_address(addr_a, google_key)
        lat_b, lng_b = geocode_address(addr_b, google_key)
        if not lat_a or not lat_b:
            st.error("❌ 無法解析其中一個地址")
            st.stop()

        info_a = query_google_places(lat_a, lng_a, google_key, radius=radius)
        info_b = query_google_places(lat_b, lng_b, google_key, radius=radius)

        text_a = format_info(addr_a, info_a)
        text_b = format_info(addr_b, info_b)

        st.subheader("📍 地圖顯示")
        center_lat = (lat_a + lat_b) / 2
        center_lng = (lng_a + lng_b) / 2
        m = folium.Map(location=[center_lat, center_lng], zoom_start=15)

        # 房屋位置
        folium.Marker(
            [lat_a, lng_a],
            popup=f"房屋 A：{addr_a}",
            icon=folium.Icon(color="red", icon="home"),
        ).add_to(m)
        folium.Marker(
            [lat_b, lng_b],
            popup=f"房屋 B：{addr_b}",
            icon=folium.Icon(color="blue", icon="home"),
        ).add_to(m)

        add_markers(m, info_a, "red")
        add_markers(m, info_b, "blue")

        html(m._repr_html_(), height=500)

        # Gemini 分析
        prompt = f"""你是一位房地產分析專家，請比較以下兩間房屋的生活機能，
        並列出優缺點與結論：
        {text_a}
        {text_b}
        """
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        st.subheader("📊 Gemini 分析結果")
        st.write(response.text)

        st.sidebar.subheader("🏠 房屋資訊對照表")
        st.sidebar.markdown(f"### 房屋 A\n{text_a}")
        st.sidebar.markdown(f"### 房屋 B\n{text_b}")
else:
    st.info("請先輸入 Google Maps 與 Gemini API Key")
