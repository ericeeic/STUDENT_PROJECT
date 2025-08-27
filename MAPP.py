import streamlit as st
import os
import pandas as pd
import math
import requests
from streamlit.components.v1 import html

# ===================== 工具函數 =====================
def get_city_options(data_dir="./Data"):
    files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    name_map = {
        "Taichung-city_buy_properties.csv": "台中市",
    }
    options = {name_map.get(f, f.replace("-city_buy_properties.csv", "")): f for f in files}
    return options

def display_pagination(df, items_per_page=10):
    if 'current_search_page' not in st.session_state:
        st.session_state.current_search_page = 1
    
    total_items = len(df)
    total_pages = math.ceil(total_items / items_per_page) if total_items > 0 else 1
    
    if st.session_state.current_search_page > total_pages:
        st.session_state.current_search_page = 1
    
    start_idx = (st.session_state.current_search_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    current_page_data = df.iloc[start_idx:end_idx]
    
    return current_page_data, st.session_state.current_search_page, total_pages, total_items

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(d_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# ===================== Google Maps 查詢分類 =====================
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
        "整脊診所": "chiropractor",
        "牙科診所": "dental_clinic",
        "牙醫": "dentist",
        "醫師": "doctor",
        "藥局": "pharmacy",
        "醫院": "hospital",
        "藥妝店": "drugstore",
        "醫學檢驗所": "medical_lab",
        "物理治療所": "physiotherapist",
        "按摩": "massage",
        "三溫暖": "sauna",
        "皮膚科診所": "skin_care_clinic",
        "SPA": "spa",
        "日曬工作室": "tanning_studio",
        "健康中心": "wellness_center",
        "瑜伽教室": "yoga_studio",
    },
    "購物": {
        "亞洲超市": "asian_grocery_store",
        "汽車零件行": "auto_parts_store",
        "腳踏車行": "bicycle_store",
        "書店": "book_store",
        "肉舖": "butcher_shop",
        "手機行": "cell_phone_store",
        "服飾店": "clothing_store",
        "便利商店": "convenience_store",
        "百貨公司": "department_store",
        "折扣商店": "discount_store",
        "電子產品店": "electronics_store",
        "食品雜貨店": "food_store",
        "家具行": "furniture_store",
        "禮品店": "gift_shop",
        "五金行": "hardware_store",
        "家居用品": "home_goods_store",
        "居家裝修": "home_improvement_store",
        "珠寶店": "jewelry_store",
        "酒類專賣": "liquor_store",
        "傳統市場": "market",
        "寵物店": "pet_store",
        "鞋店": "shoe_store",
        "購物中心": "shopping_mall",
        "體育用品店": "sporting_goods_store",
        "商店(其他)": "store",
        "超市": "supermarket",
        "倉儲商店": "warehouse_store",
        "批發商": "wholesaler",
    },
    "交通運輸": {
        "機場": "airport",
        "簡易飛機場": "airstrip",
        "公車站": "bus_station",
        "公車候車亭": "bus_stop",
        "渡輪碼頭": "ferry_terminal",
        "直升機場": "heliport",
        "國際機場": "international_airport",
        "輕軌站": "light_rail_station",
        "停車轉乘": "park_and_ride",
        "地鐵站": "subway_station",
        "計程車招呼站": "taxi_stand",
        "火車站": "train_station",
        "轉運站": "transit_depot",
        "交通站點": "transit_station",
        "卡車停靠站": "truck_stop",
    },
    "餐飲": {
        "餐廳": "restaurant"
    }
}

