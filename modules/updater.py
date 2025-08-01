import pandas as pd
import requests
import zipfile
import io
import os
from datetime import datetime
import json
import base64
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class DataUpdateResult:
    """資料更新結果類別"""
    
    def __init__(self, success: bool, message: str, data: Dict = None):
        self.success = success
        self.message = message
        self.data = data or {}
        self.timestamp = datetime.now()
    
    def to_dict(self):
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }


class DataUpdater:
    """純功能資料更新器 - 不包含任何UI組件"""
    
    def __init__(self, config: Dict):
        """
        初始化資料更新器
        
        Args:
            config (dict): 配置字典
                - data_source_url: 資料來源URL（必須）
                - local_data_path: 本地資料路徑（預設: ./data）
                - github_token: GitHub token（可選）
                - repo_owner: GitHub repo擁有者（可選）
                - repo_name: GitHub repo名稱（可選）
                - github_path: GitHub存儲路徑（可選）
                - period_format: 期數格式（預設: %Y-%m）
                - file_extensions: 支援的檔案類型（預設: ['.csv', '.xlsx', '.json']）
        """
        self.config = {
            "local_data_path": "./data",
            "github_path": "data",
            "period_format": "%Y-%m",
            "file_extensions": ['.csv', '.xlsx', '.json'],
            **config
        }
        
        if not self.config.get("data_source_url"):
            raise ValueError("data_source_url 是必須的配置項")
    
    def check_latest_period(self) -> DataUpdateResult:
        """
        檢查最新期數
        
        Returns:
            DataUpdateResult: 包含最新期數資訊
        """
        try:
            url = self.config["data_source_url"]
            response = requests.get(url, timeout=10, stream=True)
            response.raise_for_status()
            
            # 嘗試從不同來源獲取期數資訊
            latest_period = None
            available_periods = []
            
            # 方法1: 從JSON API獲取
            content_type = response.headers.get('content-type', '').lower()
            if 'application/json' in content_type:
                data = response.json()
                latest_period = data.get("latest_period")
                available_periods = data.get("available_periods", [])
            
            # 方法2: 從URL推斷
            elif not latest_period:
                # 嘗試從URL中提取日期資訊
                import re
                date_pattern = r'(\d{4})[_-]?(\d{1,2})'
                match = re.search(date_pattern, url)
                if match:
                    year, month = match.groups()
                    latest_period = f"{year}-{month.zfill(2)}"
                else:
                    # 使用當前日期
                    current_date = datetime.now()
                    latest_period = current_date.strftime(self.config["period_format"])
                
                available_periods = [latest_period]
            
            return DataUpdateResult(
                success=True,
                message=f"成功獲取最新期數: {latest_period}",
                data={
                    "latest_period": latest_period,
                    "available_periods": available_periods,
                    "source_url": url
                }
            )
            
        except Exception as e:
            return DataUpdateResult(
                success=False,
                message=f"檢查最新期數失敗: {str(e)}"
            )
    
    def get_local_data_info(self) -> DataUpdateResult:
        """
        獲取本地資料資訊
        
        Returns:
            DataUpdateResult: 包含本地資料統計
        """
        try:
            local_path = self.config["local_data_path"]
            extensions = self.config["file_extensions"]
            
            files_info = []
            total_size = 0
            last_modified = None
            
            if os.path.exists(local_path):
                for root, dirs, files in os.walk(local_path):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in extensions):
                            file_path = os.path.join(root, file)
                            try:
                                stat = os.stat(file_path)
                                modified_time = datetime.fromtimestamp(stat.st_mtime)
                                
                                files_info.append({
                                    "name": file,
                                    "path": file_path,
                                    "size": stat.st_size,
                                    "modified": modified_time.isoformat(),
                                    "relative_path": os.path.relpath(file_path, local_path)
                                })
                                
                                total_size += stat.st_size
                                
                                if last_modified is None or modified_time > last_modified:
                                    last_modified = modified_time
                            except OSError:
                                continue
            
            return DataUpdateResult(
                success=True,
                message=f"成功獲取本地資料資訊: {len(files_info)} 個檔案",
                data={
                    "files": files_info,
                    "file_count": len(files_info),
                    "total_size": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "last_modified": last_modified.isoformat() if last_modified else None,
                    "local_path": local_path
                }
            )
            
        except Exception as e:
            return DataUpdateResult(
                success=False,
                message=f"獲取本地資料資訊失敗: {str(e)}"
            )
    
    def download_data(self, target_path: str = None) -> DataUpdateResult:
        """
        下載資料檔案
        
        Args:
            target_path: 目標路徑，預設使用配置中的路徑
            
        Returns:
            DataUpdateResult: 下載結果
        """
        try:
            if target_path is None:
                target_path = self.config["local_data_path"]
            
            url = self.config["data_source_url"]
            
            # 創建目標目錄
            os.makedirs(target_path, exist_ok=True)
            
            # 下載檔案
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            content_size = len(response.content)
            
            extracted_files = []
            
            # 處理ZIP檔案
            if 'zip' in content_type or url.lower().endswith('.zip'):
                zip_buffer = io.BytesIO(response.content)
                with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                    # 獲取檔案列表
                    file_list = zip_file.namelist()
                    
                    # 只解壓支援的檔案類型
                    extensions = self.config["file_extensions"]
                    for file_name in file_list:
                        if any(file_name.lower().endswith(ext) for ext in extensions):
                            zip_file.extract(file_name, target_path)
                            extracted_files.append(file_name)
                
                message = f"成功下載並解壓 {len(extracted_files)} 個檔案"
            
            # 處理單一檔案
            else:
                filename = url.split('/')[-1] or f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # 確保檔案有適當的副檔名
                if not any(filename.lower().endswith(ext) for ext in self.config["file_extensions"]):
                    filename += ".csv"  # 預設為CSV
                
                file_path = os.path.join(target_path, filename)
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                extracted_files.append(filename)
                message = f"成功下載檔案: {filename}"
            
            return DataUpdateResult(
                success=True,
                message=message,
                data={
                    "extracted_files": extracted_files,
                    "file_count": len(extracted_files),
                    "download_size": content_size,
                    "download_size_mb": round(content_size / (1024 * 1024), 2),
                    "target_path": target_path,
                    "source_url": url
                }
            )
            
        except Exception as e:
            return DataUpdateResult(
                success=False,
                message=f"下載資料失敗: {str(e)}"
            )
    
    def upload_to_github(self, local_path: str = None, github_path: str = None) -> DataUpdateResult:
        """
        上傳檔案到GitHub
        
        Args:
            local_path: 本地路徑
            github_path: GitHub路徑
            
        Returns:
            DataUpdateResult: 上傳結果
        """
        try:
            # 檢查GitHub配置
            required_keys = ["github_token", "repo_owner", "repo_name"]
            missing_keys = [key for key in required_keys if not self.config.get(key)]
            
            if missing_keys:
                return DataUpdateResult(
                    success=False,
                    message=f"GitHub配置不完整，缺少: {', '.join(missing_keys)}"
                )
            
            if local_path is None:
                local_path = self.config["local_data_path"]
            if github_path is None:
                github_path = self.config["github_path"]
            
            headers = {
                "Authorization": f"token {self.config['github_token']}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            uploaded_files = []
            failed_files = []
            
            # 遍歷本地檔案
            extensions = self.config["file_extensions"]
            
            for root, dirs, files in os.walk(local_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in extensions):
                        local_file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(local_file_path, local_path)
                        github_file_path = f"{github_path}/{relative_path}".replace("\\", "/")
                        
                        try:
                            # 讀取檔案內容
                            with open(local_file_path, 'rb') as f:
                                content = f.read()
                            
                            # GitHub API URL
                            api_url = f"https://api.github.com/repos/{self.config['repo_owner']}/{self.config['repo_name']}/contents/{github_file_path}"
                            
                            # 檢查檔案是否已存在
                            check_response = requests.get(api_url, headers=headers)
                            sha = check_response.json().get("sha") if check_response.status_code == 200 else None
                            
                            # 準備上傳資料
                            upload_data = {
                                "message": f"更新資料檔案: {file} ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
                                "content": base64.b64encode(content).decode()
                            }
                            
                            if sha:
                                upload_data["sha"] = sha
                            
                            # 上傳檔案
                            upload_response = requests.put(api_url, headers=headers, json=upload_data)
                            
                            if upload_response.status_code in [200, 201]:
                                uploaded_files.append({
                                    "name": file,
                                    "path": github_file_path,
                                    "size": len(content)
                                })
                            else:
                                failed_files.append({
                                    "name": file,
                                    "error": upload_response.text
                                })
                        
                        except Exception as file_error:
                            failed_files.append({
                                "name": file,
                                "error": str(file_error)
                            })
            
            if failed_files:
                return DataUpdateResult(
                    success=False,
                    message=f"部分檔案上傳失敗: {len(failed_files)} 個失敗，{len(uploaded_files)} 個成功",
                    data={
                        "uploaded_files": uploaded_files,
                        "failed_files": failed_files,
                        "success_count": len(uploaded_files),
                        "fail_count": len(failed_files)
                    }
                )
            
            return DataUpdateResult(
                success=True,
                message=f"成功上傳 {len(uploaded_files)} 個檔案到GitHub",
                data={
                    "uploaded_files": uploaded_files,
                    "success_count": len(uploaded_files),
                    "repo_url": f"https://github.com/{self.config['repo_owner']}/{self.config['repo_name']}/tree/main/{github_path}"
                }
            )
            
        except Exception as e:
            return DataUpdateResult(
                success=False,
                message=f"GitHub上傳失敗: {str(e)}"
            )
    
    def check_update_needed(self) -> DataUpdateResult:
        """
        檢查是否需要更新
        
        Returns:
            DataUpdateResult: 檢查結果
        """
        try:
            # 獲取最新期數
            latest_result = self.check_latest_period()
            if not latest_result.success:
                return latest_result
            
            latest_period = latest_result.data["latest_period"]
            
            # 獲取本地資料資訊
            local_result = self.get_local_data_info()
            if not local_result.success:
                return local_result
            
            local_files = local_result.data["files"]
            
            # 判斷是否需要更新
            need_update = True
            reason = "初次下載"
            
            if local_files:
                # 檢查檔案是否包含最新期數資訊
                # 這裡可以根據你的檔案命名規則調整
                has_latest_period = any(
                    latest_period in file["name"] or 
                    latest_period.replace("-", "") in file["name"]
                    for file in local_files
                )
                
                if has_latest_period:
                    need_update = False
                    reason = "資料已是最新"
                else:
                    reason = f"本地資料不包含最新期數 {latest_period}"
            
            return DataUpdateResult(
                success=True,
                message=reason,
                data={
                    "need_update": need_update,
                    "latest_period": latest_period,
                    "local_file_count": len(local_files),
                    "reason": reason
                }
            )
            
        except Exception as e:
            return DataUpdateResult(
                success=False,
                message=f"檢查更新狀態失敗: {str(e)}"
            )
    
    def perform_full_update(self) -> DataUpdateResult:
        """
        執行完整的更新流程
        
        Returns:
            DataUpdateResult: 完整更新結果
        """
        try:
            update_steps = []
            
            # 1. 檢查是否需要更新
            check_result = self.check_update_needed()
            update_steps.append({
                "step": "檢查更新",
                "success": check_result.success,
                "message": check_result.message
            })
            
            if not check_result.success:
                return DataUpdateResult(
                    success=False,
                    message="更新檢查失敗",
                    data={"steps": update_steps}
                )
            
            if not check_result.data["need_update"]:
                return DataUpdateResult(
                    success=True,
                    message="本地資料已是最新，無需更新",
                    data={
                        "steps": update_steps,
                        "latest_period": check_result.data["latest_period"],
                        "skipped": True
                    }
                )
            
            # 2. 下載新資料
            download_result = self.download_data()
            update_steps.append({
                "step": "下載資料",
                "success": download_result.success,
                "message": download_result.message
            })
            
            if not download_result.success:
                return DataUpdateResult(
                    success=False,
                    message="資料下載失敗",
                    data={"steps": update_steps}
                )
            
            # 3. 上傳到GitHub（如果配置了）
            if self.config.get("github_token"):
                github_result = self.upload_to_github()
                update_steps.append({
                    "step": "GitHub同步",
                    "success": github_result.success,
                    "message": github_result.message
                })
                
                # GitHub同步失敗不影響整體成功
                if not github_result.success:
                    update_steps[-1]["warning"] = True
            
            return DataUpdateResult(
                success=True,
                message=f"更新完成！下載了 {download_result.data['file_count']} 個檔案",
                data={
                    "steps": update_steps,
                    "downloaded_files": download_result.data["extracted_files"],
                    "latest_period": check_result.data["latest_period"],
                    "download_size_mb": download_result.data["download_size_mb"]
                }
            )
            
        except Exception as e:
            return DataUpdateResult(
                success=False,
                message=f"更新流程失敗: {str(e)}"
            )


# 便利函數
def quick_update(data_source_url: str, local_path: str = "./data", **kwargs) -> DataUpdateResult:
    """
    快速更新函數
    
    Args:
        data_source_url: 資料來源URL
        local_path: 本地存儲路徑
        **kwargs: 其他配置參數
        
    Returns:
        DataUpdateResult: 更新結果
    """
    config = {
        "data_source_url": data_source_url,
        "local_data_path": local_path,
        **kwargs
    }
    
    updater = DataUpdater(config)
    return updater.perform_full_update()


# 使用範例
if __name__ == "__main__":
    # 基本使用
    config = {
        "data_source_url": "https://example.com/data.zip",
        "local_data_path": "./data",
        # GitHub配置（可選）
        "github_token": "your_token",
        "repo_owner": "your_username",
        "repo_name": "your_repo"
    }
    
    updater = DataUpdater(config)
    
    # 執行完整更新
    result = updater.perform_full_update()
    
    print(f"更新結果: {result.message}")
    print(f"成功: {result.success}")
    if result.data:
        print(f"詳細資訊: {result.data}")
