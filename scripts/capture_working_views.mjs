import { chromium } from "/tmp/scholarlens-playwright/node_modules/playwright-core/index.mjs";
import path from "node:path";

const output = path.join(process.cwd(), "docs", "assets", "screenshots");
const browser = await chromium.launch({ executablePath: "/usr/bin/google-chrome", headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
await page.goto("http://127.0.0.1:8502", { waitUntil: "domcontentloaded" });
await page.getByText("ScholarLens — Research Paper Assistant").waitFor({ timeout: 60000 });

const session = page.getByRole("button", { name: /Key Security Findings in Research Report/ });
await session.first().click();
await page.waitForTimeout(1500);

const sidebar = page.locator('[data-testid="stSidebar"]');
await page.getByText("Loaded Documents").scrollIntoViewIfNeeded();
await page.waitForTimeout(500);
await page.screenshot({ path: path.join(output, "02-document-ingestion.png") });

await sidebar.evaluate((element) => { element.scrollTop = 0; });
await page.evaluate(() => window.scrollTo(0, 250));
await page.waitForTimeout(500);
await page.screenshot({ path: path.join(output, "03-grounded-answer.png") });

await page.getByText("Graph state · turn 1").first().click();
await page.waitForTimeout(500);
await page.screenshot({ path: path.join(output, "04-graph-state.png") });

console.log("Captured working document, response, and graph-state views.");
await browser.close();
