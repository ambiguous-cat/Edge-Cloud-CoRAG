"""
端云协同RAG智能对话 - 主界面文件（重构版）
使用模块化结构，提高代码可维护性
"""
import gradio as gr
import requests
import json
from network_monitor import NetworkMonitor
from knowledge_base import LocalKnowledgeBase
from ui_components import UIComponents
from stream_handler import StreamHandler
from config import LOCAL_KNOWLEDGE_BASE, API_CONFIG


def create_chat_interface():
    """创建聊天界面"""
    # 初始化组件
    network_monitor = NetworkMonitor()
    knowledge_base = LocalKnowledgeBase(LOCAL_KNOWLEDGE_BASE)
    ui_components = UIComponents(network_monitor)
    stream_handler = StreamHandler()

    # 启动网络监控
    network_monitor.start_monitoring()

    # 创建UI布局并在其上下文中绑定事件
    components = ui_components.create_layout()
    
    # 在Blocks上下文中绑定事件
    with components['chat_interface']:
        # 创建状态变量来跟踪设置面板的显示状态
        settings_visible = gr.State(False)
        # 创建状态变量来跟踪隐私管理面板的显示状态
        privacy_management_visible = gr.State(False)
                
        # 绑定事件处理函数
        def update_network_display():
            """更新网络状态显示"""
            return network_monitor.get_network_display_info()
        
        def toggle_settings(current_visible):
            """切换设置面板显示状态"""
            new_visible = not current_visible
            button_text = "🔧 收起设置" if new_visible else "⚙️ 设置"
            return gr.update(visible=new_visible), new_visible, gr.update(value=button_text)
        
        def close_settings():
            """关闭设置面板"""
            return gr.update(visible=False), False, gr.update(value="⚙️ 设置")
        
        def toggle_privacy_management(current_visible):
            """切换隐私管理面板显示状态"""
            new_visible = not current_visible
            button_text = "🔓 收起隐私管理" if new_visible else "🔒 隐私管理"
            return gr.update(visible=new_visible), new_visible, gr.update(value=button_text)
        
        def close_privacy_management():
            """关闭隐私管理面板"""
            return gr.update(visible=False), False, gr.update(value="🔒 隐私管理")
        
        def close_response_info():
            """关闭响应信息弹窗"""
            return gr.update(visible=False)

        def close_complexity_detail():
            """关闭复杂度详情弹窗"""
            return gr.update(visible=False)

        def show_complexity_detail(current_model, chatbot_history):
            """显示复杂度详情弹窗"""
            # 如果当前是云端模式，不显示复杂度详情
            if current_model == "云端":
                return (
                    gr.update(visible=False),  # 隐藏弹窗
                    "",
                    "",
                    "",
                    ""
                )

            # 从聊天历史中获取最后一条用户消息
            last_user_message = None
            if chatbot_history and len(chatbot_history) > 0:
                for msg in reversed(chatbot_history):
                    if isinstance(msg, list) and len(msg) >= 2:
                        user_msg = msg[0]
                        if user_msg and user_msg.strip():
                            last_user_message = user_msg.strip()
                            break

            if not last_user_message:
                return (
                    gr.update(visible=True),
                    "⚠️ **暂无查询数据**\n\n请先发送一个问题进行复杂度分析。",
                    "ℹ️ **使用方法**\n\n1. 在输入框中输入问题\n2. 点击发送按钮\n3. 系统自动分析复杂度\n4. 点击'查看复杂度详情'按钮",
                    "📊 **等待分析**\n\n复杂度分析结果将在这里显示。",
                    "💡 **提示**\n\n发送问题后即可查看详细的五维度评分。"
                )

            # 调用API获取实际的复杂度分析数据
            try:
                from dynamic_router import DynamicRouter
                from network_monitor import NetworkMonitor
                from knowledge_base import LocalKnowledgeBase
                from config import LOCAL_KNOWLEDGE_BASE
                
                network_monitor = NetworkMonitor()
                knowledge_base = LocalKnowledgeBase(LOCAL_KNOWLEDGE_BASE)
                router = DynamicRouter(network_monitor, knowledge_base)
                
                complexity_result = router.check_complexity_analysis(last_user_message, [])
                
                if not complexity_result:
                    raise Exception("无法获取复杂度分析结果")
                
                # 获取权重配置（从环境变量或默认值）
                from complexity_analyzer import ComplexityAnalyzer
                analyzer = ComplexityAnalyzer()
                weights = analyzer.complexity_weights
                
            except Exception as e:
                return (
                    gr.update(visible=True),
                    "⚠️ **复杂度分析错误**\n\n请确保API服务器正在运行。",
                    "🔧 **故障排除**\n\n检查API服务器状态和网络连接。",
                    "📊 **错误信息**\n\n" + str(e),
                    "💡 **建议**\n\n1. 启动API服务器 (python api_server.py)\n2. 检查端口8000是否可用\n3. 重试复杂度分析"
                )

            # 格式化综合信息（只显示总分，不显示等级）
            overall_score = complexity_result.get("complexity_score", 0.0)
            confidence = complexity_result.get("confidence", 0.0)

            overall_text = f"""🧠 **综合复杂度评分**: {overall_score:.3f}
📊 **置信度**: {confidence:.3f}"""

            # 格式化路由信息
            route = complexity_result.get("route", "local")
            routing_text = f"""🚦 **推荐路由**: {route.upper()}
💡 **决策依据**: {'复杂度评分较高，建议使用云端模型' if overall_score > 0.2 else '复杂度较低，使用本地模型'}
⚡ **处理优势**: {'云端模型能更好地处理复杂查询' if route == 'cloud' else '本地模型处理更快，保护隐私'}"""

            # 格式化五维度信息（使用实际权重）
            query_length = complexity_result.get("query_length", 0.0)
            keyword_richness = complexity_result.get("keyword_richness", 0.0)
            semantic_depth = complexity_result.get("semantic_depth", 0.0)
            domain_specificity = complexity_result.get("domain_specificity", 0.0)
            reasoning_requirements = complexity_result.get("reasoning_requirements", 0.0)
            
            dimensions_text = f"""| 维度 | 评分 | 权重 | 加权得分 |
|------|------|------|----------|
| 📏 **查询长度** | {query_length:.3f} | {weights.get('query_length', 0.15)*100:.0f}% | {query_length * weights.get('query_length', 0.15):.3f} |
| 🏷️ **关键词丰富度** | {keyword_richness:.3f} | {weights.get('keyword_richness', 0.25)*100:.0f}% | {keyword_richness * weights.get('keyword_richness', 0.25):.3f} |
| 🧠 **语义深度** | {semantic_depth:.3f} | {weights.get('semantic_depth', 0.25)*100:.0f}% | {semantic_depth * weights.get('semantic_depth', 0.25):.3f} |
| 🎯 **领域特定性** | {domain_specificity:.3f} | {weights.get('domain_specificity', 0.20)*100:.0f}% | {domain_specificity * weights.get('domain_specificity', 0.20):.3f} |
| ⚡ **语法复杂度** | {reasoning_requirements:.3f} | {weights.get('reasoning_requirements', 0.15)*100:.0f}% | {reasoning_requirements * weights.get('reasoning_requirements', 0.15):.3f} |

**总复杂度**: {overall_score:.3f} (各维度加权求和)"""

            # 格式化详细分析（只显示具体分数，不显示等级）
            analysis_text = f"""🔍 **五维度详细评分**:

- **查询长度**: {query_length:.3f} (权重: {weights.get('query_length', 0.15)*100:.0f}%)
- **关键词丰富度**: {keyword_richness:.3f} (权重: {weights.get('keyword_richness', 0.25)*100:.0f}%) - 包含推理/分析关键词
- **语义深度**: {semantic_depth:.3f} (权重: {weights.get('semantic_depth', 0.25)*100:.0f}%)
- **领域特定性**: {domain_specificity:.3f} (权重: {weights.get('domain_specificity', 0.20)*100:.0f}%)
- **语法复杂度**: {reasoning_requirements:.3f} (权重: {weights.get('reasoning_requirements', 0.15)*100:.0f}%)

**计算说明**: 总复杂度 = 各维度评分 × 对应权重后求和"""

            return (
                gr.update(visible=True),  # complexity_detail_modal
                overall_text,             # overall_info
                routing_text,             # routing_info
                dimensions_text,          # dimensions_info
                analysis_text             # analysis_info
            )
        
        def add_privacy_keyword(keyword):
            """添加隐私词"""
            if not keyword or not keyword.strip():
                return "", "❌ 请输入有效的隐私词"
            
            keyword = keyword.strip()
            
            try:
                    # 尝试调用本地API
                response = requests.post(
                    f"{API_CONFIG['local']}/privacy/keywords/add",
                    json={"keyword": keyword},
                    timeout=5
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        return "", f"✅ 隐私词 '{keyword}' 添加成功"
                    else:
                        return "", f"❌ 添加失败: {result.get('message', '未知错误')}"
                else:
                    return "", f"❌ 服务器错误: {response.status_code}"

            except requests.exceptions.RequestException as e:
                return "", f"❌ 网络错误: {str(e)}"
        
        def refresh_privacy_keywords():
            """刷新隐私词列表"""
            try:
                print(f"🔄 正在刷新隐私词列表，API地址: {API_CONFIG['local']}/privacy/keywords")
                
                # 尝试调用本地API获取隐私词列表
                response = requests.get(
                    f"{API_CONFIG['local']}/privacy/keywords",
                    timeout=5
                )
                
                print(f"📡 API响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"📄 API响应数据: {result}")
                    
                    keywords_data = result.get("keywords", [])
                    print(f"🔑 关键词数据: {keywords_data}")
                    
                    if keywords_data:
                        # 提取keyword字段，处理可能的编码问题
                        keywords = []
                        for item in keywords_data:
                            if isinstance(item, dict) and "keyword" in item:
                                keyword = item["keyword"]
                                # 如果是字符串，直接使用；如果是其他类型，转换为字符串
                                keywords.append(str(keyword))
                            elif isinstance(item, str):
                                keywords.append(item)
                        
                        print(f"✅ 处理后的关键词: {keywords}")
                        
                        if keywords:
                            keyword_list = "、".join(keywords[:20])  # 最多显示20个
                            if len(keywords) > 20:
                                keyword_list += f"... (共{len(keywords)}个)"
                            result_text = f"📝 **当前隐私词** ({len(keywords)}个): {keyword_list}"
                            print(f"🎯 最终显示文本: {result_text}")
                            return result_text
                        else:
                            return "📝 **当前隐私词**: 数据格式错误"
                    else:
                        return "📝 **当前隐私词**: 暂无隐私词"
                else:
                    error_msg = f"❌ 获取隐私词失败: HTTP {response.status_code}"
                    print(error_msg)
                    return error_msg
                    
            except requests.exceptions.RequestException as e:
                error_msg = f"❌ 网络错误: {str(e)}"
                print(error_msg)
                return error_msg
            except Exception as e:
                error_msg = f"❌ 未知错误: {str(e)}"
                print(error_msg)
                return error_msg
        
        # 发送按钮事件绑定 - 恢复到原来的格式
        components['submit_btn'].click(
            fn=stream_handler.stream_response,
            inputs=[
                components['text_input'],
                components['model_selector'],
                components['chatbot'],
                components['privacy_threshold_slider'],
                components['retrieval_limit_slider'],
                components['similarity_threshold_slider'],
                components['complexity_threshold_slider'],
                components['enable_cache_check'],
                components['enable_network_check'],
                components['enable_complexity_check'],
                components['enable_privacy_check']
            ],
            outputs=[components['chatbot'], components['chatbot']]
        )
        
        # 设置按钮事件绑定 - 简化版本
        components['settings_btn'].click(
            fn=toggle_settings,
            inputs=[settings_visible],
            outputs=[components['settings_content'], settings_visible, components['settings_btn']]
        )
        
        # 关闭设置按钮事件绑定
        components['close_settings_btn'].click(
            fn=close_settings,
            inputs=None,
            outputs=[components['settings_content'], settings_visible, components['settings_btn']]
        )
        
        # 隐私管理按钮事件绑定
        components['privacy_management_btn'].click(
            fn=toggle_privacy_management,
            inputs=[privacy_management_visible],
            outputs=[components['privacy_management_content'], privacy_management_visible, components['privacy_management_btn']]
        )
        
        # 关闭隐私管理按钮事件绑定
        components['close_privacy_management_btn'].click(
            fn=close_privacy_management,
            inputs=None,
            outputs=[components['privacy_management_content'], privacy_management_visible, components['privacy_management_btn']]
        )
        
        # 关闭响应信息弹窗事件绑定
        components['close_modal_btn'].click(
            fn=close_response_info,
            inputs=None,
            outputs=[components['response_info_modal']]
        )

        # 关闭复杂度详情弹窗事件绑定
        components['close_complexity_btn'].click(
            fn=close_complexity_detail,
            inputs=None,
            outputs=[components['complexity_detail_modal']]
        )

        # 显示复杂度详情事件绑定
        components['view_complexity_btn'].click(
            fn=show_complexity_detail,
            inputs=[components['current_model'], components['chatbot']],
            outputs=[
                components['complexity_detail_modal'],
                components['overall_info'],
                components['routing_info'],
                components['dimensions_info'],
                components['analysis_info']
            ]
        )

        # 刷新按钮事件绑定
        components['refresh_btn'].click(
            fn=update_network_display,
            inputs=None,
            outputs=components['network_status']
        )
        
        # 隐私词添加按钮事件绑定
        components['add_privacy_keyword_btn'].click(
            fn=add_privacy_keyword,
            inputs=[components['privacy_keyword_input']],
            outputs=[components['privacy_keyword_input'], components['privacy_keyword_status']]
        )
        
        # 刷新隐私词列表按钮事件绑定
        components['refresh_privacy_keywords_btn'].click(
            fn=refresh_privacy_keywords,
            inputs=None,
            outputs=[components['current_privacy_keywords']]
        )
        
        # 页面初始时显示网络状态和隐私词列表
        components['chat_interface'].load(
            fn=lambda: (update_network_display(), refresh_privacy_keywords()),
            inputs=None,
            outputs=[components['network_status'], components['current_privacy_keywords']]
        )
        
    
    return components['chat_interface']


if __name__ == "__main__":
    chat_interface = create_chat_interface()
    # 指定端口避免与API服务器冲突
    chat_interface.launch(share=False, server_port=None)  # 让Gradio自动选择可用端口