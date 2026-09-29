# Architecture

## Guiding principle

This is a **general AI job-application agent**, not a set of site-specific scripts.
The core engine understands jobs, profiles, resumes, forms, questions, browser
state, human intervention and application state transitions. Job platforms are
**adapters** around that core; adding a platform must never require rewriting the
agent.

## System overview

```
                    ┌─────────────────────┐
  Browser (user) ──▶│  Next.js frontend   │
                    └─────────┬───────────┘
                              │ REST + WebSocket
                    ┌─────────▼───────────┐        ┌──────────────┐
                    │   FastAPI (api)     │───────▶│  PostgreSQL  │
                    │  thin routes →      │        └──────────────┘
                    │  services → repos   │        ┌──────────────┐
                    └─────────┬───────────┘───────▶│    Redis     │
                              │ enqueue            │ broker/locks │
                    ┌─────────▼───────────┐        │ cache/pubsub │
                    │  Celery workers     │◀──────▶└──────────────┘
                    │  (search, match,    │        ┌──────────────┐
                    │   AI, maintenance)  │───────▶│ Object store │
                    └─────────┬───────────┘        │ (GCS / S3)   │
                              │                    └──────────────┘
                    ┌─────────▼───────────┐
                    │  Browser workers    │  Playwright/Chromium, one
                    │  (application agent)│  isolated context per session
                    └─────────────────────┘
```

* **API** never runs long work. It validates, persists, enqueues and returns.
* **Workers** run job search, JD analysis, matching and AI generation.
* **Browser workers** run the application agent. They're separate because they
  need Chromium, more memory and stricter isolation.
* **Redis** is the Celery broker. It also holds rate-limit counters, distributed
  locks (one worker per application), and pub/sub for live agent events.

## Backend layering

```
api/        HTTP only: parse, authenticate, call a service, shape response
services/   business rules and use cases; own the transaction (commit)
repositories/ SQLAlchemy queries; always scoped by user_id (tenant isolation)
models/     ORM tables
schemas/    Pydantic request/response contracts
core/       config, logging, db, redis, security, encryption, rate limiting
ai/         LLM provider abstraction, prompts, parsers, matchers  (Phase 3+)
agent/      browser agent, page/form analysis, state machine      (Phase 6+)
integrations/ platform adapters (greenhouse, lever, workday, …)   (Phase 4+)
workers/    Celery app and tasks
```

Rules:

* Route functions contain no business logic.
* Every child-entity query joins back to the owning user. A resource owned by
  someone else returns **404**, never 403, so its existence isn't leaked.
* Services commit explicitly. The request-scoped session rolls back on any
  exception.
* Portable column types (`Uuid`, `JSON` → `JSONB` on Postgres, non-native enums)
  keep migrations simple and let fast unit tests run on SQLite. CI also runs
  against PostgreSQL.

## Frontend (Phase 2)

Next.js 16 App Router, React 19, TypeScript, Tailwind CSS 4, TanStack Query,
react-hook-form + Zod.

```
app/          routes. Server pages set metadata and render client feature components.
  (auth)/     /login /register           (redirect away when signed in)
  (app)/      /dashboard /profile /settings  (RequireAuth + app shell)
  onboarding/ 8-step wizard, step in ?step= (reload- and back-button-safe)
components/   ui/ primitives + feature components (profile/, preferences/, …)
hooks/        useAuth (session context), TanStack Query hooks per resource
services/     http.ts (token attach, refresh, retry) + one module per API resource
stores/       in-memory access token
lib/          Zod rules mirroring backend validation, API-error → form mapping
types/api.ts  TypeScript mirror of the backend schemas
```

* **The browser calls the API directly** at `NEXT_PUBLIC_API_URL`, with CORS.
  Proxying through Next.js would make every request come from the Next server's IP
  and collapse the API's per-IP rate limits into one shared bucket. Frontend and
  API must be same-site for the SameSite=Strict refresh cookie.
