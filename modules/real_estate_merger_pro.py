import os
import requests
import zipfile
import pandas as pd
import glob

import base64
import json

# 你的城市對照表和 classify_building_age 函式保持不變
city_code_map = {
    "a": "台北市", "b": "台中市", "c": "基隆市", "d": "台南市", "e": "高雄市",
    "f": "新北市", "g": "宜蘭縣", "h": "桃園市", "i": "嘉義市", "j": "新竹縣",
    "k": "苗栗縣", "m": "南投縣", "n": "彰化縣", "o": "新竹市",
    "p": "雲林縣", "q": "嘉義縣", "t": "屏東縣",
    "u": "花蓮縣", "v": "台東縣", "w": "金門縣", "x": "澎湖縣", "z": "連江縣"
}

def classify_building_age(age):
    if pd.isna(age):
        return None
    age = float(age)
    if age == 0:
        return "預售屋"
    elif 0 < age <= 5:
        return "新成屋"
    else:
        return "中古屋"

def season_code_to_chinese_quarter(season_code):
    if len(season_code) == 5 and season_code[3] == 'S':
        year = season_code[:3]
        quarter_map = {'1': '第一季', '2': '第二季', '3': '第三季', '4': '第四季'}
        quarter = quarter_map.get(season_code[-1], '未知季度')
        return f"{year}年{quarter}"
    return "未知季度"

def convert_season_code_input(season_code: str) -> str:
    # 將 11401 -> 114S1 的格式
    if len(season_code) == 5 and season_code.isdigit():
        year = season_code[:3]
        quarter = season_code[3:]
        if quarter in ['01', '02', '03', '04']:
            return f"{year}S{int(quarter)}"
    return season_code  # 若已是正確格式或格式不符則不變動


def convert_season_code_for_export(season_code: str) -> str:
    """
    將 S 格式轉換為 0 格式，用於檔名
    例如：114S1 -> 11401, 114S2 -> 11402
    """
    if len(season_code) == 5 and season_code[3] == 'S':
        year = season_code[:3]
        quarter = season_code[-1]
        return f"{year}0{quarter}"
    return season_code

def github_push_file(repo_owner, repo_name, branch, file_path, commit_message, github_token):
    """
    將本地檔案推送（新增或更新）到 GitHub repo。
    
    參數:
    - repo_owner: GitHub 擁有者帳號或組織名
    - repo_name: 倉庫名
    - branch: 要推送的分支名稱
    - file_path: 本地檔案路徑
    - commit_message: Commit 訊息
    - github_token: GitHub Personal Access Token
    """
    # 目標 repo 的 API URL 路徑
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{os.path.basename(file_path)}"
    
    # 先取得該檔案是否已存在(拿 SHA)
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json"
    }
    
    params = {
        "ref": branch
    }
    
    response = requests.get(api_url, headers=headers, params=params)
    
    if response.status_code == 200:
        # 檔案存在，取得 sha
        sha = response.json()["sha"]
    elif response.status_code == 404:
        # 檔案不存在，sha None
        sha = None
    else:
        print(f"取得檔案資訊失敗，狀態碼: {response.status_code}")
        print(response.text)
        return False
    
    # 讀取檔案並 base64 encode
    with open(file_path, "rb") as f:
        content = f.read()
    content_b64 = base64.b64encode(content).decode()
    
    data = {
        "message": commit_message,
        "content": content_b64,
        "branch": branch,
    }
    if sha:
        data["sha"] = sha
    
    put_resp = requests.put(api_url, headers=headers, data=json.dumps(data))
    
    if put_resp.status_code in [200, 201]:
        print(f"成功推送檔案到 GitHub: {file_path}")
        return True
    else:
        print(f"推送失敗，狀態碼: {put_resp.status_code}")
        print(put_resp.text)
        return False

def download_zip(season_code):
    base_url = "https://plvr.land.moi.gov.tw/DownloadSeason"
    params = {
        "season": season_code,
        "type": "zip",
        "fileName": "lvr_landcsv.zip"
    }
    response = requests.get(base_url, params=params, stream=True)

    if response.status_code == 200:
        os.makedirs("data", exist_ok=True)
        zip_path = f"./data/moi_data_{season_code}.zip"
        with open(zip_path, "wb") as f:
            f.write(response.content)
        print(f"✅ 已下載：{zip_path}")
        return zip_path
    else:
        raise Exception(f"下載失敗，狀態碼：{response.status_code}")

def unzip_file(zip_path, extract_to):
    os.makedirs(extract_to, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"✅ 已解壓縮至：{extract_to}")

