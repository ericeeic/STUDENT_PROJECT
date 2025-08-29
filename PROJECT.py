import streamlit as st
import requests
import folium
import os
from streamlit.components.v1 import html
from dotenv import load_dotenv

# 載入本地 .env
load_dotenv()

# 取得 OpenCage API Key
API_KEY = os.getenv("OPENCAGE_API_KEY")
if not API_KEY:
    st.error("請先設定環境變數 OPENCAGE_API_KEY")
    st.stop()

# 支援類別 (OSM tag)
PLACE_TAGS = {
    "交通": '["public_transport"="stop_position"]',
    "超商": '["shop"="convenience"]',
    "餐廳": '["amenity"="restaurant"]',
    "學校": '["amenity"="school"]',

    "教育": {
        "圖書館": '["amenity"="library"]',
        "幼兒園": '["amenity"="kindergarten"]',
        "小學": '["amenity"="school"]["school:level"="primary"]',
        "中學": '["amenity"="school"]["school:level"="secondary"]',
        "大學": '["amenity"="university"]'
    },

    "健康與保健": {
        "脊骨神經科": '["healthcare"="chiropractor"]',
        "牙科診所": '["healthcare"="dental_clinic"]',
        "牙醫": '["amenity"="dentist"]',
        "醫生": '["amenity"="doctors"]',
        "藥局": '["amenity"="pharmacy"]',
        "醫院": '["amenity"="hospital"]',
        "醫學檢驗所": '["healthcare"="medical_lab"]',
        "物理治療": '["healthcare"="physiotherapist"]',
        "皮膚護理": '["healthcare"="skin_care_clinic"]',
        "養生會館": '["leisure"="spa"]',
        "瑜珈教室": '["leisure"="yoga"]'
    },

    "建築物": {
        "醫院建築": '["building"="hospital"]',
        "學校建築": '["building"="school"]',
        "住宅大樓": '["building"="apartments"]'
    }
}

st.title("🌍 地址周邊400公尺查詢 (OSM + OpenCage)")

address = st.text_input("輸入地址")

# 先選大類
main_category = st.selectbox("選擇主分類", list(PLACE_TAGS.keys()))

# 判斷有沒有子分類
if isinstance(PLACE_TAGS[main_category], dict):
    selected_types = st.multiselect("選擇細項", PLACE_TAGS[main_category].keys())
else:
    selected_types = [main_category]

if st.button("查詢"):
    # 1️⃣ 轉換地址到經緯度 (OpenCage)
    geo_url = "https://api.opencagedata.com/geocode/v1/json"
    params = {
        "q": address,
        "key": API_KEY,
        "language": "zh-TW",
        "limit": 1
    }
    try:
        geo_res = requests.get(geo_url, params=params, timeout=10).json()
        if geo_res["results"]:
            lat = geo_res["results"][0]["geometry"]["lat"]
            lng = geo_res["results"][0]["geometry"]["lng"]
        else:
            st.error("無法解析該地址")
            st.stop()
    except requests.exceptions.RequestException as e:
        st.error(f"無法連線到 OpenCage: {e}")
        st.stop()

    # 2️⃣ 建立 Folium 地圖
    m = folium.Map(location=[lat, lng], zoom_start=16)
    folium.Marker([lat, lng], popup="查詢中心", icon=folium.Icon(color="red")).add_to(m)

    # 3️⃣ 查詢 Overpass
    all_places = []
    targets = selected_types if isinstance(PLACE_TAGS[main_category], dict) else [main_category]
    for t in targets:
        tag = PLACE_TAGS[main_category][t] if isinstance(PLACE_TAGS[main_category], dict) else PLACE_TAGS[t]
        query = f"""
        [out:json];
        (
          node{tag}(around:400,{lat},{lng});
          way{tag}(around:400,{lat},{lng});
          relation{tag}(around:400,{lat},{lng});
        );
        out center;
        """
        try:
            res = requests.post(
                "https://overpass-api.de/api/interpreter",
                data=query.encode("utf-8"),
                headers={"User-Agent": "StreamlitApp"},
                timeout=20
            )
            data = res.json()
        except requests.exceptions.RequestException as e:
            st.warning(f"無法查詢 {t}: {e}")
            continue

        for el in data.get("elements", []):
            # 建築物 way/relation 會有 center
            if "lat" in el and "lon" in el:
                lat_el, lon_el = el["lat"], el["lon"]
            elif "center" in el:
                lat_el, lon_el = el["center"]["lat"], el["center"]["lon"]
            else:
                continue

            name = el["tags"].get("name", "未命名")
            all_places.append((t, name))
            folium.Marker(
                [lat_el, lon_el],
                popup=f"{t}: {name}",
                icon=folium.Icon(color="blue" if "醫院" not in t else "green")
            ).add_to(m)

    # 4️⃣ 顯示結果與地圖
    st.subheader("查詢結果")
    if all_places:
        for t, name in all_places:
            st.write(f"**{t}** - {name}")
    else:
        st.write("該範圍內無相關地點。")

    map_html = m._repr_html_()
    html(map_html, height=500)



