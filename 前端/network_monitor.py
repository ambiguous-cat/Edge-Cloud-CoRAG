"""
网络状态监控模块
负责检测网络连接状态和云端API状态
"""
import requests
import time
import threading
from config import API_CONFIG


class NetworkMonitor:
    """网络状态检测类"""
    
    def __init__(self):
        self.online = True
        self.last_check = time.time()
        self.check_interval = 30  # 每30秒检查一次网络状态
        self.cloud_latency = None  # 云端API延迟
        self.cloud_status = "未知"  # 云端API状态
        
    def check_network_status(self):
        """检查网络连接状态"""
        try:
            # 尝试连接一个网站
            requests.get("https://www.baidu.com", timeout=3)
            self.online = True
        except:
            self.online = False
        self.last_check = time.time()
        return self.online
    
    def check_cloud_api_status(self, timeout=2.0):
        """检查云端API主机状态和延迟，默认2秒超时"""
        try:
            cloud_host = API_CONFIG["cloud"]
            start_time = time.time()
            
            # 测试API主机的docs端点，2秒超时
            response = requests.get(f"{cloud_host}/docs", timeout=timeout)
            end_time = time.time()
            
            latency_ms = round((end_time - start_time) * 1000, 2)
            
            if response.status_code == 200:
                self.cloud_status = "正常"
                self.cloud_latency = latency_ms
                return True, latency_ms, "正常"
            else:
                self.cloud_status = f"错误 ({response.status_code})"
                self.cloud_latency = latency_ms
                return False, latency_ms, f"错误 ({response.status_code})"
                
        except requests.exceptions.Timeout:
            self.cloud_status = "超时"
            self.cloud_latency = None
            return False, None, "超时"
        except requests.exceptions.ConnectionError:
            self.cloud_status = "连接失败"
            self.cloud_latency = None
            return False, None, "连接失败"
        except Exception as e:
            self.cloud_status = f"异常: {str(e)[:20]}"
            self.cloud_latency = None
            return False, None, f"异常: {str(e)[:20]}"
    
    def start_monitoring(self):
        """启动网络状态监控线程"""
        def monitor_loop():
            while True:
                self.check_network_status()
                time.sleep(self.check_interval)
                
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        
    def get_status(self):
        """获取当前网络状态"""
        # 如果超过检查间隔，重新检查
        if time.time() - self.last_check > self.check_interval:
            self.check_network_status()
        return self.online

    def get_network_display_info(self):
        """获取网络状态显示信息"""
        # 检查基础网络连接
        is_online = self.get_status()
        
        # 检查云端API状态
        api_available, latency, status = self.check_cloud_api_status()
        
        # 构建状态显示文本
        if is_online:
            base_status = "🌐 **网络状态**: 在线"
        else:
            base_status = "🌐 **网络状态**: 离线"
        
        # 添加云端API状态信息
        if api_available and latency is not None:
            api_status = f"☁️ **云端API**: {status} (延迟: {latency}ms)"
            if latency < 100:
                speed_indicator = "🟢 极快"
            elif latency < 300:
                speed_indicator = "🟡 正常"
            elif latency < 1000:
                speed_indicator = "🟠 较慢"
            else:
                speed_indicator = "🔴 很慢"
            api_status += f" {speed_indicator}"
        else:
            api_status = f"☁️ **云端API**: {status} ❌"
        
        return f"{base_status}\n{api_status}"
