import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
test("live Django session through Next proxy", async ({ page }) => {
  test.skip(
    !process.env.ORDERHUB_SMOKE_CREDENTIALS,
    "Set a local fixture credentials file to run against Django.",
  );
  const credentials = JSON.parse(
    readFileSync(process.env.ORDERHUB_SMOKE_CREDENTIALS!, "utf8"),
  ) as { username: string; password: string };
  await page.goto("/login");
  await page.getByLabel("Нэвтрэх нэр").fill(credentials.username);
  await page.getByLabel("Нууц үг").fill(credentials.password);
  await page.getByRole("button", { name: "Нэвтрэх →" }).click();
  await expect(
    page.getByRole("heading", { name: "Мессеж", exact: true }),
  ).toBeVisible();
  const cookies = await page.context().cookies();
  expect(cookies.some((c) => c.name === "sessionid" && c.httpOnly)).toBe(true);
  await page.getByRole("link", { name: "⚙ Холболтууд" }).click();
  await expect(
    page.getByRole("heading", { name: "Холболтууд", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Гарах" }).click();
  await expect(
    page.getByRole("heading", { name: "Тавтай морил" }),
  ).toBeVisible();
  await page.screenshot({ path: "/tmp/orderhub-login.png", fullPage: true });
});
