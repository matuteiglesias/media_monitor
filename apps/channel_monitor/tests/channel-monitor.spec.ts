import fs from "node:fs";
import { expect, test } from "@playwright/test";

test("Latest → People → Search → Item preserves source, corpus and detection evidence", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Media Intelligence Workbench" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Latest publisher activity" })).toBeVisible();
  await expect(page.getByText("El Destape", { exact: false }).first()).toBeVisible();
  await expect(page.getByText("Futurock", { exact: false }).first()).toBeVisible();

  await page.getByRole("button", { name: "People" }).click();
  await expect(page.getByRole("heading", { name: "People" })).toBeVisible();
  await expect(page.getByText("Carlos Melconian", { exact: true })).toBeVisible();
  await expect(page.getByText("Marina Dal Poggetto", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Open appearances" }).first().click();
  await expect(page.getByText(/matched “Carlos Melconian”/)).toBeVisible();

  await page.getByRole("button", { name: "Search" }).click();
  await page.getByLabel("Search media").fill("inflación");
  await page.getByRole("button", { name: "Search" }).last().click();
  await expect(page.getByText("metadata_and_governed_text_literal_match", { exact: false })).toBeVisible();
  await expect(page.getByText(/text_asset \(authorized_asr\)/)).toBeVisible();
  await page.getByRole("button", { name: "Open item" }).first().click();

  await expect(page.getByText("SOURCE", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("MONITOR", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("CORPUS", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("DETECTION", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("authorized_asr", { exact: false }).first()).toBeVisible();
  await expect(page.getByText("whole_item", { exact: false }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /Open on YouTube/ })).toHaveAttribute("href", /youtube\.com\/watch\?v=/);

  await page.getByRole("button", { name: "Outlets" }).click();
  await expect(page.getByText("Governed text coverage").first()).toBeVisible();
  fs.mkdirSync("artifacts", { recursive: true });
  await page.screenshot({ path: "artifacts/m4-media-intelligence-workbench.png", fullPage: true });
});
