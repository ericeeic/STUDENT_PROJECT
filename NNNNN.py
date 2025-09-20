import streamlit as st
import requests
import math
import folium
from streamlit.components.v1 import html
import google.generativeai as genai

# ===============================
# Google Places 類別
# ===============================
# 房屋比較用
PLACE_TYPES_COMPARE = {
    "交通": ["bus_stop", "subway_station", "train_station"],
    "超商": ["convenience_store"],
    "餐廳": ["restaurant", "cafe"],
    "學校": ["school", "university", "primary_school", "secondary_school"],
    "醫院": ["hospital"],
    "藥局": ["pharmacy"],
}

# 周邊查詢用
PLACE_TYPES_SEARCH = {
    "教育": ["圖書館", "幼兒園", "小學", "學校", "中學", "大學"],
    "健康與保健": ["牙醫", "醫師", "藥局", "醫院"],
    "購物": ["便利商店", "超市", "百貨公司"],
    "交通運輸": ["公車站", "地鐵站", "火車站"],
    "餐飲": ["餐廳"]
}

# 標記顏色
CATEGORY_COLORS = {
    "教育": "#1E90FF",
    "健康與保健": "#32CD32",
    "購物": "#FF8C00",
    "交通運輸": "#800080",
    "餐飲": "#FF0000",
    "關鍵字": "#000000"
}

