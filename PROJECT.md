# 端云协同RAG前端重构项目

## Overview

本项目基于现有 Python RAG 后端（FastAPI）与旧版 Gradio 前端，新增一个 React + TypeScript 前端，实现主聊天前端功能的全量重构与已知问题修复。

本轮目标明确为：
- 保留旧前端目录 `前端/`，不移除
- 不改“知识库前端”目录
- 新前端放在 `react-frontend/`
- 使用 `nvm` 管理 Node 版本（20.x）

## Agent Workflow Files

这些文件用于多会话协作，不属于业务源码。

| File | Purpose | Rules |
|------|---------|-------|
| `PROJECT.md` | Agent operating manual with workflow, conventions, and project info | Read-only, do not modify |
| `feature_list.json` | Task board tracking all features and completion status | Only change `passes` from `false` to `true`; never delete, add, or reorder entries |
| `session.txt` | History log of each session's work | Append only; never delete or modify existing records |
| `init.sh` | Startup script to launch the dev environment | Do not modify unless user explicitly asks |
| `docs.md` | Project documentation for human team members | Can add/modify/delete; update as project evolves |

### Session Record Format

```text
## Session [number] - [YYYY-MM-DD]
- Feature: [description]
- Status: [completed/in-progress/blocked]
- Changes: [summary]
- File changes:
  - Added: [file path]
  - Modified: [folder/file path] - [brief description of changes]
  - Deleted: [file path]
- Notes: [observations]
```

### Feature List Format

```json
{
  "id": "F-001",
  "category": "core|ui|api|integration|qa|docs",
  "priority": "high|medium|low",
  "description": "...",
  "acceptance_criteria": ["..."],
  "passes": false
}
```

## Tech Stack

- Backend: Python, FastAPI, SQLite, FAISS, Ollama
- Legacy Frontend: Gradio (`前端/`)
- New Frontend Target: Vite + React + TypeScript + Axios + Ant Design + pure CSS
- Package Manager: npm
- Node Version Manager: nvm
- Node Version: 20.x

## Code Conventions

- 新前端代码仅放在 `react-frontend/`，不改 `前端/` 与 `知识库前端/`
- TypeScript 开启严格类型，避免 `any` 泛滥
- 组件按“页面容器 / 业务组件 / 公共组件”分层
- API 调用统一封装在 `src/services/`
- 纯 CSS 按页面模块拆分，避免大而全单文件
- 所有用户可见错误都需要可读提示，不吞错误
- 流式消息处理必须支持增量渲染与异常中断恢复

## Workflow

Every coding session must follow this workflow:

### Step 1: Read relevant files

- Read this file (`PROJECT.md`)
- Check `git log` to understand recent changes
- Run `./init.sh` to start the development environment
- Read `feature_list.json` and pick ONE unfinished feature (`"passes": false`)
- Read `session.txt` to understand previous progress and notes

### Step 2: Present feature and propose implementation plan

- Explain the chosen feature and its acceptance criteria
- Propose concrete implementation steps and file changes
- Wait for user confirmation before coding
- Update plan if user requests adjustments

### Step 3: Implement feature and request acceptance

- Implement only after plan is approved
- Keep changes scoped to current feature
- Run basic verification for changed behavior
- Explain what was implemented and how to verify
- Ask user to accept

### Step 4: Update documentation and commit

After acceptance:

- Update `feature_list.json` (`passes: false -> true`)
- Append one record to `session.txt`
- Update `docs.md` if architecture/usage changed
- Commit with message: `feat: [feature description]`

## Environment Info

- New frontend port: 5173
- Backend port: 8005
- Legacy Gradio frontend port: 7860 (kept for reference)
- Start command: `./init.sh`
- Verify environment:
  - Backend: `http://localhost:8005/docs`
  - New frontend (after scaffold): `http://localhost:5173`
- If `init.sh` fails, fix environment first before feature work

## Communication Rules

- If requirement is unclear, ask before implementation
- If blocked by environment/dependency issues, report immediately
- For manual QA flows, provide explicit click-by-click verification steps

## Project Rules

- 保留旧前端 `前端/`，不删除、不重命名
- 不重写“知识库前端”目录
- 新 React 前端必须功能对齐主聊天前端并修复已知问题
- `init.sh` 必须包含 `nvm use 20` 的 Node 切换步骤
- API 协议优先兼容现有后端，不先改后端接口

