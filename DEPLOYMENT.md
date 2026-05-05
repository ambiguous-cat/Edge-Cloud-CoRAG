# 端云协同 RAG 系统部署说明

本文档只保留最核心的安装依赖与启动步骤。默认后端端口为 `8005`，前端端口为 `5173`，Ollama 端口为 `11434`。

## 1. 环境要求

- Python 3.10+
- Node.js 20.x
- npm
- Ollama
- Git

## 2. 获取代码

```bash
git clone <your-repo-url>
cd <project-root>
```

如果已经有项目目录，直接进入项目根目录即可。

## 3. 启动 Ollama

安装 Ollama 后启动服务：

```bash
ollama serve
```

拉取默认模型：

```bash
ollama pull qwen3:1.7b
```

检查：

```bash
ollama list
```

## 4. 安装后端依赖

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Linux/macOS：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 5. 配置后端环境变量

在项目根目录创建 `.env`：

```env
OLLAMA_HOST=http://localhost:11434
RAG_DEFAULT_MODEL=qwen3:1.7b
RAG_CHAT_MODELS=qwen3:1.7b
```

## 6. 启动后端

项目根目录执行：

```bash
python api_server.py
```

验证：

```text
http://localhost:8005/docs
```

## 7. 安装前端依赖

```bash
cd react-frontend
nvm use 20
npm install
```

如果没有 nvm，请确保当前 Node.js 是 20.x。

## 8. 配置前端环境变量

在 `react-frontend/` 下创建 `.env.local`：

```env
VITE_LOCAL_API_BASE_URL=http://localhost:8005
VITE_CLOUD_API_BASE_URL=http://localhost:8005
VITE_AUTO_ROUTE_TARGET=local
VITE_API_TIMEOUT_MS=60000
```

如有云端后端，将 `VITE_CLOUD_API_BASE_URL` 改为云端 API 地址。

## 9. 启动前端

```bash
npm run dev -- --host 0.0.0.0 --port 5173
```

访问：

```text
http://localhost:5173
```


## 10. 快速验证

- 打开 `http://localhost:8005/docs`，确认后端可用
- 打开 `http://localhost:5173`，确认前端可用
- 在前端发送一条普通问题，确认流式回答正常
- 输入 `/论文检索 RAG reranker`，确认论文检索流程正常
- 切换本地/云端/自动模式，确认接口地址配置正确

