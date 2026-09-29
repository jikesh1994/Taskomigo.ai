# Security

## Principles

1. **User authorization first.** The agent acts only on the user's own accounts and
   sessions, within each website's terms. It never creates accounts with fabricated
   identities.
2. **No security circumvention.** There is no CAPTCHA solving, MFA bypass, anti-bot
   evasion or rate-limit evasion. When one of these appears, the agent pauses and
   hands control to the user.
3. **No fabrication.** AI output may only use verified profile data, approved
   resumes and answers the user has approved.
4. **Data isolation.** Every query is scoped to the owning user. Another user's
   resource returns 404.
5. **Least exposure.** Secrets never appear in logs, API responses, audit metadata or
   error messages.

## Implemented controls (Phases 1–2)

### Authentication
* Argon2id password hashing, transparently rehashed when parameters change.
* Password policy: minimum length (default 10), at least one letter and one digit,
  maximum 128 characters, no leading or trailing whitespace.
* Access tokens: HS256 JWT, 15-minute lifetime. `typ`, `iss`, `exp`, `nbf` and
  `jti` are validated. Algorithms are pinned, so `alg=none` is rejected.
* Refresh tokens: 384-bit random strings, stored only as SHA-256 hashes, rotated
  on every use.
  * An atomic compare-and-set means only one concurrent refresh can succeed.
  * **Reuse detection**: presenting an already-rotated token revokes the whole
    token family and writes an audit event.
* Refresh cookie: `HttpOnly`, `SameSite=Strict`, `Secure` in staging and
  production, path-scoped to `/api/v1/auth`.
* Login failures return one identical message, and unknown emails get a dummy
  hash verification to equalize timing (no account enumeration).
* A password change revokes every session.

### Authorization
* `require_role()` dependency (roles `user` and `admin`). Users cannot change their
  own role: request schemas use `extra="forbid"`.
* Tenant isolation is enforced in repositories and covered by tests.

### Abuse protection
* Redis fixed-window rate limiting per client IP on register, login and refresh
  (default 10 per minute), returning `429` with `Retry-After`.
* **Per-account login throttling** (Phase 2): after 10 failed sign-ins for one email
  within 15 minutes, from any IP, further attempts for that email get
  `429 login_throttled`, even with the right password. The rules:
  * The check runs before password verification, so it gives no oracle.
  * It applies to unknown emails too, so it can't be used to probe which accounts exist.
  * Redis keys hold a SHA-256 of the email.
  * A successful login resets the count.
  * Trade-off: anyone who knows an email can block that account's sign-in for one
    window. Throttled attempts are audited (`reason: account_throttled`).
  * Configure with `LOGIN_MAX_FAILURES_PER_ACCOUNT` and `LOGIN_FAILURE_WINDOW_SECONDS`.
* Behind a proxy, set `FORWARDED_ALLOW_IPS` to the load balancer's addresses so
  the client IP can't be spoofed through `X-Forwarded-For`.
* The browser calls the API directly rather than through a Next.js proxy, so the
  API's per-IP limits see real client addresses.

### Data protection
* `EncryptionService` (MultiFernet with key rotation) for secrets at rest, such as
  browser-session references from Phase 6.
* Validation error responses omit submitted values, so passwords are never
  echoed.
* Structured logs recursively redact keys matching password, secret, token,
  cookie, authorization, api_key and credential.
* Audit logs record which fields changed, not their values. The exception is
  agent-autonomy toggles, whose new values are recorded.

### Transport and headers
* `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy`, `Cross-Origin-Opener-Policy` and `Permissions-Policy`.
  HSTS is added in production.
* CORS allows only `FRONTEND_URL` plus `CORS_ORIGINS`.

### Configuration safety
* Staging and production refuse to start if `SECRET_KEY` or `JWT_SECRET` is a
  default, shorter than 32 characters, or identical to the other, if
  `ENCRYPTION_KEYS` is missing, or if `DEBUG` is on.
* Empty signing secrets are rejected in every environment.
* Containers run as a non-root user. Compose binds ports to 127.0.0.1 only.

### Frontend (Phase 2)
* **Access token only in memory.** Never in localStorage or sessionStorage, so an
  XSS payload can't read a stored credential. It is lost on reload and restored
  from the refresh cookie.
