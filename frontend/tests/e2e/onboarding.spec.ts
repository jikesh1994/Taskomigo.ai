import path from "node:path";
import { expect, test } from "@playwright/test";
import { registerUser, stepHeading } from "./support/helpers";

test("a new user completes all eight onboarding steps and lands on the dashboard", async ({ page }) => {
  await registerUser(page);
  const continueButton = page.getByRole("button", { name: "Save and continue" });

  // 1. Personal information
  await expect(page.getByText("Step 1 of 8")).toBeVisible();
  await page.getByLabel("Phone").fill("+91 98765 43210");
  await page.getByLabel("Timezone").selectOption("Asia/Kolkata");
  await continueButton.click();

  // 2. Professional information: client-side URL validation, then save
  await expect(stepHeading(page, "Professional information")).toBeVisible();
  await expect(page).toHaveURL(/step=professional/);
  await page.getByLabel("Professional headline").fill("Senior Python Engineer");
  await page.getByLabel("Current job title").fill("Senior Backend Engineer");
  await page.getByLabel("Current company").fill("Acme");
  await page.getByLabel("Total years of experience").fill("7");
  await page.getByLabel("Require visa sponsorship?").selectOption("no");
  await page.getByLabel("LinkedIn").fill("linkedin.com/in/ada");
  await continueButton.click();
  await expect(page.getByText("Enter a full link, starting with https://")).toBeVisible();
  await page.getByLabel("LinkedIn").fill("https://linkedin.com/in/ada");
  await continueButton.click();

  // 3. Experience
  await expect(stepHeading(page, "Experience")).toBeVisible();
  await page.getByLabel("Job title").fill("Senior Backend Engineer");
  await page.getByLabel("Company").fill("Acme");
  await page.getByLabel("Start month").fill("2019-04");
  await page.getByLabel("I currently work here").check();
  await expect(page.getByLabel("End month")).toBeDisabled();
  const technologies = page.getByRole("textbox", { name: /^Technologies used/ });
  await technologies.fill("Python");
  await technologies.press("Enter");
  await technologies.fill("Django");
  await technologies.press("Enter");
  await page.getByRole("button", { name: "Add experience" }).click();
  await expect(page.getByText("Senior Backend Engineer · Acme")).toBeVisible();
  await expect(page.getByText("Apr 2019 – Present")).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();

  // 4. Education
  await expect(stepHeading(page, "Education")).toBeVisible();
  await page.getByLabel("Institution").fill("IIT Madras");
  await page.getByLabel("Degree or qualification").fill("B.Tech");
  await page.getByLabel("Field of study").fill("Computer Science");
  await page.getByRole("button", { name: "Add education" }).click();
  await expect(page.getByText("B.Tech, Computer Science")).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();

  // 5. Skills: add one, then see the duplicate rejected by the API
  await expect(stepHeading(page, "Skills")).toBeVisible();
  await page.getByLabel("Skill", { exact: true }).fill("Python");
  await page.getByLabel("Years").fill("7");
  await page.getByLabel("Proficiency").selectOption("expert");
  await page.getByRole("button", { name: "Add skill" }).click();
  const skills = page.getByRole("list", { name: "Your skills" });
  await expect(skills.getByText("Python")).toBeVisible();
  await expect(skills).toContainText("7 years · Expert");
  await page.getByLabel("Skill", { exact: true }).fill("python");
  await page.getByRole("button", { name: "Add skill" }).click();
  await expect(page.getByText(/already added this skill/)).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();

  // 6. Resume: uploaded, read by the (fake) AI, and marked as done in the step list
  await expect(stepHeading(page, "Resume")).toBeVisible();
  await page.getByLabel("Upload a resume").setInputFiles(path.join(__dirname, "fixtures", "priya-resume.pdf"));
  await expect(page.getByText(/Read successfully/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Resume (completed)" })).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();

  // 7. Job preferences: a salary needs a currency
  await expect(stepHeading(page, "Job preferences")).toBeVisible();
  const titles = page.getByRole("textbox", { name: /^Job titles/ });
  await titles.fill("Backend Engineer");
  await titles.press("Enter");
  const locations = page.getByRole("textbox", { name: /^Preferred locations/ });
  await locations.fill("Remote");
  await locations.press("Enter");
  await page.getByLabel("Work arrangement").selectOption("remote");
  await page.getByLabel("Expected salary from").fill("3000000");
  await page.getByLabel("Expected salary to").fill("4500000");
  await continueButton.click();
  await expect(page.getByText("Choose a currency for your salary figures")).toBeVisible();
  await page.getByLabel("Currency").selectOption("INR");
  await continueButton.click();

  // 8. Application preferences: auto-submit is locked until review is turned off
  await expect(stepHeading(page, "Application preferences")).toBeVisible();
  const review = page.getByRole("switch", { name: "Review before submitting" });
  const autoSubmit = page.getByRole("switch", { name: "Submit routine applications automatically" });
  await expect(autoSubmit).toBeDisabled();
  await review.click();
  await autoSubmit.click();
  await expect(autoSubmit).toHaveAttribute("aria-checked", "true");
  await page.getByLabel("Applications per day").fill("10");
  await page.getByRole("button", { name: "Finish setup" }).click();

  // Dashboard reflects everything that was saved.
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Welcome, Ada" })).toBeVisible();
  await expect(page.getByText("Finish setting up your profile")).toHaveCount(0);
  await expect(page.getByText("7 of 7")).toBeVisible();
  const behaviour = page.getByRole("definition");
  await expect(behaviour.nth(3)).toHaveText("On"); // Automatic submission
  await expect(behaviour.nth(5)).toHaveText("10"); // Applications per day

  // The profile page shows the saved data after a full reload (session restored from
  // the httpOnly refresh cookie; the access token only ever lived in memory).
  await page.goto("/profile");
  await expect(page.getByLabel("Professional headline")).toHaveValue("Senior Python Engineer");
  await expect(page.getByLabel("Phone")).toHaveValue("+91 98765 43210");
  await expect(page.getByText("Senior Backend Engineer · Acme")).toBeVisible();
  await expect(page.getByRole("list", { name: "Your skills" })).toContainText("Python");
});

test("pages fit a phone screen without horizontal scrolling", async ({ page }) => {
  await registerUser(page);
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of ["/onboarding?step=application-preferences", "/dashboard", "/profile", "/settings"]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, `${path} overflows by ${overflow}px`).toBeLessThanOrEqual(0);
  }
});

test("onboarding progress survives a reload and can be resumed from any step", async ({ page }) => {
  await registerUser(page);
  await page.goto("/onboarding?step=skills");
  await expect(stepHeading(page, "Skills")).toBeVisible();
  await expect(page.getByText("Step 5 of 8")).toBeVisible();

  await page.getByRole("button", { name: /Job preferences/ }).click();
  await expect(page).toHaveURL(/step=job-preferences/);

  await page.goBack();
  await expect(stepHeading(page, "Skills")).toBeVisible();

  // Unknown steps fall back to the first one.
  await page.goto("/onboarding?step=nope");
  await expect(stepHeading(page, "Personal information")).toBeVisible();
});
