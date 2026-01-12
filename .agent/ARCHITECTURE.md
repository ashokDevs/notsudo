# Cloud Agent PR - Architecture & Implementation Plan

## Overview

A GitHub automation tool that creates pull requests in response to issue comments. When someone comments `@notsudo` on an issue, an AI agent analyzes the codebase, generates fixes, **validates them in a Docker sandbox**, and creates a PR.

---



## Target Architecture (Docker Sandbox)

```
GitHub Webhook
    ↓
Flask API
    ↓
Stack Detection (Python? Node.js? Java?)
    ↓
AI Analysis → Generate Code Changes
    ↓
Docker Sandbox
  ├── Clone repo
  ├── Apply changes
  ├── Install dependencies
  └── Run tests
    ↓
┌─────────────────┐
│  Tests Pass?    │
│   Yes → Create PR
│   No  → AI Retry (max 3x)
└─────────────────┘
```

---

## Key Components

### Backend Services (`backend/services/`)

| Service | Purpose |
|---------|---------|
| `ai_service.py` | OpenAI GPT-4 integration with function calling |
| `github_service.py` | GitHub API operations (repos, branches, PRs) |
| `pr_service.py` | Orchestrates the full issue → PR workflow with sandbox validation |
| `stack_detector.py` | Detect project type + Docker config by marker files |
| `docker_sandbox.py` | Container lifecycle management with image resolution |
| `code_execution.py` | Clone → apply → test inside container |

### Frontend (`frontend/`)

Next.js 14 dashboard for:
- Configuration (API keys)
- Job history with status
- Execution logs viewer

---

## Tech Stack

- **Backend**: Python 3.11, Flask, PyGithub, OpenAI SDK, Docker SDK
- **Frontend**: Next.js 14, TypeScript, Tailwind, shadcn/ui
- **Infrastructure**: Docker for sandboxing

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/webhook` | GitHub webhook handler |
| GET | `/api/jobs` | List all jobs |
| GET | `/api/jobs/:id/logs` | Get execution logs |
| GET | `/api/config` | Check credential status |
| GET | `/health` | Health check |

---

## Environment Variables

```bash
GITHUB_TOKEN=       # GitHub PAT with repo access
OPENAI_API_KEY=     # OpenAI API key
WEBHOOK_SECRET=     # Optional: GitHub webhook secret
```
