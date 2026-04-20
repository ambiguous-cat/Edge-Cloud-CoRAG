"""
UI组件模块
负责创建和管理Gradio界面组件
"""
import gradio as gr
from config import APP_CSS


class UIComponents:
    """UI组件管理器"""
    
    def __init__(self, network_monitor):
        self.network_monitor = network_monitor
    
    def create_model_selector(self):
        """创建模型选择器"""
        is_online = self.network_monitor.get_status()
        if is_online:
            model_choices = ["自动", "云端", "本地"]
            model_value = "自动"
            model_interactive = True
        else:
            model_choices = ["本地"]
            model_value = "本地"
            model_interactive = False
            
        model_selector = gr.Dropdown(
            choices=model_choices,
            value=model_value,
            label="端云模型选择",
            elem_classes=["model-selector"],
            interactive=model_interactive
        )
        return model_selector
    
    
    
    def create_status_components(self):
        """创建状态显示组件"""
        network_status = gr.Markdown("", elem_id="network-status")
        refresh_btn = gr.Button("🔄 刷新网络状态", elem_id="refresh-network-btn")
        status_indicator = gr.Markdown("", elem_id="status-indicator")
        
        return network_status, refresh_btn, status_indicator
    
    def create_layout(self):
        """创建完整的界面布局"""
        with gr.Blocks(css=APP_CSS, title="端云协同RAG智能对话", theme=gr.themes.Default()) as chat_interface:
            current_model = gr.State("云端")
            
            with gr.Column(elem_classes=["feature-card", "app-container"]):
                gr.Markdown("# 💬 端云协同RAG智能对话", elem_classes="app-title")
                
                with gr.Row():
                    # 左侧：网络与模型相关控件
                    with gr.Column(scale=1, min_width=350):
                        network_status, refresh_btn, status_indicator = self.create_status_components()
                        model_selector = self.create_model_selector()
                        
                        model_info = gr.Markdown(
                            "🤖 **自动**: 智能选择最佳RAG模型<br>"
                            "💬 **云端**: 使用云端RAG检索对话<br>"
                            "💻 **本地**: 使用本地RAG检索对话", 
                            elem_classes="model-info"
                        )
                        
                        # 创建可折叠的设置面板
                        settings_btn = gr.Button("⚙️ 设置", elem_classes=["settings-button"], size="sm")
                        
                        # 创建隐私管理按钮
                        privacy_management_btn = gr.Button("🔒 隐私管理", elem_classes=["privacy-management-button"], size="sm")
                        
                        # 可折叠的设置内容（默认隐藏）
                        with gr.Column(visible=False, elem_classes=["settings-content"]) as settings_content:
                            gr.Markdown("### 🔧 高级设置", elem_classes=["settings-title"])
                            
                            # 相似度阈值调节滑条
                            similarity_threshold_slider = gr.Slider(
                                minimum=0.0,
                                maximum=1.0,
                                value=0.0,
                                step=0.01,
                                label="🎯 相似度阈值",
                                info="设置文档相似度过滤阈值，低于此值的文档将被过滤掉",
                                elem_classes=["similarity-slider"]
                            )
                            
                            # 检索片段数量调节滑条
                            retrieval_limit_slider = gr.Slider(
                                minimum=1,
                                maximum=10,
                                value=3,
                                step=1,
                                label="📄 检索片段数量",
                                info="设置每次检索返回的文档片段数量，数量越多信息越全面但响应越慢",
                                elem_classes=["retrieval-slider"]
                            )
                            
                            # 复杂度阈值调节滑条
                            complexity_threshold_slider = gr.Slider(
                                minimum=0.0,
                                maximum=1.0,
                                value=0.2,
                                step=0.01,
                                label="🧠 复杂度阈值",
                                info="设置复杂度评分阈值，高于此值的查询将优先使用云端模型处理",
                                elem_classes=["complexity-threshold-slider"]
                            )
                            
                            # 关闭按钮
                            close_settings_btn = gr.Button("✖️ 关闭设置", elem_classes=["close-settings-button"], size="sm")
                        
                        # 可折叠的隐私管理内容（默认隐藏）
                        with gr.Column(visible=False, elem_classes=["privacy-management-content"]) as privacy_management_content:
                            gr.Markdown("### 🔒 隐私管理", elem_classes=["privacy-management-title"])
                            
                            # 隐私阈值调节滑条
                            privacy_threshold_slider = gr.Slider(
                                minimum=0.0,
                                maximum=1.0,
                                value=0.85,
                                step=0.01,
                                label="🔒 隐私检测阈值",
                                info="设置隐私检测的敏感度，值越高越容易触发隐私保护模式",
                                elem_classes=["privacy-slider"]
                            )
                            
                            # 隐私词管理区域
                            gr.Markdown("### 🔑 隐私词管理", elem_classes=["privacy-subtitle"])
                            
                            with gr.Row():
                                privacy_keyword_input = gr.Textbox(
                                    placeholder="输入要添加的隐私词...",
                                    label="新增隐私词",
                                    scale=3,
                                    elem_classes=["privacy-keyword-input"]
                                )
                                add_privacy_keyword_btn = gr.Button(
                                    "➕ 添加",
                                    elem_classes=["add-privacy-keyword-button"],
                                    size="sm",
                                    scale=1
                                )
                            
                            # 隐私词添加状态显示
                            privacy_keyword_status = gr.Markdown(
                                "",
                                elem_classes=["privacy-keyword-status"]
                            )
                            
                            # 当前隐私词列表显示
                            current_privacy_keywords = gr.Markdown(
                                "📝 **当前隐私词**: 加载中...",
                                elem_classes=["current-privacy-keywords"]
                            )
                            
                            # 刷新隐私词列表按钮
                            refresh_privacy_keywords_btn = gr.Button(
                                "🔄 刷新隐私词列表",
                                elem_classes=["refresh-privacy-keywords-button"],
                                size="sm"
                            )
                            
                            # 关闭按钮
                            close_privacy_management_btn = gr.Button("✖️ 关闭隐私管理", elem_classes=["close-privacy-management-button"], size="sm")
                        
                    # 右侧：对话区和输入区
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(
                            height=500,
                            render_markdown=True,
                            elem_id="chatbot",
                            elem_classes=["feature-card", "enhanced-chat"],
                            type="messages"
                        )
                        
                        
                        # 响应信息弹窗（默认隐藏）
                        with gr.Column(visible=False, elem_classes=["response-info-modal"]) as response_info_modal:
                            gr.Markdown("## 📊 响应详细信息", elem_classes=["modal-title"])
                            
                            with gr.Row():
                                with gr.Column(scale=1):
                                    gr.Markdown("### 📈 基本统计")
                                    basic_info = gr.Markdown("", elem_classes=["basic-info"])
                                    
                                with gr.Column(scale=1):
                                    gr.Markdown("### 🎯 检索统计")
                                    filter_info = gr.Markdown("", elem_classes=["filter-info"])
                            
                            gr.Markdown("### 📚 引用文档详情")
                            documents_info = gr.Markdown("", elem_classes=["documents-info"])

                            close_modal_btn = gr.Button("✖️ 关闭", elem_classes=["close-modal-button"], size="sm")

                            # 查看复杂度详情按钮
                            view_complexity_btn = gr.Button(
                                "🧠 查看复杂度详情",
                                elem_classes=["view-complexity-button"],
                                size="sm"
                            )

                        # 复杂度详情弹窗（默认隐藏）
                        with gr.Column(visible=False, elem_classes=["complexity-detail-modal"]) as complexity_detail_modal:
                            gr.Markdown("## 🧠 复杂度分析详情", elem_classes=["modal-title"])

                            with gr.Row():
                                with gr.Column(scale=1):
                                    gr.Markdown("### 📊 综合评分")
                                    overall_info = gr.Markdown("", elem_classes=["overall-info"])

                                with gr.Column(scale=1):
                                    gr.Markdown("### 🎯 路由决策")
                                    routing_info = gr.Markdown("", elem_classes=["routing-info"])

                            gr.Markdown("### 📈 五维度详细评分")
                            dimensions_info = gr.Markdown("", elem_classes=["dimensions-info"])

                            gr.Markdown("### 📝 详细分析")
                            analysis_info = gr.Markdown("", elem_classes=["analysis-info"])

                            close_complexity_btn = gr.Button("✖️ 关闭", elem_classes=["close-complexity-button"], size="sm")
                        
                        with gr.Row(elem_classes=["input-container"]):
                            text_input = gr.Textbox(
                                placeholder="输入问题或上传文件...", 
                                lines=1, 
                                scale=3,
                                container=False,
                                elem_classes="input-box",
                                max_lines=2
                            )
                            submit_btn = gr.Button("🚀 发送", elem_classes="action-button")
                        
                        # 检测功能开关（放在对话框下方）
                        with gr.Row(elem_classes=["detection-controls"]):
                            enable_cache_check = gr.Checkbox(
                                value=True,
                                label="💾 缓存",
                                elem_classes=["detection-checkbox-inline"]
                            )
                            enable_network_check = gr.Checkbox(
                                value=True,
                                label="🌐 网络",
                                elem_classes=["detection-checkbox-inline"]
                            )
                            enable_complexity_check = gr.Checkbox(
                                value=True,
                                label="🧠 复杂度",
                                elem_classes=["detection-checkbox-inline"]
                            )
                            enable_privacy_check = gr.Checkbox(
                                value=True,
                                label="🔒 隐私",
                                elem_classes=["detection-checkbox-inline"]
                            )
            
            # 返回所有组件以便在主文件中绑定事件
            components = {
                'chat_interface': chat_interface,
                'current_model': current_model,
                'network_status': network_status,
                'refresh_btn': refresh_btn,
                'status_indicator': status_indicator,
                'model_selector': model_selector,
                'settings_btn': settings_btn,
                'settings_content': settings_content,
                'close_settings_btn': close_settings_btn,
                'privacy_management_btn': privacy_management_btn,
                'privacy_management_content': privacy_management_content,
                'close_privacy_management_btn': close_privacy_management_btn,
                'privacy_threshold_slider': privacy_threshold_slider,
                'similarity_threshold_slider': similarity_threshold_slider,
                'retrieval_limit_slider': retrieval_limit_slider,
                'complexity_threshold_slider': complexity_threshold_slider,
                'enable_cache_check': enable_cache_check,
                'enable_network_check': enable_network_check,
                'enable_complexity_check': enable_complexity_check,
                'enable_privacy_check': enable_privacy_check,
                'privacy_keyword_input': privacy_keyword_input,
                'add_privacy_keyword_btn': add_privacy_keyword_btn,
                'privacy_keyword_status': privacy_keyword_status,
                'current_privacy_keywords': current_privacy_keywords,
                'refresh_privacy_keywords_btn': refresh_privacy_keywords_btn,
                'chatbot': chatbot,
                'response_info_modal': response_info_modal,
                'basic_info': basic_info,
                'filter_info': filter_info,
                'documents_info': documents_info,
                'close_modal_btn': close_modal_btn,
                'view_complexity_btn': view_complexity_btn,
                'complexity_detail_modal': complexity_detail_modal,
                'overall_info': overall_info,
                'routing_info': routing_info,
                'dimensions_info': dimensions_info,
                'analysis_info': analysis_info,
                'close_complexity_btn': close_complexity_btn,
                'text_input': text_input,
                'submit_btn': submit_btn
            }
            
        return components

def handle_file_upload(file):
    """处理上传的文件"""
    try:
        if hasattr(file, 'name') and hasattr(file, 'read'):
            filename = file.name
            content = file.read().decode('utf-8')
            return f"📄 已上传文件: {filename}"
        else:
            return "❌ 文件上传失败"
    except Exception as e:
        return f"❌ 文件处理错误: {str(e)}"
