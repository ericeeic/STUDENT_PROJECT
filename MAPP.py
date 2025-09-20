import streamlit as st
import requests
import math
import folium
from streamlit.components.v1 import html
import google.generativeai as genai

st.title("🏠 房屋比較 + Google Places 雙地圖 + Gemini 分析 + 關鍵字搜尋")

# ===============================
# 大類別對應關鍵字
# ===============================
CATEGORY_KEYWORDS = {
    "教育": ["小學", "中學", "大學", "圖書館", "幼兒園"],
    "健康與保健": ["醫院", "診所", "牙醫", "藥局"],
    "購物": ["便利商店", "超市", "百貨公司"],
    "餐飲": ["餐廳", "咖啡廳"],
    "交通運輸": ["公車站", "地鐵站", "火車站"]
}

CATEGORY_COLORS = {
    "教育": "#1E90FF",
    "健康與保健": "#32CD32",
    "購物": "#FF8C00",
    "餐飲": "#FF0000",
    "交通運輸": "#800080",
    "關鍵字": "#000000"
}

# ===============================
# 工具函式
# ===============================
def geocode_address(address: str, api_key: str):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key, "language": "zh-TW"}
    r = requests.get(url, params=params, timeout=10).json()
    if r.get("status") == "OK" and r["results"]:
        loc = r["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    return None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(d_lambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def query_by_keyword(lat, lng, api_key, selected_categories, keyword="", radius=500):
    results = {cat: [] for cat in selected_categories}
    if keyword and not selected_categories:
        results["關鍵字"] = []

    for cat in selected_categories:
        for kw in CATEGORY_KEYWORDS[cat]:
            search_kw = f"{kw} {keyword}" if keyword else kw
            params = {
                "location": f"{lat},{lng}",
                "radius": radius,
                "keyword": search_kw,
                "key": api_key,
                "language": "zh-TW"
            }
            r = requests.get("https://maps.googleapis.com/maps/api/place/nearbysearch/json", params=params).json()
            for place in r.get("results", []):
                p_lat = place["geometry"]["location"]["lat"]
                p_lng = place["geometry"]["location"]["lng"]
                dist = int(haversine(lat, lng, p_lat, p_lng))
                results[cat].append((place.get("name", "未命名"), p_lat, p_lng, dist))

    if keyword and not selected_categories:
        params = {
            "location": f"{lat},{lng}",
            "radius": radius,
            "keyword": keyword,
            "key": api_key,
            "language": "zh-TW"
        }
        r = requests.get("https://maps.googleapis.com/maps/api/place/nearbysearch/json", params=params).json()
        for place in r.get("results", []):
            p_lat = place["geometry"]["location"]["lat"]
            p_lng = place["geometry"]["location"]["lng"]
            dist = int(haversine(lat, lng, p_lat, p_lng))
            results["關鍵字"].append((place.get("name", "未命名"), p_lat, p_lng, dist))
    return results

def add_markers(m, info_dict):
    for category, places in info_dict.items():
        color = CATEGORY_COLORS.get(category, "#000000")
        for name, lat, lng, dist in places:
            folium.Marker(
                [lat, lng],
                popup=f"{category}：{name}（{dist} 公尺）",
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(m)
            folium.CircleMarker(
                location=[lat, lng],
                radius=6,
                color=color,
                fill=True,
                fill_opacity=0.8
            ).add_to(m)

def format_info(address, info_dict):
    lines = [f"房屋（{address}）："]
    for k, v in info_dict.items():
        lines.append(f"- {k}: {len(v)} 個")
    return "\n".join(lines)

# ===============================
# Streamlit 介面
# ===============================
google_key = st.text_input("🔑 輸入 Google Maps API Key", type="password")
gemini_key = st.text_input("🔑 輸入 Gemini API Key", type="password")

if google_key and gemini_key:
    genai.configure(api_key=gemini_key)

    col1, col2 = st.columns(2)
    with col1:
        addr_a = st.text_input("房屋 A 地址")
    with col2:
        addr_b = st.text_input("房屋 B 地址")

    radius = st.slider("搜尋半徑 (公尺)", 100, 2000, 500, 50)
    keyword = st.text_input("關鍵字搜尋（可留空）")

    st.subheader("選擇生活機能類別")
    selected_categories = []
    cols = st.columns(len(CATEGORY_KEYWORDS))
    for i, cat in enumerate(CATEGORY_KEYWORDS.keys()):
        color = CATEGORY_COLORS[cat]
        with cols[i]:
            st.markdown(
                f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{color};margin-right:4px"></span>',
                unsafe_allow_html=True
            )
            if st.checkbox(cat, key=f"cat_{cat}", value=True):
                selected_categories.append(cat)

    if st.button("比較房屋"):
        if not addr_a or not addr_b:
            st.warning("請輸入兩個地址")
            st.stop()
        if not selected_categories and not keyword:
            st.warning("請至少選擇一個類別或輸入關鍵字")
            st.stop()

        lat_a, lng_a = geocode_address(addr_a, google_key)
        lat_b, lng_b = geocode_address(addr_b, google_key)
        if not lat_a or not lat_b:
            st.error("❌ 無法解析其中一個地址")
            st.stop()

        info_a = query_by_keyword(lat_a, lng_a, google_key, selected_categories, keyword, radius)
        info_b = query_by_keyword(lat_b, lng_b, google_key, selected_categories, keyword, radius)

        text_a = format_info(addr_a, info_a)
        text_b = format_info(addr_b, info_b)

        # 房屋 A 地圖
        st.subheader("📍 房屋 A 周邊地圖")
        m_a = folium.Map(location=[lat_a, lng_a], zoom_start=15)
        folium.Marker([lat_a, lng_a], popup=f"房屋 A：{addr_a}", icon=folium.Icon(color="red", icon="home")).add_to(m_a)
        folium.Circle([lat_a, lng_a], radius=radius, color="red", fill=True, fill_opacity=0.1).add_to(m_a)
        add_markers(m_a, info_a)
        html(m_a._repr_html_(), height=400)

        # 房屋 B 地圖
        st.subheader("📍 房屋 B 周邊地圖")
        m_b = folium.Map(location=[lat_b, lng_b], zoom_start=15)
        folium.Marker([lat_b, lng_b], popup=f"房屋 B：{addr_b}", icon=folium.Icon(color="blue", icon="home")).add_to(m_b)
        folium.Circle([lat_b, lng_b], radius=radius, color="blue", fill=True, fill_opacity=0.1).add_to(m_b)
        add_markers(m_b, info_b)
        html(m_b._repr_html_(), height=400)

        # Gemini 分析
        prompt = f"""你是一位房地產分析專家，請比較以下兩間房屋的生活機能，
        並列出優缺點與結論：
        {text_a}
        {text_b}
        """
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        st.subheader("📊 Gemini 分析結果")
        st.write(response.text)

        st.sidebar.subheader("🏠 房屋資訊對照表")
        st.sidebar.markdown(f"### 房屋 A\n{text_a}")
        st.sidebar.markdown(f"### 房屋 B\n{text_b}")

else:
    st.info("請先輸入 Google Maps 與 Gemini API Key")
