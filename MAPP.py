import streamlit as st
import requests
import math
from streamlit.components.v1 import html

st.title("地址周邊查詢（多類別按鈕 + 彩色標記）")

# Google Maps API Key 與地址
google_api_key = st.text_input("輸入 Google Maps API Key", type="password")
address = st.text_input("輸入地址")

# 半徑
radius = st.slider("選擇搜尋半徑 (公尺)", min_value=200, max_value=600, value=400, step=50)

# 關鍵字
keyword = st.text_input("輸入關鍵字")

# 大類別與子類別（只用關鍵字搜尋，不用 type）
PLACE_TYPES = {
    "教育": ["圖書館", "幼兒園", "小學", "學校", "中學", "大學"],
    "健康與保健": ["牙醫", "醫師", "藥局", "醫院"],
    "購物": ["便利商店", "超市", "百貨公司"],
    "交通運輸": ["公車站", "地鐵站", "火車站"],
    "餐飲": ["餐廳"]
}

# 每個大類別對應不同顏色
CATEGORY_COLORS = {
    "教育": "#1E90FF",         # 藍
    "健康與保健": "#32CD32",    # 綠
    "購物": "#FF8C00",         # 橘
    "交通運輸": "#800080",     # 紫
    "餐飲": "#FF0000"          # 紅
}

# ====== 按鈕式多選 ======
st.subheader("選擇大類別（可多選）")
selected_categories = []
cols = st.columns(len(PLACE_TYPES))
for i, cat in enumerate(PLACE_TYPES.keys()):
    if cols[i].toggle(cat, key=f"cat_{cat}"):
        selected_categories.append(cat)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(d_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def search_places():
    if not google_api_key:
        st.error("請先輸入 Google Maps API Key")
        return
    if not address:
        st.error("請輸入地址")
        return
    if not selected_categories and not keyword:
        st.error("請至少選擇一個大類別或輸入關鍵字")
        return

    # 轉換地址為座標
    geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
    geo_res = requests.get(geo_url, params={"address": address, "key": google_api_key, "language": "zh-TW"}).json()
    if geo_res.get("status") != "OK":
        st.error("無法解析該地址")
        return

    lat, lng = geo_res["results"][0]["geometry"]["location"].values()
    all_places = []

    # 依每個大類別與其子關鍵字查詢
    for cat in selected_categories:
        for kw in PLACE_TYPES[cat]:
            places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": f"{lat},{lng}",
                "radius": radius,
                "keyword": kw,
                "key": google_api_key,
                "language": "zh-TW"
            }
            if keyword:
                params["keyword"] += f" {keyword}"
            res = requests.get(places_url, params=params).json()
            for p in res.get("results", []):
                name = p.get("name", "未命名")
                p_lat = p["geometry"]["location"]["lat"]
                p_lng = p["geometry"]["location"]["lng"]
                dist = int(haversine(lat, lng, p_lat, p_lng))
                pid = p.get("place_id", "")
                if dist <= radius:
                    all_places.append((cat, kw, name, p_lat, p_lng, dist, pid))

    # 如果只輸入關鍵字（沒有選大類別）
    if keyword and not selected_categories:
        places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            "location": f"{lat},{lng}",
            "radius": radius,
            "keyword": keyword,
            "key": google_api_key,
            "language": "zh-TW"
        }
        res = requests.get(places_url, params=params).json()
        for p in res.get("results", []):
            name = p.get("name", "未命名")
            p_lat = p["geometry"]["location"]["lat"]
            p_lng = p["geometry"]["location"]["lng"]
            dist = int(haversine(lat, lng, p_lat, p_lng))
            pid = p.get("place_id", "")
            if dist <= radius:
                all_places.append(("關鍵字", keyword, name, p_lat, p_lng, dist, pid))

    all_places.sort(key=lambda x: x[5])

    st.write(f"目前搜尋半徑：{radius} 公尺")
    st.subheader("查詢結果")
    if not all_places:
        st.write("範圍內無符合地點。")
        return

    # 清單
    for cat, kw, name, _, _, dist, _ in all_places:
        st.write(f"**[{cat}]** {kw} - {name} ({dist} 公尺)")

    # 側邊欄
    st.sidebar.subheader("Google 地圖連結")
    for cat, kw, name, _, _, dist, pid in all_places:
        if pid:
            st.sidebar.markdown(f"- [{name} ({dist}m)](https://www.google.com/maps/place/?q=place_id:{pid})")

    # 地圖標記
    markers_js = ""
    for cat, kw, name, p_lat, p_lng, dist, pid in all_places:
        gmap_url = f"https://www.google.com/maps/place/?q=place_id:{pid}" if pid else ""
        info = f'{cat}-{kw}: <a href="{gmap_url}" target="_blank">{name}</a><br>距離中心 {dist} 公尺'
        color = CATEGORY_COLORS.get(cat, "#000000")
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
    <script src="https://maps.googleapis.com/maps/api/js?key={google_api_key}&callback=initMap" async defer></script>
    """
    html(map_html, height=500)

# 查詢按鈕
if st.button("開始查詢", use_container_width=True):
    search_places()
