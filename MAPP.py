import streamlit as st
import requests
import math
from streamlit.components.v1 import html

st.title("🌍 地址周邊400公尺查詢 (Google Maps + Places API)")

# 使用者手動輸入 Google API Key
google_api_key = st.text_input("輸入 Google Maps API Key", type="password")
address = st.text_input("輸入地址")
radius = 400  # 搜尋半徑（公尺）

PLACE_TYPES = {
    "交通": "transit_station",
    "醫院": "hospital",
    "超商": "convenience_store",
    "餐廳": "restaurant",
    "學校": "school"
}

selected_types = st.multiselect("選擇要查詢的類別", PLACE_TYPES.keys(), default=["超商", "交通"])

# 計算經緯度距離（Haversine formula, 回傳公尺）
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # 地球半徑 (公尺)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(d_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

if st.button("查詢"):
    if not google_api_key:
        st.error("請先輸入 Google Maps API Key")
        st.stop()

    # 1️⃣ Google Geocoding API 轉換地址 → 經緯度
    geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
    geo_params = {"address": address, "key": google_api_key, "language": "zh-TW"}
    geo_res = requests.get(geo_url, params=geo_params).json()

    if geo_res.get("status") != "OK":
        st.error("無法解析該地址")
        st.stop()

    location = geo_res["results"][0]["geometry"]["location"]
    lat, lng = location["lat"], location["lng"]

    all_places = []

    # 2️⃣ Google Places API 搜尋周邊地點
    for t in selected_types:
        place_type = PLACE_TYPES[t]
        places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        places_params = {
            "location": f"{lat},{lng}",
            "radius": radius,
            "type": place_type,
            "key": google_api_key,
            "language": "zh-TW"
        }
        places_res = requests.get(places_url, params=places_params).json()

        for place in places_res.get("results", []):
            name = place.get("name", "未命名")
            p_lat = place["geometry"]["location"]["lat"]
            p_lng = place["geometry"]["location"]["lng"]
            dist = int(haversine(lat, lng, p_lat, p_lng))  # 四捨五入成整數公尺
            all_places.append((t, name, p_lat, p_lng, dist))

    # **依距離排序**
    all_places = sorted(all_places, key=lambda x: x[4])

    # 3️⃣ 顯示查詢結果
    st.subheader("查詢結果（由近到遠）")
    if all_places:
        for t, name, _, _, dist in all_places:
            st.write(f"**{t}** - {name} ({dist} 公尺)")
    else:
        st.write("該範圍內無相關地點。")

    # 4️⃣ 依類別設定 icon 顏色
    icon_map = {
        "交通": "http://maps.google.com/mapfiles/ms/icons/yellow-dot.png",
        "醫院": "http://maps.google.com/mapfiles/ms/icons/green-dot.png",
        "超商": "http://maps.google.com/mapfiles/ms/icons/blue-dot.png",
        "餐廳": "http://maps.google.com/mapfiles/ms/icons/orange-dot.png",
        "學校": "http://maps.google.com/mapfiles/ms/icons/purple-dot.png"
    }

    markers_js = ""
    for t, name, p_lat, p_lng, dist in all_places:
        icon_url = icon_map.get(t, "http://maps.google.com/mapfiles/ms/icons/blue-dot.png")
        markers_js += f"""
        var marker = new google.maps.Marker({{
            position: {{lat: {p_lat}, lng: {p_lng}}},
            map: map,
            title: "{t}: {name}",
            icon: {{
                url: "{icon_url}"
            }}
        }});
        var infowindow = new google.maps.InfoWindow({{
            content: "{t}: {name}<br>距離中心 {dist} 公尺"
        }});
        marker.addListener("click", function() {{
            infowindow.open(map, marker);
        }});
        """

    # 5️⃣ Google Maps 顯示
    map_html = f"""
    <div id="map" style="height:500px;"></div>
    <script>
    function initMap() {{
        var center = {{lat: {lat}, lng: {lng}}};
        var map = new google.maps.Map(document.getElementById('map'), {{
            zoom: 16,
            center: center
        }});

        // 🔴 使用者輸入的地址標記
        new google.maps.Marker({{
            position: center,
            map: map,
            title: "查詢中心",
            icon: {{
                url: "http://maps.google.com/mapfiles/ms/icons/red-dot.png"
            }}
        }});

        // 其他地點
        {markers_js}
    }}
    </script>
    <script src="https://maps.googleapis.com/maps/api/js?key={google_api_key}&callback=initMap" async defer></script>
    """

    html(map_html, height=500)
