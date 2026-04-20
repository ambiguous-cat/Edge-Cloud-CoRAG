#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级知识库管理界面
包含完整的增删查功能和数据库管理
"""

import gradio as gr
import requests
import json
import os
import pandas as pd
from typing import List, Dict, Any, Tuple
from config import API_CONFIG, UI_CONFIG, SEARCH_CONFIG

class AdvancedKnowledgeManager:
    def __init__(self):
        self.current_api = "local"  # 默认使用本地API
        self.api_base_url = API_CONFIG[self.current_api]
        self.privacy_threshold = 0.85  # 默认隐私阈值
    
    def switch_api(self, api_type: str):
        """切换API服务器"""
        if api_type in ["local", "cloud"]:
            self.current_api = api_type
            self.api_base_url = API_CONFIG[api_type]
            return f"✅ 已切换到{('本地' if api_type == 'local' else '云端')}知识库"
        return "❌ 无效的API类型"
    
    def set_privacy_threshold(self, threshold: float):
        """设置隐私检测阈值"""
        self.privacy_threshold = threshold
        return f"✅ 隐私阈值已设置为 {threshold:.2f}"
    
    def get_current_api_status(self):
        """获取当前API状态"""
        api_name = "本地" if self.current_api == "local" else "云端"
        try:
            response = requests.get(f"{self.api_base_url}/docs", timeout=3)
            if response.status_code == 200:
                return f"🟢 {api_name}知识库连接正常"
            else:
                return f"🔴 {api_name}知识库连接异常 (状态码: {response.status_code})"
        except Exception as e:
            return f"🔴 {api_name}知识库连接失败: {str(e)}"
        
    
    def search_documents(self, query: str, top_k: int = 10) -> Tuple[str, pd.DataFrame]:
        """搜索文档"""
        if not query.strip():
            return "请输入搜索关键词", pd.DataFrame()
        
        try:
            response = requests.post(
                f"{self.api_base_url}/search",
                json={"query": query, "top_k": top_k},
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json().get("results", [])
                
                if not results:
                    return "未找到相关文档", pd.DataFrame()
                
                # 创建表格数据
                table_data = []
                result_text = f"🔍 找到 {len(results)} 个相关文档\n\n"
                
                for i, doc in enumerate(results):
                    similarity = doc.get('similarity_score', 0)
                    content = doc.get('content', '')
                    content_preview = content[:SEARCH_CONFIG["preview_length"]] + "..." if len(content) > SEARCH_CONFIG["preview_length"] else content
                    source = doc.get('source', 'Unknown')
                    
                    table_data.append({
                        "序号": i + 1,
                        "相似度": f"{similarity:.4f}",
                        "来源": source,
                        "内容预览": content_preview,
                        "完整内容": content
                    })
                
                df = pd.DataFrame(table_data)
                return result_text, df
            else:
                return f"搜索失败: {response.text}", pd.DataFrame()
                
        except Exception as e:
            return f"搜索出错: {str(e)}", pd.DataFrame()
    
    def get_all_documents(self) -> Tuple[str, pd.DataFrame]:
        """通过API获取所有文档片段列表"""
        try:
            response = requests.get(
                f"{self.api_base_url}/documents",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                chunks = data.get("chunks", [])
                statistics = data.get("statistics", {})
                
                if not chunks:
                    return "知识库中暂无文档片段", pd.DataFrame()
                
                table_data = []
                for chunk in chunks:
                    table_data.append({
                        "片段ID": chunk["chunk_id"],
                        "文档ID": chunk["document_id"],
                        "文档标题": chunk["document_title"],
                        "来源": chunk["source"],
                        "片段索引": chunk["chunk_index"],
                        "片段长度": f"{chunk['chunk_length']} 字符",
                        "创建时间": chunk["created_at"],
                        "内容预览": chunk["content_preview"]
                    })
                
                df = pd.DataFrame(table_data)
                
                # 构建详细的统计信息
                faiss_info = statistics.get("faiss_index", {})
                summary = f"""📚 知识库片段统计信息

