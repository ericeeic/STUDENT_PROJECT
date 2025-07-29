import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_echarts import st_echarts
import json
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
import os

# 頁面設定
st.set_page_config(page_title="台灣不動產與 Gemini 聊天室", layout="wide")

# 頁面選擇
page = st.sidebar.selectbox("選擇頁面", ["不動產分析", "Gemini 聊天室"], key="page")

# 共用 Session State 初始化
def init_state(defaults):
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ---------------- 不動產分析頁 ----------------
if page == "不動產分析":
    st.title("台灣地圖與不動產資料分析")

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

    init_state({"selected_city": None, "selected_district": None, "show_filtered_data": False})

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

    # 載入多個 CSV，合併成一個 DataFrame（請確保檔案存在）
    file_names = [f"合併後不動產統計_{y}.csv" for y in [
        "11101", "11102", "11103", "11104",
        "11201", "11202", "11203", "11204",
        "11301", "11302", "11303", "11304",
        "11401", "11402"
    ]]
    dfs = []
    for name in file_names:
        try:
            df = pd.read_csv(name)
            dfs.append(df)
        except Exception as e:
            st.warning(f"無法讀取 {name}：{e}")
    combined_df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    chart_type = st.sidebar.selectbox(
    "選擇圖表類型",
    ["不動產價格趨勢分析", "交易筆數分布"]
    )
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
                    st.session_state.show_filtered_data = True

        if st.session_state.selected_city:
            st.subheader(f"行政區：{st.session_state.selected_city}")
            districts = district_coords.get(st.session_state.selected_city, {})
            district_names = ["全部的"] + list(districts.keys())
            for i in range(0, len(district_names), 3):
                row = st.columns(3)
                for j, name in enumerate(district_names[i:i + 3]):
                    if row[j].button(name):
                        st.session_state.selected_district = None if name == "全部的" else name
                        st.session_state.show_filtered_data = True

            st.divider()
            if st.button("回到全台灣"):
                st.session_state.selected_city = None
                st.session_state.selected_district = None
                st.session_state.show_filtered_data = False
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
            
            if chart_type == "不動產價格趨勢分析":
                if len(filtered_df) > 0:
                    filtered_df['年份'] = filtered_df['季度'].str[:3].astype(int) + 1911
                    yearly_avg = filtered_df.groupby(['年份', 'BUILD'])['平均單價元平方公尺'].mean().reset_index()
                    years = sorted(yearly_avg['年份'].unique())
                    year_labels = [str(year) for year in years]
    
                    new_house_data = []
                    old_house_data = []
                    for year in years:
                        new_avg = yearly_avg[(yearly_avg['年份'] == year) & (yearly_avg['BUILD'] == '新成屋')]['平均單價元平方公尺']
                        old_avg = yearly_avg[(yearly_avg['年份'] == year) & (yearly_avg['BUILD'] == '中古屋')]['平均單價元平方公尺']
                        new_house_data.append(int(new_avg.iloc[0]) if len(new_avg) > 0 else 0)
                        old_house_data.append(int(old_avg.iloc[0]) if len(old_avg) > 0 else 0)
                    
                    
                    options = {
                        "title": {"text": "不動產價格趨勢分析"},
                        "tooltip": {"trigger": "axis"},
                        "legend": {"data": ["新成屋", "中古屋"]},
                        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
                        "toolbox": {"feature": {"saveAsImage": {}}},
                        "xAxis": {"type": "category", "boundaryGap": False, "data": year_labels},
                        "yAxis": {"type": "value", "name": "平均單價(元/平方公尺)"},
                        "series": [
                            {"name": "新成屋", "type": "line", "data": new_house_data,
                             "lineStyle": {"color": "#ff7f0e"}, "itemStyle": {"color": "#ff7f0e"}},
                            {"name": "中古屋", "type": "line", "data": old_house_data,
                             "lineStyle": {"color": "#1f77b4"}, "itemStyle": {"color": "#1f77b4"}},
                        ]
                    }
                    st_echarts(options=options, height="400px")
                
                # Gemini AI 趨勢分析按鈕與結果區塊
                if "api_key" in st.session_state and st.session_state.api_key:
                    if st.button("📈 用 Gemini AI 分析趨勢"):
                        with st.spinner("Gemini AI 正在分析中..."):
                            try:
                                genai.configure(api_key=st.session_state.api_key)
                                model = genai.GenerativeModel("models/gemini-2.0-flash")
    
                                # 將篩選資料取前10筆CSV字串當成 prompt 資料
                                sample_text = filtered_df.head(1000).to_csv(index=False, encoding="utf-8")
                                prompt = (
                                    "請根據以下台灣不動產資料，分析未來趨勢和重要觀察點：\n"
                                    f"{sample_text}\n"
                                    "請用繁體中文簡潔且專業地說明趨勢分析。"
                                )
                                response = model.generate_content(prompt).text.strip()
    
                                st.markdown("### 🤖 Gemini AI 趨勢分析結果")
                                st.write(response)
                            except Exception as e:
                                st.error(f"Gemini AI 分析錯誤：{e}")
                else:
                    st.info("請先在 Gemini 聊天室頁面輸入並保存 API 金鑰，才能使用趨勢分析功能。")               
            
            elif chart_type == "交易筆數分布":
                if len(filtered_df) > 0:        
                    if st.session_state.selected_city is None:
                        group_column = '縣市'
                        chart_title = "各縣市購房交易筆數分布"
                    else:
                        group_column = '行政區'
                    
                        # 先處理預設標題
                        chart_title = f"{st.session_state.selected_city} 交易筆數分布"
                    
                        # 如果有選行政區，代表只有一筆資料，那就改成該行政區為標題
                        if st.session_state.selected_district:
                            chart_title = f"{st.session_state.selected_district} 交易筆數分布"
                        
                    if group_column in filtered_df.columns:
                        has_transaction = '交易筆數' in filtered_df.columns
                        # 統計資料
                        if has_transaction:
                            counts = filtered_df.groupby(group_column)['交易筆數'].sum().reset_index()
                        else:
                            counts = filtered_df.groupby(group_column).size().reset_index(name='交易筆數')
            
                        # 準備餅圖資料
                        pie_data = [
                            {"value": int(row["交易筆數"]), "name": row[group_column]}
                            for _, row in counts.iterrows()
                        ]
                        pie_data = sorted(pie_data, key=lambda x: x['value'], reverse=True)[:10]
                        # 檢查資料後繪製圖表
                        if pie_data and sum(item['value'] for item in pie_data) > 0:
                            subtext = f"顯示前{len(pie_data)}名" if len(pie_data) >= 10 else ""
                            options = {
                                "title": {
                                    "text": chart_title,
                                    "subtext": subtext,
                                    "left": "center"
                                },
                                "tooltip": {
                                    "trigger": "item",
                                    "formatter": "{a} <br/>{b} : {c} ({d}%)"
                                },
                                "legend": {
                                    "orient": "vertical",
                                    "left": "left",
                                },
                                "series": [
                                    {
                                        "name": "交易筆數",
                                        "type": "pie",
                                        "radius": "50%",
                                        "data": pie_data,
                                        "emphasis": {
                                            "itemStyle": {
                                                "shadowBlur": 10,
                                                "shadowOffsetX": 0,
                                                "shadowColor": "rgba(0, 0, 0, 0.5)",
                                            }
                                        },
                                    }
                                ],
                            }
            
                            st_echarts(options=options, height="500px")

                # Gemini AI 趨勢分析按鈕與結果區塊
                if "api_key" in st.session_state and st.session_state.api_key:
                    if st.button("📈 用 Gemini AI 分析趨勢"):
                        with st.spinner("Gemini AI 正在分析中..."):
                            try:
                                genai.configure(api_key=st.session_state.api_key)
                                model = genai.GenerativeModel("models/gemini-2.0-flash")
    
                                # 將篩選資料取前10筆CSV字串當成 prompt 資料
                                sample_text = filtered_df.head(1000).to_csv(index=False, encoding="utf-8")
                                prompt = (
                                    "請根據以下台灣不動產資料，分析未來趨勢和重要觀察點：\n"
                                    f"{sample_text}\n"
                                    "請用繁體中文簡潔且專業地說明趨勢分析。"
                                )
                                response = model.generate_content(prompt).text.strip()
    
                                st.markdown("### 🤖 Gemini AI 趨勢分析結果")
                                st.write(response)
                            except Exception as e:
                                st.error(f"Gemini AI 分析錯誤：{e}")
                else:
                    st.info("請先在 Gemini 聊天室頁面輸入並保存 API 金鑰，才能使用趨勢分析功能。")

