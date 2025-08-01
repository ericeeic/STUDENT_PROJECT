import requests
import re

def get_seasons():
    url = "https://plvr.land.moi.gov.tw/DownloadSeason_ajax_list"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://plvr.land.moi.gov.tw/DownloadOpenData'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            html = response.text
            
            # 提取季度選項
            pattern = r'<option[^>]*value=["\']([^"\']*\d+S\d+[^"\']*)["\'[^>]*>([^<]*\d+年第\d+季[^<]*)</option>'
            matches = re.findall(pattern, html, re.IGNORECASE)
            
            if matches:
                return [(value.strip(), text.strip()) for value, text in matches]
            
            # 備用模式
            pattern2 = r'<option[^>]*value=["\']([^"\']*S\d+[^"\']*)["\'[^>]*>([^<]*季[^<]*)</option>'
            matches2 = re.findall(pattern2, html, re.IGNORECASE)
            if matches2:
                return [(value.strip(), text.strip()) for value, text in matches2]
                
    except Exception as e:
        print(f"錯誤: {e}")
    
    return []

# 執行
seasons = get_seasons()

if seasons:
    print(f"✓ 找到 {len(seasons)} 個季度:")
    for value, text in seasons:
        print(f"{value} -> {text}")
    
    # 輸出程式碼格式
    values = [s[0] for s in seasons]
    print(f"\n# 季度代碼列表")
    print(f"seasons = {values}")
    
    # 字典格式
    season_dict = {s[0]: s[1] for s in seasons}
    print(f"\n# 季度字典")
    print(f"season_dict = {season_dict}")
else:
    print("未找到季度資料")
