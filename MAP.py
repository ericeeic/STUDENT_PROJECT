import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import pandas as pd

st.set_page_config(layout="wide")
st.title("台灣地圖")

# 縣市中心座標
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
}

# 載入行政區座標
with open("district_coords.json", "r", encoding="utf-8") as f:
    district_coords = json.load(f)


# 初始化 session_state
if "selected_city" not in st.session_state:
    st.session_state.selected_city = None
if "selected_district" not in st.session_state:
    st.session_state.selected_district = None

def create_map(selected_city=None, selected_district=None):
    if selected_city and selected_district and selected_district in district_coords.get(selected_city, {}):
        zoom_loc = district_coords[selected_city][selected_district]
        zoom_level = 14
    else:
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

    # 行政區標記
    if selected_city and selected_city in district_coords:
        for district, coord in district_coords[selected_city].items():
            color = "orange" if district == selected_district else "green"
            folium.Marker(
                location=coord,
                popup=district,
                icon=folium.Icon(color=color, icon="home"),
            ).add_to(m)

    return m

# 上傳 CSV 檔案
uploaded_file = st.file_uploader("上傳 CSV 檔案", type=["csv"])
data_df = None
if uploaded_file:
    data_df = pd.read_csv(uploaded_file)
    st.success(f"已成功讀取 CSV 檔案，資料列數：{len(data_df)}")

col1, col2 = st.columns([3, 1])

with col1:
    map_data = create_map(st.session_state.selected_city, st.session_state.selected_district)
    st_folium(map_data, width=800, height=600)

    # 顯示資料表格
    st.markdown("### 資料表")
    if data_df is not None:
        # 根據選擇過濾資料
        df_filtered = data_df.copy()
        if st.session_state.selected_city:
            df_filtered = df_filtered[df_filtered["city"] == st.session_state.selected_city]
        if st.session_state.selected_district:
            df_filtered = df_filtered[df_filtered["district"] == st.session_state.selected_district]

        st.dataframe(df_filtered)
    else:
        st.info("請先上傳 CSV 檔案")

with col2:
    st.write("### 縣市選擇")
    cities_per_row = 3
    cities = list(city_coords.keys())
    for i in range(0, len(cities), cities_per_row):
        cols = st.columns(cities_per_row)
        for idx, city in enumerate(cities[i:i + cities_per_row]):
            if cols[idx].button(city):
                st.session_state.selected_city = city
                st.session_state.selected_district = None  # 清除行政區選擇

    if st.session_state.selected_city:
        st.subheader(f"行政區：{st.session_state.selected_city}")
        districts = district_coords.get(st.session_state.selected_city, {})
        district_names = list(districts.keys())
        districts_per_row = 3
        for i in range(0, len(district_names), districts_per_row):
            row = st.columns(districts_per_row)
            for j, name in enumerate(district_names[i:i + districts_per_row]):
                if row[j].button(name):
                    st.session_state.selected_district = name

        st.divider()
        if st.button("回到全台灣"):
            st.session_state.selected_city = None
            st.session_state.selected_district = None
    else:
        st.info("請從右側選擇縣市查看行政區")

