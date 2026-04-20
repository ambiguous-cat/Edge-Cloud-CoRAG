# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个端云协同RAG（检索增强生成）智能助理系统，主要用于学术文献智能问答场景。系统采用分层架构设计，包含用户交互层、智能路由层、端侧处理层和云端处理层，支持弱网/离线模式、隐私保护和智能路由决策。

## 核心架构

### 端云协同决策流程
系统采用四层优先级决策机制：

1. **缓存命中判断** - 基于语义向量余弦相似度（阈值0.95）
2. **网络状态检测** - 监控云端连接状态和延迟
3. **隐私风险评估** - 双重检测机制（关键词匹配 + 语义相似度）
4. **复杂度评估与路由选择** - 智能分流简单查询到本地、复杂查询到云端

### 关键组件

- **DynamicRouter** (`前端/dynamic_router.py`): 四层优先级决策核心
- **ComplexityAnalyzer** (`complexity_analyzer.py`): 五维复杂度评估
- **PrivacyDetector** (`privacy_detector.py`): 双重隐私检测机制
- **NetworkMonitor** (`前端/network_monitor.py`): 网络状态实时监控
- **DocumentSearcher** (`search_similar_documents.py`): FAISS向量搜索
- **RAGChatService** (`rag_chat.py`): 智能对话生成服务

### 数据层
- **主数据库**: `local_knowledge.db` (SQLite) - documents, document_chunks表
- **向量索引**: `faiss_index.index` (FAISS) - 语义搜索索引
- **隐私数据库**: `privacy_data/privacy_data.db` - 敏感数据保护
- **隐私索引**: `privacy_data/privacy_questions.index` - 隐私检测索引

### 技术栈
- **后端**: FastAPI, SQLite, FAISS, Ollama, OpenAI
- **前端**: Gradio, HTML/CSS, JavaScript
- **AI模型**: Qwen3:1.7b (本地), GLM-4 (云端), BGE嵌入模型
- **核心依赖**: LangChain, Pydantic, Requests, NumPy, scikit-learn

## 常用开发命令

### 服务启动
```bash
# 启动主API服务器（默认端口8005）
python api_server.py

# 启动知识库管理界面
cd 知识库前端 && python advanced_manager.py  # 端口7860

# 启动云端精简版API服务器
cd 云端 && python api_server.py
```

### 文档管理
```bash
# 从文件添加文档到知识库
python add_document_from_file.py <file_path>

# 批量添加JSON论文
python add_json_papers.py

# 重建FAISS索引（删除文档后必须执行）
python rebuild_faiss_index.py

# 初始化隐私检测系统
python initialize_privacy.py
```

### 测试套件
```bash
cd 测试文件

# 核心功能测试
python test.py                    # 基础功能测试
python test_enhanced_api.py       # API接口测试
python test7-rag_chat.py          # RAG对话测试
python test_complexity_analyzer.py # 复杂度分析测试

# 文档管理测试
python test1-add_text.py          # 文档添加测试
python test3-search_similar.py    # 搜索功能测试

# 隐私保护测试
python quick_privacy_view.py      # 隐私数据查看
python check_privacy_db_structure.py # 数据库结构检查
```

## API端点说明

### 文档管理
- `POST /add_document` - 添加文件文档
- `POST /add_json_document` - 添加JSON格式文档
- `GET /documents` - 获取所有文档信息
- `GET /documents/{doc_id}` - 获取指定文档详情
- `DELETE /documents/{doc_id}` - 删除文档

### 检索和对话
- `POST /search` - 文档搜索
- `POST /chat` - 普通对话（支持文档上传）
- `POST /rag_chat` - RAG增强对话

### 隐私和复杂度分析
- `POST /privacy_check` - 隐私风险检测
- `GET /privacy/keywords` - 隐私关键词管理
- `POST /complexity/analyze` - 查询复杂度分析
- `POST /complexity/route` - 路由推荐

### 系统监控
- `GET /system/status` - 系统整体状态
- `POST /feedback` - 用户反馈收集

## 配置文件

### 环境变量配置 (`.env`)
```env
OLLAMA_HOST=http://localhost:11434
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE=your_openai_api_base
DIMENSION=1024
EMBEDDING_MODEL=bge-large:latest
DB_PATH=local_knowledge.db
FAISS_INDEX_PATH=faiss_index
```