**文档信息:**
- 总文档数: {statistics.get('total_documents', 0)}
- 总文档片段数: {statistics.get('total_chunks', 0)}
- 当前显示片段: {len(chunks)}

**FAISS索引信息:**
- 向量总数: {faiss_info.get('total_vectors', 0)}
- 向量维度: {faiss_info.get('dimension', 0)}
- 索引类型: {faiss_info.get('index_type', '未知')}

**数据一致性:** {'✅ 正常' if statistics.get('total_chunks', 0) == faiss_info.get('total_vectors', 0) else '⚠️ 不一致'}
"""
                
                return summary, df
            else:
                return f"获取文档片段列表失败: {response.text}", pd.DataFrame()
                
        except Exception as e:
            return f"获取文档片段列表出错: {str(e)}", pd.DataFrame()
    
    def get_document_details(self, doc_id: int) -> str:
        """通过API获取文档详细信息"""
        if not doc_id:
            return "请输入文档ID"
        
        try:
            response = requests.get(
                f"{self.api_base_url}/documents/{doc_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                document = data.get("document", {})
                
                # 构建文档块信息
                chunks_info = ""
                chunks = document.get("chunks", [])
                if chunks:
                    chunks_info = f"\n### 📝 文档块信息 ({len(chunks)} 个)\n"
                    for i, chunk in enumerate(chunks[:5]):  # 只显示前5个块
                        chunks_info += f"\n**块 {chunk['index']}:**\n{chunk['content'][:200]}...\n"
                    
                    if len(chunks) > 5:
                        chunks_info += f"\n*... 还有 {len(chunks) - 5} 个文档块*\n"
                
                details = f"""
## 📄 文档详情

**文档ID**: {document.get('id')}
**标题**: {document.get('title')}
**来源**: {document.get('source', '未知')}
**创建时间**: {document.get('created_at')}
**内容长度**: {document.get('content_length', 0)} 字符
**文档块数量**: {document.get('chunk_count', 0)}

### 📝 完整内容
{document.get('content', '')}

{chunks_info}
                """
                
                return details
            elif response.status_code == 404:
                return f"未找到ID为 {doc_id} 的文档"
            else:
                return f"获取文档详情失败: {response.text}"
                
        except Exception as e:
            return f"获取文档详情出错: {str(e)}"
    
    def delete_document(self, doc_id: int) -> str:
        """通过API删除文档"""
        if not doc_id:
            return "请输入要删除的文档ID"
        
        try:
            response = requests.delete(
                f"{self.api_base_url}/documents/{doc_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # 检查是否有新的响应格式（包含faiss_removed字段）
                if 'faiss_removed' in data:
                    return f"""✅ 删除成功!

**文档信息:**
- 文档ID: {data.get('document_id')}
- 文档标题: {data.get('title')}
- 删除的文档块: {data.get('chunks_deleted')} 个
- 已删除FAISS索引向量: {data.get('faiss_removed')} 个

✅ **状态:** {data.get('message', '删除完成，FAISS索引已同步删除')}
"""
                else:
                    # 兼容旧格式
                    return f"""✅ 删除成功!

**文档信息:**
- 文档ID: {data.get('document_id')}
- 文档标题: {data.get('title')}
- 删除的文档块: {data.get('chunks_deleted')} 个

{data.get('message', '删除完成')}
"""
            elif response.status_code == 404:
                return f"❌ 未找到ID为 {doc_id} 的文档"
            else:
                return f"❌ 删除失败: {response.text}"
                
        except Exception as e:
            return f"❌ 删除文档出错: {str(e)}"
    
    def get_database_stats(self) -> str:
        """通过API获取数据库统计信息"""
        try:
            response = requests.get(
                f"{self.api_base_url}/documents",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                documents = data.get("documents", [])
                statistics = data.get("statistics", {})
                faiss_info = statistics.get("faiss_index", {})
                
                stats = f"""
