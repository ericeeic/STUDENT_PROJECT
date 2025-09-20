import streamlit as st
import requests
import math
from streamlit.components.v1 import html

# Add a horizontal line to improve visual separation
st.markdown("---")

st.title("地址周邊查詢")

# --- UI Components ---
# Google Maps API Key
google_api_key = st.text_input("輸入 Google Maps API Key", type="password")

# Address input
address = st.text_input("輸入地址")

# Radius slider
radius = st.slider("選擇搜尋半徑 (公尺)", min_value=200, max_value=600, value=400, step=50)

# Keyword search
keyword = st.text_input("輸入關鍵字")

# Place categories
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
        "公車站": "bus_stop",
        "地鐵站": "subway_station",
        "火車站": "train_station",
    },
    "餐飲": {
        "餐廳": "restaurant"
    }
}

# Category selection
selected_category = st.selectbox("選擇想查詢的大類別", ["(不選)", *PLACE_TYPES.keys()])


# --- Helper Functions ---
def haversine(lat1, lon1, lat2, lon2):
    """
    Calculates the distance between two geographical points using the Haversine formula.
    """
    R = 6371000  # Radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def search_places():
    """
    Handles the main logic for searching places and displaying results.
    """
    # --- Input Validation ---
    if not google_api_key:
        st.error("請先輸入 Google Maps API Key")
        return
    if not address:
        st.error("請輸入地址")
        return
    if selected_category == "(不選)" and not keyword:
        st.error("請至少選擇一個大類別或輸入關鍵字")
        return

    # --- Geocoding (Address to Lat/Lng) ---
    geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
    geo_params = {"address": address, "key": google_api_key, "language": "zh-TW"}
    try:
        geo_res = requests.get(geo_url, params=geo_params).json()
        if geo_res.get("status") != "OK":
            st.error(f"無法解析該地址。錯誤訊息: {geo_res.get('status')}")
            return
        location = geo_res["results"][0]["geometry"]["location"]
        lat, lng = location["lat"], location["lng"]
    except requests.exceptions.RequestException as e:
        st.error(f"連線錯誤：{e}")
        return

    # --- Nearby Search ---
    search_kw = keyword.strip()
    if selected_category != "(不選)":
        sub_keywords = list(PLACE_TYPES[selected_category].keys())
        cat_kw = " OR ".join(sub_keywords)
        search_kw = f"{search_kw} OR {cat_kw}" if search_kw else cat_kw

    places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    places_params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "keyword": search_kw,
        "key": google_api_key,
        "language": "zh-TW"
    }
    try:
        places_res = requests.get(places_url, params=places_params).json()
        if places_res.get("status") not in ["OK", "ZERO_RESULTS"]:
            st.error(f"地點搜尋失敗。錯誤訊息: {places_res.get('status')}")
            return
    except requests.exceptions.RequestException as e:
        st.error(f"連線錯誤：{e}")
        return

    all_places = []
    for place in places_res.get("results", []):
        p_lat = place["geometry"]["location"]["lat"]
        p_lng = place["geometry"]["location"]["lng"]
        dist = int(haversine(lat, lng, p_lat, p_lng))
        if dist <= radius:
            name = place.get("name", "未命名")
            place_id = place.get("place_id", "")
            cat_label = selected_category if selected_category != "(不選)" else "關鍵字"
            all_places.append((cat_label, name, p_lat, p_lng, dist, place_id))

    all_places = sorted(all_places, key=lambda x: x[4])

    # --- Display Results ---
    st.write(f"目前搜尋半徑：{radius} 公尺")
    st.subheader("查詢結果（由近到遠）")

    if not all_places:
        st.write("該範圍內無相關地點。")
        return

    # Main results list
    for t, name, _, _, dist, _ in all_places:
        st.write(f"**{t}** - {name} ({dist} 公尺)")

    # --- Sidebar Links (Corrected URL) ---
    st.sidebar.subheader("Google 地圖連結")
    for _, name, _, _, dist, place_id in all_places:
        if place_id:
            # Correct URL for linking to a specific place on Google Maps
            url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
            st.sidebar.markdown(f"- [{name} ({dist} 公尺)]({url})")

    # --- Dynamic HTML for Google Maps ---
    markers_js = ""
    for t, name, p_lat, p_lng, dist, place_id in all_places:
        # Correct URL for linking to a specific place on Google Maps
        gmap_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else ""
        info_text = f'{t}: <a href="{gmap_url}" target="_blank">{name}</a><br>距離中心 {dist} 公尺'
        
        markers_js += f"""
        var marker = new google.maps.Marker({{
            position: {{lat: {p_lat}, lng: {p_lng}}},
            map: map,
            title: "{t}: {name}",
        }});
        var infowindow = new google.maps.InfoWindow({{
            content: `{info_text}`
        }});
        marker.addListener("click", function() {{
            infowindow.open(map, marker);
        }});
        """

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
            # Use a valid icon URL, or let Google use the default one.
            # Using a public icon URL for demonstration.
            icon: "http://maps.google.com/mapfiles/ms/icons/red-dot.png" 
        }});

        {circle_js}
        {markers_js}
    }}
    </script>
    <script src="https://maps.googleapis.com/maps/api/js?key={google_api_key}&callback=initMap" async defer></script>
    """
    html(map_html, height=500)


# --- Search Button ---
if st.button("開始查詢", use_container_width=True):
    search_places()