### API配置 (`前端/config.py`)
```python
API_CONFIG = {
    "cloud": "http://120.26.231.14:8005",  # 云端API主机
    "local": "http://localhost:8005"       # 本地API主机
}
MODEL_MAP = {
    "云端": "glm-4",           # 云端使用GLM-4
    "本地": "qwen3:1.7b"       # 本地使用Qwen3
}
```

## 重要注意事项

### 数据一致性维护
- **删除文档后必须运行**: `python rebuild_faiss_index.py`
- **添加隐私关键词后必须运行**: `python initialize_privacy.py`
- 定期备份 `local_knowledge.db` 和隐私数据库

### 性能监控点
- **网络延迟**: 通过 `NetworkMonitor` 监控云端API响应时间
- **模型预热**: 系统启动时自动预热，避免首次请求延迟
- **缓存命中率**: 监控语义缓存的命中率和响应性能
- **复杂度分析**: 通过 `ComplexityAnalyzer` 的统计API监控路由决策效果

### 故障排除
- **API服务器连接失败**: 检查端口8005是否被占用，确认ollama服务运行状态
- **模型加载失败**: 检查环境变量配置，确认模型文件存在
- **FAISS索引错误**: 运行 `rebuild_faiss_index.py` 重建索引
- **数据库锁定**: 确保没有多个进程同时访问数据库文件

## 核心架构组件

### 智能路由系统
- **DynamicRouter** (`前端/dynamic_router.py`): 四层优先级决策核心
- **ComplexityAnalyzer** (`complexity_analyzer.py`): 五维复杂度评估
- **PrivacyDetector** (`privacy_detector.py`): 双重隐私检测机制
- **NetworkMonitor** (`前端/network_monitor.py`): 网络状态实时监控

### 核心服务模块
- **主API服务**: `api_server.py` - FastAPI主服务入口
- **文档检索**: `search_similar_documents.py` - FAISS向量搜索
- **RAG对话**: `rag_chat.py` - 智能对话生成服务
- **嵌入模型**: `embedding.py` - 多模型嵌入支持
- **聊天模型**: `chat_model.py` - 统一聊天模型接口

### 前端管理界面
- **高级管理器**: `知识库前端/advanced_manager.py` - Gradio界面
- **配置管理**: `前端/config.py` - API配置和模型映射
- **知识库前端**: `知识库前端/config.py` - 文档管理配置

## 关键配置文件

### API配置 (`前端/config.py`)
```python
API_CONFIG = {
    "cloud": "http://120.26.231.14:8005",  # 云端API主机
    "local": "http://localhost:8005"       # 本地API主机
}
MODEL_MAP = {
    "云端": "glm-4",           # 云端使用GLM-4
    "本地": "qwen3:1.7b"       # 本地使用Qwen3
}
```

### 数据库结构
- **主数据库**: `local_knowledge.db` (SQLite)
- **隐私数据库**: `privacy_data/privacy_data.db`
- **向量索引**: `faiss_index.index` (FAISS)
- **隐私索引**: `privacy_data/privacy_questions.index`

## 开发最佳实践

### 扩展开发指南
- **添加嵌入模型**: 在 `embedding.py` 中扩展 `embedding_models` 列表
- **自定义隐私规则**: 通过 `privacy_detector.py` 的关键词管理API
- **调整路由策略**: 修改 `complexity_analyzer.py` 中的权重配置和维度评估
- **前端界面定制**: 修改 `知识库前端/advanced_manager.py` 和配置文件

### 测试流程
```bash
# 核心功能测试
cd 测试文件
python test.py                    # 基础功能测试
python test_enhanced_api.py       # API接口测试
python test7-rag_chat.py          # RAG对话测试
python test_complexity_analyzer.py # 复杂度分析测试

# 文档管理测试
python test1-add_text.py          # 文档添加测试
python test3-search_similar.py    # 搜索功能测试
python add_json_papers.py          # JSON批量添加测试

# 隐私保护测试
python quick_privacy_view.py      # 隐私数据查看
python check_privacy_db_structure.py # 数据库结构检查
```

### 数据一致性维护
- **索引重建**: 删除文档后必须运行 `rebuild_faiss_index.py`
- **隐私索引更新**: 添加隐私关键词后需运行 `initialize_privacy.py`
- **数据库备份**: 定期备份 `local_knowledge.db` 和隐私数据库

### 性能监控点
- **网络延迟**: 通过 `NetworkMonitor` 监控云端API响应时间
- **模型预热**: 系统启动时自动预热，避免首次请求延迟
- **缓存命中率**: 监控语义缓存的命中率和响应性能
- **复杂度分析**: 通过 `ComplexityAnalyzer` 的统计API监控路由决策效果