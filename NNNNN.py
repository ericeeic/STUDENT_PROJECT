import streamlit as st
import requests
import os
from dotenv import load_dotenv
import google.generativeai as genai
import math
from streamlit_folium import folium_static
import folium

# ===============================
# 載入環境變數
# ===============================
load_dotenv()
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")   # 使用者需在 .env 中設定
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not GOOGLE_KEY:
    st.error("❌ 請先設定環境變數 GOOGLE_API_KEY")
    st.stop()

if not GEMINI_KEY:
    st.error("❌ 請先設定環境變數 GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=GEMINI_KEY)

# ===============================
# Google Places 類別
# ===============================
PLACE_TYPES = {
    "交通": ["bus_station", "subway_station", "train_station"],
    "超商": ["convenience_store"],
    "餐廳": ["restaurant", "cafe"],
    "學校": ["school", "university", "primary_school", "secondary_school"],
    "醫院": ["hospital"],
    "藥局": ["pharmacy"]
}

# ===============================
# 工具函式
# ===============================
def geocode_address(address: str):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": GOOGLE_KEY, "language": "zh-TW"}
    r = requests.get(url, params=params, timeout=10).json()
    if r.get("status") == "OK" and r["results"]:
        loc = r["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    return None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    from math import radians, sin, cos, sqrt, atan2
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

def query_google_places(lat, lng, radius=500):
    results = {k: [] for k in PLACE_TYPES.keys()}
    for label, types in PLACE_TYPES.items():
        for t in types:
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": f"{lat},{lng}",
                "radius": radius,
                "type": t,
                "language": "zh-TW",
                "key": GOOGLE_KEY
            }
            r = requests.get(url, params=params, timeout=10).json()
            for place in r.get("results", []):
                name = place.get("name", "未命名")
                p_lat = place["geometry"]["location"]["lat"]
                p_lng = place["geometry"]["location"]["lng"]
                dist = int(haversine(lat, lng, p_lat, p_lng))
                results[label].append(f"{name}（{dist} 公尺）")
    return results

def format_info(address, info_dict):
    lines = [f"房屋（{address}）："]
    for k, v in info_dict.items():
        lines.append(f"- {k}: {len(v)} 個")
    return "\n".join(lines)

def draw_map(lat_a, lng_a, lat_b, lng_b):
    m = folium.Map(location=[(lat_a + lat_b) / 2, (lng_a + lng_b) / 2], zoom_start=14)
    folium.Marker([lat_a, lng_a], popup="房屋 A", icon=folium.Icon(color="red")).add_to(m)
    folium.Marker([lat_b, lng_b], popup="房屋 B", icon=folium.Icon(color="blue")).add_to(m)
    folium_static(m)

# ===============================
# Streamlit 介面
# ===============================
st.title("🏠 房屋比較助手 (Google Places)")

if "comparison_done" not in st.session_state:
    st.session_state["comparison_done"] = False
    st.session_state["chat_history"] = []
    st.session_state["text_a"] = ""
    st.session_state["text_b"] = ""

col1, col2 = st.columns(2)
with col1:
    addr_a = st.text_input("輸入房屋 A 地址")
with col2:
    addr_b = st.text_input("輸入房屋 B 地址")

# ✅ 使用 slider 取代 select_slider
radius = st.slider(
    "搜尋半徑 (公尺)",
    min_value=200,
    max_value=1000,
    step=50,
    value=500,
)

if st.button("比較房屋"):
    if not addr_a or not addr_b:
        st.warning("請輸入兩個地址")
        st.stop()

    lat_a, lng_a = geocode_address(addr_a)
    lat_b, lng_b = geocode_address(addr_b)
    if not lat_a or not lat_b:
        st.error("❌ 無法解析其中一個地址")
        st.stop()

    info_a = query_google_places(lat_a, lng_a, radius=radius)
    info_b = query_google_places(lat_b, lng_b, radius=radius)

    text_a = format_info(addr_a, info_a)
    text_b = format_info(addr_b, info_b)

    st.session_state["text_a"] = text_a
    st.session_state["text_b"] = text_b

    draw_map(lat_a, lng_a, lat_b, lng_b)

    prompt = f"""你是一位房地產分析專家，請比較以下兩間房屋的生活機能，
    並列出優缺點與結論：
    {text_a}
    {text_b}
    """
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)

    st.subheader("📊 Gemini 分析結果")
    st.write(response.text)

    st.session_state["comparison_done"] = True

# 側邊欄
with st.sidebar:
    if st.session_state["comparison_done"]:
        st.subheader("🏠 房屋資訊對照表")
        st.markdown(f"### 房屋 A\n{st.session_state['text_a']}")
        st.markdown(f"### 房屋 B\n{st.session_state['text_b']}")
    else:
        st.info("⚠️ 請先輸入房屋地址並比較")

# 聊天
if st.session_state["comparison_done"]:
    st.header("💬 對話")
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("想問什麼？", placeholder="請輸入問題…")
        submitted = st.form_submit_button("🚀 送出")
    if submitted and user_input:
        st.session_state["chat_history"].append(("👤", user_input))
        chat_prompt = f"""
        以下是兩間房屋的周邊資訊：
        {st.session_state['text_a']}
        {st.session_state['text_b']}
        使用者問題：{user_input}
        請根據房屋周邊的生活機能提供回覆。
        """
        model = genai.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content(chat_prompt)
        st.session_state["chat_history"].append(("🤖", resp.text))

    for role, msg in st.session_state["chat_history"]:
        st.markdown(f"**{role}**：{msg}")
