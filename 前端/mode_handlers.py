"""
三种独立模式的处理器
每个模式都有完整的处理逻辑，不相互依赖
"""
import requests
import time
from config import API_CONFIG, MODEL_MAP
from network_monitor import NetworkMonitor
from privacy_detector import create_privacy_detector
from complexity_analyzer import ComplexityAnalyzer


class BaseModeHandler:
    """基础模式处理器"""

    def __init__(self, network_monitor, knowledge_base):
        self.network_monitor = network_monitor
        self.knowledge_base = knowledge_base
        self.privacy_detector = create_privacy_detector()
        self.complexity_analyzer = ComplexityAnalyzer()

    def get_model_prefix(self):
        """获取模式前缀"""
        raise NotImplementedError

    def handle_request(self, prompt, history, retrieval_limit=5,
                       similarity_threshold=0.0, **kwargs):
        """处理请求的核心方法"""
        raise NotImplementedError


class AutoModeHandler(BaseModeHandler):
    """自动模式处理器 - 智能路由决策"""

    def __init__(self, network_monitor, knowledge_base):
        super().__init__(network_monitor, knowledge_base)
        self.privacy_threshold = 0.85
        self.complexity_threshold = 0.2  # 默认复杂度阈值

    def get_model_prefix(self):
        return "🤖【智能RAG】"

    def set_privacy_threshold(self, threshold):
        """设置隐私检测阈值"""
        self.privacy_threshold = threshold
    
    def set_complexity_threshold(self, threshold):
        """设置复杂度阈值"""
        self.complexity_threshold = threshold

    def _make_routing_decision(self, prompt, history):
        """智能路由决策"""
        # 1. 检测网络状态
        is_cloud_available = self.network_monitor.check_cloud_api_status()[0]

        # 2. 检测隐私分值
        chat_history = history + [{"role": "user", "content": prompt}]
        try:
            local_host = API_CONFIG["local"]
            response = requests.post(
                f"{local_host}/privacy_check",
                json={"chat_history": chat_history, "get_details": False},
                timeout=2
            )
            if response.status_code == 200:
                privacy_score = response.json().get("privacy_score", 0.0)
            else:
                privacy_score = 0.0
        except:
            privacy_score = 0.0

        # 3. 复杂度分析
        try:
            # ComplexityAnalyzer.analyze_complexity 直接返回各维度分数和 total_complexity
            complexity_result = self.complexity_analyzer.analyze_complexity(prompt)
            # 直接用 total_complexity 作为复杂度评分
            complexity_score = complexity_result.get("total_complexity", 0.5)
            complexity_data = complexity_result
        except Exception:
            complexity_data = {}
            complexity_score = 0.5

        # 4. 路由决策
        route = "local"
        reason = ""

        if not is_cloud_available:
            route = "local"
            reason = "cloud_unavailable"
        elif privacy_score > self.privacy_threshold:
            route = "local"
            reason = f"privacy_protection (score: {privacy_score:.2f})"
        elif complexity_score > self.complexity_threshold:
            # 复杂度高于阈值，且云端可用时优先云端
            route = "cloud"
            reason = f"high_complexity (score: {complexity_score:.2f})"
        elif self.knowledge_base.get_cached_response(prompt):
            route = "local"
            reason = "cache_hit"
        else:
            route = "cloud"
            reason = "default_cloud_preferred"

        return route, reason, privacy_score, complexity_data

    def handle_request(self, prompt, history, retrieval_limit=5,
                       similarity_threshold=0.0, **kwargs):
        """处理自动模式请求"""
        # 路由决策
        route, reason, privacy_score, complexity_data = self._make_routing_decision(prompt, history)

        # 根据路由结果选择具体的处理方式
        if route == "local":
            # 使用本地处理
            yield from self._handle_local_processing(
                prompt, history, retrieval_limit, similarity_threshold,
                reason, privacy_score, complexity_data, is_auto_mode=True
            )
        else:
            # 使用云端处理
            yield from self._handle_cloud_processing(
                prompt, history, retrieval_limit, similarity_threshold,
                reason, privacy_score, complexity_data, is_auto_mode=True
            )

    def _handle_local_processing(self, prompt, history, retrieval_limit,
                                similarity_threshold, reason, privacy_score,
                                complexity_data, is_auto_mode=False):
        """本地处理逻辑"""
        try:
            local_host = API_CONFIG["local"]
            model_type = MODEL_MAP["本地"]

            # 显示处理状态
            mode_text = "智能-本地" if is_auto_mode else "本地"
            processing_note = {"role": "assistant", "content": f"🤖 正在使用{mode_text}RAG模式处理请求..."}
            current_history = history + [{"role": "user", "content": prompt}, processing_note]
            yield current_history, current_history

            # 构建请求数据
            api_history = history.copy() if history else []
            request_data = {
                "query": prompt,
                "model_type": model_type,
                "top_k": retrieval_limit,
                "stream": True,
                "history": api_history,
                "similarity_threshold": similarity_threshold
            }

            # 调用本地API
            response = requests.post(
                f"{local_host}/rag_chat",
                json=request_data,
                timeout=60,
                stream=True
            )

            if response.status_code == 200:
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str.strip() == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if data.get("type") == "content":
                                    delta = data.get("content", "")
                                    full_response += delta
                                    current_history = history + [
                                        {"role": "user", "content": prompt},
                                        {"role": "assistant", "content": f"🤖【智能-本地RAG】{full_response}▌"}
                                    ]
                                    yield current_history, current_history
                            except json.JSONDecodeError:
                                continue

                # 生成最终响应
                final_response = f"🤖【智能RAG】{full_response}"
                info_text = f"\n\n📋 **智能路由信息**:\n- 🤯 决策原因: {reason}\n- 🔒 隐私评分: {privacy_score:.2f}\n- 📊 复杂度分析: {complexity_data.get('complexity_score', 0.5):.2f}"

                final_history = history + [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": final_response + info_text}
                ]
                yield final_history, final_history

        except Exception as e:
            error_msg = f"⚠️ 智能模式本地处理错误：{str(e)}"
            error_history = history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": error_msg}
            ]
            yield error_history, error_history

    def _handle_cloud_processing(self, prompt, history, retrieval_limit,
                                 similarity_threshold, reason, privacy_score,
                                 complexity_data, is_auto_mode=False):
        """云端处理逻辑"""
        try:
            cloud_host = API_CONFIG["cloud"]
            model_type = MODEL_MAP["云端"]

            # 显示处理状态
            mode_text = "智能-云端" if is_auto_mode else "云端"
            processing_note = {"role": "assistant", "content": f"🤖 正在使用{mode_text}RAG模式处理请求..."}
            current_history = history + [{"role": "user", "content": prompt}, processing_note]
            yield current_history, current_history

            # 构建请求数据
            api_history = history.copy() if history else []
            request_data = {
                "query": prompt,
                "model_type": model_type,
                "top_k": retrieval_limit,
                "stream": True,
                "history": api_history,
                "similarity_threshold": similarity_threshold
            }

            # 调用云端API
            response = requests.post(
                f"{cloud_host}/rag_chat",
                json=request_data,
                timeout=120,
                stream=True
            )

            if response.status_code == 200:
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str.strip() == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if data.get("type") == "content":
                                    delta = data.get("content", "")
                                    full_response += delta
                                    current_history = history + [
                                        {"role": "user", "content": prompt},
                                        {"role": "assistant", "content": f"🤖【智能-云端RAG】{full_response}▌"}
                                    ]
                                    yield current_history, current_history
                            except json.JSONDecodeError:
                                continue

                # 检查是否已有前缀
                if full_response.strip().startswith("🤖"):
                    final_response = full_response
                else:
                    final_response = f"🤖【智能RAG】{full_response}"

                info_text = f"\n\n📋 **智能路由信息**:\n- 🤯 决策原因: {reason}\n- 🔒 隐私评分: {privacy_score:.2f}\n- 📊 复杂度分析: {complexity_data.get('complexity_score', 0.5):.2f}"

                final_history = history + [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": final_response + info_text}
                ]
                yield final_history, final_history

        except Exception as e:
            error_msg = f"⚠️ 智能模式云端处理错误：{str(e)}"
            error_history = history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": error_msg}
            ]
            yield error_history, error_history


