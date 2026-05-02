# Edge-Cloud Collaborative RAG Frontend Rewrite

## Overview

This project is based on an existing Python RAG backend (FastAPI) and a legacy Gradio frontend.
The current goal is to add a new React + TypeScript frontend that fully rewrites the main chat UI and fixes known interaction issues.

Current scope:
- Keep the legacy frontend directory (`legacy_gradio_frontend_dir` in this document).
- Do not rewrite the knowledge-base management frontend (`knowledge_base_frontend_dir` in this document).
- Place the new frontend in `react-frontend/`.
- Use `nvm` to manage Node version (`20.x`).

## Agent Workflow Files

These files are collaboration artifacts for coding agents and are separate from business source code.

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
- Legacy Frontend: Gradio (`legacy_gradio_frontend_dir`)
- New Frontend Target: Vite + React + TypeScript + Axios + Ant Design + pure CSS
- Package Manager: npm
- Node Version Manager: nvm
- Node Version: 20.x

## Code Conventions

- Put all new frontend code only in `react-frontend/`; do not modify `legacy_gradio_frontend_dir` or `knowledge_base_frontend_dir` unless explicitly requested.
- Use strict TypeScript typing; avoid unnecessary `any`.
- Organize components by page containers, business components, and shared components.
- Centralize all API calls under `src/services/`.
- Use modular pure CSS files by page/feature, not one oversized stylesheet.
- All user-visible errors must be readable; do not swallow errors silently.
- Streaming message handling must support incremental rendering and graceful interruption recovery.

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
- Update the plan if user requests adjustments

### Step 3: Implement feature and request acceptance

- Implement only after plan is approved
- Keep changes scoped to the current feature
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
- Legacy Gradio frontend port: 7860 (for reference)
- Start command: `./init.sh`
- Verify environment:
  - Backend: `http://localhost:8005/docs`
  - New frontend (after scaffold): `http://localhost:5173`
- If `init.sh` fails, fix the environment first before feature work

## Communication Rules

- If a requirement is unclear, ask before implementation
- If blocked by environment/dependency issues, report immediately
- For manual QA flows, provide explicit step-by-step verification instructions

## Project Rules

- Keep the legacy frontend (`legacy_gradio_frontend_dir`); do not delete or rename it.
- Do not rewrite the knowledge-base frontend (`knowledge_base_frontend_dir`).
- The new React frontend must match all main-chat features and fix known issues.
- `init.sh` must include a Node switch step using `nvm use 20`.
- Keep API compatibility with the existing backend protocol whenever possible.