# ===============================
# 工具函式
# ===============================
def geocode_address(address: str, api_key: str):
    """將地址轉換為經緯度"""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key, "language": "zh-TW"}
    r = requests.get(url, params=params, timeout=10).json()
    if r.get("status") == "OK" and r["results"]:
        loc = r["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    return None, None

def haversine(lat1, lon1, lat2, lon2):
    """計算兩點間的球面距離（公尺）"""
    R = 6371000
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def query_google_places_by_type(lat, lng, api_key, selected_categories, radius=500):
    """根據 Places API 的 type 參數查詢（房屋比較用）"""
    results = {k: [] for k in selected_categories}
    for label in selected_categories:
        for t in PLACE_TYPES_COMPARE[label]:
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
    """將查詢結果格式化為文字"""
    lines = [f"房屋（{address}）："]
    for k, v in info_dict.items():
        lines.append(f"- {k}: {len(v)} 個")
    return "\n".join(lines)

def add_markers(m, info_dict, color):
    """在 Folium 地圖上添加標記"""
    for category, places in info_dict.items():
        for name, lat, lng, dist in places:
            folium.Marker(
                [lat, lng],
                popup=f"{category}：{name}（{dist} 公尺）",
                icon=folium.Icon(color=color, icon="info-sign"),
            ).add_to(m)

def query_google_places_by_keyword(lat, lng, api_key, selected_categories, keyword, radius):
    """根據 Places API 的 keyword 參數查詢（周邊查詢用）"""
    all_places = []

    for cat in selected_categories:
        for kw in PLACE_TYPES_SEARCH[cat]:
            params = {
                "location": f"{lat},{lng}",
                "radius": radius,
                "keyword": kw + (f" {keyword}" if keyword else ""),
                "key": api_key,
                "language": "zh-TW"
            }
            res = requests.get("https://maps.googleapis.com/maps/api/place/nearbysearch/json", params=params).json()
            for p in res.get("results", []):
                p_lat = p["geometry"]["location"]["lat"]
                p_lng = p["geometry"]["location"]["lng"]
                dist = int(haversine(lat, lng, p_lat, p_lng))
                if dist <= radius:
                    all_places.append((cat, kw, p.get("name", "未命名"), p_lat, p_lng, dist, p.get("place_id", "")))

    if keyword and not selected_categories:
        params = {
            "location": f"{lat},{lng}",
            "radius": radius,
            "keyword": keyword,
            "key": api_key,
            "language": "zh-TW"
        }
        res = requests.get("https://maps.googleapis.com/maps/api/place/nearbysearch/json", params=params).json()
        for p in res.get("results", []):
            p_lat = p["geometry"]["location"]["lat"]
            p_lng = p["geometry"]["location"]["lng"]
            dist = int(haversine(lat, lng, p_lat, p_lng))
            if dist <= radius:
                all_places.append(("關鍵字", keyword, p.get("name", "未命名"), p_lat, p_lng, dist, p.get("place_id", "")))
    
    return all_places


def render_map_with_markers(lat, lng, api_key, all_places, radius):
    """渲染帶有標記的 Google Maps"""
    markers_js = ""
    for cat, kw, name, p_lat, p_lng, dist, pid in all_places:
        color = CATEGORY_COLORS.get(cat, "#000000")
        gmap_url = f"https://www.google.com/maps/place/?q=place_id:{pid}" if pid else ""
        info = f'[{cat}-{kw}]: <a href="{gmap_url}" target="_blank">{name}</a><br>距離中心 {dist} 公尺'
        markers_js += f"""
        new google.maps.Marker({{
            position: {{lat: {p_lat}, lng: {p_lng}}},
            map: map,
            title: "{cat}-{name}",
            icon: {{
                path: google.maps.SymbolPath.CIRCLE,
                scale: 7,
                fillColor: "{color}",
                fillOpacity: 1,
                strokeColor: "white",
                strokeWeight: 1
            }}
        }}).addListener("click", function() {{
            new google.maps.InfoWindow({{content: `{info}`}}).open(map, this);
        }});
        """
    
    circle_js = f"""
        new google.maps.Circle({{
            strokeColor: "#FF0000",
            strokeOpacity: 0.8,
            strokeWeight: 2,
            fillColor: "#FF0000",
            fillOpacity: 0.1,
            map: map,
            center: center,
            radius: {radius}
        }});
    """

    map_html = f"""
    <div id="map" style="height:500px;"></div>
    <script>
    function initMap() {{
        var center = {{lat: {lat}, lng: {lng}}};
        var map = new google.maps.Map(document.getElementById('map'), {{
            zoom: 16,
            center: center
        }});
        new google.maps.Marker({{
            position: center,
            map: map,
            title: "查詢中心",
            icon: {{ url: "http://maps.google.com/mapfiles/ms/icons/red-dot.png" }}
        }});
        {circle_js}
        {markers_js}
    }}
    </script>
    <script async defer src="https://maps.googleapis.com/maps/api/js?key={api_key}&callback=initMap"></script>
    """
    html(map_html, height=500)

# ===============================
# Streamlit 介面
# ===============================
st.set_page_config(layout="wide", page_title="🏠 房屋生活機能查詢與比較")

st.title("🏠 房屋生活機能查詢與比較")

# API Key 輸入區
with st.sidebar:
    st.header("🔑 API Key 設定")
    google_key = st.text_input("Google Maps API Key", type="password")
    gemini_key = st.text_input("Gemini API Key", type="password")

if not google_key or not gemini_key:
    st.info("請先在左側欄位輸入 Google Maps 與 Gemini API Key")
    st.stop()
else:
    genai.configure(api_key=gemini_key)

# 功能選擇
option = st.sidebar.radio(
    "選擇功能",
    ("房屋比較與分析", "單一地址周邊查詢")
)

if option == "房屋比較與分析":
    st.header("🏠 房屋比較 + 雙地圖 + Gemini 分析")
    col1, col2 = st.columns(2)
    with col1:
        addr_a = st.text_input("房屋 A 地址")
    with col2:
        addr_b = st.text_input("房屋 B 地址")

    radius = st.slider("搜尋半徑 (公尺)", min_value=100, max_value=2000, value=500, step=50)

    st.subheader("選擇要比較的生活機能類別")
    selected_categories = []
    cols = st.columns(3)
    for idx, cat in enumerate(PLACE_TYPES_COMPARE.keys()):
        if cols[idx % 3].checkbox(cat, value=True):
            selected_categories.append(cat)

    if st.button("比較房屋", use_container_width=True):
        if not addr_a or not addr_b:
            st.warning("請輸入兩個地址")
            st.stop()
        if not selected_categories:
            st.warning("請至少選擇一個類別")
            st.stop()

        with st.spinner("正在查詢並分析..."):
            lat_a, lng_a = geocode_address(addr_a, google_key)
            lat_b, lng_b = geocode_address(addr_b, google_key)
            if not lat_a or not lat_b:
                st.error("❌ 無法解析其中一個地址，請檢查地址是否正確。")
                st.stop()

            info_a = query_google_places_by_type(lat_a, lng_a, google_key, selected_categories, radius=radius)
            info_b = query_google_places_by_type(lat_b, lng_b, google_key, selected_categories, radius=radius)

            text_a = format_info(addr_a, info_a)
            text_b = format_info(addr_b, info_b)
            
            st.subheader("📍 房屋 A 周邊地圖")
            m_a = folium.Map(location=[lat_a, lng_a], zoom_start=15)
            folium.Marker([lat_a, lng_a], popup=f"房屋 A：{addr_a}", icon=folium.Icon(color="red", icon="home")).add_to(m_a)
            add_markers(m_a, info_a, "red")
            html(m_a._repr_html_(), height=400)

            st.subheader("📍 房屋 B 周邊地圖")
            m_b = folium.Map(location=[lat_b, lng_b], zoom_start=15)
            folium.Marker([lat_b, lng_b], popup=f"房屋 B：{addr_b}", icon=folium.Icon(color="blue", icon="home")).add_to(m_b)
            add_markers(m_b, info_b, "blue")
            html(m_b._repr_html_(), height=400)

            prompt = f"""你是一位房地產分析專家，請比較以下兩間房屋的生活機能，
            並列出優缺點與結論：
            {text_a}
            {text_b}
            """
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)

            st.subheader("📊 Gemini 分析結果")
            st.markdown(response.text)

            st.sidebar.subheader("🏠 房屋資訊對照表")
            st.sidebar.markdown(f"**房屋 A**\n{text_a}")
            st.sidebar.markdown(f"**房屋 B**\n{text_b}")

