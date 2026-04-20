"""
响应处理模块
负责处理不同路由的API调用和流式响应
"""
import json
import time
import logging
import requests
from config import API_CONFIG, MODEL_MAP, MATHJAX_CONFIG


class ResponseHandler:
    """响应处理器"""
    
    def __init__(self, knowledge_base):
        self.knowledge_base = knowledge_base
        
    def handle_offline_response(self, prompt, history, model, retrieval_limit, similarity_threshold, privacy_score=0.0, complexity_data=None):
        """处理离线响应 - 调用本地RAG模型"""
        offline_note = {"role": "assistant", "content": "🌐 云端服务不可用，已自动切换到本地RAG模型"}
        new_history = history + [{"role": "user", "content": prompt}, offline_note]
        yield new_history, new_history
        time.sleep(1)

        try:
            # 尝试调用本地RAG服务
            endpoint = API_CONFIG["local"]
            model_type = MODEL_MAP["本地"]
            api_history = history.copy() if history else []

            # 显示处理状态
            processing_note = {"role": "assistant", "content": "🤖💻 离线模式：正在检索文档并生成回答..."}
            current_history = history + [{"role": "user", "content": prompt}, processing_note]
            yield current_history, current_history

            # 发起API请求
            response = self._make_api_request(endpoint, prompt, model_type, retrieval_limit, 
                                            similarity_threshold, api_history)

            # 处理流式响应
            model_prefix = "🤖【自动-离线RAG】"
            full_response = ""
            response_info = {}
            
            for line in response.iter_lines():
                if not line:
                    continue
                decoded_line = line.decode("utf-8").strip()
                if decoded_line.startswith("data:"):
                    json_str = decoded_line[5:].strip()
                    try:
                        data = json.loads(json_str)

                        if data.get("type") == "content":
                            # 处理内容片段
                            delta = data.get("content", "")
                            if delta:
                                full_response += delta
                                current_history = history + [
                                    {"role": "user", "content": prompt},
                                    {"role": "assistant", "content": f"{model_prefix}{full_response}▌"}
                                ]
                                yield current_history, current_history

                        elif data.get("type") == "info":
                            # 处理响应信息
                            response_info = data
                            break

                        elif data.get("type") == "error":
                            # 处理错误
                            full_response += f"\n\n❌ {data.get('content', '未知错误')}"
                            break

                        # 兼容旧格式
                        elif "content" in data and "type" not in data:
                            delta = data.get("content", "")
                            if delta:
                                full_response += delta
                                current_history = history + [
                                    {"role": "user", "content": prompt},
                                    {"role": "assistant", "content": f"{model_prefix}{full_response}▌"}
                                ]
                                yield current_history, current_history
                            if data.get("done"):
                                break

                        # 处理新格式（云端API的带type字段的数据）
                        elif data.get("type") == "content":
                            delta = data.get("content", "")
                            if delta:
                                full_response += delta
                                current_history = history + [
                                    {"role": "user", "content": prompt},
                                    {"role": "assistant", "content": f"{model_prefix}{full_response}▌"}
                                ]
                                yield current_history, current_history
                        elif data.get("type") in ["info", "debug", "performance", "documents"]:
                            # 跳过信息类型的数据，不显示给用户
                            continue
                        elif data.get("done"):
                            # 处理完成标志
                            current_history = history + [
                                {"role": "user", "content": prompt},
                                {"role": "assistant", "content": f"{model_prefix}{full_response}"}
                            ]
                            yield current_history, current_history
                            break

                    except Exception:
                        pass

            # 格式化响应信息
            info_text = self._format_response_info(response_info, "离线模式", privacy_score, complexity_data)

            # 生成最终响应，在末尾添加响应信息
            final_response = model_prefix + full_response + "\n\n" + info_text + MATHJAX_CONFIG
            final_history = history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": final_response}
            ]
            yield final_history, final_history

        except Exception as e:
            # 如果本地RAG也失败，则返回错误信息
            error_msg = f"⚠️ 离线模式下本地RAG服务也不可用：{str(e)}\n\n💡 请确保本地API服务正在运行。"
            if model == "自动":
                final_response = f"🤖【自动-离线】{error_msg}"
            else:
                final_response = f"🤖【本地】{error_msg}"
            final_history = history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": final_response}
            ]
            yield final_history, final_history

    def handle_cache_response(self, prompt, history, model, privacy_score=0.0, complexity_data=None):
        """处理缓存响应"""
        cached_response = self.knowledge_base.get_cached_response(prompt)
        cached_note = {"role": "assistant", "content": "💾 使用本地缓存回答"}
        current_history = history + [{"role": "user", "content": prompt}, cached_note]
        yield current_history, current_history
        time.sleep(1)
        
        if model == "自动":
            model_prefix = f"🤖【自动-缓存】"
        else:
            model_prefix = f"🤖【本地缓存】"
        # 为缓存响应添加响应信息按钮
        cache_info = {
            "type": "info",
            "mode": "缓存模式",
            "response_time": 0.01,  # 缓存的首字响应时间几乎为0
            "char_count": len(cached_response),
            "estimated_tokens": len(cached_response) // 3,
            "filter_stats": {},
            "retrieved_documents": []
        }
        # 格式化响应信息
        info_text = self._format_response_info(cache_info, "缓存模式", privacy_score, complexity_data)
        final_response = model_prefix + cached_response + "\n\n" + info_text + MATHJAX_CONFIG
        final_history = history + [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": final_response}
        ]
        yield final_history, final_history

    def _make_api_request(self, endpoint, prompt, model_type, retrieval_limit, 
                         similarity_threshold, api_history, timeout=12.0):
        """发起API请求，默认12秒超时"""
        request_json = {
            "query": prompt,
            "model_type": model_type,
            "top_k": retrieval_limit,
            "stream": True,
            "history": api_history,
            "similarity_threshold": similarity_threshold
        }
        headers = {"Content-Type": "application/json"}
        
        url = endpoint.rstrip("/") + "/rag_chat"
        response = requests.post(
            url,
            headers=headers,
            json=request_json,
            stream=True,
            timeout=timeout
        )
        response.raise_for_status()
        return response


    def _format_response_info(self, response_info, mode_name, privacy_score=0.0, complexity_data=None):
        """格式化响应信息为简洁的文本格式"""
        if not response_info or response_info.get("type") != "info":
            return ""

        response_time = response_info.get("response_time", 0)
        char_count = response_info.get("char_count", 0)
        estimated_tokens = response_info.get("estimated_tokens", 0)
        retrieved_docs = response_info.get("retrieved_documents", [])

        # 判断是否为云端模式
        is_cloud_mode = "云端" in mode_name
        # 判断是否为自动模式（需要显示决策信息）
        is_auto_mode = "自动" in mode_name

        # 构建基础信息摘要
        summary_info = f"\n\n📊 **响应信息（{mode_name}）**: ⏱️ {response_time:.2f}s | 📝 {char_count}字符 | 📚 {len(retrieved_docs)}个引用"

        # 在自动模式或非云端模式下显示隐私度和复杂度信息
        if is_auto_mode or not is_cloud_mode:
            # 隐私分数显示 - 保留图标，简洁格式
            privacy_text = f"🔒 {privacy_score:.3f}"
            summary_info += f" | 隐私度: {privacy_text}"

            # 复杂度信息显示 - 保留图标，简洁格式
            complexity_text = ""
            if complexity_data:
                complexity_score = complexity_data.get("complexity_score", 0.0)
                scaled_complexity = complexity_score
                complexity_text = f"🧠 {scaled_complexity:.3f}"

            # 添加复杂度信息 - 保留图标，简洁格式
            if complexity_text:
                summary_info += f" | 复杂度: {complexity_text}"

        # 添加过滤统计信息（如果有）
        filter_stats = response_info.get("filter_stats", {})
        if filter_stats:
            threshold = filter_stats.get("similarity_threshold", 0.0)
            accepted_count = filter_stats.get("accepted_count", 0)
            summary_info += f" | 🎯 阈值{threshold:.2f} 采纳{accepted_count}个"

        # 添加详细信息（折叠格式）
        details = ""
        if retrieved_docs:
            details += "\n\n<details>\n<summary><strong>📚 点击查看引用文档详情</strong></summary>\n\n"

            # 显示所有引用文档的完整内容
            for i, doc in enumerate(retrieved_docs):
                full_content = doc.get('content', '').strip()
                similarity = doc.get('similarity_score', 0)
                title = doc.get('title', '未知标题')

                details += f"**文档 {i+1}**: {title}  \n"
                details += f"**相似度**: {similarity:.3f}  \n"
                details += f"**完整内容**:  \n{full_content}\n\n"

                # 添加分隔线（除了最后一个文档）
                if i < len(retrieved_docs) - 1:
                    details += "---\n\n"

            details += "\n</details>"

        # 添加复杂度分析详情（只在非云端模式下显示）
        if complexity_data and not is_cloud_mode:
            # 获取五维评分和权重
            try:
                from complexity_analyzer import ComplexityAnalyzer
                analyzer = ComplexityAnalyzer()
                weights = analyzer.complexity_weights
            except:
                # 如果无法获取权重，使用默认值
                weights = {
                    'query_length': 0.15,
                    'keyword_richness': 0.25,  # 包含推理关键词
                    'semantic_depth': 0.25,
                    'domain_specificity': 0.20,
                    'reasoning_requirements': 0.15  # 语法复杂度
                }
            
            complexity_score = complexity_data.get("complexity_score", 0.0)
            query_length = complexity_data.get("query_length", 0.0)
            keyword_richness = complexity_data.get("keyword_richness", 0.0)
            semantic_depth = complexity_data.get("semantic_depth", 0.0)
            domain_specificity = complexity_data.get("domain_specificity", 0.0)
            reasoning_requirements = complexity_data.get("reasoning_requirements", 0.0)

            complexity_details = f"\n\n<details>\n<summary><strong>🧠 复杂度分析详情</strong></summary>\n\n"
            complexity_details += f"**总复杂度评分**: {complexity_score:.3f}\n\n"
            complexity_details += f"**五维度详细评分**:\n\n"
            complexity_details += f"| 维度 | 评分 | 权重 | 加权得分 |\n"
            complexity_details += f"|------|------|------|----------|\n"
            complexity_details += f"| 📏 查询长度 | {query_length:.3f} | {weights.get('query_length', 0.15)*100:.0f}% | {query_length * weights.get('query_length', 0.15):.3f} |\n"
            complexity_details += f"| 🏷️ 关键词丰富度 | {keyword_richness:.3f} | {weights.get('keyword_richness', 0.25)*100:.0f}% | {keyword_richness * weights.get('keyword_richness', 0.25):.3f} |\n"
            complexity_details += f"| 🧠 语义深度 | {semantic_depth:.3f} | {weights.get('semantic_depth', 0.25)*100:.0f}% | {semantic_depth * weights.get('semantic_depth', 0.25):.3f} |\n"
            complexity_details += f"| 🎯 领域特定性 | {domain_specificity:.3f} | {weights.get('domain_specificity', 0.20)*100:.0f}% | {domain_specificity * weights.get('domain_specificity', 0.20):.3f} |\n"
            complexity_details += f"| ⚡ 语法复杂度 | {reasoning_requirements:.3f} | {weights.get('reasoning_requirements', 0.15)*100:.0f}% | {reasoning_requirements * weights.get('reasoning_requirements', 0.15):.3f} |\n\n"
            complexity_details += f"**计算说明**: 总复杂度 = 各维度评分 × 对应权重后求和\n"

            complexity_details += "\n</details>"
            details += complexity_details

        return summary_info + details

    def _extract_response_info_data(self, response_info, mode_name, privacy_score=0.0, complexity_data=None):
        """提取响应信息数据用于弹窗显示"""
        if not response_info or response_info.get("type") != "info":
            return None
            
        data = {
            "mode": mode_name,
            "response_time": response_info.get("response_time", 0),
            "char_count": response_info.get("char_count", 0),
            "estimated_tokens": response_info.get("estimated_tokens", 0),
            "retrieved_docs": response_info.get("retrieved_documents", []),
            "filter_stats": response_info.get("filter_stats", {}),
            "privacy_score": privacy_score,
            "complexity_data": complexity_data
        }
        
        return data

    def handle_privacy_response(self, prompt, history, model, privacy_threshold,
                               retrieval_limit, similarity_threshold, privacy_score=0.0, complexity_data=None):
        """处理隐私保护响应"""
        privacy_note = {"role": "assistant", 
                       "content": f"🔒 检测到隐私敏感内容（阈值: {privacy_threshold}），已自动切换到本地模型保护您的隐私"}
        new_history = history + [{"role": "user", "content": prompt}, privacy_note]
        yield new_history, new_history
        time.sleep(1)

        try:
            endpoint = API_CONFIG["local"]
            model_type = MODEL_MAP["本地"]
            api_history = history.copy() if history else []

            # 隐私保护模式下也进行文档检索
            searching_note = {"role": "assistant", "content": "🔍🔒 隐私保护模式下正在检索文档..."}
            current_history = history + [{"role": "user", "content": prompt}, privacy_note, searching_note]
            yield current_history, current_history

            # 发起API请求
            response = self._make_api_request(endpoint, prompt, model_type, retrieval_limit, 
                                            similarity_threshold, api_history, timeout=12)

            # 处理流式响应
            model_prefix = "🤖【自动-隐私保护】"
            full_response = ""
            response_info = {}
            
            for line in response.iter_lines():
                if not line:
                    continue
                decoded_line = line.decode("utf-8").strip()
                if decoded_line.startswith("data:"):
                    json_str = decoded_line[5:].strip()
                    try:
                        data = json.loads(json_str)

                        if data.get("type") == "content":
                            # 处理内容片段
                            delta = data.get("content", "")
                            if delta:
                                full_response += delta
                                current_history = history + [
                                    {"role": "user", "content": prompt},
                                    {"role": "assistant", "content": f"{model_prefix}{full_response}▌"}
                                ]
                                yield current_history, current_history

                        elif data.get("type") == "info":
                            # 处理响应信息
                            response_info = data
                            break

                        elif data.get("type") == "error":
                            # 处理错误
                            full_response += f"\n\n❌ {data.get('content', '未知错误')}"
                            break

                        # 兼容旧格式
                        elif "content" in data and "type" not in data:
                            delta = data.get("content", "")
                            if delta:
                                full_response += delta
                                current_history = history + [
                                    {"role": "user", "content": prompt},
                                    {"role": "assistant", "content": f"{model_prefix}{full_response}▌"}
                                ]
                                yield current_history, current_history
                            if data.get("done"):
                                break

                        # 处理新格式（云端API的带type字段的数据）
                        elif data.get("type") == "content":
                            delta = data.get("content", "")
                            if delta:
                                full_response += delta
                                current_history = history + [
                                    {"role": "user", "content": prompt},
                                    {"role": "assistant", "content": f"{model_prefix}{full_response}▌"}
                                ]
                                yield current_history, current_history
                        elif data.get("type") in ["info", "debug", "performance", "documents"]:
                            # 跳过信息类型的数据，不显示给用户
                            continue
                        elif data.get("done"):
                            # 处理完成标志
                            current_history = history + [
                                {"role": "user", "content": prompt},
                                {"role": "assistant", "content": f"{model_prefix}{full_response}"}
                            ]
                            yield current_history, current_history
                            break

                    except Exception:
                        pass

            # 格式化响应信息
            info_text = self._format_response_info(response_info, "隐私保护模式", privacy_score, complexity_data)

            # 生成最终响应
            if model == "自动":
                final_model_prefix = "🤖【自动-隐私保护RAG】"
            else:
                final_model_prefix = "🤖【本地隐私保护】"

            # 格式化响应信息
            info_text = self._format_response_info(response_info, "隐私保护模式", privacy_score, complexity_data)
            final_response = final_model_prefix + full_response + "\n\n" + info_text + MATHJAX_CONFIG
            final_history = history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": final_response}
            ]
            yield final_history, final_history

        except Exception as e:
            error_msg = f"⚠️ 隐私保护模式下本地处理失败：{str(e)}"
            error_history = history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": error_msg}
            ]
            yield error_history, error_history

    def handle_local_response(self, prompt, history, model, reason, retrieval_limit,
                             similarity_threshold, privacy_score=0.0, complexity_data=None):
        """处理本地响应"""
        try:
            endpoint = API_CONFIG["local"]
            model_type = MODEL_MAP["本地"]
            api_history = history.copy() if history else []

            # 显示本地模式提示
            if reason == "user_selected":
                local_note = {"role": "assistant", "content": "💻 使用本地模型进行RAG对话"}
            else:
                local_note = {"role": "assistant", "content": f"💻 本地模式: {reason}"}

            current_history = history + [{"role": "user", "content": prompt}, local_note]
            yield current_history, current_history

            # 立即显示处理状态
            processing_note = {"role": "assistant", "content": "🤖💻 本地模式：正在检索文档并生成回答..."}
            current_history = history + [{"role": "user", "content": prompt}, processing_note]
            yield current_history, current_history

            # 发起API请求
            response = self._make_api_request(endpoint, prompt, model_type, retrieval_limit, 
                                            similarity_threshold, api_history)

            # 处理流式响应
            model_prefix = "🤖【本地RAG】"
            full_response = ""
            response_info = {}
            
            for line in response.iter_lines():
                if not line:
                    continue
                decoded_line = line.decode("utf-8").strip()
                if decoded_line.startswith("data:"):
                    json_str = decoded_line[5:].strip()
                    try:
                        data = json.loads(json_str)

                        if data.get("type") == "content":
                            # 处理内容片段
                            delta = data.get("content", "")
                            if delta:
                                full_response += delta
                                current_history = history + [
                                    {"role": "user", "content": prompt},
                                    {"role": "assistant", "content": f"{model_prefix}{full_response}▌"}
                                ]
                                yield current_history, current_history

                        elif data.get("type") == "info":
                            # 处理响应信息
                            response_info = data
                            
                            # 记录详细的本地模式日志信息
                            if response_info.get("response_time"):
                                response_time = response_info.get("response_time")
                                char_count = response_info.get("char_count", 0)
                                estimated_tokens = response_info.get("estimated_tokens", 0)
                                retrieved_docs = response_info.get("retrieved_documents", [])
                                filter_stats = response_info.get("filter_stats", {})
                                context_length = response_info.get("context_length", 0)
                                
                                # 计算平均相似度
                                avg_similarity = sum(doc.get('similarity_score', 0) for doc in retrieved_docs) / len(retrieved_docs) if retrieved_docs else 0
                                
                                print(f"DEBUG: 本地模式首字响应时间: {response_time:.3f}秒, 隐私度: {privacy_score:.3f}")
                                import logging
                                # 分多行记录本地响应详细信息
                                logging.info(f"=== Local Response Start ===")
                                logging.info(f"Performance: response_time={response_time:.3f}s, char_count={char_count}, estimated_tokens={estimated_tokens}")
                                logging.info(f"Request: prompt_length={len(prompt)}, model={model}, reason={reason}, has_history={len(history) > 0}")
                                logging.info(f"Privacy: privacy_score={privacy_score:.3f}")
                                logging.info(f"Retrieval: retrieved_docs={len(retrieved_docs)}, accepted_docs={filter_stats.get('accepted_count', 0)}, similarity_threshold={filter_stats.get('similarity_threshold', 0.0):.2f}")
                                logging.info(f"Quality: avg_similarity={avg_similarity:.3f}, context_length={context_length}")
                                logging.info(f"=== Local Response End ===")
                            
                            break

                        elif data.get("type") == "error":
                            # 处理错误
                            full_response += f"\n\n❌ {data.get('content', '未知错误')}"
                            break

                        # 兼容旧格式
                        elif "content" in data and "type" not in data:
                            delta = data.get("content", "")
                            if delta:
                                full_response += delta
                                current_history = history + [
                                    {"role": "user", "content": prompt},
                                    {"role": "assistant", "content": f"{model_prefix}{full_response}▌"}
                                ]
                                yield current_history, current_history
                            if data.get("done"):
                                break

                        # 处理新格式（云端API的带type字段的数据）
                        elif data.get("type") == "content":
                            delta = data.get("content", "")
                            if delta:
                                full_response += delta
                                current_history = history + [
                                    {"role": "user", "content": prompt},
                                    {"role": "assistant", "content": f"{model_prefix}{full_response}▌"}
                                ]
                                yield current_history, current_history
                        elif data.get("type") in ["info", "debug", "performance", "documents"]:
                            # 跳过信息类型的数据，不显示给用户
                            continue
                        elif data.get("done"):
                            # 处理完成标志
                            current_history = history + [
                                {"role": "user", "content": prompt},
                                {"role": "assistant", "content": f"{model_prefix}{full_response}"}
                            ]
                            yield current_history, current_history
                            break

                    except Exception:
                        pass

            # 格式化响应信息
            info_text = self._format_response_info(response_info, "本地模式", privacy_score, complexity_data)

            # 生成最终响应
            if model == "自动":
                final_model_prefix = "🤖【自动-本地RAG】"
            else:
                final_model_prefix = "🤖【本地RAG】"

            # 格式化响应信息
            info_text = self._format_response_info(response_info, "本地模式", privacy_score, complexity_data)
            final_response = final_model_prefix + full_response + "\n\n" + info_text + MATHJAX_CONFIG

            # 在自动模式下，本地路由的短问题也写入缓存，便于后续优先命中缓存
            if model == "自动" and len(prompt) < 100:
                self.knowledge_base.cache_response(prompt, full_response)

            final_history = history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": final_response}
            ]
            yield final_history, final_history

        except Exception as e:
            error_msg = f"⚠️ 本地模型响应错误：{str(e)}"
            error_history = history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": error_msg}
            ]
            yield error_history, error_history

    def handle_cloud_response(self, prompt, history, model, route, retrieval_limit,
                             similarity_threshold, privacy_score=0.0, complexity_data=None):
        """处理云端响应，智能超时策略"""
        endpoint = API_CONFIG["cloud"]
        model_type = MODEL_MAP["云端"]
        api_history = history.copy() if history else []

        # 立即显示处理状态
        processing_note = {"role": "assistant", "content": "🤖 正在检索文档并生成回答..."}
        current_history = history + [{"role": "user", "content": prompt}, processing_note]
        yield current_history, current_history

        # 根据模式设置不同的超时策略
        if model == "自动":
            # 自动模式：先快速测试云端是否在线
            print("DEBUG: 自动模式 - 先测试云端连接状态")
            
            # 使用NetworkMonitor快速测试云端状态（1秒超时）
            from network_monitor import NetworkMonitor
            network_monitor = NetworkMonitor()
            is_online, latency, status = network_monitor.check_cloud_api_status(timeout=1.0)
            
            if not is_online:
                # 云端不在线，直接切换到本地模式
                offline_message = {"role": "assistant", "content": f"🌐 云端服务不可用({status})，自动切换到本地RAG模式..."}
                offline_history = history + [{"role": "user", "content": prompt}, offline_message]
                yield offline_history, offline_history
                
                print(f"DEBUG: 云端连接测试失败({status})，直接切换到本地模式")
                for result in self.handle_offline_response(prompt, history, model, retrieval_limit, similarity_threshold, privacy_score):
                    yield result
                return
            
            # 云端在线，使用20秒超时发送请求
            timeout = 20.0
            print(f"DEBUG: 云端在线(延迟: {latency}ms)，使用{timeout}秒超时发送请求")
        else:
            # 云端模式：直接使用20秒超时，不区分问题长短
            timeout = 20.0
            print(f"DEBUG: 云端模式，使用{timeout}秒超时")

        try:
            # 发起API请求，使用相应的超时时间
            response = self._make_api_request(endpoint, prompt, model_type, retrieval_limit, 
                                            similarity_threshold, api_history, timeout=timeout)

            # 处理流式响应
            full_response = ""
            response_info = {}
            
            for line in response.iter_lines():
                if not line:
                    continue
                decoded_line = line.decode("utf-8").strip()
                if decoded_line.startswith("data:"):
                    json_str = decoded_line[5:].strip()
                    try:
                        data = json.loads(json_str)

                        if data.get("type") == "content":
                            # 处理内容片段
                            delta = data.get("content", "")
                            if delta:
                                full_response += delta
                                current_history = history + [
                                    {"role": "user", "content": prompt},
                                    {"role": "assistant", "content": full_response + "▌"}
                                ]
                                yield current_history, current_history

                        elif data.get("type") == "info":
                            # 处理响应信息
                            response_info = data
                            
                            # 记录详细的云端模式日志信息
                            if response_info.get("response_time"):
                                response_time = response_info.get("response_time")
                                char_count = response_info.get("char_count", 0)
                                estimated_tokens = response_info.get("estimated_tokens", 0)
                                retrieved_docs = response_info.get("retrieved_documents", [])
                                filter_stats = response_info.get("filter_stats", {})
                                context_length = response_info.get("context_length", 0)
                                
                                # 计算平均相似度
                                avg_similarity = sum(doc.get('similarity_score', 0) for doc in retrieved_docs) / len(retrieved_docs) if retrieved_docs else 0
                                
                                print(f"DEBUG: 云端模式首字响应时间: {response_time:.3f}秒, 隐私度: {privacy_score:.3f}")
                                import logging
                                # 分多行记录云端响应详细信息
                                logging.info(f"=== Cloud Response Start ===")
                                logging.info(f"Performance: response_time={response_time:.3f}s, char_count={char_count}, estimated_tokens={estimated_tokens}")
                                logging.info(f"Request: prompt_length={len(prompt)}, model={model}, route={route}, has_history={len(history) > 0}")
                                logging.info(f"Privacy: privacy_score={privacy_score:.3f}")
                                logging.info(f"Retrieval: retrieved_docs={len(retrieved_docs)}, accepted_docs={filter_stats.get('accepted_count', 0)}, similarity_threshold={filter_stats.get('similarity_threshold', 0.0):.2f}")
                                logging.info(f"Quality: avg_similarity={avg_similarity:.3f}, context_length={context_length}")
                                logging.info(f"=== Cloud Response End ===")
                            
                            break

                        elif data.get("type") == "error":
                            # 处理错误
                            full_response += f"\n\n❌ {data.get('content', '未知错误')}"
                            break

                        # 兼容旧格式
                        elif "content" in data and "type" not in data:
                            delta = data.get("content", "")
                            if delta:
                                full_response += delta
                                current_history = history + [
                                    {"role": "user", "content": prompt},
                                    {"role": "assistant", "content": full_response + "▌"}
                                ]
                                yield current_history, current_history
                            if data.get("done"):
                                break

                    except Exception:
                        pass

            # 缓存常见问题的回答
            if len(prompt) < 100:
                self.knowledge_base.cache_response(prompt, full_response)

            # 根据实际使用的路由显示模型信息
            if model == "自动":
                if route == "cloud":
                    model_prefix = f"🤖【自动-云端RAG】"
                else:
                    model_prefix = f"🤖【自动-本地RAG】"
            else:
                model_prefix = f"🤖【{model}RAG】"

            # 检查响应内容是否已经包含前缀，避免重复
            response_content = full_response.replace("$$", "$")
            # 如果响应内容已经包含🤖开头的前缀，则不再添加额外前缀
            if response_content.strip().startswith("🤖"):
                final_response = response_content
            else:
                final_response = model_prefix + response_content

            # 格式化响应信息 - 使用传入的实际模式名称而不是硬编码"云端模式"
            display_mode = "云端模式" if model == "云端" else "自动模式"
            info_text = self._format_response_info(response_info, display_mode, privacy_score, complexity_data)
            final_response = final_response + "\n\n" + info_text + MATHJAX_CONFIG

            # 在自动模式下，无论最终路由到本地还是云端，都可以将短问题的回答写入缓存
            if model == "自动" and len(prompt) < 100:
                self.knowledge_base.cache_response(prompt, full_response)

            final_history = history + [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": final_response}
            ]
            yield final_history, final_history

        except requests.exceptions.RequestException as e:
            # 检查是否为超时错误（包括连接超时和读取超时）
            is_timeout = (isinstance(e, requests.exceptions.Timeout) or 
                         isinstance(e, requests.exceptions.ConnectionError) and "timed out" in str(e).lower())
            
            # 只有在自动模式下才允许自动切换
            if is_timeout and model == "自动":
                # 自动模式下的超时：自动切换到本地模式
                timeout_message = {"role": "assistant", "content": f"⏰ 云端服务响应超时(>{timeout}秒)，自动切换到本地RAG模式..."}
                timeout_history = history + [{"role": "user", "content": prompt}, timeout_message]
                yield timeout_history, timeout_history
                
                # 切换到本地RAG处理
                print(f"DEBUG: 自动模式云端超时，切换到本地模式处理: {str(e)}")
                for result in self.handle_offline_response(prompt, history, model, retrieval_limit, similarity_threshold, privacy_score):
                    yield result
            else:
                # 手动选择云端模式或其他网络错误：显示错误信息，不自动切换
                import traceback
                tb = traceback.format_exc()
                
                if is_timeout:
                    error_detail = f"⚠️ 云端服务响应超时(>{timeout}秒)\n" \
                                  f"您手动选择了云端模式，系统不会自动切换。\n" \
                                  f"请检查云端服务状态或切换到自动模式以启用智能切换。\n\n" \
                                  f"错误详情：{str(e)}"
                else:
                    error_detail = f"⚠️ 云端请求失败：{str(e)}\n" \
                                  f"类型: {type(e)}\n" \
                                  f"Traceback:\n{tb}\n" \
                                  f"请检查网络、端口、防火墙或API服务状态。"
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            error_detail += f"\n服务器响应内容：{e.response.text}"
                        except Exception:
                            pass
                
                error_history = history + [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": error_detail}
                ]
                yield error_history, error_history