def process_real_estate_data(data_folder_path):
    all_data = []
    
    land_files = glob.glob(os.path.join(data_folder_path, "*_lvr_land_*.csv"))
    
    for land_file in land_files:
        filename = os.path.basename(land_file)
        city_code = filename[0].lower()
        
        if city_code not in city_code_map:
            print(f"警告: 未知的城市代碼 {city_code} 在檔案 {filename}")
            continue
        
        city_name = city_code_map[city_code]
        build_file = land_file.replace('.csv', '_build.csv')
        
        if not os.path.exists(build_file):
            print(f"警告: 找不到對應的建物檔案 {build_file}")
            continue
        
        try:
            print(f"處理 {city_name} 的資料...")
            land_df = pd.read_csv(land_file)
            build_df = pd.read_csv(build_file)
            
            land_df.columns = land_df.columns.str.strip()
            build_df.columns = build_df.columns.str.strip()
            
            serial_columns = ['編號', 'The serial number', '序號']
            land_serial_col = next((col for col in serial_columns if col in land_df.columns), None)
            build_serial_col = next((col for col in serial_columns if col in build_df.columns), None)
            
            if land_serial_col is None or build_serial_col is None:
                print(f"警告: 無法找到編號欄位在檔案 {filename}")
                continue
            
            district_col = next((col for col in ['鄉鎮市區', '行政區'] if col in land_df.columns), None)
            price_col = next((col for col in ['單價元平方公尺', '平方公尺單價(元)', '單價(元/平方公尺)'] if col in land_df.columns), None)
            age_col = next((col for col in ['屋齡', 'room age', '建物完成年月'] if col in build_df.columns), None)
            target_col = next((col for col in ['交易標的'] if col in land_df.columns), None)
            zone_col = next((col for col in ['都市土地使用分區'] if col in land_df.columns), None)
            
            if None in [district_col, price_col, age_col, target_col, zone_col]:
                print(f"警告: 必要欄位缺失，跳過檔案 {filename}")
                continue
            
            land_df_filtered = land_df[land_df[target_col] != '車位']
            land_df_filtered = land_df_filtered[land_df_filtered[zone_col].str.contains('住', na=False)]
            
            merged_df = pd.merge(
                land_df_filtered[[land_serial_col, district_col, price_col]],
                build_df[[build_serial_col, age_col]],
                left_on=land_serial_col,
                right_on=build_serial_col,
                how='inner'
            )
            
            merged_df = merged_df.dropna(subset=[age_col])
            
            merged_df[price_col] = pd.to_numeric(merged_df[price_col], errors='coerce')
            merged_df[age_col] = pd.to_numeric(merged_df[age_col], errors='coerce')
            
            merged_df = merged_df[(merged_df[price_col] > 0) & (merged_df[price_col].notna())]
            
            merged_df['縣市'] = city_name
            merged_df['BUILD'] = merged_df[age_col].apply(classify_building_age)
            
            merged_df = merged_df.rename(columns={
                district_col: '行政區',
                price_col: '單價元平方公尺'
            })
            
            final_df = merged_df[['縣市', '行政區', 'BUILD', '單價元平方公尺']].copy()
            all_data.append(final_df)
            
        except Exception as e:
            print(f"錯誤: 處理檔案 {filename} 時發生錯誤: {e}")
            continue
    
    if not all_data:
        print("錯誤: 沒有成功處理任何檔案")
        return None
    
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.dropna(subset=['BUILD'])
    
    result_df = combined_df.groupby(['縣市', '行政區', 'BUILD']).agg({
        '單價元平方公尺': ['mean', 'count']
    }).round(2)
    
    result_df.columns = ['平均單價元平方公尺', '交易筆數']
    result_df = result_df.reset_index()
    return result_df

def main(season_code):
    season_code_2 = convert_season_code_input(season_code)  # 加這行做轉換

    zip_path = download_zip(season_code_2)
    extract_to = f"./data/lvr_landcsv_{season_code_2}"
    unzip_file(zip_path, extract_to)

    result = process_real_estate_data(extract_to)
    if result is not None:
        quarter_str = season_code_to_chinese_quarter(season_code_2)
        result['季度'] = [quarter_str] * len(result)

        os.makedirs("output", exist_ok=True)
        export_season_code = convert_season_code_for_export(season_code_2)
        output_file = f"./output/合併後不動產統計_{export_season_code}.csv"
        result.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"📄 統計完成，已輸出: {output_file}")

        repo_owner = "ericeeic"
        repo_name = "STUDENT_PROJECT"
        branch = "main"
        commit_message = f"更新統計資料 {season_code_2}"
        github_token = os.environ.get("GITHUB_TOKEN")

        if github_token:
            github_push_file(repo_owner, repo_name, branch, output_file, commit_message, github_token)
        else:
            print("❌ 找不到 GITHUB_TOKEN，請確認是否有設定環境變數")
    else:
        print("⚠️ 資料處理失敗")

if __name__ == "__main__":
    season = input("請輸入欲下載的期數（例如：114S2）：").strip()
    main(season)












