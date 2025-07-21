import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import pandas as pd
import matplotlib.pyplot as plt
import google.generativeai as genai

# ======= 側邊欄選頁 =======
page = st.sidebar.selectbox("選擇頁面", ["不動產分析", "Gemini 聊天室"])

# ==== 不動產分析頁 ====
# ==== 不動產分析頁 ====
if page == "不動產分析":
    st.set_page_config(page_title="台灣不動產分析", layout="wide")
    st.title("台灣地圖與不動產資料分析")

    # 縣市與行政區座標
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

    with open("district_coords.json", "r", encoding="utf-8") as f:
        district_coords = json.load(f)

    # Session 狀態
    if "selected_city" not in st.session_state:
        st.session_state.selected_city = None
    if "selected_district" not in st.session_state:
        st.session_state.selected_district = None
    if "show_filtered_data" not in st.session_state:
        st.session_state.show_filtered_data = False

    def create_map(selected_city=None, selected_district=None):
        if selected_city and selected_district and selected_district in district_coords.get(selected_city, {}):
            zoom_loc = district_coords[selected_city][selected_district]
            zoom_level = 14
        else:
            zoom_loc = city_coords.get(selected_city, [23.7, 121])
            zoom_level = 12 if selected_city else 7

        m = folium.Map(location=zoom_loc, zoom_start=zoom_level)

        for city, coord in city_coords.items():
            folium.Marker(
                location=coord,
                popup=city,
                tooltip=f"點擊選擇 {city}",
                icon=folium.Icon(color="red" if city == selected_city else "blue", icon="info-sign"),
            ).add_to(m)

        if selected_city and selected_city in district_coords:
            for district, coord in district_coords[selected_city].items():
                color = "orange" if district == selected_district else "green"
                folium.Marker(
                    location=coord,
                    popup=district,
                    icon=folium.Icon(color=color, icon="home"),
                ).add_to(m)

        return m

    # 合併不動產 CSV
    file_names = [
        "合併後不動產統計_11101.csv", "合併後不動產統計_11102.csv", "合併後不動產統計_11103.csv", "合併後不動產統計_11104.csv",
        "合併後不動產統計_11201.csv", "合併後不動產統計_11202.csv", "合併後不動產統計_11203.csv", "合併後不動產統計_11204.csv",
        "合併後不動產統計_11301.csv", "合併後不動產統計_11302.csv", "合併後不動產統計_11303.csv", "合併後不動產統計_11304.csv",
        "合併後不動產統計_11401.csv", "合併後不動產統計_11402.csv"
    ]
    dfs = [pd.read_csv(name) for name in file_names]
    combined_df = pd.concat(dfs, ignore_index=True)

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
                    st.session_state.show_filtered_data = True  # 顯示資料

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
                        st.session_state.show_filtered_data = True  # 顯示資料

            st.divider()
            if st.button("回到全台灣"):
                st.session_state.selected_city = None
                st.session_state.selected_district = None
                st.session_state.show_filtered_data = False  # 隱藏資料
        else:
            st.info("請從右側選擇縣市查看行政區")

    with col1:
        map_data = create_map(st.session_state.selected_city, st.session_state.selected_district)
        st_folium(map_data, width=800, height=600)

        if st.session_state.show_filtered_data:
            filtered_df = combined_df.copy()
            if st.session_state.selected_city:
                filtered_df = filtered_df[filtered_df["縣市"] == st.session_state.selected_city]
            if st.session_state.selected_district:
                filtered_df = filtered_df[filtered_df["行政區"] == st.session_state.selected_district]

            st.markdown("## 📊 篩選後的不動產資料")
            st.write(f"共 {len(filtered_df)} 筆資料")
            st.dataframe(filtered_df)

# ==== Gemini 聊天室頁 ====
elif page == "Gemini 聊天室":
    st.set_page_config(page_title="Gemini 聊天室", layout="wide")
    st.title("🤖 Gemini AI 聊天室")

    # Session State 初始化
    _default_state = {
        "api_key": "",
        "remember_api": False,
        "conversations": {},
        "topic_ids": [],
        "current_topic": "new",
    }
    for k, v in _default_state.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Sidebar API Key 輸入區
    with st.sidebar:
        st.markdown("## 🔐 API 設定 ")
        st.session_state.remember_api = st.checkbox(
            "記住 API 金鑰", value=st.session_state.remember_api
        )
        if st.session_state.remember_api and st.session_state.api_key:
            api_key_input = st.session_state.api_key
            st.success("✅ 已使用儲存的 API Key")
        else:
            api_key_input = st.text_input("請輸入 Gemini API 金鑰", type="password")
        if api_key_input and api_key_input != st.session_state.api_key:
            st.session_state.api_key = api_key_input

    # 初始化 Gemini
    if st.session_state.api_key:
        try:
            genai.configure(api_key=st.session_state.api_key)
            MODEL_NAME = "models/gemini-2.0-flash"
            model = genai.GenerativeModel(MODEL_NAME)
        except Exception as e:
            st.error(f"❌ 初始化 Gemini 失敗：{e}")
            st.stop()
    else:
        st.info("⚠️ 請在左側輸入 API 金鑰後開始使用。")
        st.stop()

    # 主題列表
    with st.sidebar:
        st.markdown("---")
        st.markdown("## 💡 主題列表")
        topic_options = ["new"] + st.session_state.topic_ids
        selected_topic_id = st.radio(
            "選擇主題以查看或開始對話：",
            options=topic_options,
            index=0 if st.session_state.current_topic == "new" else topic_options.index(st.session_state.current_topic),
            format_func=lambda tid: "🆕 新對話" if tid == "new" else st.session_state.conversations[tid]["title"],
            key="topic_selector",
        )
        st.session_state.current_topic = selected_topic_id

    # 輸入區
    with st.form("user_input_form", clear_on_submit=True):
        user_input = st.text_input("你想問什麼？", placeholder="請輸入問題...")
        submitted = st.form_submit_button("🚀 送出")

    if submitted and user_input:
        with st.spinner("Gemini 正在思考中..."):
            try:
                response = model.generate_content(user_input)
                answer = response.text.strip()
            except Exception as e:
                st.error(f"❌ 發生錯誤：{e}")
                st.stop()

        if st.session_state.current_topic == "new":
            topic_title = user_input if len(user_input) <= 10 else user_input[:10] + "..."
            topic_id = f"topic_{len(st.session_state.topic_ids) + 1}"

            st.session_state.conversations[topic_id] = {
                "title": topic_title,
                "history": [{"user": user_input, "bot": answer}],
            }
            st.session_state.topic_ids.append(topic_id)
            st.session_state.current_topic = topic_id
        else:
            st.session_state.conversations[st.session_state.current_topic]["history"].append({
                "user": user_input,
                "bot": answer
            })

    # 顯示對話紀錄
    if st.session_state.current_topic != "new":
        conv = st.session_state.conversations[st.session_state.current_topic]
        for msg in reversed(conv["history"]):
            st.markdown(f"**👤 你：** {msg['user']}")
            st.markdown(f"**🤖 Gemini：** {msg['bot']}")
            st.markdown("---")
