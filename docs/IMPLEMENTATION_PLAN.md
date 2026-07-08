# Canvas SaaS Commercial V1 Implementation Plan

> **For agentic workers:** implement task-by-task, with tests before production code.

**Goal:** Ship a clean-room invite-only SaaS canvas skeleton that can be deployed and iterated commercially.

**Architecture:** FastAPI serves JSON APIs and static frontend. SQLite stores users, credits, projects, canvases, and tasks. The frontend is plain HTML/CSS/JS and persists canvas state through the API.

**Tech Stack:** Python 3.13, FastAPI, Uvicorn, HTTPX, SQLite, vanilla JavaScript.

## Global Constraints

- No source copy from `Infinite-Canvas` or `Infinite-Canvas-OnlineV1`.
- No original GitHub/ModelScope update logic.
- No real API keys in source.
- Every user-owned object must include `user_id`.
- Failed charged tasks must refund credits once.

## Tasks

- [ ] Core storage and authentication.
- [ ] Credit ledger and admin manual recharge.
- [ ] Project, canvas, asset, and task persistence APIs.
- [ ] Clean commercial frontend.
- [ ] Deployment files and verification.