# ---------------- Gemini 聊天室頁 ----------------
elif page == "Gemini 聊天室":
    st.title("🤖 Gemini AI 聊天室")
# Session State 初始化
# ============================================
_default_state = {
    "api_key": "",
    "remember_api": False,
    "conversations": {},        # {topic_id: {"title": str, "history": list[dict]} }
    "topic_ids": [],            # 主題順序
    "current_topic": "new",     # 預設為新對話
    "uploaded_df": None,        # 上傳的 CSV DataFrame
}
for k, v in _default_state.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================
# Sidebar ── API Key 區塊
# ============================================
with st.sidebar:
    st.markdown("## 🔐 API 設定 ")

    st.session_state.remember_api = st.checkbox("記住 API 金鑰", value=st.session_state.remember_api)

    if st.session_state.remember_api and st.session_state.api_key:
        api_key_input = st.session_state.api_key
        st.success("✅ 已使用儲存的 API Key")
    else:
        api_key_input = st.text_input("請輸入 Gemini API 金鑰", type="password")

    if api_key_input and api_key_input != st.session_state.api_key:
        st.session_state.api_key = api_key_input

# ============================================
# 驗證並初始化 Gemini 模型
# ============================================
if st.session_state.api_key:
    try:
        genai.configure(api_key=st.session_state.api_key)
        MODEL_NAME = "models/gemini-2.0-flash"
        model = genai.GenerativeModel(MODEL_NAME)

        # 使用簡單訊息來測試 API Key 是否有效
        test_response = model.generate_content("Hello")
        if test_response.text.strip() == "":
            raise ValueError("API 回應為空，可能是無效金鑰")

    except Exception as e:
        st.error(f"❌ API 金鑰驗證失敗或無效")
        st.stop()
