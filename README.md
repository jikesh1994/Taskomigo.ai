# Taskomigo

*Your AI amigo for the job hunt.*

Taskomigo is a controlled personal AI agent that searches for relevant jobs, understands
application forms, fills routine fields from **verified** profile data, and **pauses
for the user** whenever a human decision or verification is needed: account
creation, CAPTCHA, MFA, legal declarations, low-confidence answers and final
approval.

> Current status: **Phases 1–3 are done.** Phase 1 is the backend foundation, Phase 2
> the web app (sign-in, 8-step onboarding, profile and settings), and Phase 3 resumes
> with AI parsing. See
> [docs/ROADMAP.md](docs/ROADMAP.md) for the phase plan and
> [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design.

## Repository layout

```
job-agent/
├── backend/                 FastAPI API + Celery workers (Python)
│   ├── app/
│   │   ├── api/             HTTP layer (thin routes, deps, error envelope, health)
│   │   ├── core/            config, logging, db, redis, security, encryption, rate limits
│   │   ├── models/          SQLAlchemy models
│   │   ├── schemas/         Pydantic request/response models
│   │   ├── repositories/    data access, always scoped to the owning user
│   │   ├── services/        business logic + transactions
│   │   └── workers/         Celery app + tasks
│   ├── alembic/             database migrations
│   └── tests/               unit + integration tests
├── frontend/                Next.js web app (see frontend/README.md)
├── docs/                    architecture, roadmap, security
├── docker-compose.yml       local stack
└── .env.example             configuration template
```

Later phases add `backend/app/ai`, `backend/app/agent`, `backend/app/integrations`, a
browser-worker service and `infra/` (Terraform/GCP).

## Quick start (Docker)

```bash
cp .env.example .env          # optional for local dev; dev-only defaults are built in
docker compose up --build
```

* App: http://localhost:3000. The public landing page is at `/`. Create an account
  and you're taken to onboarding.
* API docs: http://localhost:8000/docs (Swagger) and http://localhost:8000/redoc
* Health: http://localhost:8000/health/live and http://localhost:8000/health/ready
* Postgres is exposed on `localhost:5433` and Redis on `localhost:6379`

The `migrate` service runs `alembic upgrade head` before `api`, `worker` and `beat`
start. `frontend` waits for a healthy `api`.

Open the app at `http://localhost:3000`, not `127.0.0.1`. The frontend and API must be
same-site for the sign-in cookie. `PUBLIC_API_URL` is baked into the frontend image at
build time, so rebuild after changing it.

## Turning on AI (resume parsing)

Resumes can be uploaded without AI, but they're only read once a model is configured.
Put these in `.env` (never commit it), then restart with `docker compose up -d`:

```bash
# Anthropic (default model claude-opus-5-5)
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...

# or OpenAI
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
LLM_MODEL=<model id>

# or a local OpenAI-compatible server (Ollama, vLLM, ...)
LLM_PROVIDER=local
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_MODEL=<model>
```

Resumes that failed while AI was off show **Try again**; use it after adding the key.

`api`, `worker`, `beat` and `migrate` share one image. After changing backend code, run
`docker compose up --build -d --force-recreate` so the worker doesn't keep old code.
Every AI result is checked against the resume text, and anything that can't be found in
it is discarded (see [docs/SECURITY.md](docs/SECURITY.md#ai-and-uploaded-documents)).

## Local development (without Docker)

Requirements: Python 3.11+ (3.12 recommended; the Docker image uses 3.12),
PostgreSQL 14+, Redis 6+, Node.js 20.9+.

```powershell
# API
cd backend
pip install -e ".[dev]"
$env:DATABASE_URL = "postgresql+asyncpg://postgres@localhost:5432/jobagent_dev"
$env:REDIS_URL    = "redis://localhost:6379/0"
# Required for resume uploads (files are encrypted at rest):
$env:ENCRYPTION_KEYS = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Optional: parse inside the API instead of the worker
$env:RESUME_PARSE_INLINE = "true"
alembic upgrade head
uvicorn app.main:create_app --factory --reload
celery -A app.workers.celery_app worker --pool=solo --loglevel=INFO   # --pool=solo on Windows
celery -A app.workers.celery_app beat --loglevel=INFO

# Web app (another terminal)
cd frontend
npm install
npm run dev                                   # http://localhost:3000
```

## Tests and quality

```powershell
# backend
cd backend
pytest                                   # fast: SQLite + fakeredis
$env:TEST_DATABASE_URL = "postgresql+asyncpg://postgres@localhost:5432/jobagent_test"
pytest                                   # same suite against real PostgreSQL
ruff check . ; ruff format --check .
alembic check                            # fails if models and migrations drift

# frontend
cd frontend
npm run lint ; npm run typecheck ; npm test
npm run test:e2e                         # real backend + browser; see frontend/README.md
```

## API overview

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/auth/register` | Create account (plus empty profile and default preferences) |
| POST | `/api/v1/auth/login` | Sign in → access and refresh tokens (throttled per IP and per account) |
| POST | `/api/v1/auth/refresh` | Rotate refresh token (body or httpOnly cookie) |
| POST | `/api/v1/auth/logout` | Revoke current session |
| GET/PATCH | `/api/v1/users/me` | Personal information |
| POST | `/api/v1/users/me/onboarding/complete` | Mark onboarding done (idempotent) |
| POST | `/api/v1/users/me/password` | Change password (revokes all sessions) |
| GET/PUT/PATCH | `/api/v1/profile` | Professional profile |
| GET/POST/PATCH/DELETE | `/api/v1/profile/experiences[/{id}]` | Work experience |
| GET/POST/PATCH/DELETE | `/api/v1/profile/education[/{id}]` | Education |
| GET/POST/PATCH/DELETE | `/api/v1/profile/skills[/{id}]` | Skills (unique, case-insensitive) |
| GET/PUT/PATCH | `/api/v1/preferences` | Job-search criteria and agent autonomy settings |
| POST/GET | `/api/v1/resumes` | Upload (PDF/DOCX, multipart, 202 then parsed in the background) / list |
| GET/PATCH/DELETE | `/api/v1/resumes/{id}` | Details and parsed data / rename or make default / delete with the file |
| GET | `/api/v1/resumes/{id}/file` | Download the original |
| POST | `/api/v1/resumes/{id}/parse` | Parse again (for example after configuring AI) |
| GET/POST | `/api/v1/resumes/{id}/review` | Conflicts and additions vs. the profile / apply your decisions |
| GET | `/health/live`, `/health/ready` | Liveness and readiness (DB + Redis) |

Every error uses one envelope:
`{"error": {"code", "message", "details", "request_id"}}`. Timestamps always carry
a UTC offset.

## Further reading

* [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): layering, data flow, frontend, state machine
* [docs/SECURITY.md](docs/SECURITY.md): threat model and controls
* [docs/ROADMAP.md](docs/ROADMAP.md): phases
* [frontend/README.md](frontend/README.md): web app structure and session handling
