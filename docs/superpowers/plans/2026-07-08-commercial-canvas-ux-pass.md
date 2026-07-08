# Commercial Canvas UX Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the clean-room commercial canvas from a thin node prototype into a usable visual AI workflow editor.

**Architecture:** Keep the existing FastAPI, SQLite, auth, credit, project, canvas, upload, and task APIs. Improve the vanilla HTML/CSS/JS canvas UI only, using original copy, original layout, and original interaction code.

**Tech Stack:** FastAPI backend, SQLite persistence, vanilla JavaScript, SVG edge layer, CSS transform viewport.

## Global Constraints

- Do not copy HTML, CSS, JS, prompts, assets, bundled vendors, or branding from `Infinite-Canvas` or `Infinite-Canvas-OnlineV1`.
- Keep changes scoped to `Canvas-SaaS-Commercial`.
- Preserve invite registration, user center, credit balance, admin recharge, per-user storage, and task persistence.
- Do not add API keys or provider secrets.
- Keep drag performance based on transform updates and animation-frame edge redraws.

---

### Task 1: Toolbar And Side Panels

**Files:**
- Modify: `Canvas-SaaS-Commercial/static/index.html`
- Modify: `Canvas-SaaS-Commercial/static/app.css`

**Interfaces:**
- Consumes: existing DOM anchors used by `app.js`.
- Produces: toolbar buttons for prompt, loop, LLM, image, video, output, upload, group, run, workflow, assets, logs; right-side sections for inspector, tasks, assets, logs, workflow.

- [ ] Add compact top-toolbar buttons.
- [ ] Add right panel sections with stable IDs.
- [ ] Add styling for dense operational panels.
- [ ] Verify the page loads without missing DOM anchors.

### Task 2: Specialized Nodes

**Files:**
- Modify: `Canvas-SaaS-Commercial/static/app.js`
- Modify: `Canvas-SaaS-Commercial/static/app.css`

**Interfaces:**
- Consumes: saved canvas state `{ nodes, edges, viewport }`.
- Produces: normalized node state for `prompt`, `loop`, `llm`, `image`, `video`, `output`, and `group`.

- [ ] Add clean Chinese labels and defaults.
- [ ] Add node fields for provider, model, ratio, duration, resolution, output FPS, quantity, system prompt, loop items, and notes.
- [ ] Render each node type with its own controls and previews.
- [ ] Persist control edits into canvas state.

### Task 3: Workflow Semantics And Feedback

**Files:**
- Modify: `Canvas-SaaS-Commercial/static/app.js`

**Interfaces:**
- Consumes: `/api/tasks`, `/api/tasks/{id}`, `/api/uploads`, `/api/canvases/{id}`.
- Produces: upstream context, output aggregation, one-click chain execution, log list, asset list, and workflow JSON export.

- [ ] Keep prompt/image/video references meaningful in upstream context.
- [ ] Run selected node or all selected runnable nodes.
- [ ] Add Output aggregation for upstream text and media.
- [ ] Log task start/success/failure in the right panel.
- [ ] Add asset panel from uploaded/generated nodes.
- [ ] Add workflow export for selected nodes.

### Task 4: Verification

**Files:**
- Test: `Canvas-SaaS-Commercial/static/app.js`
- Test: `Canvas-SaaS-Commercial/main.py`
- Test: `Canvas-SaaS-Commercial/tests/test_*.py`

- [ ] Run `node --check Canvas-SaaS-Commercial/static/app.js`.
- [ ] Run `python -m py_compile Canvas-SaaS-Commercial/main.py`.
- [ ] Run `python -m unittest discover -s Canvas-SaaS-Commercial/tests -p "test_*.py"`.
- [ ] Smoke-test the page loads on `http://127.0.0.1:3020/`.
