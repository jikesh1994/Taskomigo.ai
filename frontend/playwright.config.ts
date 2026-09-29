import os from "node:os";
import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

// End-to-end tests run the real stack: FastAPI backend + production Next.js build.
//
// Required: a PostgreSQL database the tests may wipe (its schema is reset with
// `alembic downgrade base && upgrade head` on every run), and the backend's Python
// environment. Configure with:
//   E2E_DATABASE_URL  postgresql+asyncpg://postgres@localhost:5432/jobagent_e2e
//   E2E_PYTHON        python executable with the backend installed (default: python)
//   E2E_REDIS_URL     real Redis to use; if unset, an in-memory fake is started
//
// The frontend and API must be same-site for the SameSite=Strict refresh cookie, so
// both are addressed as "localhost".

const FRONTEND_PORT = Number(process.env.E2E_FRONTEND_PORT ?? 3100);
const API_PORT = Number(process.env.E2E_API_PORT ?? 8011);
const FAKE_REDIS_PORT = 6391;
const FAKE_LLM_PORT = 8766;

const FRONTEND_URL = `http://localhost:${FRONTEND_PORT}`;
const API_URL = `http://localhost:${API_PORT}`;
const PYTHON = process.env.E2E_PYTHON ?? "python";
const BACKEND_DIR = path.resolve(__dirname, "../backend");
const DATABASE_URL = process.env.E2E_DATABASE_URL;

if (!DATABASE_URL) {
  throw new Error("Set E2E_DATABASE_URL to a disposable PostgreSQL database (see playwright.config.ts).");
}

// fakeredis's TCP server answers some commands (e.g. GET on a missing key) with RESP3
// nulls even to RESP2 clients, so talk RESP3 to it. Real Redis needs nothing special.
const redisUrl = process.env.E2E_REDIS_URL ?? `redis://127.0.0.1:${FAKE_REDIS_PORT}/0?protocol=3`;

const backendEnv = {
  ENVIRONMENT: "local",
  DATABASE_URL,
  REDIS_URL: redisUrl,
  SECRET_KEY: "e2e-secret-key-0000000000000000000000",
  JWT_SECRET: "e2e-jwt-secret-1111111111111111111111",
  FRONTEND_URL,
  LOG_JSON: "false",
  LOG_LEVEL: "WARNING",
  // Every page load restores the session via /auth/refresh; don't let the suite trip
  // the per-IP auth rate limit.
  RATE_LIMIT_AUTH_REQUESTS: "10000",
  // Resumes: stored encrypted in a throwaway folder, parsed inline (no worker needed)
  // by the fake OpenAI-compatible model below, through the real provider code.
  ENCRYPTION_KEYS: "ZTJlLW9ubHktZmVybmV0LWtleS1ub3QtZm9yLXByb2Q=",
  STORAGE_LOCAL_PATH: path.join(os.tmpdir(), `taskomigo-e2e-uploads-${process.pid}`),
  RESUME_PARSE_INLINE: "true",
  LLM_PROVIDER: "local",
  LLM_BASE_URL: `http://127.0.0.1:${FAKE_LLM_PORT}/v1`,
  LLM_MODEL: "fake-resume-parser",
  // Jobs: the fake server also plays Greenhouse and Lever (boards "acme" and "globex").
  GREENHOUSE_API_BASE: `http://127.0.0.1:${FAKE_LLM_PORT}`,
  LEVER_API_BASE: `http://127.0.0.1:${FAKE_LLM_PORT}`,
  JOB_TASKS_INLINE: "true",
};

const quoted = (value: string) => `"${value}"`;

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: FRONTEND_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    ...(process.env.E2E_REDIS_URL
      ? []
      : [
          {
            command: `${quoted(PYTHON)} tests/e2e/support/fake_redis.py ${FAKE_REDIS_PORT}`,
            port: FAKE_REDIS_PORT,
            reuseExistingServer: false,
            timeout: 30_000,
          },
        ]),
    {
      command: `${quoted(PYTHON)} -m tests.fake_llm_server ${FAKE_LLM_PORT}`,
      cwd: BACKEND_DIR,
      url: `http://127.0.0.1:${FAKE_LLM_PORT}/health`,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command:
        `${quoted(PYTHON)} -m alembic downgrade base && ${quoted(PYTHON)} -m alembic upgrade head && ` +
        `${quoted(PYTHON)} -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port ${API_PORT}`,
      cwd: BACKEND_DIR,
      env: backendEnv,
      url: `http://127.0.0.1:${API_PORT}/health/ready`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npm run build && npm run start -- --port ${FRONTEND_PORT}`,
      env: { NEXT_PUBLIC_API_URL: API_URL, NEXT_TELEMETRY_DISABLED: "1" },
      url: FRONTEND_URL,
      reuseExistingServer: false,
      timeout: 240_000,
    },
  ],
});
