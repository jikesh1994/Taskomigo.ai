import { expect, test } from "@playwright/test";
import { registerUser } from "./support/helpers";

test("profile and settings edits persist", async ({ page }) => {
  await registerUser(page);

  await page.goto("/profile");
  const personal = page.locator("form").first();
  await page.getByLabel("First name").fill("Augusta");
  await personal.getByRole("button", { name: "Save changes" }).click();
  await expect(personal.getByText("Saved")).toBeVisible();
  // The header uses the updated user without a refetch.
  await expect(page.getByRole("banner")).toContainText("Augusta Lovelace");

  await page.goto("/settings");
  await page.getByLabel("Minimum salary filter").fill("2500000");
  await page.getByLabel("Currency").selectOption("INR");
  await page.getByLabel("Only show remote jobs").check();
  const jobForm = page.locator("form").first();
  await jobForm.getByRole("button", { name: "Save changes" }).click();
  await expect(jobForm.getByText("Saved")).toBeVisible();

  await page.reload();
  await expect(page.getByLabel("Minimum salary filter")).toHaveValue("2500000");
  await expect(page.getByLabel("Only show remote jobs")).toBeChecked();
});

test("platform limits from the API are shown on the field", async ({ page }) => {
  await registerUser(page);
  await page.goto("/settings");

  // The backend caps applications per day platform-wide (100 by default).
  const perDay = page.getByLabel("Applications per day");
  await perDay.fill("500");
  const agentForm = page.locator("form").filter({ has: perDay });
  await agentForm.getByRole("button", { name: "Save changes" }).click();
  await expect(agentForm.getByText("Must be at most 100")).toBeVisible();
  await expect(perDay).toHaveAttribute("aria-invalid", "true");
});

test("experience entries can be edited and deleted", async ({ page }) => {
  await registerUser(page);
  await page.goto("/profile");

  // The profile page also has an education form with month fields; scope to experience.
  const add = page.getByRole("form", { name: "Add experience" });
  await add.getByLabel("Job title").fill("Engineer");
  await add.getByLabel("Company").fill("Initech");
  await add.getByLabel("Start month").fill("2016-01");
  await add.getByLabel("End month").fill("2015-01");
  await add.getByRole("button", { name: "Add experience" }).click();
  await expect(add.getByText(/End can.t be before the start/)).toBeVisible();

  await add.getByLabel("End month").fill("2018-06");
  await add.getByRole("button", { name: "Add experience" }).click();
  await expect(page.getByText("Engineer · Initech")).toBeVisible();

  await page.getByRole("button", { name: "Edit Engineer at Initech" }).click();
  const edit = page.getByRole("form", { name: "Edit experience" });
  await edit.getByLabel("Job title").fill("Staff Engineer");
  await edit.getByRole("button", { name: "Save experience" }).click();
  await expect(page.getByText("Staff Engineer · Initech")).toBeVisible();

  await page.getByRole("button", { name: "Delete Staff Engineer at Initech" }).click();
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByText("Staff Engineer · Initech")).toHaveCount(0);
});
