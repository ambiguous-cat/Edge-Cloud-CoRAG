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

## 9. F-003 Delivery Notes (2026-04-20)

- Added centralized API configuration in `src/services/apiConfig.ts`
  - Supports `VITE_LOCAL_API_BASE_URL`, `VITE_CLOUD_API_BASE_URL`
  - Preserves compatibility with legacy `VITE_API_BASE_URL`
  - Supports `VITE_API_TIMEOUT_MS` and `VITE_AUTO_ROUTE_TARGET`
- Added shared Axios client factory and baseline error normalization in `src/services/httpClient.ts`
- Added service modules:
  - `src/services/chatService.ts` for `/rag_chat` requests
  - `src/services/systemService.ts` for `/system/status` checks
- Updated `src/pages/ChatPage.tsx` to call backend through the unified services layer instead of local placeholder responses
- Unified current user-facing frontend copy to Chinese across updated chat and API status components

Verification:
- `npm run lint` succeeded
- `npm run build` succeeded
- URL hardcoding in frontend request code was centralized under `src/services/apiConfig.ts` and client modules

## 10. F-004 Delivery Notes (2026-04-20)

- Added streaming chat API in `src/services/chatService.ts`
  - Uses `stream: true` with `/rag_chat`
  - Parses SSE blocks (`data: ...`) incrementally
  - Normalizes events to four client-level types: `content`, `info`, `error`, `done`
- Updated chat page send flow in `src/pages/ChatPage.tsx`
  - Uses `for await` over stream events
  - Appends `content` chunks incrementally to the latest assistant message
  - Recognizes and displays `info` statistics
  - Handles `error` and `done` events explicitly
- Added interruption safety
  - Detects unexpected stream termination when terminal event is missing
  - Adds inactivity timeout guard (not only first-chunk timeout)
  - Preserves already streamed content and appends interruption diagnostics

Verification:
- `npm run lint` succeeded
- `npm run build` succeeded

## 11. F-005 Delivery Notes (2026-04-22)

- Added routing decision service in `react-frontend/src/services/routingService.ts`
  - Supports auto/manual mode routing outputs
  - Supports toggle-controlled checks for cache/network/privacy/complexity
  - Supports fallback target calculation based on availability
- Updated chat send flow in `react-frontend/src/pages/ChatPage.tsx`
  - Calls routing decision before request dispatch
  - Shows route reason/status in chat header
  - In auto mode, retries with fallback target when recoverable stream failures occur
- Updated request layer in `react-frontend/src/services/chatService.ts`
  - Added optional `target` override so routing decisions can force local/cloud per request
  - Kept existing mode-based resolution as backward-compatible fallback
- Added routing exports in `react-frontend/src/services/index.ts`

Warning fix completed:
- Converted stream error-event handling to throw `RagStreamError` (instead of plain `Error`) so auto-mode fallback conditions are correctly matched.

Verification:
- `npm run lint` succeeded
- `npm run build` succeeded

## 12. F-006 Delivery Notes (2026-04-22)

- Updated advanced settings behavior in `react-frontend/src/pages/ChatPage.tsx`
  - Added session-scoped persistence via `sessionStorage` for:
    - `similarityThreshold`
    - `retrievalCount`
    - `complexityThreshold`
  - Added input normalization when loading persisted values to keep ranges safe.
- Updated routing linkage in `react-frontend/src/services/routingService.ts`
  - Complexity decision now includes current `complexityThreshold` in route evaluation flow.
  - Route reason text now includes both complexity score and threshold to aid debugging.

Known warning (recorded from review):
- `complexity_threshold` is currently sent by frontend to `/complexity/route`, while backend request model currently only declares `query`.
- Current behavior relies on backend tolerating unknown fields. If backend is switched to strict extra-field validation in the future, this could return 422 and degrade complexity-route behavior.
- Recommended follow-up:
  - Either formally add `complexity_threshold` to backend request model;
  - Or stop sending this field and keep threshold comparison purely on frontend with returned complexity score.

Verification:
- `npm run lint` succeeded
- `npm run build` succeeded

## 13. F-007 Delivery Notes (2026-04-22)

- Added privacy keyword service in `react-frontend/src/services/privacyService.ts`
  - `fetchPrivacyKeywords()` calls `GET /privacy/keywords`
  - `createPrivacyKeyword()` calls `POST /privacy/keywords/add`
- Updated chat page privacy flow in `react-frontend/src/pages/ChatPage.tsx`
  - Loads privacy keyword list on page initialization
  - Submits new keyword to backend and refreshes keyword list after success
  - Shows readable status text for both success and failure cases
- Updated privacy panel interactions in `react-frontend/src/components/chat/PrivacySection.tsx`
  - Added loading state for add/refresh actions
  - Prevented conflicting operations by disabling related controls during requests
- Updated service exports in `react-frontend/src/services/index.ts`

Warning fix from review:
- Added explicit `success === true` validation in privacy service responses before marking add/list calls as successful.

Verification:
- `npm run lint` succeeded
- `npm run build` succeeded
