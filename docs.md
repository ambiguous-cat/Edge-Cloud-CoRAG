# Edge-Cloud RAG Frontend Refactor Documentation

## 1. Project Overview

This project keeps the existing Python RAG backend and legacy Gradio frontend, while introducing a new React frontend for the main chat experience.

Key goals:
- Preserve the legacy frontend directory.
- Do not rewrite or remove the knowledge-base frontend directory.
- Build the new frontend in `react-frontend/`.
- Use Node 20.x managed by `nvm`.

## 2. Tech Stack

- Backend: Python, FastAPI, SQLite, FAISS, Ollama
- Legacy Frontend: Gradio
- New Frontend: Vite, React, TypeScript, Axios, Ant Design, CSS
- Node manager: nvm
- Package manager: npm

## 3. Run Instructions

### 3.1 Standard Startup

```bash
./init.sh
```

Expected behavior of `init.sh`:
- Attempts `nvm use 20`
- Starts backend service (`api_server.py`) on port 8005
- Starts new frontend (`react-frontend`) on port 5173 if present

### 3.2 Manual Startup

Backend:
```bash
python api_server.py
```

Frontend:
```bash
cd react-frontend
nvm use 20
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## 4. Architecture Notes

### 4.1 Current Core Components

- API entry: `api_server.py`
- RAG flow: `rag_chat.py`
- Legacy frontend: preserved in original folder
- New React frontend: `react-frontend/`

### 4.2 Target Direction

- Keep legacy frontend for reference/fallback.
- Deliver main chat features in the React frontend.
- Keep API protocol compatible with existing backend endpoints first.

## 5. Refactor Scope

Included:
- Main chat frontend rewrite and alignment
- Fixes for known frontend issues (state sync, modal behavior, data structure handling, error visibility)

Excluded:
- Knowledge-base frontend rewrite
- Deletion of legacy frontend

## 6. Troubleshooting

1. `nvm` not found
- Cause: current shell did not load nvm.
- Fix: load nvm in the current shell and run `nvm use 20`.

2. Frontend fails to start
- Cause: dependencies missing or port conflict.
- Fix: run `npm install`, then retry; check whether port 5173 is occupied.

3. Backend endpoint not reachable
- Cause: `api_server.py` not running.
- Fix: check `http://localhost:8005/docs`.

## 7. F-001 Delivery Notes (2026-04-20)

- Created new frontend workspace: `react-frontend/`
- Initialized stack: Vite + React + TypeScript
- Installed dependencies: `axios`, `antd`
- Added base folders and starter files under `src/pages`, `src/components`, `src/services`, `src/styles`
- Added Axios client scaffold in `src/services/httpClient.ts`
- Enabled TypeScript strict mode in `react-frontend/tsconfig.app.json`

Verification:
- `npm install` completed successfully in `react-frontend/`
- `npm run dev -- --host 0.0.0.0 --port 5173` starts successfully
- `npm run build` succeeds (non-blocking chunk-size warning only)

## 8. F-002 Delivery Notes (2026-04-20)

- Implemented main chat page desktop layout with left control area and right chat area
- Left panel includes model selector, network status, settings section, and privacy management section
- Right panel includes chat message list and composer with send interaction
- UI is implemented with React + Ant Design components (no Gradio dependency)

Verification:
- `npm run build` succeeded
- `npm run lint` succeeded
- Desktop manual flow verified: model switching, network refresh timestamp update, settings toggle/edit, privacy keyword add/refresh, and message send loop

Scope note:
- This delivery follows user-confirmed scope for desktop layout only.
