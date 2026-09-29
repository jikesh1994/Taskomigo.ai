import { expect, test } from "@playwright/test";
import { registerUser } from "./support/helpers";

test("the landing page introduces Taskomigo and leads to sign-up", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Taskomigo/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Your AI amigo for the job hunt");
  await expect(page.getByRole("heading", { name: "The amigo that never lies for you" })).toBeVisible();

  await page.getByRole("link", { name: "See how it works" }).click();
  await expect(page).toHaveURL(/#how-it-works$/);

  await page.getByRole("banner").getByRole("link", { name: "Join early access" }).click();
  await expect(page).toHaveURL(/\/register$/);
  await expect(page.getByRole("heading", { name: "Create your account" })).toBeVisible();
});

test("signed-in visitors get a way back into the app from the landing page", async ({ page }) => {
  await registerUser(page);
  await page.goto("/");
  const open = page.getByRole("banner").getByRole("link", { name: "Open Taskomigo" });
  await expect(open).toBeVisible();
  await open.click();
  await expect(page).toHaveURL(/\/onboarding$/);
});

test("the 3D amigo renders, or its static stand-in without WebGL", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("img", { name: /friendly mascot/ })).toBeVisible();
  await expect(
    page.getByTestId("landing-3d").locator("canvas").or(page.getByTestId("static-amigo")).filter({ visible: true }),
  ).toBeVisible();
});

test("with reduced motion nothing flies: static amigo, still chips", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.getByTestId("static-amigo")).toBeVisible();
  await expect(page.getByTestId("landing-3d")).toHaveCount(0);
  const chip = page.getByText("Filled 11 of 12 fields", { exact: true });
  await expect(chip).toBeVisible();
  const animation = await chip.evaluate((el) => getComputedStyle(el.parentElement!).animationName);
  expect(animation).toBe("none");
});

test("scrolling through the pipeline highlights each step in turn", async ({ page }) => {
  await page.goto("/");
  const pipeline = page.locator("#pipeline");
  const scrollTo = (fraction: number) =>
    page.evaluate((f) => {
      const el = document.querySelector<HTMLElement>("#pipeline")!;
      window.scrollTo(0, el.offsetTop + (el.offsetHeight - window.innerHeight) * f);
    }, fraction);
  await scrollTo(0);
  await expect(pipeline).toHaveAttribute("data-step", "0");
  await scrollTo(0.5);
  await expect(pipeline).toHaveAttribute("data-step", /^[23]$/);
  await scrollTo(1);
  await expect(pipeline).toHaveAttribute("data-step", "5");
  await expect(pipeline.locator('.ring-card[data-active]')).toContainText("Submit");
});

test("hero buttons receive clicks (3D layers never swallow them)", async ({ page }) => {
  await page.goto("/");
  for (const name of ["See how it works", "Join early access"]) {
    const link = page.getByRole("main").getByRole("link", { name }).first();
    const box = (await link.boundingBox())!;
    const hit = await page.evaluate(
      ([x, y]) => document.elementFromPoint(x, y)?.closest("a")?.textContent?.trim(),
      [box.x + box.width / 2, box.y + box.height / 2],
    );
    expect(hit).toBe(name);
  }
});

test("the landing page fits a phone screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