else:
    st.info("⚠️ 請在左側輸入 API 金鑰後開始使用。")
    st.stop()


# ============================================
# 📂 CSV 檔案上傳與顯示
# ============================================
uploaded_file = st.file_uploader("📁 上傳 CSV 檔案（Gemini 可讀取）", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.session_state.uploaded_df = df
        st.success("✅ 檔案上傳成功，前幾列資料如下：")
        st.dataframe(df.head())
    except Exception as e:
        st.error(f"❌ 無法讀取 CSV 檔案：{e}")
        st.session_state.uploaded_df = None

# ============================================
# Sidebar ── 聊天主題清單（按鈕版）
# ============================================
with st.sidebar:
    st.markdown("---")
    st.header("🗂️ 聊天紀錄")

    if st.button("🆕 新對話", key="new_btn"):
        st.session_state.current_topic = "new"

    for tid in st.session_state.topic_ids:
        title = st.session_state.conversations[tid]["title"]
        label = f"✔️ {title}" if tid == st.session_state.current_topic else title
        if st.button(label, key=f"topic_btn_{tid}"):
            st.session_state.current_topic = tid

    st.markdown("---")
    if st.button("🧹 清除所有聊天紀錄"):
        st.session_state.conversations = {}
        st.session_state.topic_ids = []
        st.session_state.current_topic = "new"

# ============================================
# 使用者輸入區塊
# ============================================
with st.form("user_input_form", clear_on_submit=True):
    user_input = st.text_input("你想問什麼？", placeholder="請輸入問題...")
    submitted = st.form_submit_button("🚀 送出")

if submitted and user_input:
    is_new = st.session_state.current_topic == "new"

    if is_new:
        topic_id = f"topic_{len(st.session_state.topic_ids) + 1}"
        st.session_state.conversations[topic_id] = {
            "title": "（產生主題中...）",
            "history": [{"user": user_input, "bot": "⏳ 回覆生成中..."}],
        }
        st.session_state.topic_ids.append(topic_id)
        st.session_state.current_topic = topic_id
    else:
        st.session_state.conversations[st.session_state.current_topic]["history"].append({
            "user": user_input,
            "bot": "⏳ 回覆生成中..."
        })

    # === Gemini 回覆內容與主題生成（使用主題作為提示）===
    with st.spinner("Gemini 正在思考中..."):
        try:
            # 如果是新對話，先產生主題
            if is_new:
                title_prompt = f"請為以下這句話產生一個簡短主題（10 個中文字以內）：「{user_input}」，請直接輸出主題，不要加引號或多餘說明。"
                title_response = model.generate_content(title_prompt)
                topic_title = title_response.text.strip().replace("主題：", "").replace("\n", "")
                topic_title = topic_title[:10]
                st.session_state.conversations[topic_id]["title"] = topic_title
            else:
                topic_title = st.session_state.conversations[st.session_state.current_topic]["title"]
    
        # 組合提示詞
            prompt = f"主題是「{topic_title}」。"
            if st.session_state.uploaded_df is not None:
                csv_preview = st.session_state.uploaded_df.head(10).to_csv(index=False)
                prompt += f"\n以下是使用者提供的 CSV 資料（前 10 筆）：\n{csv_preview}"
            prompt += f"\n\n根據這些資料與主題，請回答：「{user_input}」"

            response = model.generate_content(prompt)
            answer = response.text.strip()

        except Exception as e:
            answer = f"⚠️ 發生錯誤：{e}"
            if is_new:
                st.session_state.conversations[topic_id]["title"] = "錯誤主題"

    # === 更新對話內容 ===
        st.session_state.conversations[st.session_state.current_topic]["history"][-1]["bot"] = answer

# ============================================
# 對話紀錄顯示區
# ============================================
if st.session_state.current_topic != "new":
    conv = st.session_state.conversations[st.session_state.current_topic]

    for msg in reversed(conv["history"]):
        st.markdown(f"**👤 你：** {msg['user']}")
        st.markdown(f"**🤖 Gemini：** {msg['bot']}")
        st.markdown("---")
