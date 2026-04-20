"""
动态路由模块
负责根据多维决策选择最佳的模型路由
"""
import requests
from config import API_CONFIG


class DynamicRouter:
    """动态路由器，支持多维决策"""
    
    def __init__(self, network_monitor, knowledge_base):
        self.network_monitor = network_monitor
        self.knowledge_base = knowledge_base
        # 设置默认隐私检测阈值
        self.privacy_threshold = 0.85  # 默认隐私检测阈值
        # 设置默认复杂度阈值
        self.complexity_threshold = 0.25  # 默认复杂度阈值
        # 设置默认检测功能开关
        self.enable_cache_check = True
        self.enable_network_check = True
        self.enable_complexity_check = True
        self.enable_privacy_check = True

    def set_privacy_threshold(self, threshold):
        """设置隐私检测阈值"""
        self.privacy_threshold = threshold
    
    def set_complexity_threshold(self, threshold):
        """设置复杂度阈值"""
        self.complexity_threshold = threshold
    
    def set_detection_flags(self, enable_cache=True, enable_network=True, 
                           enable_complexity=True, enable_privacy=True):
        """设置检测功能开关"""
        self.enable_cache_check = enable_cache
        self.enable_network_check = enable_network
        self.enable_complexity_check = enable_complexity
        self.enable_privacy_check = enable_privacy
    
    def check_cloud_connectivity(self):
        """检测云端主机连接状态"""
        # 复用NetworkMonitor的检测功能
        api_available, _, _ = self.network_monitor.check_cloud_api_status()
        return api_available

    def check_privacy_score(self, prompt, history, force_cloud_mode=False):
        """检测隐私分值"""
        # 如果强制云端模式，跳过隐私检测
        if force_cloud_mode:
            print("DEBUG: 云端模式，跳过隐私检测")
            return 0.0

        # 构建聊天历史，包含当前问题
        chat_history = history + [{"role": "user", "content": prompt}]

        # 只在本地模式下进行隐私检测
        try:
            local_host = API_CONFIG["local"]
            response = requests.post(
                f"{local_host}/privacy_check",
                json={
                    "chat_history": chat_history,
                    "get_details": False
                },
                timeout=2  # 使用2秒超时
            )

            if response.status_code == 200:
                result = response.json()
                privacy_score = result.get("privacy_score", 0.0)
                print(f"DEBUG: 本地隐私检测成功，分数: {privacy_score}")
                return privacy_score
            else:
                print(f"DEBUG: 本地隐私检测失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"DEBUG: 本地隐私检测异常: {str(e)}")

        # 隐私检测失败，返回0分（安全起见）
        print("DEBUG: 隐私检测失败，跳过隐私检查")
        return 0.0

    def check_complexity_analysis(self, prompt, history):
        """检测问题复杂度分析"""
        try:
            local_host = API_CONFIG["local"]
            response = requests.post(
                f"{local_host}/complexity/route",
                json={"query": prompt},
                timeout=3  # 使用3秒超时
            )

            if response.status_code == 200:
                result = response.json()
                complexity_data = result.get("routing_result", {})
                complexity_analysis = complexity_data.get("complexity_analysis", {})
                print(f"DEBUG: 复杂度分析成功，复杂度: {complexity_analysis.get('total_complexity', 0.0):.3f}")
                return {
                    "complexity_score": complexity_analysis.get("total_complexity", 0.0),
                    "route": complexity_data.get("route", "local"),
                    "confidence": complexity_data.get("confidence", 0.5),
                    "explanation": complexity_data.get("explanation", ""),
                    "recommendations": complexity_data.get("recommendations", []),
                    "network_status": result.get("network_status", {}),
                    # 五维评分详情
                    "query_length": complexity_analysis.get("query_length", 0.0),
                    "keyword_richness": complexity_analysis.get("keyword_richness", 0.0),
                    "semantic_depth": complexity_analysis.get("semantic_depth", 0.0),
                    "domain_specificity": complexity_analysis.get("domain_specificity", 0.0),
                    "reasoning_requirements": complexity_analysis.get("reasoning_requirements", 0.0)
                }
            else:
                print(f"DEBUG: 复杂度分析失败，状态码: {response.status_code}")
            return {
                "complexity_score": 0.5,
                "route": "local",
                "confidence": 0.3,
                "explanation": "复杂度分析失败，使用默认值",
                "recommendations": [],
                "network_status": {"cloud_available": False}
            }
        except Exception as e:
            print(f"DEBUG: 复杂度分析异常: {str(e)}")
            return {
                "complexity_score": 0.5,
                "route": "local",
                "confidence": 0.3,
                "explanation": "复杂度分析异常，使用默认值",
                "recommendations": [],
                "network_status": {"cloud_available": False}
            }

    def decide_route(self, prompt, history, force_cloud_mode=False):
        """决策路由选择"""
        # 0. 缓存检测（如果启用）
        if self.enable_cache_check:
            cached_response = self.knowledge_base.get_cached_response(prompt)
            if cached_response:
                return "local", "cache_hit"

        # 1. 网络检测（如果启用）
        is_cloud_available = True  # 默认假设云端可用
        if self.enable_network_check:
            is_cloud_available = self.check_cloud_connectivity()
            if not is_cloud_available and not force_cloud_mode:
                return "local", "cloud_unavailable"
        elif not force_cloud_mode:
            # 如果网络检测关闭，默认假设云端可用
            is_cloud_available = True

        # 如果强制云端模式且云端可用，直接返回云端
        if force_cloud_mode and is_cloud_available:
            return "cloud", "user_selected_cloud"

        # 2. 隐私检测（如果启用）
        if self.enable_privacy_check:
            privacy_score = self.check_privacy_score(prompt, history, force_cloud_mode)
            if privacy_score > self.privacy_threshold:
                return "local", f"privacy_protection (score: {privacy_score:.2f})"

        # 3. 复杂度检测（如果启用）
        if self.enable_complexity_check:
            complexity_result = self.check_complexity_analysis(prompt, history)
            complexity_score = complexity_result.get("complexity_score", 0.5)
            
            # 根据复杂度分析结果进行路由决策
            if complexity_score > self.complexity_threshold and is_cloud_available:
                return "cloud", f"complexity_analysis (score: {complexity_score:.2f}, high_complexity)"
            else:
                return "local", f"complexity_analysis (score: {complexity_score:.2f}, low_complexity)"
        else:
            # 如果复杂度检测关闭，默认使用云端（如果可用）
            if is_cloud_available:
                return "cloud", "default_cloud_preferred"
            else:
                return "local", "default_local_fallback"

    def get_route_info(self, route, reason, model, complexity_data=None):
        """获取路由信息"""
        route_info = {
            "route": route,
            "reason": reason,
            "model": model,
            "is_auto": model == "自动",
            "complexity_data": complexity_data
        }

        if route == "local":
            if reason == "cloud_unavailable":
                route_info["message"] = "🌐 云端服务不可用，已自动切换到本地模型"
            elif reason.startswith("privacy_protection"):
                route_info["message"] = f"🔒 检测到隐私敏感内容（阈值: {self.privacy_threshold}），已自动切换到本地模型保护您的隐私"
            elif reason == "cache_hit":
                route_info["message"] = "💾 使用本地缓存回答"
            elif reason.startswith("complexity_analysis"):
                if complexity_data:
                    complexity_score = complexity_data.get("complexity_score", 0.0)
                    route_info["message"] = f"🧠 复杂度分析建议本地处理（复杂度: {complexity_score:.2f}）"
                else:
                    route_info["message"] = f"💻 本地模式: {reason}"
            else:
                route_info["message"] = f"💻 本地模式: {reason}"
        else:
            if reason.startswith("complexity_analysis"):
                if complexity_data:
                    complexity_score = complexity_data.get("complexity_score", 0.0)
                    route_info["message"] = f"🧠 复杂度分析建议云端处理（复杂度: {complexity_score:.2f}）"
                else:
                    route_info["message"] = "🤖 正在检索文档并生成回答..."
            else:
                route_info["message"] = "🤖 正在检索文档并生成回答..."

        return route_info