* **Refresh token only in the httpOnly cookie.** The copy in the JSON body is
  ignored. `credentials: "include"` is sent only to `/auth/*`, where the cookie is
  path-scoped anyway.
* **Refreshes are single-flight and serialized across tabs** (Web Locks API). The
  backend's reuse detection would otherwise revoke the session when two tabs
  refresh at once. An e2e test covers this, and it fails without the lock.
* **Cross-tab sign-out** via BroadcastChannel.
* **Open-redirect guard:** `?next=` accepts only same-origin relative paths
  (`//host` and `/\host` are rejected).
* **CSRF:** the cookie is `SameSite=Strict` and only authenticates `/auth/refresh`
  and `/auth/logout`. Every other endpoint needs the bearer token, which a
  cross-site page can't obtain. JSON bodies force a CORS preflight.
* **Headers:** `X-Content-Type-Options`, `X-Frame-Options: DENY`,
  `Referrer-Policy`, `Permissions-Policy`, and a CSP with `frame-ancestors 'none'`,
  `base-uri 'self'` and `form-action 'self'`. `X-Powered-By` is removed.
* Client-side route guards are UX only. Authorization is enforced by the API on
  every request.
* Error messages shown to users come from the API's safe messages. Unknown
  exceptions show a generic message, and 5xx errors show only a short request ID.
* Frontend and API must be **same-site** (for example `app.example.com` and
  `api.example.com`) for the SameSite=Strict cookie to work.

### AI and uploaded documents (Phase 3)
* **Uploads are identified by content**, not by filename or declared type: a PDF must
  start with the PDF signature, and a DOCX must be a ZIP containing a Word body.
  Anything else gets `415`. The limits are 5 MB, 10 resumes per user and 20 parsed pages.
* **Zip-bomb guard** for DOCX: archives with more than 2,000 entries or more than 50 MB
  uncompressed are refused before parsing. Encrypted PDFs are refused with a clear
  message.
* **Encrypted at rest in the application:** every stored file is Fernet-encrypted with
  `ENCRYPTION_KEYS` before it reaches local disk, S3 or GCS, so a leaked bucket or disk
  image alone exposes nothing. Object keys hold no filenames (`resumes/<user>/<id>`).
* **Downloads** are authenticated and owner-scoped (other users get `404`), sent as an
  attachment with `Cache-Control: private, no-store`.
* **Deleting a resume deletes the stored file first.** If that fails, the record is kept
  so the delete can be retried, rather than leaving an orphaned copy.
* **Prompt injection:** resume text is wrapped in `<resume>` tags and the system prompt
  says it is data, not instructions.
* **Grounding (no fabrication):** each value the model returns is checked against the
  extracted resume text: names, companies, titles, degrees, skills, years, dates,
  links and phone numbers. Anything not found is discarded before storage. This is
  enforced in code (`app/ai/resume/grounding.py`), not just requested in the prompt.
* **Nothing reaches the profile without a decision.** Parsed data only becomes profile
  data through the review endpoint, and it passes through the same validation schemas
  as manual edits.
* **AI keys** stay in configuration and are never logged. Provider errors are mapped to
  generic user messages, so vendor details and response bodies never reach users.
  Logs record counts and codes, never resume content.
* **Server-side refusal fallback** is enabled for Anthropic (`fallbacks: "default"`).
  A refused request is reported to the user as "declined", never retried blindly.

## Secret management

* Local: `.env`, which is git-ignored. `.env.example` holds no values.
* GCP: Secret Manager, mounted as environment variables into Cloud Run. Rotate
  `ENCRYPTION_KEYS` by prepending a new key, then re-encrypting stored values
  with `EncryptionService.rotate`.

## Planned (later phases)

* Account deletion, data export and retention policy (Phase 9).
* A full script CSP with nonces (`script-src 'nonce-…'`) once the app has
  server-rendered pages that need it (Phase 10).
* Browser-session isolation: one Chromium context per session, encrypted
  storage-state references, and no raw passwords stored (Phase 6).
* Error tracking (Sentry) with PII scrubbing, plus security-event alerting
  (Phase 9).
