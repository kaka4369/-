# 云芝画布 V1 Spec

## Goal

Build a clean-room commercial canvas product that can be deployed as a paid invite-only web app without using code, visual assets, docs, names, update logic, or license text from the previous Infinite-Canvas project.

## Scope

- Invite-code registration.
- Email/password login.
- Account center with current user and credit balance.
- Admin page for manual credit adjustment.
- Per-user projects, canvases, uploads, outputs, and task records.
- Persisted generation tasks for LLM, image, and video nodes.
- Basic infinite-canvas editor with draggable nodes, connections, saving, and task execution.
- Docker-ready deployment.

## Clean-Room Rules

- Do not copy code from the previous canvas project.
- Do not copy CSS, HTML, prompt templates, bundled assets, README text, update checks, or original project links.
- Use only new source files in this directory.
- Use permissive dependencies only: FastAPI, Uvicorn, HTTPX, Pydantic, Requests, and Python standard library.
- Keep third-party API keys in environment variables or admin-controlled config, not in source.

## V1 Non-Goals

- Automatic payment callbacks.
- Full production object storage.
- Multi-worker queue recovery.
- Full director desk.
- Pixel-perfect parity with the old canvas.

## Data Model

- SQLite database: `data/app.db`.
- User files: `storage/users/<user_id>/`.
- Canvas state: stored as JSON in SQLite.
- Tasks: stored in SQLite with status, cost, result, and error.

## Local Defaults

- `INVITE_CODE=canvasv1`
- `AUTO_ADMIN_FIRST_USER=1`
- `DEFAULT_CREDITS=100`
- Local port: `3020`
