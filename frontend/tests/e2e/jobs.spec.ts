import { expect, test } from "@playwright/test";
import { registerUser } from "./support/helpers";

// The fake server in backend/tests/fake_llm_server.py plays Greenhouse (board "acme",
// 3 jobs) and Lever (board "globex", 2 jobs), and the AI model for job analysis.

test("follow job boards, search, triage matches and analyse a job", async ({ page }) => {
  await registerUser(page);
  await page.goto("/profile");
  // Enough of the backend job's requirements to clear the default minimum score (60).
  const skills = page.getByRole("list", { name: "Your skills" });
  for (const [skill, years] of [["Python", "6"], ["PostgreSQL", "4"], ["Docker", "3"]]) {
    await page.getByLabel("Skill", { exact: true }).fill(skill);
    await page.getByRole("form", { name: "Add a skill" }).getByLabel("Years").fill(years);
    await page.getByRole("button", { name: "Add skill" }).click();
    await expect(skills).toContainText(skill);
  }

  await page.getByRole("link", { name: "Jobs" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Jobs" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Search for jobs" })).toBeDisabled();

  const boardInput = page.getByLabel("Add a company careers page");
  await boardInput.fill("https://www.linkedin.com/jobs/view/123");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByText(/Paste a Greenhouse or Lever careers link/)).toBeVisible();

  for (const source of ["https://boards.greenhouse.io/acme", "lever:globex"]) {
    await boardInput.fill(source);
    await page.getByRole("button", { name: "Add", exact: true }).click();
    await expect(boardInput).toHaveValue("");
  }
  const boards = page.getByRole("list", { name: "Your job boards" });
  await expect(boards).toContainText("Acme");
  await expect(boards).toContainText("Globex");

  await page.getByRole("button", { name: "Search for jobs" }).click();
  await expect(page.getByText(/5 open jobs, 5 new/)).toBeVisible();

  const backend = page.getByRole("article", { name: "Senior Backend Engineer at Acme" });
  await expect(backend).toBeVisible();
  await expect(backend.getByText(/Python required: on your profile \(you have 6 years\)/)).toBeVisible();
  await expect(page.getByText(/aren.t a prediction of interviews or offers/)).toBeVisible();

  await backend.getByRole("button", { name: "Save" }).click();
  await expect(backend).toBeHidden();
  await page.getByRole("tab", { name: /Saved/ }).click();
  const saved = page.getByRole("article", { name: "Senior Backend Engineer at Acme" });
  await expect(saved).toBeVisible();

  await saved.getByRole("link", { name: "Senior Backend Engineer" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Senior Backend Engineer" })).toBeVisible();
  await expect(page.getByRole("meter", { name: "Skills" })).toBeVisible();
  await expect(page.getByText("“5+ years of experience building backend systems”").first()).toBeVisible();
  await expect(page.getByRole("button", { name: /Apply with AI/ })).toBeDisabled();

  await page.getByRole("button", { name: "Analyse with AI" }).click();
  const degree = page.getByRole("listitem").filter({ hasText: "Computer science degree" });
  await expect(degree.getByText("Inferred")).toBeVisible();
  const python = page.getByRole("listitem").filter({ hasText: "Python and PostgreSQL" });
  await expect(python.getByText("Stated")).toBeVisible();

  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(page.getByText("Job boards", { exact: true })).toBeVisible();
  await expect(page.getByRole("definition").filter({ hasText: /^1$/ }).first()).toBeVisible();
});