## 📊 知识库完整统计

### 📄 文档统计
- **总文档数**: {statistics.get('total_documents', 0)}
- **总文档片段数**: {statistics.get('total_chunks', 0)}

### 🔍 FAISS索引统计
- **向量总数**: {faiss_info.get('total_vectors', 0)}
- **向量维度**: {faiss_info.get('dimension', 0)}
- **索引类型**: {faiss_info.get('index_type', '未知')}

### 🎯 数据一致性检查
- **片段与向量匹配**: {'✅ 一致' if statistics.get('total_chunks', 0) == faiss_info.get('total_vectors', 0) else '⚠️ 不一致'}

### 📅 最近的文档片段
"""
                
                chunks = data.get("chunks", [])
                for i, chunk in enumerate(chunks[:5], 1):
                    stats += f"{i}. **{chunk['document_title']}** - 片段 {chunk['chunk_index']} ({chunk['created_at']})\n"
                    stats += f"   - 来源: {chunk['source']} | 长度: {chunk['chunk_length']} 字符 | 片段ID: {chunk['chunk_id']}\n\n"
                
                if len(chunks) > 5:
                    stats += f"*... 还有 {len(chunks) - 5} 个文档片段*\n"
                
                return stats
            else:
                return f"获取统计信息失败: {response.text}"
                
        except Exception as e:
            return f"获取统计信息出错: {str(e)}"
    
    def add_document_from_file(self, file_path: str, title: str, source: str = "") -> str:
        """从文件添加文档"""
        if not file_path:
            return "请选择文件"
        
        if not title.strip():
            return "请输入文档标题"
        
        try:
            response = requests.post(
                f"{self.api_base_url}/add_document",
                json={
                    "file_path": file_path,
                    "title": title.strip(),
                    "source": source.strip() if source.strip() else None
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return f"✅ 文档添加成功!\n文档ID: {result.get('document_id')}"
            else:
                return f"❌ 添加失败: {response.text}"
                
        except Exception as e:
            return f"❌ 添加出错: {str(e)}"
    
    def add_json_document(self, title: str, source: str, json_content: str) -> str:
        """添加JSON格式文档（智能隐私检测和云端同步）"""
        if not title.strip():
            return "请输入文档标题"
        
        if not json_content.strip():
            return "请输入JSON内容"
        
        try:
            json_data = json.loads(json_content)
            
            if not isinstance(json_data, list):
                return "JSON内容必须是数组格式"
            
            result_message = ""
            
            # 根据当前选择的知识库类型决定处理逻辑
            if self.current_api == "local":
                # 本地知识库模式：进行隐私检测
                result_message += "📍 当前模式: 本地知识库（启用隐私检测）\n"
                
                # 1. 隐私检测
                privacy_result = self._check_json_privacy(json_data)
                result_message += f"🔒 隐私检测: {privacy_result['message']}\n"
                
                # 2. 添加到本地知识库
                local_result = self._add_to_local_kb(title, source, json_data)
                result_message += f"🏠 本地添加: {local_result['message']}\n"
                
                # 3. 如果没有隐私风险，同步到云端
                if not privacy_result['has_privacy'] and local_result['success']:
                    cloud_result = self._sync_to_cloud_kb(title, source, json_data)
                    result_message += f"☁️ 云端同步: {cloud_result['message']}\n"
                elif privacy_result['has_privacy']:
                    result_message += "☁️ 云端同步: 跳过（检测到隐私内容）\n"
                    
            else:
                # 云端知识库模式：跳过隐私检测，直接同步
                result_message += "📍 当前模式: 云端知识库（跳过隐私检测）\n"
                result_message += "🔒 隐私检测: 跳过（云端模式）\n"
                
                # 1. 添加到本地知识库
                local_result = self._add_to_local_kb(title, source, json_data)
                result_message += f"🏠 本地添加: {local_result['message']}\n"
                
                # 2. 直接同步到云端（无论内容如何）
                if local_result['success']:
                    cloud_result = self._sync_to_cloud_kb(title, source, json_data)
                    result_message += f"☁️ 云端同步: {cloud_result['message']}\n"
            
            return result_message
                
        except json.JSONDecodeError as e:
            return f"❌ JSON格式错误: {str(e)}"
        except Exception as e:
            return f"❌ 添加出错: {str(e)}"
    
    def _check_json_privacy(self, json_data: list) -> dict:
        """检测JSON内容的隐私风险（阈值: 0.85）"""
        try:
            # 将JSON数据转换为聊天历史格式进行隐私检测
            chat_history = []
            for item in json_data:
                if isinstance(item, dict) and 'text' in item:
                    chat_history.append({
                        "role": "user", 
                        "content": str(item['text'])
                    })
            
            if not chat_history:
                return {"has_privacy": False, "score": 0.0, "message": "无文本内容，跳过检测"}
            
            # 调用本地隐私检测API
            response = requests.post(
                f"{API_CONFIG['local']}/privacy_check",
                json={
                    "chat_history": chat_history,
                    "get_details": False
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                privacy_score = result.get("privacy_score", 0.0)
                is_privacy_risk = result.get("is_privacy_risk", False)
                
                # 使用用户设置的阈值进行判断
                actual_privacy_risk = privacy_score >= self.privacy_threshold
                
                if actual_privacy_risk:
                    return {
                        "has_privacy": True, 
                        "score": privacy_score, 
                        "message": f"检测到隐私内容 (分数: {privacy_score:.2f} ≥ {self.privacy_threshold:.2f})"
                    }
                else:
                    return {
                        "has_privacy": False, 
                        "score": privacy_score, 
                        "message": f"未检测到隐私内容 (分数: {privacy_score:.2f} < {self.privacy_threshold:.2f})"
                    }
            else:
                return {"has_privacy": False, "score": 0.0, "message": "隐私检测失败，默认为安全"}
                
        except Exception as e:
            return {"has_privacy": False, "score": 0.0, "message": f"隐私检测异常: {str(e)}"}
    
    def _add_to_local_kb(self, title: str, source: str, json_data: list) -> dict:
        """添加到本地知识库"""
        try:
            response = requests.post(
                f"{API_CONFIG['local']}/add_json_document",
                json={
                    "title": title.strip(),
                    "source": source.strip() if source.strip() else None,
                    "json_data": json_data
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {"success": True, "message": "添加成功"}
            else:
                return {"success": False, "message": f"添加失败 ({response.status_code})"}
                
        except Exception as e:
            return {"success": False, "message": f"添加异常: {str(e)}"}
    
    def _sync_to_cloud_kb(self, title: str, source: str, json_data: list) -> dict:
        """同步到云端知识库"""
        try:
            response = requests.post(
                f"{API_CONFIG['cloud']}/add_json_document",
                json={
                    "title": title.strip(),
                    "source": source.strip() if source.strip() else None,
                    "json_data": json_data
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "同步成功"}
            else:
                return {"success": False, "message": f"同步失败 ({response.status_code})"}
                
        except Exception as e:
            return {"success": False, "message": f"同步异常: {str(e)}"}

def create_advanced_interface():
    """创建高级知识库管理界面"""
    
    manager = AdvancedKnowledgeManager()
    
    with gr.Blocks(
        title=UI_CONFIG["title"],
        theme=gr.themes.Soft(),
        css="""
        .main-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
        }
        .section-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        }
        .danger-zone {
            background: #fff5f5;
            border: 1px solid #fed7d7;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }
        .stats-card {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border-radius: 8px;
            padding: 20px;
            margin: 10px 0;
        }
        """
    ) as interface:
        
        # 主标题
        gr.HTML("""
        <div class="main-header">
            <h1>📚 高级知识库管理系统</h1>
            <p>完整的知识库增删查管理功能</p>
        </div>
        """)
        
        # API选择器和状态显示
        with gr.Row():
            with gr.Column(scale=2):
                api_selector = gr.Radio(
                    choices=[("🏠 本地知识库", "local"), ("☁️ 云端知识库", "cloud")],
                    value="local",
                    label="选择知识库",
                    interactive=True
                )
            with gr.Column(scale=3):
                api_status = gr.Markdown(manager.get_current_api_status())
            with gr.Column(scale=1):
                refresh_status_btn = gr.Button("🔄 刷新状态", size="sm")
        
        
        # 标签页界面
        with gr.Tabs():
            
            # 搜索标签页
            with gr.TabItem("🔍 文档搜索"):
                with gr.Row():
                    search_query = gr.Textbox(
                        placeholder="输入搜索关键词...",
                        label="搜索内容",
                        scale=3
                    )
                    search_top_k = gr.Slider(
                        minimum=1,
                        maximum=50,
                        value=10,
                        step=1,
                        label="返回数量",
                        scale=1
                    )
                    search_btn = gr.Button("🔍 搜索", variant="primary", scale=1)
                
                search_results = gr.Markdown("")
                search_table = gr.Dataframe(
                    label="搜索结果",
                    interactive=False,
                    wrap=True
                )
            
            # 文档管理标签页
            with gr.TabItem("📋 文档片段管理"):
                with gr.Row():
                    with gr.Column(scale=2):
                        list_docs_btn = gr.Button("📚 获取所有文档片段", variant="primary")
                        doc_list_info = gr.Markdown("")
                        doc_list_table = gr.Dataframe(
                            label="文档片段列表",
                            interactive=False,
                            wrap=True
                        )
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### 📄 文档详情查看")
                        detail_doc_id = gr.Number(
                            label="文档ID",
                            precision=0,
                            minimum=1
                        )
                        get_detail_btn = gr.Button("📖 查看详情")
                        doc_details = gr.Markdown("", label="文档详情")
            
            # 添加文档标签页
            with gr.TabItem("➕ 添加文档"):
                # JSON文档添加区域
                gr.Markdown("### 📝 JSON文档添加（智能隐私检测）")
                with gr.Row():
                    with gr.Column(scale=3):
                        gr.Markdown("""
                        **🔒 智能隐私保护功能**：
                        - **本地知识库模式**: 启用隐私检测，安全内容自动同步到云端
                        - **云端知识库模式**: 跳过隐私检测，所有内容直接同步到云端
                        - 所有内容都会保存到本地知识库作为备份
                        """)
                    with gr.Column(scale=2):
                        privacy_threshold_slider = gr.Slider(
                            minimum=0.0,
                            maximum=1.0,
                            value=0.85,
                            step=0.05,
                            label="🔒 隐私检测阈值（仅本地模式生效）",
                            info="分数高于此阈值的内容将被视为隐私内容"
                        )
                with gr.Row():
                    json_title = gr.Textbox(label="文档标题", placeholder="输入JSON文档标题...")
                    json_source = gr.Textbox(label="文档来源", placeholder="输入文档来源（可选）...")
                json_content = gr.Textbox(
                    label="JSON内容",
                    placeholder="""[{"text": "内容", "section": "章节"}]""",
                    lines=8
                )
                json_add_btn = gr.Button("🔒 智能添加JSON文档", variant="primary")
                json_result = gr.Markdown("", label="添加结果")
                
                # 分隔线
                gr.HTML("<hr style='margin: 30px 0; border: 1px solid #e0e0e0;'>")
                
                # 文件上传区域
                gr.Markdown("### 📁 文件上传")
                file_input = gr.File(
                    label="选择文档文件 (.txt)",
                    file_types=[".txt"]
                )
                with gr.Row():
                    file_title = gr.Textbox(label="文档标题", placeholder="输入文档标题...")
                    file_source = gr.Textbox(label="文档来源", placeholder="输入文档来源（可选）...")
                upload_btn = gr.Button("📤 上传文档", variant="primary")
                upload_result = gr.Markdown("")
            
            # 删除管理标签页
            with gr.TabItem("🗑️ 删除管理"):
                gr.HTML('<div class="danger-zone">')
                gr.Markdown("### ⚠️ 危险操作区域")
                gr.Markdown("**注意**: 删除操作不可恢复，请谨慎操作！")
                
                delete_doc_id = gr.Number(
                    label="要删除的文档ID",
                    precision=0,
                    minimum=1
                )
                delete_btn = gr.Button("🗑️ 删除文档", variant="stop")
                
                delete_result = gr.Markdown("")
                gr.HTML('</div>')
            
            # 统计信息标签页
            with gr.TabItem("📊 统计信息"):
                with gr.Row():
                    stats_btn = gr.Button("📊 获取统计信息", variant="primary")
                
                stats_info = gr.Markdown("", elem_classes=["stats-card"])
        
        # 使用说明
        with gr.Accordion("📖 使用说明", open=False):
            gr.Markdown("""
            ### 功能说明
            
            1. **文档搜索**: 根据关键词搜索知识库中的相关文档
            2. **文档管理**: 查看所有文档列表和详细信息
            3. **添加文档**: 支持文件上传和JSON格式直接添加
            4. **删除管理**: 删除不需要的文档（谨慎操作）
            5. **统计信息**: 查看知识库的整体统计数据
            
            ### 注意事项
            - 确保API服务器正在运行
            - 删除文档后需要手动重建FAISS索引
            - JSON格式必须是有效的数组格式
            """)
        
        # 事件绑定
        
        # API选择器事件
        def handle_api_switch(api_type):
            manager.switch_api(api_type)
            return manager.get_current_api_status()
        
        def handle_refresh_status():
            return manager.get_current_api_status()
        
        # 隐私阈值滑块事件
        def handle_threshold_change(threshold):
            manager.set_privacy_threshold(threshold)
        
        api_selector.change(
            fn=handle_api_switch,
            inputs=[api_selector],
            outputs=[api_status]
        )
        
        refresh_status_btn.click(
            fn=handle_refresh_status,
            outputs=[api_status]
        )
        
        privacy_threshold_slider.change(
            fn=handle_threshold_change,
            inputs=[privacy_threshold_slider]
        )
        
        search_btn.click(
            fn=manager.search_documents,
            inputs=[search_query, search_top_k],
            outputs=[search_results, search_table]
        )
        
        list_docs_btn.click(
            fn=manager.get_all_documents,
            outputs=[doc_list_info, doc_list_table]
        )
        
        get_detail_btn.click(
            fn=manager.get_document_details,
            inputs=[detail_doc_id],
            outputs=[doc_details]
        )
        
        upload_btn.click(
            fn=lambda file, title, source: manager.add_document_from_file(
                file.name if file else "", title, source
            ),
            inputs=[file_input, file_title, file_source],
            outputs=[upload_result]
        )
        
        json_add_btn.click(
            fn=manager.add_json_document,
            inputs=[json_title, json_source, json_content],
            outputs=[json_result]
        )
        
        delete_btn.click(
            fn=manager.delete_document,
            inputs=[delete_doc_id],
            outputs=[delete_result]
        )
        
        stats_btn.click(
            fn=manager.get_database_stats,
            outputs=[stats_info]
        )
        
    
    return interface

if __name__ == "__main__":
    print("🚀 启动高级知识库管理系统...")
    
    interface = create_advanced_interface()
    
    interface.launch(
        server_name=UI_CONFIG["host"],
        server_port=UI_CONFIG["port"],
        share=False,
        show_error=True
    )
