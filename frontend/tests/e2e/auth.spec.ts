import { expect, test } from "@playwright/test";
import { PASSWORD, registerUser, signIn, signOut, uniqueEmail } from "./support/helpers";

test("protected pages send anonymous visitors to sign in, then back", async ({ page }) => {
  const email = await registerUser(page);
  await signOut(page);

  await page.goto("/profile");
  await expect(page).toHaveURL(/\/login\?next=%2Fprofile$/);
  await signIn(page, email);
  await expect(page).toHaveURL(/\/profile$/);
  await expect(page.getByRole("heading", { level: 1, name: "Profile" })).toBeVisible();
});

test("the post-login redirect ignores off-site targets", async ({ page }) => {
  const email = await registerUser(page);
  await signOut(page);

  await page.goto("/login?next=//evil.example/steal");
  await signIn(page, email);
  // Not onboarded yet, so the safe default is the wizard, on our own origin.
  await expect(page).toHaveURL(/^http:\/\/localhost:\d+\/onboarding$/);
});

test("wrong credentials show one generic message", async ({ page }) => {
  const email = await registerUser(page);
  await signOut(page);

  await signIn(page, email, "not-the-password-1");
  await expect(page.getByText("Invalid email or password.")).toBeVisible();
  await signIn(page, uniqueEmail("nobody"), PASSWORD);
  await expect(page.getByText("Invalid email or password.")).toBeVisible();
});

test("registering an existing email is reported on the email field", async ({ page }) => {
  const email = await registerUser(page);
  await signOut(page);

  await page.goto("/register");
  await page.getByLabel("First name").fill("Grace");
  await page.getByLabel("Last name").fill("Hopper");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("An account with this email already exists.")).toBeVisible();
});

test("several tabs restoring the session at once all stay signed in", async ({ page, context }) => {
  // Refresh tokens rotate and reuse revokes the session, so simultaneous refreshes
  // from different tabs must be serialised (Web Locks) or everyone gets signed out.
  await registerUser(page);
  const tabs = [page, ...(await Promise.all([1, 2, 3].map(() => context.newPage())))];

  for (let round = 0; round < 2; round += 1) {
    await Promise.all(tabs.map((tab) => tab.goto("/dashboard")));
    for (const tab of tabs) {
      await expect(tab.getByRole("heading", { name: "Welcome, Ada" })).toBeVisible();
    }
  }
});

test("signing out in one tab signs out the others", async ({ page, context }) => {
  await registerUser(page);
  const other = await context.newPage();
  await other.goto("/dashboard");
  await expect(other.getByRole("heading", { name: "Welcome, Ada" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(other).toHaveURL(/\/login$/);
});

test("changing the password keeps this session and signs in with the new one", async ({ page }) => {
  const email = await registerUser(page);
  await page.goto("/settings");

  await page.getByLabel("Current password").fill(PASSWORD);
  await page.getByLabel("New password", { exact: true }).fill("brand-new-pass-7");
  await page.getByLabel("Confirm new password").fill("brand-new-pass-7");
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page.getByText("Password changed")).toBeVisible();

  // The old refresh token family was revoked server-side; a reload proves the
  // automatic re-login issued a fresh one.
  await page.reload();
  await expect(page.getByRole("heading", { level: 1, name: "Settings" })).toBeVisible();

  await signOut(page);
  await signIn(page, email, PASSWORD);
  await expect(page.getByText("Invalid email or password.")).toBeVisible();
  await signIn(page, email, "brand-new-pass-7");
  await expect(page).toHaveURL(/\/onboarding$/);
});
