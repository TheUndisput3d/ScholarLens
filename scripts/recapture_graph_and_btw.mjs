import { chromium } from "/tmp/scholarlens-playwright/node_modules/playwright-core/index.mjs";
import path from "node:path";

const output = path.join(process.cwd(), "docs", "assets", "screenshots");
const browser = await chromium.launch({ executablePath: "/usr/bin/google-chrome", headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
await page.goto("http://127.0.0.1:8502", { waitUntil: "domcontentloaded" });
await page.getByText("ScholarLens — Research Paper Assistant").waitFor({ timeout: 60000 });

// Use the report session, ask a completed retrieval question, and capture only
// the corresponding inspector rather than a partially scrolled page.
await page.getByRole("button", { name: /Key Security Findings in Research Report/ }).first().click();
await page.waitForTimeout(3000);
const input = page.getByPlaceholder("Ask about your papers, verify a claim, or search the web…");
const graphInspectors = page.locator('[data-testid="stExpander"]').filter({ hasText: /Graph state · turn/ });
const existingInspectorCount = await graphInspectors.count();
await input.fill("Summarize the report's credential-storage risks in three bullets.");
await input.press("Enter");
await page.waitForFunction(
  (count) => document.querySelectorAll('[data-testid="stExpander"]').length > count,
  existingInspectorCount,
  { timeout: 300000 },
);
const inspector = graphInspectors.last();
await inspector.locator('summary').click();
await page.waitForTimeout(750);
await inspector.scrollIntoViewIfNeeded();
await page.screenshot({ path: path.join(output, "04-graph-state.png") });

// A new side-channel question has no persisted history. Wait beyond the
// streaming interval so the screenshot contains the completed answer.
await page.getByRole("button", { name: "+ New Chat" }).click();
await page.waitForTimeout(750);
await input.fill("/btw What is cosine similarity?");
await input.press("Enter");
await page.getByText("Cosine similarity is").waitFor({ timeout: 90000 });
await page.waitForTimeout(8000);
await page.screenshot({ path: path.join(output, "06-btw-direct.png") });

console.log("Recaptured completed graph-state and /btw evidence.");
await browser.close();
