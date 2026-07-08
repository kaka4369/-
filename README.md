# Canvas SaaS Commercial V1

Clean-room commercial canvas prototype.

## What is included

- Invite-code registration
- Email login
- User center with credit balance
- First registered user becomes admin by default
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

Default invite code in `.env.example` is:

```text
canvasv1
```

The first registered user is admin when `AUTO_ADMIN_FIRST_USER=1`.

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

The V1 task adapters use simple OpenAI-style JSON calls. Provider-specific routes can be added later in `call_llm`, `call_image`, and `call_video`.

## Production checklist

- Set a strong `SESSION_SECRET`.
- Set `COOKIE_SECURE=1` behind HTTPS.
- Use a private `INVITE_CODE`.
- Move secrets into platform secret storage.
- Put the app behind HTTPS reverse proxy.
- Back up `data/` and `storage/`.
- Replace SQLite with PostgreSQL before scaling beyond internal beta.
- Add payment provider webhooks before public self-serve recharge.
