import os
import re
import requests
from bs4 import BeautifulSoup

def get_local_periods(folder="./"):
    pattern = re.compile(r"合併後不動產統計_(\d{5})\.csv")
    periods = []
    for fname in os.listdir(folder):
        match = pattern.match(fname)
        if match:
            periods.append(match.group(1))
    return sorted(periods)

def get_available_periods_from_moi():
    """從內政部網站獲取可用的期數"""
    url = "https://plvr.land.moi.gov.tw/DownloadSeason_ajax_list"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://plvr.land.moi.gov.tw/DownloadOpenData'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"請求失敗，狀態碼: {response.status_code}")
            return []
        
        html = response.text
        
        # 提取季度選項
        pattern = r'<option[^>]*value=["\']([^"\']*\d+S\d+[^"\']*)["\'[^>]*>([^<]*\d+年第\d+季[^<]*)</option>'
        matches = re.findall(pattern, html, re.IGNORECASE)
        
        if not matches:
            # 備用模式
            pattern2 = r'<option[^>]*value=["\']([^"\']*S\d+[^"\']*)["\'[^>]*>([^<]*季[^<]*)</option>'
            matches = re.findall(pattern2, html, re.IGNORECASE)
        
        periods = []
        for value, text in matches:
            # 解析季度代碼，如 "114S2" -> "11402"
            match = re.match(r"(\d{3})S([1-4])", value)
            if match:
                year = match.group(1)
                season = match.group(2)
                periods.append(f"{year}S{season}")  # 轉成 5碼格式
        
        return sorted(periods)
        
    except Exception as e:
        print(f"獲取線上期數失敗: {e}")
        return []

def find_missing_periods(local_periods, web_periods):
    """找出缺少的期數"""
    return sorted(set(web_periods) - set(local_periods))

def check_missing_periods(folder="./"):
    """檢查缺少的期數"""
    local = get_local_periods(folder)
    online = get_available_periods_from_moi()
    missing = find_missing_periods(local, online)
    
    return local, online, missing        
