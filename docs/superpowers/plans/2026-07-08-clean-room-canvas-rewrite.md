# Clean-Room Canvas Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the commercial prototype's thin canvas with a usable clean-room visual workflow editor.

**Architecture:** Keep the existing FastAPI, SQLite, session, project, canvas, upload, task, credit, and admin APIs. Rebuild only the commercial frontend shell and canvas engine in original vanilla HTML/CSS/JS under `Canvas-SaaS-Commercial/static`.

**Tech Stack:** FastAPI backend, SQLite persistence, vanilla JavaScript canvas engine, SVG edge layer, CSS transform viewport, no old project code or assets.

## Global Constraints

- Do not copy source, CSS, HTML, prompt templates, bundled assets, docs, names, update logic, or visual resources from `Infinite-Canvas` or `Infinite-Canvas-OnlineV1`.
- Keep all implementation files inside `Canvas-SaaS-Commercial`.
- Preserve invite registration, user center, credit balance, admin recharge, per-user storage, and task persistence APIs.
- Do not add API keys or provider secrets to source.
- Optimize dragging by updating element transforms and redrawing edges on animation frames instead of full-rendering every pointer event.

---

### Task 1: Workbench Shell

**Files:**
- Modify: `Canvas-SaaS-Commercial/static/index.html`
- Modify: `Canvas-SaaS-Commercial/static/app.css`

**Interfaces:**
- Consumes: existing `/api/me`, `/api/projects`, `/api/projects/{id}/canvases`, `/api/canvases/{id}`.
- Produces: DOM anchors used by `app.js`: `canvasArea`, `world`, `edgeLayer`, `nodeLayer`, `projectList`, `canvasList`, `nodeInspector`, `taskList`, `accountModal`.

- [x] Build a three-pane workbench: left project/canvas navigation, center canvas area, right inspector/tasks.
- [x] Add compact top toolbar for text, LLM, image, video, output, upload, group, run, save.
- [x] Keep Chinese UI copy while using new wording and no old project branding.

### Task 2: Canvas Engine

**Files:**
- Modify: `Canvas-SaaS-Commercial/static/app.js`
- Modify: `Canvas-SaaS-Commercial/static/app.css`

**Interfaces:**
- Consumes: canvas state JSON `{ nodes, edges, viewport }`.
- Produces: saved canvas state with node positions, prompts, results, edges, groups, and viewport.

- [x] Implement viewport pan and wheel zoom using CSS transforms.
- [x] Implement original node rendering for text, LLM, image, video, output, and group nodes.
- [x] Implement output-to-input connection dragging with SVG Bezier paths.
- [x] Implement multi-select with Shift-click and selection marquee.
- [x] Implement Ctrl+G grouping with dashed group frame and group resize handle.
- [x] Ensure dragging a group moves nodes inside the group boundary.

### Task 3: SaaS API Wiring

**Files:**
- Modify: `Canvas-SaaS-Commercial/static/app.js`

**Interfaces:**
- Consumes: `/api/uploads`, `/api/tasks`, `/api/tasks/{id}`, `/api/canvases/{id}`.
- Produces: task status/result display and persistent canvas state.

- [x] Wire uploads to create image/video nodes with preview URLs.
- [x] Wire run action for text/output local aggregation.
- [x] Wire run action for LLM/image/video tasks with credit refresh and polling.
- [x] Save and reload canvas state through existing backend endpoints.

### Task 4: Verification

**Files:**
- Test: `Canvas-SaaS-Commercial/static/app.js`
- Test: `Canvas-SaaS-Commercial/main.py`
- Test: `Canvas-SaaS-Commercial/tests/test_*.py`

**Interfaces:**
- Produces: verified local URL `http://127.0.0.1:3020/`.

- [x] Run `node --check Canvas-SaaS-Commercial/static/app.js`.
- [x] Run `python -m py_compile Canvas-SaaS-Commercial/main.py`.
- [x] Run `python -m unittest discover -s Canvas-SaaS-Commercial/tests -p "test_*.py"`.
- [x] Run browser smoke test for registration, node creation, edge creation, grouping, save, and console errors.
- [x] Run browser check that moving a group also moves the grouped nodes.
