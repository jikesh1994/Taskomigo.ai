import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { registerUser } from "./support/helpers";

const FIXTURES = path.join(__dirname, "fixtures");
const PDF = path.join(FIXTURES, "priya-resume.pdf");
const DOCX = path.join(FIXTURES, "priya-resume.docx");

async function uploadOnResumesPage(page: Page, file: string) {
  await page.goto("/resumes");
  await page.getByLabel("Upload a resume").setInputFiles(file);
}

test("upload a resume, review differences, and update the profile from it", async ({ page }) => {
  await registerUser(page);
  // A profile that disagrees with the resume on Python experience.
  await page.goto("/profile");
  await page.getByLabel("Skill", { exact: true }).fill("Python");
  await page.getByRole("form", { name: "Add a skill" }).getByLabel("Years").fill("5");
  await page.getByRole("button", { name: "Add skill" }).click();
  await expect(page.getByRole("list", { name: "Your skills" })).toContainText("5 years");

  await uploadOnResumesPage(page, PDF);
  const card = page.getByRole("article", { name: "priya resume" });
  await expect(card.getByText(/Read successfully/)).toBeVisible();
  await expect(card.getByText("Default")).toBeVisible();

  await card.getByRole("button", { name: /^Review \d+$/ }).click();
  await expect(
    card.getByText("Profile and resume contain different experience values. Which should be used?"),
  ).toBeVisible();
  await card.getByRole("radio", { name: "Use resume: 7 years" }).check();
  await card.getByRole("checkbox", { name: /Django \(5 years\)/ }).check();
  await card.getByRole("checkbox", { name: /Senior Backend Engineer at Acme Fintech/ }).check();
  await card.getByRole("button", { name: "Apply 3 choices" }).click();
  await expect(card.getByText("Done: 3 added to your profile.")).toBeVisible();

  await page.goto("/profile");
  const skills = page.getByRole("list", { name: "Your skills" });
  await expect(skills).toContainText("Python · 7 years");
  await expect(skills).toContainText("Django · 5 years");
  await expect(page.getByText("Senior Backend Engineer · Acme Fintech")).toBeVisible();
});

test("manage resumes: second upload, default, rename, download, duplicate, delete", async ({ page }) => {
  await registerUser(page);
  await uploadOnResumesPage(page, PDF);
  const pdfCard = page.getByRole("article", { name: "priya resume" });
  await expect(pdfCard.getByText(/Read successfully/)).toBeVisible();

  // The same file again is refused.
  await page.getByLabel("Upload a resume").setInputFiles(PDF);
  await expect(page.getByText(/already uploaded this file/)).toBeVisible();

  // A Word version, renamed and made the default.
  await page.getByLabel("Upload a resume").setInputFiles(DOCX);
  const cards = page.getByRole("list", { name: "Your resumes" }).getByRole("article");
  await expect(cards).toHaveCount(2);
  const docxCard = cards.filter({ hasText: "priya-resume.docx" });
  await expect(docxCard.getByText(/Read successfully/)).toBeVisible();
  await docxCard.getByRole("button", { name: "Rename" }).click();
  await docxCard.getByLabel("Resume name").fill("General CV");
  await docxCard.getByRole("button", { name: "Save" }).click();
  const general = page.getByRole("article", { name: "General CV" });
  await general.getByRole("button", { name: "Make default" }).click();
  await expect(general.getByText("Default")).toBeVisible();
  await expect(cards.first()).toHaveAccessibleName("General CV"); // default listed first

  const download = page.waitForEvent("download");
  await general.getByRole("button", { name: "Download" }).click();
  expect((await download).suggestedFilename()).toBe("priya-resume.docx");

  await general.getByRole("button", { name: "Delete General CV" }).click();
  await general.getByRole("button", { name: "Confirm" }).click();
  await expect(cards).toHaveCount(1);
  await expect(pdfCard.getByText("Default")).toBeVisible(); // default moves to the remaining resume
});

test("unsupported files are rejected before upload", async ({ page }) => {
  await registerUser(page);
  await page.goto("/resumes");
  await page.getByLabel("Upload a resume").setInputFiles({
    name: "photo.png",
    mimeType: "image/png",
    buffer: Buffer.from([0x89, 0x50, 0x4e, 0x47]),
  });
  await expect(page.getByRole("main").getByRole("alert")).toHaveText("Please choose a PDF or Word (.docx) file.");
  await expect(page.getByText("No resumes yet. Upload one to get started.")).toBeVisible();
});

test("a file disguised as a PDF is rejected by the server", async ({ page }) => {
  await registerUser(page);
  await page.goto("/resumes");
  await page.getByLabel("Upload a resume").setInputFiles({
    name: "resume.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("MZ this is really an executable"),
  });
  await expect(page.getByRole("main").getByRole("alert")).toHaveText("Please upload a PDF or Word (.docx) file.");
});
