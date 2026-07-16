import { chromium } from "/tmp/scholarlens-playwright/node_modules/playwright-core/index.mjs";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const baseUrl = process.env.SCHOLARLENS_URL || "http://127.0.0.1:8502";
const root = process.cwd();
const shots = path.join(root, "docs", "assets", "screenshots");

await mkdir(shots, { recursive: true });

const browser = await chromium.launch({
  executablePath: "/usr/bin/google-chrome",
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
const page = await context.newPage();

await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.getByText("ScholarLens — Research Paper Assistant").waitFor({ timeout: 60000 });
await page.waitForTimeout(2000);
await page.screenshot({ path: path.join(shots, "01-scholar-lens-home.png"), fullPage: true });

const loadedReport = page.getByText("Openclaw_Research_Report");
if (!(await loadedReport.isVisible().catch(() => false))) {
  await page.locator('input[type="file"]').setInputFiles(
    path.join(root, "documents", "Openclaw_Research_Report.pdf"),
  );
  await page.getByRole("button", { name: "Add Files", exact: true }).click();
}
await loadedReport.waitFor({ timeout: 180000 });
await page.waitForTimeout(1500);
await page.screenshot({ path: path.join(shots, "02-document-ingestion.png"), fullPage: true });

const chatInput = page.getByPlaceholder("Ask about your papers, verify a claim, or search the web…");
await chatInput.fill("What are the key security findings in the uploaded research report?");
await chatInput.press("Enter");
await page.getByText("Graph state · turn 1").waitFor({ timeout: 240000 });
await page.waitForTimeout(1500);
await page.screenshot({ path: path.join(shots, "03-grounded-answer.png"), fullPage: true });

await page.getByText("Graph state · turn 1").click();
await page.waitForTimeout(500);
await page.screenshot({ path: path.join(shots, "04-graph-state.png"), fullPage: true });

console.log("Captured document ingestion, grounded answer, and graph state.");
await browser.close();
