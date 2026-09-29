# Delivery roadmap

Each phase ends runnable, tested and verified before the next starts.

| Phase | Scope | Status |
|---|---|---|
| **1. Foundation** | Repo layout, config, structured logging, DB layer, models (user, profile, experience, education, skills, job preferences, refresh tokens, audit log), Alembic, JWT auth with rotating refresh tokens, RBAC, rate limiting, encryption service, profile/preferences APIs, health checks, Celery skeleton + maintenance task, Docker Compose, tests | **Done** |
| **2. Frontend foundation** | Next.js 16 + TS + Tailwind 4, login/register, in-memory access token with cross-tab-safe refresh, 8-step onboarding (resume step waits on Phase 3), dashboard, profile & settings pages, change password; backend: `onboarding_completed_at`, per-account login throttling, UTC-offset timestamps; Vitest unit + Playwright e2e against the real backend; frontend Docker image | **Done** |
| **3. Resumes + AI core** | Resume upload (onboarding step 6 and /resumes), encrypted storage (local / S3 / GCS), PDF & DOCX extraction with content sniffing and zip-bomb/page limits, `LLMProvider` (Anthropic, OpenAI, local OpenAI-compatible) with versioned prompts, AI resume parsing in the worker, grounding (anti-fabrication) check, profile-vs-resume review (conflicts and additions) with explicit apply | **Done** (needs an AI key to parse) |
| **4. Jobs** | `JobSearchProvider` interface, Greenhouse & Lever public job-board adapters (add by careers URL, validated live; suggested catalog), normalization into shared `jobs`, closed-posting detection, cross-board dedup, deterministic JD facts with evidence, optional AI JD analysis (explicit/inferred/unknown, grounded, cached per job), deterministic weighted matching (configurable weights) with reasons / missing / concerns and hard filters, resume recommendation, `/jobs` (search, Matches/Saved/Skipped/Hidden) and `/jobs/[id]`, dashboard stats | **Done** |
| 5. Applications | Application model + formal state machine with transition log, duplicate protection, Redis locks, idempotent submission, application APIs | Planned |
| 6. Browser agent | BrowserManager, PageAnalyzer (DOM + accessibility), deterministic field mapping then AI fallback, intervention detection (account/CAPTCHA/MFA/verification), resume upload, pause/save/resume | Planned |
| 7. Questions + review | Question classifier, verified-info retrieval, answer generation + validation + confidence gating, review/approve/submit flow | Planned |
| 8. Realtime + control | WebSocket agent events, agent page, start/pause/resume/stop/skip, notifications (in-app, email) | Planned |
| 9. Privacy, admin, observability | Export/delete account/resume/application data, session revoke, admin dashboard, metrics | Planned |
| 10. Production | GCP (Cloud Run, Cloud SQL, Memorystore, GCS, Secret Manager), Terraform, CI/CD | Planned |
