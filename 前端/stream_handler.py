"""
流式响应处理模块 - 临时简化版本
使用原始的response_handler避免格式问题
"""
import logging
from network_monitor import NetworkMonitor
from knowledge_base import LocalKnowledgeBase
from response_handler import ResponseHandler
from config import LOCAL_KNOWLEDGE_BASE, API_CONFIG, MODEL_MAP


class StreamHandler:
    """流式响应处理器"""

    def __init__(self):
        # 初始化各个组件
        self.network_monitor = NetworkMonitor()
        self.knowledge_base = LocalKnowledgeBase(LOCAL_KNOWLEDGE_BASE)

        # 使用原始的ResponseHandler
        self.response_handler = ResponseHandler(self.knowledge_base)

        # 从动态路由器创建智能路由功能（仅在自动模式下使用）
        from dynamic_router import DynamicRouter
        self.router = DynamicRouter(self.network_monitor, self.knowledge_base)

        # 启动网络监控
        self.network_monitor.start_monitoring()

        # 配置日志
        logging.basicConfig(filename='app.log', level=logging.INFO,
                          format='%(asctime)s - %(message)s')

    def stream_response(self, prompt: str, model: str, history: list,
                       privacy_threshold: float = 0.85, retrieval_limit: int = 3,
                       similarity_threshold: float = 0.0, complexity_threshold: float = 0.2,
                       enable_cache_check: bool = True, enable_network_check: bool = True,
                       enable_complexity_check: bool = True, enable_privacy_check: bool = True):
        """处理流式响应的主函数 - 使用三个独立模式的概念，但保持原始的响应处理"""
        try:
            # 显示用户输入
            new_history = history + [{"role": "user", "content": prompt}]
            yield new_history, new_history

            # 根据用户选择的模式进行不同的处理
            if model == "自动":
                # 设置动态隐私阈值
                self.router.set_privacy_threshold(privacy_threshold)
                # 设置复杂度阈值
                self.router.set_complexity_threshold(complexity_threshold)
                # 设置检测功能开关
                self.router.set_detection_flags(
                    enable_cache=enable_cache_check,
                    enable_network=enable_network_check,
                    enable_complexity=enable_complexity_check,
                    enable_privacy=enable_privacy_check
                )
                # 使用智能路由决策（decide_route内部已经包含隐私检测）
                route, reason = self.router.decide_route(prompt, history, force_cloud_mode=False)

                # 只有在隐私检测开启时才获取隐私分数用于展示
                # 如果隐私检测关闭，返回0.0表示未检测
                if enable_privacy_check:
                    privacy_score = self.router.check_privacy_score(prompt, history, force_cloud_mode=False)
                else:
                    privacy_score = 0.0  # 隐私检测关闭时，不显示隐私分数

                # 复杂度分析结果（用于展示）
                complexity_result = self.router.check_complexity_analysis(prompt, history)

                # 根据路由结果选择处理方式
                if route == "local" and reason == "cloud_unavailable":
                    # 云端不可用，使用离线模式
                    for result in self.response_handler.handle_offline_response(
                        prompt, history, model, retrieval_limit, similarity_threshold, privacy_score, complexity_result
                    ):
                        yield result
                elif route == "local" and reason.startswith("privacy_protection"):
                    # 隐私保护，使用隐私模式
                    for result in self.response_handler.handle_privacy_response(
                        prompt, history, model, privacy_threshold, retrieval_limit, similarity_threshold, privacy_score, complexity_result
                    ):
                        yield result
                elif route == "local" and reason == "cache_hit":
                    # 缓存命中，使用缓存模式
                    for result in self.response_handler.handle_cache_response(prompt, history, model, privacy_score, complexity_result):
                        yield result
                elif route == "local":
                    # 本地模式
                    for result in self.response_handler.handle_local_response(
                        prompt, history, model, reason, retrieval_limit, similarity_threshold, privacy_score, complexity_result
                    ):
                        yield result
                else:
                    # 云端模式
                    for result in self.response_handler.handle_cloud_response(
                        prompt, history, model, route, retrieval_limit, similarity_threshold, privacy_score, complexity_result
                    ):
                        yield result

            elif model == "云端":
                # 用户手动选择云端时，根据隐私检测开关决定是否检测隐私分数用于展示
                if enable_privacy_check:
                    privacy_score = self.router.check_privacy_score(prompt, history, force_cloud_mode=True)
                else:
                    privacy_score = 0.0  # 隐私检测关闭时，不显示隐私分数

                # 直接使用云端模式
                for result in self.response_handler.handle_cloud_response(
                    prompt, history, model, "cloud", retrieval_limit, similarity_threshold, privacy_score
                ):
                    yield result

            elif model == "本地":
                # 用户手动选择本地时，根据隐私检测开关决定是否检测隐私分数用于展示
                if enable_privacy_check:
                    privacy_score = self.router.check_privacy_score(prompt, history, force_cloud_mode=False)
                else:
                    privacy_score = 0.0  # 隐私检测关闭时，不显示隐私分数

                # 直接使用本地模式
                for result in self.response_handler.handle_local_response(
                    prompt, history, model, "local_selected", retrieval_limit, similarity_threshold, privacy_score
                ):
                    yield result

            else:
                # 未知模式
                error_msg = f"❌ 未知的模式: {model}"
                error_history = history + [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": error_msg}
                ]
                yield error_history, error_history

        except Exception as e:
            # 统一错误处理
            logging.error(f"StreamHandler Error: {str(e)}, model={model}, prompt_length={len(prompt)}")
            error_msg = f"⚠️ 系统响应错误：{str(e)}"
            error_history = history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": error_msg}
            ]
            yield error_history, error_history