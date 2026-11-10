import { expect, test } from "@playwright/test";

// Full user journey from SRS §2.2 / demo script §13.3.
test("import sample → dashboard → alert evidence → triage → export", async ({ page, request }) => {
  // Start from a clean slate for repeatability (local mode only).
  const datasets = await (await request.get("/api/v1/datasets")).json();
  for (const d of datasets) await request.delete(`/api/v1/datasets/${d.id}`);

  // 1. Import the SSH brute-force sample from the Datasets page.
  await page.goto("/datasets");
  const sample = page.locator("li", { hasText: "SSH – brute force" });
  await sample.getByRole("button", { name: "Load" }).click();
  const banner = page.getByRole("status").filter({ hasText: "Import completed" });
  await expect(banner).toContainText("2 alerts");

  // 2. Dashboard reflects the dataset.
  await banner.getByRole("link", { name: "Open dashboard" }).click();
  await expect(page.getByTestId("stat-Alerts")).toHaveText("2");
  await expect(page.getByTestId("stat-High")).toHaveText("2");
  await expect(page.getByText("Log activity trend")).toBeVisible();

  // 3. Open the alert for the rapid attacker and inspect the evidence.
  await page.getByRole("link", { name: "View all →" }).click();
  const row = page.locator("tr", { hasText: "203.0.113.99" });
  await row.getByRole("link", { name: "Possible SSH Brute Force" }).click();
  await expect(page.getByText("Why this alert fired")).toBeVisible();
  await expect(page.getByText(/not a confirmed attack/)).toBeVisible();
  await expect(page.getByText(/log events linked to this alert/)).toBeVisible();

  await page.locator("tbody tr").first().click();
  const drawer = page.getByRole("dialog");
  await expect(drawer.getByText("Raw log line")).toBeVisible();
  await expect(drawer.locator("pre")).toContainText("Failed password");
  await page.keyboard.press("Escape");

  // 4. Triage: acknowledge and add a note.
  const status = page.getByRole("group", { name: "Alert status" });
  await status.getByRole("button", { name: "ACKNOWLEDGED" }).click();
  await expect(status.getByRole("button", { name: "ACKNOWLEDGED" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("textbox", { name: "Investigation note" }).fill("Dictionary attack from documentation range; no success.");
  await page.getByRole("button", { name: "Add note" }).click();
  await expect(page.getByText("Dictionary attack from documentation range")).toBeVisible();

  // 5. Export JSON for this alert and verify its contents.
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: /Export JSON/ }).click(),
  ]);
  const path = await download.path();
  const json = JSON.parse(await (await import("node:fs/promises")).readFile(path!, "utf-8"));
  expect(json.alert_count).toBe(1);
  expect(json.alerts[0].status).toBe("ACKNOWLEDGED");
  expect(json.alerts[0].notes).toHaveLength(1);
  expect(json.alerts[0].evidence.length).toBe(json.alerts[0].occurrence_count);
});

test("events are filterable and paginated on the server", async ({ page }) => {
  await page.goto("/events");
  await page.getByRole("textbox", { name: "Source IP" }).fill("203.0.113.99");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page).toHaveURL(/source_ip=203.0.113.99/);
  await expect(page.getByText(/matching events/)).toBeVisible();
  const rows = page.locator("tbody tr");
  await expect(rows.first()).toContainText("203.0.113.99");
  expect(await rows.count()).toBeLessThanOrEqual(50);
});
