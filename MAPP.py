import streamlit as st
import requests
import math
from streamlit.components.v1 import html

st.title("地址周邊400公尺查詢")

# Google Maps API Key 與地址
google_api_key = st.text_input("輸入 Google Maps API Key", type="password")
address = st.text_input("輸入地址")
radius = 400  # 搜尋半徑

# 分類 + 子類別
PLACE_TYPES = {
    "教育": {
        "圖書館": "library",
        "幼兒園": "preschool",
        "小學": "primary_school",
        "學校": "school",
        "中學": "secondary_school",
        "大學": "university",
    },
    "健康與保健": {
        "牙醫": "dentist",
        "醫師": "doctor",
        "藥局": "pharmacy",
        "醫院": "hospital",
    },
    "購物": {
        "便利商店": "convenience_store",
        "超市": "supermarket",
        "百貨公司": "department_store",
    },
    "交通運輸": {
        "公車站": "bus_station",
        "地鐵站": "subway_station",
        "火車站": "train_station",
    },
    "餐飲": {
        "餐廳": "restaurant"
    }
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(d_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def search_category(main_category):
    if not google_api_key:
        st.error("請先輸入 Google Maps API Key")
        return
    if not address:
        st.error("請輸入地址")
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
    for sub_type, place_type in PLACE_TYPES[main_category].items():
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
            dist = int(haversine(lat, lng, p_lat, p_lng))
            all_places.append((sub_type, name, p_lat, p_lng, dist))

    all_places = sorted(all_places, key=lambda x: x[4])

    st.subheader(f"【{main_category}】查詢結果（由近到遠）")
    if not all_places:
        st.write("該範圍內無相關地點。")
        return

    for t, name, _, _, dist in all_places:
        st.write(f"**{t}** - {name} ({dist} 公尺)")

    icon_map = {
        "餐廳": "http://maps.google.com/mapfiles/ms/icons/orange-dot.png",
        "醫院": "http://maps.google.com/mapfiles/ms/icons/green-dot.png",
        "便利商店": "http://maps.google.com/mapfiles/ms/icons/blue-dot.png",
        "交通站點": "http://maps.google.com/mapfiles/ms/icons/yellow-dot.png"
    }

    markers_js = ""
    for t, name, p_lat, p_lng, dist in all_places:
        icon_url = icon_map.get(t, "http://maps.google.com/mapfiles/ms/icons/blue-dot.png")
        markers_js += f"""
        var marker = new google.maps.Marker({{
            position: {{lat: {p_lat}, lng: {p_lng}}},
            map: map,
            title: "{t}: {name}",
            icon: {{ url: "{icon_url}" }}
        }});
        var infowindow = new google.maps.InfoWindow({{
            content: "{t}: {name}<br>距離中心 {dist} 公尺"
        }});
        marker.addListener("click", function() {{
            infowindow.open(map, marker);
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

        {markers_js}
    }}
    </script>
    <script src="https://maps.googleapis.com/maps/api/js?key={google_api_key}&callback=initMap" async defer></script>
    """
    html(map_html, height=500)

# 主分類按鈕列：點擊即搜尋
st.write("### 點擊分類直接搜尋")
cols = st.columns(len(PLACE_TYPES))
for i, cat in enumerate(PLACE_TYPES.keys()):
    if cols[i].button(cat, use_container_width=True):
        search_category(cat)
