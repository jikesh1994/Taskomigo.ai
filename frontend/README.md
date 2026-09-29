# Frontend

Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS 4.

## Run it

```powershell
npm install
$env:NEXT_PUBLIC_API_URL = "http://localhost:8000"   # default; the API must be running
npm run dev                                          # http://localhost:3000
```

The API's `FRONTEND_URL` must match the address you open the app on (CORS), and the
two must be **same-site** (`localhost` + `localhost`, or `app.example.com` +
`api.example.com`). Otherwise the SameSite=Strict refresh cookie isn't sent. Don't mix
`localhost` and `127.0.0.1`.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with hot reload |
| `npm run build` / `npm start` | Production build and server |
| `npm run lint` | ESLint (Next.js core-web-vitals + TypeScript rules) |
| `npm run typecheck` | Generates route types, then `tsc --noEmit` |
| `npm test` | Unit and component tests (Vitest + Testing Library, jsdom) |
| `npm run test:e2e` | End-to-end tests against the real backend (Playwright) |

### End-to-end tests

Playwright starts the whole stack itself: an in-memory Redis (or yours), the FastAPI
backend on a disposable PostgreSQL database whose schema it **resets**, and a production
build of this app.

```powershell
npx playwright install chromium                # once
$env:E2E_DATABASE_URL = "postgresql+asyncpg://postgres@localhost:5432/jobagent_e2e"
$env:E2E_PYTHON = "C:\path\to\.venv\Scripts\python.exe"   # has the backend installed
# optional: $env:E2E_REDIS_URL = "redis://localhost:6379/15"
npm run test:e2e
```

## Layout

```
app/                  routes (server components that set metadata and render client views)
  (auth)/             /login, /register: redirect away if already signed in
  (app)/              /dashboard, /profile, /settings: signed-in app shell
  onboarding/         the 8-step wizard (?step=… in the URL)
components/
  ui/                 design-system primitives (Button, fields, Switch, TagInput, …)
  auth/ profile/ preferences/ settings/ onboarding/ dashboard/   feature components
hooks/                useAuth (session context), TanStack Query hooks
services/             API client: http.ts (auth + refresh), per-resource modules
stores/session.ts     in-memory access token
lib/                  validation (mirrors backend rules), form-error mapping, options, dates
types/api.ts          TypeScript mirror of the backend schemas
tests/unit/           Vitest
tests/e2e/            Playwright
```

Section forms (`PersonalForm`, `JobSearchForm`, `AgentSettingsForm`, …) are shared by
the onboarding wizard and the profile/settings pages. The host only chooses the submit
label, what happens after a save, and any extra buttons.

## How authentication works

* **Access token:** kept **only in memory** (`stores/session.ts`), never in
  localStorage. It is sent as `Authorization: Bearer …`.
* **Refresh token:** an httpOnly, SameSite=Strict cookie scoped to `/api/v1/auth`.
  JavaScript never reads it. The copy in the JSON response body is ignored.
* **After a reload:** the app calls `POST /auth/refresh` (cookie only) to get a new
  access token. A spinner shows until that resolves.
* **Before each request:** if the token is missing or expires within 30 s, it's
  refreshed first. A 401 triggers one refresh and one retry. If the refresh itself
  fails, the session ends and you're sent to `/login?next=…`.
* **Refresh tokens rotate** and the backend treats reuse as theft, revoking the whole
  session. So refreshes are **single-flight** within a tab and **serialised across
  tabs** with the Web Locks API. Two tabs refreshing at once would otherwise sign the
  user out everywhere. An e2e test covers this, and it fails when the lock is removed.
* **Signing out** in one tab signs out the others (BroadcastChannel).
* **`?next=`** redirects accept same-origin relative paths only.
* Route guards (`components/auth-guard.tsx`) are for UX only. The API enforces
  authorization on every request.
