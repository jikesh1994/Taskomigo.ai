import { expect, type Page } from "@playwright/test";

export const PASSWORD = "correct-horse-42";

let counter = 0;
export function uniqueEmail(prefix = "e2e"): string {
  counter += 1;
  return `${prefix}-${Date.now()}-${counter}@example.com`;
}

/** Registers through the UI and waits for the onboarding wizard. */
export async function registerUser(page: Page, email = uniqueEmail()): Promise<string> {
  await page.goto("/register");
  await page.getByLabel("First name").fill("Ada");
  await page.getByLabel("Last name").fill("Lovelace");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/onboarding/);
  await expect(page.getByRole("heading", { name: "Personal information" })).toBeVisible();
  return email;
}

export async function signIn(page: Page, email: string, password = PASSWORD) {
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

export async function signOut(page: Page) {
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
}

export const stepHeading = (page: Page, name: string) => page.getByRole("heading", { level: 1, name });
