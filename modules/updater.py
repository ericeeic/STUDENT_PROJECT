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
    url = "https://plvr.land.moi.gov.tw/DownloadOpenData"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    select = soup.find("select", id="historySeason_id")
    if not select:
        return []

    options = select.find_all("option")
    periods = []
    for opt in options:
        val = opt.get("value", "")
        m = re.match(r"(\d{3})S([1-4])", val)
        if m:
            year = m.group(1)
            season = m.group(2)
            periods.append(f"{year}0{season}")  # 轉成 5碼，例如11402
    return sorted(periods)

    options = select.find_all("option")
    return sorted(opt["value"] for opt in options if re.match(r"\d{5}", opt["value"]))

def find_missing_periods(local_periods, web_periods):
    return sorted(set(web_periods) - set(local_periods))

def check_missing_periods(folder="./"):
    local = get_local_periods(folder)
    online = get_available_periods_from_moi()
    missing = find_missing_periods(local, online)
    return local, online, missing