elif option == "單一地址周邊查詢":
    st.header("🔍 單一地址周邊查詢")
    address = st.text_input("輸入地址")
    radius = st.slider("選擇搜尋半徑 (公尺)", min_value=100, max_value=2000, value=500, step=50)
    keyword = st.text_input("輸入關鍵字 (選填)")

    st.subheader("選擇大類別")
    selected_categories = []
    cols = st.columns(len(PLACE_TYPES_SEARCH))
    for i, cat in enumerate(PLACE_TYPES_SEARCH.keys()):
        color = CATEGORY_COLORS[cat]
        with cols[i]:
            st.markdown(
                f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{color};margin-right:4px"></span>',
                unsafe_allow_html=True,
            )
            if st.toggle(cat, key=f"cat_{cat}"):
                selected_categories.append(cat)

    if st.button("開始查詢", use_container_width=True):
        if not address:
            st.error("請輸入地址")
            st.stop()
        if not selected_categories and not keyword:
            st.error("請至少選擇一個大類別或輸入關鍵字")
            st.stop()
        
        with st.spinner("正在查詢..."):
            lat, lng = geocode_address(address, google_key)
            if not lat:
                st.error("無法解析該地址")
                st.stop()
            
            all_places = query_google_places_by_keyword(lat, lng, google_key, selected_categories, keyword, radius)
            all_places.sort(key=lambda x: x[5])

            st.subheader("📍 查詢結果地圖")
            render_map_with_markers(lat, lng, google_key, all_places, radius)

            st.subheader("📝 查詢結果列表")
            if not all_places:
                st.write("範圍內無符合地點。")
            else:
                for cat, kw, name, _, _, dist, _ in all_places:
                    st.markdown(f"**<span style='color:{CATEGORY_COLORS.get(cat, 'black')};'>[{cat}]</span>** {kw} - {name} ({dist} 公尺)", unsafe_allow_html=True)