* **Sessions:** the access token lives in memory. After a reload, `/auth/refresh`
  (cookie only) restores it. Refreshes are single-flight per tab and serialized
  across tabs (Web Locks), because rotated tokens are single-use. See
  [frontend/README.md](../frontend/README.md#how-authentication-works).
* **One form per section, two hosts.** `PersonalForm`, `ProfessionalForm`, the
  experience, education and skills sections, `JobSearchForm` and
  `AgentSettingsForm` are shared by the onboarding wizard and the profile and
  settings pages. The host supplies only the submit label, the post-save action
  and extra buttons.
* **Validation twice:** Zod mirrors the backend rules for instant feedback, and API
  422 details are mapped back onto the matching fields.
* `users.onboarding_completed_at` decides whether sign-in lands on `/onboarding`
  or `/dashboard`. Onboarding never traps the user: the dashboard shows a
  "finish setup" banner instead.

## Resumes and the AI layer (Phase 3)

```
browser ──upload──▶ API: sniff type, size/limit/duplicate checks
                      ├─▶ storage.put(encrypted)          app/storage (local | S3 | GCS)
                      ├─▶ resumes row (status=pending)
                      └─▶ Celery "resumes.parse" ──▶ worker:
                              storage.get → extract text (pypdf / python-docx)
                              → ResumeParser: prompt resume_parsing@v1 → LLMProvider.generate_structured(ParsedResume)
                              → grounding.ground(): drop anything not in the text
                              → resumes.parsed_data, status=parsed | failed(code, message)
browser polls GET /resumes ─▶ GET /resumes/{id}/review ─▶ POST decisions ─▶ profile updated
```

* **`LLMProvider`** (`app/ai/llm`) is the only way the app reaches a model. It offers
  `generate`, `generate_structured` and `embed`. The implementations are
  `AnthropicProvider` (official SDK, structured outputs, server-side refusal fallback),
  `OpenAIProvider` (also used for `local` OpenAI-compatible servers) and
  `DisabledProvider`. `LLM_PROVIDER` picks one, and vendor errors are mapped to
  `LLMError` subclasses with user-safe messages.
* **Prompts** are versioned files in `app/ai/prompts/<name>.v<N>.{system,user}.txt`.
  Each parse stores `prompt_version` and `parser` (`provider:model`), so results stay
  reproducible when prompts change.
* **Idempotent parsing:** the task skips already-parsed resumes, so `acks_late`
  redelivery can't cause duplicate AI calls. Parse failures are stored on the resume
  with a code and a user-safe message, and the user can retry. There is no automatic
  retry.
* **Review items** have stable content-derived IDs. Decisions are stored on the resume,
  so answered items don't come back, and a fresh parse resets them.

## Job search and matching (Phase 4)

```
browser ─POST /job-sources {url}─▶ parse_source → (platform, board) → provider.company_name (validates live)
browser ─POST /jobs/search──────▶ search_runs row (queued) ─▶ Celery "jobs.search" ─▶ worker:
          for each enabled source, concurrently (semaphore):
              provider.search(board) → [NormalizedJob]          app/jobs/providers (greenhouse | lever)
          per board, as results arrive:
              upsert jobs by (platform, external_id); content changed → extract_facts()
              postings missing from the board → is_active=false (closed)
          JobMatchService.match_jobs(user, open jobs from their boards):
              one job per dedupe key (company|title|location) → match_job() → job_matches
browser polls GET /jobs/search/latest ─▶ GET /jobs?tab=matches ─▶ GET /jobs/{id}
          optional: POST /jobs/{id}/analyze ─▶ "jobs.analyze" ─▶ JobAnalyzer (LLM) → grounded → jobs.analysis
```

* **`JobSearchProvider`** (`app/jobs/providers/base.py`) is the only contract a platform
  implements: `supports(source)`, `search(board)`, `get_job`, `normalize_job`,
  `company_name`. Every adapter returns the same `NormalizedJob`. Adding a platform means
  one module plus a line in `registry.py`.
* **`jobs` are shared** across users (one row per posting). Facts, the content hash and
  any AI analysis are computed once per posting, not once per user. `job_matches` hold
  each user's scores and their saved/skipped status, which survives re-searches.
* **Deterministic facts** (`app/jobs/extract.py`): required vs preferred skills by section,
  minimum years, workplace, salary (structured first, then text; `LPA` for India),
  sponsorship and employment type. Each fact keeps the line it came from; anything not
  found stays `null` ("unknown"), never guessed. `EXTRACTOR_VERSION` makes a rules change
  refresh stored facts on the next search without touching AI analyses.
* **Matching** (`app/jobs/matching.py`, no AI): six components (skills 40, experience 20,
  location 10, salary 10, preferences 10, other 10 by default; per-user
  `match_weights`), each producing reasons, missing requirements, concerns and neutral
  notes. Hard filters (excluded company or industry, unrelated title, remote-only,
  minimum salary, employment type, sponsorship) hide a job with the reason shown. Jobs
  below `min_match_score` go to the Hidden tab. Profile skills are canonicalised
  ("postgres" → PostgreSQL) and work-history technologies count too.
* **Resume recommendation:** the parsed resume covering most of the job's skills (the
  default wins ties).
* **AI analysis** is optional and on demand. It uses prompt `job_analysis@v1` and a flat
  schema, is cached per job and invalidated when the posting changes, and every item is
  labelled explicit, inferred or unknown.

## Security model (Phase 1 parts)

| Concern | Implementation |
|---|---|
| Passwords | Argon2id (`argon2-cffi`), transparent rehash on login |
| Access tokens | Short-lived JWT (HS256, 15 min), `typ=access`, issuer checked |
| Refresh tokens | Opaque random, stored as SHA-256 hash, rotated on every use, **reuse detection revokes the whole token family** |
| Account enumeration | Login does a dummy hash verify for unknown emails; identical error message |
| Rate limiting | Redis fixed-window per client IP on auth endpoints, plus failed-login throttling per account |
| RBAC | `role` on user, `require_role()` dependency |
| Secrets at rest | `EncryptionService` (MultiFernet, key rotation) for future browser-session references |
| Logging | structlog JSON, request IDs, recursive redaction of password/token/cookie/secret keys |
| Validation errors | Input values are stripped from 422 responses, so passwords are never echoed |
| Headers | nosniff, frame deny, referrer policy, HSTS in production |
| Production guard | Startup refuses default/short secrets or missing encryption keys |

## Application state machine (implemented in Phase 5)

```
DISCOVERED → MATCHED → READY → STARTED → FORM_FILLING → QUESTIONS_REQUIRED
    → REVIEW_REQUIRED → APPROVED → SUBMITTED
Any active state ⇄ WAITING_FOR_USER / ACCOUNT_REQUIRED   (human intervention)
Any non-terminal state → FAILED | CANCELLED
```
Every transition is persisted with its reason. Submission is idempotent and
guarded by a Redis lock plus a DB uniqueness check on (user, job).

## Human-in-the-loop (non-negotiable)

The agent **stops** and hands control to the user for: account creation, CAPTCHA,
MFA, email verification, legal declarations, sensitive information, low-confidence
answers, unknown questions and final approval. It never tries to bypass CAPTCHA,
MFA, anti-bot or access controls, and it never fabricates user information.
