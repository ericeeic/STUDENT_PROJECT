import streamlit as st
import requests
import math
from streamlit.components.v1 import html

st.title("🌍 地址周邊查詢 (Google Maps + Places API)")

# 使用者輸入 Google API Key
google_api_key = st.text_input("輸入 Google Maps API Key", type="password")
address = st.text_input("輸入地址")
radius = 600  # 搜尋半徑（公尺）

# 大類別 & 顏色
PLACE_TYPES = {
    "餐飲": "restaurant",
    "咖啡廳": "cafe",
    "便利商店": "convenience_store",
    "學校": "school",
    "公園": "park",
    "醫院": "hospital"
}
CATEGORY_COLORS = {
    "餐飲": "red",
    "咖啡廳": "orange",
    "便利商店": "green",
    "學校": "blue",
    "公園": "purple",
    "醫院": "brown"
}

# 多選按鈕
st.write("選擇類別：")
selected_categories = []
for cat in PLACE_TYPES.keys():
    if st.toggle(f"{cat}  🔵", key=f"btn_{cat}"):
        selected_categories.append(cat)

# 顯示對應顏色
for cat in selected_categories:
    st.markdown(
        f"<span style='display:inline-block;width:12px;height:12px;"
        f"background:{CATEGORY_COLORS[cat]};margin-right:4px;'></span>{cat}",
        unsafe_allow_html=True
    )

keyword = st.text_input("關鍵字(選填)")
if keyword:
    st.markdown(
        f"<span style='display:inline-block;width:12px;height:12px;background:black;"
        f"margin-right:4px;'></span>關鍵字",
        unsafe_allow_html=True
    )

# 取得中心座標
def geocode(addr):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={addr}&key={google_api_key}"
    r = requests.get(url).json()
    if r["status"] == "OK":
        loc = r["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    return None, None

def search_places(lat, lng):
    markers_js = ""
    for cat in selected_categories:
        place_type = PLACE_TYPES[cat]
        color = CATEGORY_COLORS[cat]
        url = (
            f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            f"?location={lat},{lng}&radius={radius}&type={place_type}&key={google_api_key}"
        )
        if keyword:
            url += f"&keyword={keyword}"
        r = requests.get(url).json()
        if r["status"] != "OK":
            continue
        for p in r["results"]:
            p_lat = p["geometry"]["location"]["lat"]
            p_lng = p["geometry"]["location"]["lng"]
            name = p.get("name", "")
            gmap_url = f"https://www.google.com/maps/place/?q=place_id:{p['place_id']}"
            dist = int(
                math.dist([lat, lng], [p_lat, p_lng]) * 111000
            )
            info = f'{cat}-{keyword or ""}: <a href="{gmap_url}" target="_blank">{name}</a><br>距離中心 {dist} 公尺'

            # ★ 這裡加入寬度、字體、maxWidth
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
                new google.maps.InfoWindow({{
                    content: `<div style="width:320px;font-size:16px">{info}</div>`,
                    maxWidth: 400
                }}).open(map, this);
            }});
            """
    return markers_js

if st.button("搜尋並顯示地圖"):
    lat, lng = geocode(address)
    if not lat:
        st.error("地址找不到座標")
    else:
        markers_js = search_places(lat, lng)
        map_html = f"""
        <div id="map" style="height:600px;width:100%;"></div>
        <script>
        function initMap() {{
            var center = {{lat: {lat}, lng: {lng}}};
            var map = new google.maps.Map(
                document.getElementById('map'),
                {{
                    zoom: 16,
                    center: center
                }}
            );
            new google.maps.Circle({{
                strokeColor: '#0000FF',
                strokeOpacity: 0.5,
                strokeWeight: 1,
                fillColor: '#0000FF',
                fillOpacity: 0.1,
                map: map,
                center: center,
                radius: {radius}
            }});
            {markers_js}
        }}
        </script>
        <script src="https://maps.googleapis.com/maps/api/js?key={google_api_key}&callback=initMap" async defer></script>
        """
        html(map_html, height=620)
