import { chromium } from "/tmp/scholarlens-playwright/node_modules/playwright-core/index.mjs";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const output = path.join(root, "docs", "assets", "screenshots");
await mkdir(output, { recursive: true });

const browser = await chromium.launch({
  executablePath: "/usr/bin/google-chrome",
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
await page.goto("http://127.0.0.1:8502", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.getByText("ScholarLens — Research Paper Assistant").waitFor({ timeout: 60000 });

await page.getByRole("button", { name: "+ New Chat" }).click();
await page.waitForTimeout(1000);
await page.locator('input[type="file"]').setInputFiles(
  path.join(root, "documents", "Openclaw_Research_Report.pdf"),
);
await page.getByRole("button", { name: "Add Files", exact: true }).click();
await page.getByText("Openclaw_Research_Report").last().waitFor({ timeout: 180000 });
await page.waitForTimeout(1000);
await page.screenshot({ path: path.join(output, "02-document-ingestion.png"), fullPage: true });

const input = page.getByPlaceholder("Ask about your papers, verify a claim, or search the web…");
await input.fill("What are the key security findings in the uploaded research report?");
await input.press("Enter");
await page.getByText("Graph state · turn 1").waitFor({ timeout: 300000 });
await page.waitForTimeout(1500);
await page.screenshot({ path: path.join(output, "03-grounded-answer.png"), fullPage: true });
await page.getByText("Graph state · turn 1").click();
await page.waitForTimeout(500);
await page.screenshot({ path: path.join(output, "04-graph-state.png"), fullPage: true });

console.log("Captured completed ingestion, answer, and graph evidence.");
await browser.close();