# ===================== 主程式 =====================
def main():
    st.set_page_config(layout="wide")

    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'home'

    # ======= 側邊欄 =======
    if st.sidebar.button("🏠 首頁", use_container_width=True, key="home_button"):
        st.session_state.current_page = 'home'
        if 'current_search_page' in st.session_state:
            del st.session_state.current_search_page

    if st.sidebar.button("🔍 搜尋頁面", use_container_width=True, key="search_button"):
        st.session_state.current_page = 'search'

    if st.sidebar.button("📊 分析頁面", use_container_width=True, key="analysis_button"):
        st.session_state.current_page = 'analysis'
        if 'current_search_page' in st.session_state:
            del st.session_state.current_search_page

    st.sidebar.title("⚙️設置")
    with st.sidebar.expander("🔑Gemini API KEY"):
        api_key_input = st.text_input("請輸入 Gemini API 金鑰", type="password")
        if st.button("確定", key="api_confirm_button"):
            st.success("✅API KEY已設定")
    with st.sidebar.expander("🗺️MAP API KEY"):
        st.write("施工中...")
    with st.sidebar.expander("🔄更新資料"):
        st.write("施工中...")
    if st.sidebar.button("其他功能一", use_container_width=True, key="updata_button"):
        st.sidebar.write("施工中...")
    if st.sidebar.button("💬智能小幫手", use_container_width=True, key="line_button"):
        st.sidebar.write("施工中...")

    # ======= 首頁 =======
    if st.session_state.current_page == 'home':
        st.title("🏠AI購屋分析")
        st.write("👋歡迎來到房地產分析系統")

        col1, col2 = st.columns(2)
        with col1:
            with st.form("search"):
                st.subheader("🔍 搜尋頁面")
                st.write("第一步：選擇條件開始搜尋")
                search_bt = st.form_submit_button("開始")
                if search_bt:
                    st.session_state.current_page = 'search'
            with st.form("form2"):
                st.subheader("表單 2")
                submit2 = st.form_submit_button("提交")
                if submit2:
                    st.write("施工中...")
        with col2:
            with st.form("analysis"):
                st.subheader("📊 分析頁面")
                st.write("第二步：查看數據分析")
                analysis_bt = st.form_submit_button("開始")
                if analysis_bt:
                    st.session_state.current_page = 'analysis'
            with st.form("form4"):
                st.subheader("表單 4")
                submit4 = st.form_submit_button("提交")
                if submit4:
                    st.write("施工中...")

    # ======= 搜尋頁面 =======
    elif st.session_state.current_page == 'search':
        st.title("🔍 搜尋頁面")
        with st.form("property_requirements"):
            st.subheader("📍 房產篩選條件")
            housetype = ["大樓", "華廈", "公寓", "套房", "透天", "店面", "辦公", "別墅", "倉庫", "廠房", "土地", "單售車位", "其它"]
            options = get_city_options()
            col1, col2 = st.columns([1, 1])
            with col1:
                selected_label = st.selectbox("請選擇城市：", list(options.keys()))
            with col2:
                housetype_change = st.selectbox("請選擇房產類別：", housetype, key="housetype")
            submit = st.form_submit_button("開始篩選")

        if submit:
            st.session_state.current_search_page = 1
            selected_file = options[selected_label]
            file_path = os.path.join("./Data", selected_file)
            try:
                df = pd.read_csv(file_path)
                df = df[df['類型'] == housetype_change]
                st.session_state.filtered_df = df
                st.session_state.search_params = {'city': selected_label, 'housetype': housetype_change}
            except Exception as e:
                st.error(f"讀取 CSV 發生錯誤: {e}")

        if 'filtered_df' in st.session_state and not st.session_state.filtered_df.empty:
            df = st.session_state.filtered_df
            search_params = st.session_state.search_params
            current_page_data, current_page, total_pages, total_items = display_pagination(df, 10)
            st.subheader(f"🏠 {search_params['city']}房產列表")
            st.write(f"共找到 **{total_items}** 筆，第 **{current_page}** / **{total_pages}** 頁")

            for idx, (index, row) in enumerate(current_page_data.iterrows()):
                with st.container():
                    global_idx = (current_page - 1) * 10 + idx + 1
                    col1, col2, col3, col4 = st.columns([7, 1, 1, 2])
                    with col1:
                        st.subheader(f"#{global_idx} 🏠 {row['標題']}")
                        st.write(f"**地址：** {row['地址']} | **屋齡：** {row['屋齡']} | **類型：** {row['類型']}")
                        st.write(f"**建坪：** {row['建坪']} | **主+陽：** {row['主+陽']} | **格局：** {row['格局']} | **樓層：** {row['樓層']}")
                    with col4:
                        st.metric("Price(NT$)", f"${int(row['總價(萬)'] * 10):,}K")

                    col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1, 1, 1, 1, 1, 1])
                    with col7:
                        property_url = f"https://www.sinyi.com.tw/buy/house/{row['編號']}?breadcrumb=list"
                        st.markdown(
                            f'<a href="{property_url}" target="_blank"><button style="padding:5px 10px;">Property Link</button></a>',
                            unsafe_allow_html=True
                        )
                    st.markdown("---")

            if total_pages > 1:
                col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
                with col1:
                    if st.button("⏮️ 第一頁", disabled=(current_page == 1)):
                        st.session_state.current_search_page = 1
                        st.rerun()
                with col2:
                    if st.button("⏪ 上一頁", disabled=(current_page == 1)):
                        st.session_state.current_search_page = max(1, current_page - 1)
                        st.rerun()
                with col3:
                    new_page = st.selectbox("", range(1, total_pages + 1), index=current_page - 1, key="page_selector")
                    if new_page != current_page:
                        st.session_state.current_search_page = new_page
                        st.rerun()
                with col4:
                    if st.button("下一頁 ⏩", disabled=(current_page == total_pages)):
                        st.session_state.current_search_page = min(total_pages, current_page + 1)
                        st.rerun()
                with col5:
                    if st.button("最後一頁 ⏭️", disabled=(current_page == total_pages)):
                        st.session_state.current_search_page = total_pages
                        st.rerun()
                st.info(f"📄 第 {current_page} 頁，共 {total_pages} 頁 | 顯示 {(current_page-1)*10+1}-{min(current_page*10, total_items)} 筆")

        st.subheader("📍 地址周邊查詢")
        google_api_key = st.text_input("輸入 Google Maps API Key", type="password")
        address = st.text_input("輸入地址")
        main_category = st.selectbox("選擇分類", PLACE_TYPES.keys())
        sub_types = st.multiselect("選擇地點類型", list(PLACE_TYPES[main_category].keys()))
        radius = 600

        if st.button("查詢"):
            if not google_api_key:
                st.error("請先輸入 Google Maps API Key")
                st.stop()
            geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
            geo_params = {"address": address, "key": google_api_key, "language": "zh-TW"}
            geo_res = requests.get(geo_url, params=geo_params).json()
            if geo_res.get("status") != "OK":
                st.error("無法解析該地址")
                st.stop()
            location = geo_res["results"][0]["geometry"]["location"]
            lat, lng = location["lat"], location["lng"]

            all_places = []
            for sub_type in sub_types:
                place_type = PLACE_TYPES[main_category][sub_type]
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
            st.subheader("查詢結果（由近到遠）")
            if all_places:
                for t, name, _, _, dist in all_places:
                    st.write(f"**{t}** - {name} ({dist} 公尺)")
            else:
                st.write("該範圍內無相關地點。")

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

    elif st.session_state.current_page == 'analysis':
        st.title("📊 分析頁面")
        st.write("房產分析與數據展示 (施工中...)")

if __name__ == "__main__":
    main()
