import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_echarts import st_echarts
import json
import pandas as pd
import google.generativeai as genai
import os
from modules.updater import check_missing_periods

st.set_page_config(page_title="台灣不動產分析與 Gemini 對話", layout="wide")

def init_state(defaults):
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state({
    "selected_city": None,
    "selected_district": None,
    "show_filtered_data": False,
    "api_key": "",
    "remember_api": False,
    "conversations": {},
    "topic_ids": [],
    "current_topic": None,
    "previous_topic_title": None,  # 新增用於追蹤上一次主題
})

with st.sidebar:
    st.markdown("## 🔐 API 設定")
    st.session_state.remember_api = st.checkbox("記住 API 金鑰", value=st.session_state.remember_api)
    api_key_input = st.text_input("請輸入 Gemini API 金鑰", type="password")
    if api_key_input and api_key_input != st.session_state.api_key:
        st.session_state.api_key = api_key_input

    st.markdown("---")
    st.markdown("## 📥 資料更新")
    if st.button("一鍵更新至當前期數"):
        with st.spinner("正在更新中..."):
            local, online, missing = check_missing_periods()
            st.info(f"本地共有 {len(local)} 期資料")
            st.info(f"內政部目前共提供 {len(online)} 期資料")
            if missing:
                st.warning(f"缺少以下期數：{', '.join(missing)}")
            else:
                st.success("恭喜，本地資料已是最新！")

    st.markdown("---")
    st.markdown("## 💬 對話紀錄")
    # 左側顯示對話主題列表，點擊切換
    for tid in reversed(st.session_state.topic_ids):
        label = st.session_state.conversations[tid]["title"]
        if st.button(f"🗂️ {label}", key=f"sidebar_topic_{tid}"):
            st.session_state.current_topic = tid

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

folder = "./"
file_names = [f for f in os.listdir(folder) if f.startswith("合併後不動產統計_") and f.endswith(".csv")]
dfs = []
for file in file_names:
    try:
        df = pd.read_csv(os.path.join(folder, file))
        dfs.append(df)
    except Exception as e:
        print(f"讀取 {file} 失敗：{e}")
combined_df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

st.title("台灣地圖與不動產資料分析")

chart_type = st.sidebar.selectbox("選擇圖表類型", ["不動產價格趨勢分析", "交易筆數分布"])
col1, col2 = st.columns([3, 1])

with col2:
    st.write("### 縣市選擇")
    for i in range(0, len(city_coords), 3):
        cols = st.columns(3)
        for j, city in enumerate(list(city_coords.keys())[i:i+3]):
            if cols[j].button(city):
                st.session_state.selected_city = city
                st.session_state.selected_district = None
                st.session_state.show_filtered_data = True

    if st.session_state.selected_city:
        st.subheader(f"行政區：{st.session_state.selected_city}")
        districts = district_coords.get(st.session_state.selected_city, {})
        district_names = ["全部的"] + list(districts.keys())
        for i in range(0, len(district_names), 3):
            row = st.columns(3)
            for j, name in enumerate(district_names[i:i+3]):
                if row[j].button(name):
                    st.session_state.selected_district = None if name == "全部的" else name
                    st.session_state.show_filtered_data = True

        st.divider()
        if st.button("回到全台灣"):
            st.session_state.selected_city = None
            st.session_state.selected_district = None
            st.session_state.show_filtered_data = False

