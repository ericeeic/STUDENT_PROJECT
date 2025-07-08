import streamlit as st
import folium
from streamlit_folium import st_folium
import json

st.set_page_config(layout="wide")
st.title("台灣互動地圖｜點擊縮放縣市並顯示行政區")

# 載入縣市中心座標
city_coords = {
    "臺北市": [25.0330, 121.5654],
    "新北市": [25.0169, 121.4628],
    "桃園市": [24.9936, 121.2969],
    "臺中市": [24.1477, 120.6736],
    "臺南市": [22.9999, 120.2270],
    "高雄市": [22.6273, 120.3014],
    "基隆市": [25.1276, 121.7392],
    "新竹市": [24.8036, 120.9686],
    "嘉義市": [23.4800, 120.4494],
    "新竹縣": [24.8387, 121.0256],
    "苗栗縣": [24.5636, 120.8214],
    "彰化縣": [24.0681, 120.5730],
    "南投縣": [23.9150, 120.6856],
    "雲林縣": [23.7092, 120.5450],
    "嘉義縣": [23.4582, 120.5190],
    "屏東縣": [22.5500, 120.5500],
    "宜蘭縣": [24.7021, 121.7378],
    "花蓮縣": [23.9833, 121.6000],
    "臺東縣": [22.7583, 121.1500],
    "澎湖縣": [23.5653, 119.5803],
    "金門縣": [24.4333, 118.3167],
    "連江縣": [26.1600, 119.9500]
}

# 載入行政區資料 (從 JSON 檔讀取)
with open("district_coords.json", "r", encoding="utf-8") as f:
    district_coords = json.load(f)

if "selected_city" not in st.session_state:
    st.session_state.selected_city = None

def create_map(selected_city=None):
    zoom_loc = city_coords.get(selected_city, [23.7, 121])
    zoom_level = 12 if selected_city else 7
    m = folium.Map(location=zoom_loc, zoom_start=zoom_level)

    # 縣市標記
    for city, coord in city_coords.items():
        folium.Marker(
            location=coord,
            popup=city,
            tooltip=f"點擊選擇 {city}",
            icon=folium.Icon(color="red" if city == selected_city else "blue", icon="info-sign"),
        ).add_to(m)

    # 如果有選擇縣市，加入行政區圖釘
    if selected_city and selected_city in district_coords:
        for district, coord in district_coords[selected_city].items():
            folium.Marker(
                location=coord,
                popup=district,
                icon=folium.Icon(color="green", icon="home"),
            ).add_to(m)

    return m

col1, col2 = st.columns([3, 1])

with col1:
    map_data = create_map(st.session_state.selected_city)
    st_folium(map_data, width=800, height=600)

with col2:
    st.write("### 縣市選擇")
    # 動態建立按鈕
    cities_per_row = 3
    cities = list(city_coords.keys())
    for i in range(0, len(cities), cities_per_row):
        cols = st.columns(cities_per_row)
        for idx, city in enumerate(cities[i:i+cities_per_row]):
            if cols[idx].button(city):
                st.session_state.selected_city = city

    if st.session_state.selected_city:
        st.subheader(f"已選縣市：{st.session_state.selected_city}")
        districts = district_coords.get(st.session_state.selected_city, {})
        if districts:
            st.markdown("行政區：")
            for d in districts:
                st.markdown(f"- {d}")
        else:
            st.info("無行政區資料")
        if st.button("回到全台灣"):
            st.session_state.selected_city = None
    else:
        st.info("請從右側選擇縣市查看行政區")