class CloudModeHandler(BaseModeHandler):
    """云端模式处理器 - 纯云端处理"""

    def get_model_prefix(self):
        return "🤖【云端RAG】"

    def handle_request(self, prompt, history, retrieval_limit=5,
                       similarity_threshold=0.0, **kwargs):
        """处理云端模式请求"""
        try:
            cloud_host = API_CONFIG["cloud"]
            model_type = MODEL_MAP["云端"]

            # 显示处理状态
            processing_note = {"role": "assistant", "content": "🤖 正在检索云端文档并生成回答..."}
            current_history = history + [{"role": "user", "content": prompt}, processing_note]
            yield current_history, current_history

            # 构建请求数据
            api_history = history.copy() if history else []
            request_data = {
                "query": prompt,
                "model_type": model_type,
                "top_k": retrieval_limit,
                "stream": True,
                "history": api_history,
                "similarity_threshold": similarity_threshold
            }

            # 调用云端API
            response = requests.post(
                f"{cloud_host}/rag_chat",
                json=request_data,
                timeout=120,
                stream=True
            )

            if response.status_code == 200:
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str.strip() == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if data.get("type") == "content":
                                    delta = data.get("content", "")
                                    full_response += delta
                                    current_history = history + [
                                        {"role": "user", "content": prompt},
                                        {"role": "assistant", "content": f"🤖【云端RAG】{full_response}▌"}
                                    ]
                                    yield current_history, current_history
                            except json.JSONDecodeError:
                                continue

                # 检查是否已有前缀，避免重复
                if full_response.strip().startswith("🤖"):
                    final_response = full_response
                else:
                    final_response = f"🤖【云端RAG】{full_response}"

                final_history = history + [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": final_response}
                ]
                yield final_history, final_history
            else:
                raise Exception(f"云端API错误: HTTP {response.status_code}")

        except requests.exceptions.RequestException as e:
            # 网络错误处理
            error_msg = f"🌐 云端服务不可用 ({str(e)})，请检查网络连接或尝试其他模式"
            error_history = history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": error_msg}
            ]
            yield error_history, error_history

        except Exception as e:
            error_msg = f"⚠️ 云端模式处理错误：{str(e)}"
            error_history = history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": error_msg}
            ]
            yield error_history, error_history


