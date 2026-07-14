# Canvas SaaS Commercial V1

Clean-room commercial canvas prototype.

## What is included

- Invite-code registration
- Email login
- User center with credit balance
- First registered user can become admin in local development only
- Admin manual credit recharge
- Per-user projects, canvases, uploads, tasks, and storage folders
- Persistent canvas state in SQLite
- Persistent generation tasks with credit deduction and failure refund
- Basic LLM, image, and video task adapters through environment variables
- Docker and docker-compose deployment files

## Local run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python main.py
```

Open:

```text
http://127.0.0.1:3020/register
```

Development invite code in `.env.example` is:

```text
canvasv1
```

This default is for local testing only. The first registered user is admin when `AUTO_ADMIN_FIRST_USER=1`. Keep this local-only convenience off in production.

## Docker run

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

Open:

```text
http://127.0.0.1:3020/
```

## API configuration

Put provider keys and endpoints into `.env`.

```text
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=

IMAGE_API_KEY=
IMAGE_GENERATION_URL=
IMAGE_MODEL=

VIDEO_API_KEY=
VIDEO_GENERATION_URL=
VIDEO_MODEL=
```

The V1 task adapters use OpenAI-style JSON calls with normalized node options. Image, video, and LLM model settings are stored with each task and passed through provider-specific payload builders. Successful image and video media is copied into `storage/users/<user_id>/outputs` before the task is marked complete.

## Production checklist

- Set `APP_ENV=production` or `CANVAS_PRODUCTION=1`.
- Set a strong `SESSION_SECRET` with at least 32 characters.
- Set `COOKIE_SECURE=1` behind HTTPS.
- Set `AUTO_ADMIN_FIRST_USER=0` and initialize the admin account deliberately.
- Use a private `INVITE_CODE` instead of the development default.
- Keep `.env`, `data/`, `storage/`, generated images, and logs out of the Docker image.
- Keep `AUTH_RATE_LIMIT_MAX` and `AUTH_RATE_LIMIT_WINDOW_SECONDS` enabled.
- Keep `TASK_WORKER_ENABLED=1`; tune lease and heartbeat values only when upstream generation regularly exceeds two minutes.
- Set `MAX_OUTPUT_MB` high enough for the largest expected video while retaining an upload/download safety limit.
- Move secrets into platform secret storage.
- Put the app behind HTTPS reverse proxy.
- Back up `data/` and `storage/`.
- Replace SQLite with PostgreSQL before scaling beyond internal beta.
- Add payment provider webhooks before public self-serve recharge.

Initialize the production admin account with:

```powershell
python main.py create-admin owner@example.com <strong-password>
```

Build a clean deployable bundle with:

```powershell
python scripts\build_release_bundle.py --output output\release\canvas-saas-commercial --zip
```
