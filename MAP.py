import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("台灣地圖與不動產資料分析")

# 縣市中心座標
city_coords = {
    "台北市": [25.0330, 121.5654],
    "新北市": [25.0169, 121.4628],
    "桃園市": [24.9936, 121.2969],
    "台中市": [24.1477, 120.6736],
    "台南市": [22.9999, 120.2270],
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
    "台東縣": [22.7583, 121.1500],
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

# 讀取多個 CSV 並合併
file_names = [
    "合併後不動產統計_11101.csv", "合併後不動產統計_11102.csv", "合併後不動產統計_11103.csv", "合併後不動產統計_11104.csv",
    "合併後不動產統計_11201.csv", "合併後不動產統計_11202.csv", "合併後不動產統計_11203.csv", "合併後不動產統計_11204.csv",
    "合併後不動產統計_11301.csv", "合併後不動產統計_11302.csv", "合併後不動產統計_11303.csv", "合併後不動產統計_11304.csv",
    "合併後不動產統計_11401.csv", "合併後不動產統計_11402.csv"
]

dfs = [pd.read_csv(name) for name in file_names]
combined_df = pd.concat(dfs, ignore_index=True)

# 顯示欄位名稱，方便除錯
st.write("資料欄位：", combined_df.columns.tolist())

# 定義函式取得季度 (假設有年月欄位叫 '年月' 並為民國年 + 月格式，ex: 11103 表示111年3月)
def get_quarter(ym):
    try:
        ym_str = str(int(ym))
        if len(ym_str) < 4:
            return None
        year = int(ym_str[:3])
        month = int(ym_str[3:])  # 後兩碼是月份
        quarter = (month - 1) // 3 + 1
        return f"{year}Q{quarter}"
    except:
        return None

# 確認你的年月欄名稱，這邊假設叫 "年月"
if "年月" in combined_df.columns:
    combined_df['季度'] = combined_df['年月'].apply(get_quarter)
else:
    st.warning("找不到 '年月' 欄位，請確認你的資料欄位名稱並修改程式。")

# 右側縣市與行政區選擇 UI
col1, col2 = st.columns([3, 1])

with col2:
    st.write("### 縣市選擇")
    cities_per_row = 3
    cities = list(city_coords.keys())
    for i in range(0, len(cities), cities_per_row):
        cols = st.columns(cities_per_row)
        for idx, city in enumerate(cities[i:i + cities_per_row]):
            if cols[idx].button(city):
                st.session_state.selected_city = city
                st.session_state.selected_district = None

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

with col1:
    # 顯示地圖
    map_data = create_map(st.session_state.selected_city, st.session_state.selected_district)
    st_folium(map_data, width=800, height=600)

    # 篩選資料
    filtered_df = combined_df.copy()
    if st.session_state.selected_city:
        filtered_df = filtered_df[filtered_df["縣市"] == st.session_state.selected_city]
    if st.session_state.selected_district:
        filtered_df = filtered_df[filtered_df["行政區"] == st.session_state.selected_district]

    st.markdown("## 📊 篩選後的不動產資料")
    st.write(f"共 {len(filtered_df)} 筆資料")
    st.dataframe(filtered_df)

    # 繪製折線圖分析
    st.markdown("## 折線圖分析")

    # 總和：BUILD vs 交易筆數總和
    if 'BUILD' in combined_df.columns and '交易筆數' in combined_df.columns:
        agg_total = combined_df.groupby('BUILD')['交易筆數'].sum().reset_index()

        fig, ax = plt.subplots()
        ax.plot(agg_total['BUILD'], agg_total['交易筆數'], marker='o')
        ax.set_title("不同 BUILD 類別交易筆數總和")
        ax.set_xlabel("BUILD")
        ax.set_ylabel("交易筆數")
        plt.xticks(rotation=45)
        st.pyplot(fig)
    else:
        st.warning("資料中缺少 'BUILD' 或 '交易筆數' 欄位，無法繪製總和折線圖。")

    # 分季度折線圖
    if '季度' in combined_df.columns and 'BUILD' in combined_df.columns and '交易筆數' in combined_df.columns:
        quarters = combined_df['季度'].dropna().unique()
        quarters = sorted(quarters)

        with st.expander("各季度 BUILD vs 交易筆數折線圖"):
            for q in quarters:
                df_q = combined_df[combined_df['季度'] == q]
                agg_q = df_q.groupby('BUILD')['交易筆數'].sum().reset_index()

                fig, ax = plt.subplots()
                ax.plot(agg_q['BUILD'], agg_q['交易筆數'], marker='o')
                ax.set_title(f"{q} BUILD 類別交易筆數")
                ax.set_xlabel("BUILD")
                ax.set_ylabel("交易筆數")
                plt.xticks(rotation=45)
                st.pyplot(fig)
    else:
        st.warning("資料中缺少 '季度'、'BUILD' 或 '交易筆數' 欄位，無法繪製分季度折線圖。")
