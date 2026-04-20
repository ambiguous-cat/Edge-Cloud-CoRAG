# 端云协同RAG前端重构文档

## 1. 项目概述

本项目当前以 Python RAG 服务为核心，原有主前端使用 Gradio。  
重构目标是在不删除旧前端的前提下，新增 `react-frontend/`，使用 React 技术栈重写主聊天前端（不包含“知识库前端”）。

## 2. 技术栈

- Backend: Python + FastAPI + SQLite + FAISS + Ollama
- Legacy Frontend: Gradio
- New Frontend (target): Vite + React + TypeScript + Axios + Ant Design + pure CSS
- Node manager: nvm
- Package manager: npm

## 3. 运行方式

### 3.1 环境启动（统一）

```bash
./init.sh
```

`init.sh` 行为：
- 尝试执行 `nvm use 20`
- 后台启动 `api_server.py`（8005）
- 若 `react-frontend/` 已存在则后台启动前端（5173）

### 3.2 手动启动（可选）

后端：
```bash
python api_server.py
```

新前端（脚手架完成后）：
```bash
cd react-frontend
nvm use 20
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## 4. 架构说明

### 4.1 当前架构

- API 服务入口：`api_server.py`
- RAG 服务：`rag_chat.py`
- 原主前端：`前端/`
- 知识库前端：`知识库前端/`

### 4.2 目标架构（重构后）

- 保留：`前端/`（仅作对照/回退）
- 新增：`react-frontend/`（主前端）
- 后端接口保持兼容，优先复用现有 `/rag_chat`、`/privacy_*`、`/complexity/*`、`/system/*`

## 5. 项目目录结构（当前）

```text
新建文件夹/
├─ api_server.py
├─ rag_chat.py
├─ chat_model.py
├─ complexity_analyzer.py
├─ privacy_detector.py
├─ search_similar_documents.py
├─ 前端/
├─ 知识库前端/
├─ 云端/
├─ privacy_data/
├─ 语料/
├─ PROJECT.md
├─ feature_list.json
├─ session.txt
├─ init.sh
└─ docs.md
```

## 6. 重构范围

包含：
- 主聊天前端功能全量复刻
- 已知问题修复（状态同步、弹窗可达性、消息结构兼容、错误处理等）

不包含：
- 知识库前端重写
- 旧前端删除

## 7. 常见问题排查

1. `nvm` 命令不可用  
原因：shell 未加载 nvm。  
处理：在当前 shell 先加载 nvm，再执行 `nvm use 20`。

2. 前端无法启动  
原因：依赖未安装或端口占用。  
处理：`npm install` 后重试，检查 5173 端口占用。

3. 后端接口不可达  
原因：`api_server.py` 未启动。  
处理：访问 `http://localhost:8005/docs` 确认服务状态。


## 8. F-001 Delivery Notes (2026-04-20)

- Created new frontend workspace: `react-frontend/`
- Initialized stack: Vite + React + TypeScript
- Installed dependencies: `axios`, `antd`
- Added base folders and starter files under `src/pages`, `src/components`, `src/services`, `src/styles`
- Added Axios client scaffold in `src/services/httpClient.ts`
- Enabled TypeScript strict mode in `react-frontend/tsconfig.app.json`

### Verification

- `npm install` completed successfully in `react-frontend/`
- `npm run dev -- --host 0.0.0.0 --port 5173` starts successfully
- `npm run build` succeeds (non-blocking chunk-size warning only)
