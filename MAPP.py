import streamlit as st
import requests
import math
from streamlit.components.v1 import html

st.title("地址周邊查詢（多分類 + 不同標記顏色）")

# Google Maps API Key 與地址
google_api_key = st.text_input("輸入 Google Maps API Key", type="password")
address = st.text_input("輸入地址")

# 半徑用滑桿控制
radius = st.slider("選擇搜尋半徑 (公尺)", min_value=200, max_value=600, value=400, step=50)

# 自訂額外關鍵字
keyword = st.text_input("額外關鍵字（可選）")

# 分類 + 子類別
PLACE_TYPES = {
    "教育": ["圖書館", "幼兒園", "小學", "學校", "中學", "大學"],
    "健康與保健": ["牙醫", "醫師", "藥局", "醫院"],
    "購物": ["便利商店", "超市", "百貨公司"],
    "交通運輸": ["公車站", "地鐵站", "火車站"],
    "餐飲": ["餐廳"]
}

# 為每個大類別指定標記顏色 (Google Maps 預設 icon 顏色)
CATEGORY_COLORS = {
    "教育": "blue",
    "健康與保健": "green",
    "購物": "orange",
    "交通運輸": "purple",
    "餐飲": "yellow"
}

# ✅ 允許多選
selected_categories = st.multiselect(
    "選擇要搜尋的大類別（可複選）",
    list(PLACE_TYPES.keys())
)


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

    # 地址轉經緯度
    geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
    geo_params = {"address": address, "key": google_api_key, "language": "zh-TW"}
    geo_res = requests.get(geo_url, params=geo_params).json()
    if geo_res.get("status") != "OK":
        st.error("無法解析該地址")
        return

    location = geo_res["results"][0]["geometry"]["location"]
    lat, lng = location["lat"], location["lng"]

    all_places = []

    # 依照每個選中的大類別進行關鍵字搜尋
    for cat in selected_categories:
        sub_keywords = PLACE_TYPES[cat]
        cat_kw = " OR ".join(sub_keywords)
        search_kw = f"{keyword} OR {cat_kw}" if keyword else cat_kw

        places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        places_params = {
            "location": f"{lat},{lng}",
            "radius": radius,
            "keyword": search_kw,
            "key": google_api_key,
            "language": "zh-TW"
        }
        places_res = requests.get(places_url, params=places_params).json()

        for place in places_res.get("results", []):
            name = place.get("name", "未命名")
            p_lat = place["geometry"]["location"]["lat"]
            p_lng = place["geometry"]["location"]["lng"]
            dist = int(haversine(lat, lng, p_lat, p_lng))
            place_id = place.get("place_id", "")
            if dist <= radius:
                all_places.append((cat, name, p_lat, p_lng, dist, place_id))

    # 如果完全沒選大類別，但有單純輸入關鍵字
    if keyword and not selected_categories:
        places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        places_params = {
            "location": f"{lat},{lng}",
            "radius": radius,
            "keyword": keyword,
            "key": google_api_key,
            "language": "zh-TW"
        }
        places_res = requests.get(places_url, params=places_params).json()
        for place in places_res.get("results", []):
            name = place.get("name", "未命名")
            p_lat = place["geometry"]["location"]["lat"]
            p_lng = place["geometry"]["location"]["lng"]
            dist = int(haversine(lat, lng, p_lat, p_lng))
            place_id = place.get("place_id", "")
            if dist <= radius:
                all_places.append(("關鍵字", name, p_lat, p_lng, dist, place_id))

    all_places = sorted(all_places, key=lambda x: x[4])

    st.write(f"目前搜尋半徑：{radius} 公尺")
    st.subheader("查詢結果（由近到遠）")

    if not all_places:
        st.write("該範圍內無相關地點。")
        return

    # 主畫面清單
    for t, name, _, _, dist, _ in all_places:
        st.write(f"**{t}** - {name} ({dist} 公尺)")

    # 側邊欄 Google 地圖連結
    st.sidebar.subheader("Google 地圖連結")
    for t, name, _, _, dist, place_id in all_places:
        if place_id:
            color = CATEGORY_COLORS.get(t, "red")
            url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
            st.sidebar.markdown(f"- <span style='color:{color}'>{t}</span> [{name} ({dist} 公尺)]({url})", unsafe_allow_html=True)

    # -------- 地圖標記 -----------
    markers_js = ""
    for t, name, p_lat, p_lng, dist, place_id in all_places:
        gmap_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else ""
        color = CATEGORY_COLORS.get(t, "red")
        icon_url = f"http://maps.google.com/mapfiles/ms/icons/{color}-dot.png"
        info_text = f'{t}: <a href="{gmap_url}" target="_blank">{name}</a><br>距離中心 {dist} 公尺'
        markers_js += f"""
        var marker = new google.maps.Marker({{
            position: {{lat: {p_lat}, lng: {p_lng}}},
            map: map,
            title: "{t}: {name}",
            icon: {{ url: "{icon_url}" }}
        }});
        var infowindow = new google.maps.InfoWindow({{
            content: `{info_text}`
        }});
        marker.addListener("click", function() {{
            infowindow.open(map, marker);
        }});
        """

    # 搜尋範圍圓圈
    circle_js = f"""
        var circle = new google.maps.Circle({{
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
