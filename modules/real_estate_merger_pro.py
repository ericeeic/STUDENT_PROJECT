import os
import requests
import zipfile
import pandas as pd
import glob

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
    zip_path = download_zip(season_code)
    extract_to = f"./data/lvr_landcsv_{season_code}"
    unzip_file(zip_path, extract_to)
    
    result = process_real_estate_data(extract_to)
    if result is not None:
        os.makedirs("output", exist_ok=True)
        output_file = f"./output/合併後不動產統計_{season_code}.csv"
        result.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"📄 統計完成，已輸出: {output_file}")
    else:
        print("⚠️ 資料處理失敗")

if __name__ == "__main__":
    season = input("請輸入欲下載的期數（例如：114S2）：").strip()
    main(season)