class LocalModeHandler(BaseModeHandler):
    """本地模式处理器 - 纯本地处理"""

    def get_model_prefix(self):
        return "🤖【本地RAG】"

    def handle_request(self, prompt, history, retrieval_limit=5,
                       similarity_threshold=0.0, **kwargs):
        """处理本地模式请求"""
        try:
            local_host = API_CONFIG["local"]
            model_type = MODEL_MAP["本地"]

            # 显示处理状态
            processing_note = {"role": "assistant", "content": "🤖 正在检索本地文档并生成回答..."}
            current_history = history + [{"role": "user", "content": prompt}, processing_note]
            yield current_history, current_history

            # 构建请求数据
            api_history = history.copy() if history else []
            request_data = {
                "query": prompt,
                "model_type": model_type,
                "top_k": retrieval_limit,
                "stream": True,
                "history": api_history,
                "similarity_threshold": similarity_threshold
            }

            # 调用本地API
            response = requests.post(
                f"{local_host}/rag_chat",
                json=request_data,
                timeout=60,
                stream=True
            )

            if response.status_code == 200:
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str.strip() == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if data.get("type") == "content":
                                    delta = data.get("content", "")
                                    full_response += delta
                                    current_history = history + [
                                        {"role": "user", "content": prompt},
                                        {"role": "assistant", "content": f"🤖【本地RAG】{full_response}▌"}
                                    ]
                                    yield current_history, current_history
                            except json.JSONDecodeError:
                                continue

                final_response = f"🤖【本地RAG】{full_response}"
                final_history = history + [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": final_response}
                ]
                yield final_history, final_history
            else:
                raise Exception(f"本地API错误: HTTP {response.status_code}")

        except Exception as e:
            error_msg = f"⚠️ 本地模式处理错误：{str(e)}"
            error_history = history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": error_msg}
            ]
            yield error_history, error_history


def create_mode_handler(mode, network_monitor, knowledge_base):
    """工厂函数：创建对应的模式处理器"""
    handlers = {
        "自动": AutoModeHandler,
        "云端": CloudModeHandler,
        "本地": LocalModeHandler
    }

    handler_class = handlers.get(mode)
    if not handler_class:
        raise ValueError(f"不支持的模式: {mode}")

    return handler_class(network_monitor, knowledge_base)