with col1:
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

        topic_title = f"{st.session_state.selected_city or '全台'} - {chart_type}"

        # 如果主題改變，建立新的對話
        if st.session_state.previous_topic_title != topic_title:
            tid = f"topic_{len(st.session_state.topic_ids) + 1}"
            st.session_state.topic_ids.append(tid)
            st.session_state.current_topic = tid
            st.session_state.conversations[tid] = {
                "title": topic_title,
                "history": []
            }
            st.session_state.previous_topic_title = topic_title

        if chart_type == "不動產價格趨勢分析" and len(filtered_df) > 0:
            filtered_df['年份'] = filtered_df['季度'].str[:3].astype(int) + 1911
            yearly_avg = filtered_df.groupby(['年份', 'BUILD'])['平均單價元平方公尺'].mean().reset_index()
            years = sorted(yearly_avg['年份'].unique())
            year_labels = [str(year) for year in years]
            new_house_data = [int(yearly_avg[(yearly_avg['年份'] == y) & (yearly_avg['BUILD'] == '新成屋')]['平均單價元平方公尺'].values[0]) if not yearly_avg[(yearly_avg['年份'] == y) & (yearly_avg['BUILD'] == '新成屋')].empty else 0 for y in years]
            old_house_data = [int(yearly_avg[(yearly_avg['年份'] == y) & (yearly_avg['BUILD'] == '中古屋')]['平均單價元平方公尺'].values[0]) if not yearly_avg[(yearly_avg['年份'] == y) & (yearly_avg['BUILD'] == '中古屋')].empty else 0 for y in years]

            options = {
                "title": {"text": "不動產價格趨勢分析"},
                "tooltip": {"trigger": "axis"},
                "legend": {"data": ["新成屋", "中古屋"]},
                "xAxis": {"type": "category", "data": year_labels},
                "yAxis": {"type": "value"},
                "series": [
                    {"name": "新成屋", "type": "line", "data": new_house_data},
                    {"name": "中古屋", "type": "line", "data": old_house_data},
                ]
            }
            st_echarts(options, height="400px")

        elif chart_type == "交易筆數分布" and len(filtered_df) > 0:
            group_column = "縣市" if st.session_state.selected_city is None else "行政區"
            if group_column in filtered_df.columns:
                if '交易筆數' in filtered_df.columns:
                    counts = filtered_df.groupby(group_column)['交易筆數'].sum().reset_index()
                else:
                    counts = filtered_df.groupby(group_column).size().reset_index(name='交易筆數')
                pie_data = [{"value": int(row["交易筆數"]), "name": row[group_column]} for _, row in counts.iterrows()]
                pie_data = sorted(pie_data, key=lambda x: x['value'], reverse=True)[:10]
                options = {
                    "title": {"text": "交易筆數分布", "left": "center"},
                    "tooltip": {"trigger": "item"},
                    "legend": {"orient": "vertical", "left": "left"},
                    "series": [{
                        "name": "交易筆數",
                        "type": "pie",
                        "radius": "50%",
                        "data": pie_data
                    }]
                }
                st_echarts(options, height="400px")

        if st.session_state.api_key:
            genai.configure(api_key=st.session_state.api_key)
            model = genai.GenerativeModel("models/gemini-2.0-flash")
            sample_text = filtered_df.head(1000).to_csv(index=False)

            with st.form(key="gemini_chat_form", clear_on_submit=True):
                user_input = st.text_input("🗣️ 請問 Gemini：", placeholder="請輸入問題...")
                submitted = st.form_submit_button("送出")

            if submitted and user_input:
                # 持續對話，追加對話歷史
                if st.session_state.current_topic is None:
                    # 沒有對話主題，先建立
                    tid = f"topic_{len(st.session_state.topic_ids) + 1}"
                    st.session_state.topic_ids.append(tid)
                    st.session_state.current_topic = tid
                    st.session_state.conversations[tid] = {"title": topic_title, "history": []}

                conv = st.session_state.conversations[st.session_state.current_topic]

                # 建立 prompt（包含前10筆資料及歷史對話）
                prompt = f"請根據以下台灣不動產資料，分析未來趨勢和重要觀察點：\n{sample_text}\n"
                prompt += f"主題是「{topic_title}」。\n"
                if conv["history"]:
                    prompt += "以下是之前的對話記錄：\n"
                    for msg in conv["history"]:
                        prompt += f"使用者：{msg['user']}\nGemini：{msg['bot']}\n"
                prompt += f"使用者：{user_input}\nGemini："

                with st.spinner("Gemini AI 正在分析中..."):
                    try:
                        response = model.generate_content(prompt)
                        answer = response.text.strip()
                    except Exception as e:
                        answer = f"⚠️ 產生錯誤：{e}"

                conv["history"].append({"user": user_input, "bot": answer})

            # 顯示對話紀錄
            if st.session_state.current_topic:
                conv = st.session_state.conversations[st.session_state.current_topic]
                st.markdown(f"### 💬 對話紀錄（{conv['title']}）")
                for msg in reversed(conv["history"]):
                    st.markdown(f"**👤 你：** {msg['user']}")
                    st.markdown(f"**🤖 Gemini：** {msg['bot']}")
                    st.markdown("---")
        else:
            st.info("請在左側輸入並保存 API 金鑰以使用 Gemini AI 功能。")


