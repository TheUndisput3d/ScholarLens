import { chromium } from "/tmp/scholarlens-playwright/node_modules/playwright-core/index.mjs";

const browser = await chromium.launch({
  executablePath: "/usr/bin/google-chrome",
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
await page.goto("http://127.0.0.1:8502", { waitUntil: "domcontentloaded" });
await page.getByText("ScholarLens — Research Paper Assistant").waitFor({ timeout: 60000 });
await page.getByRole("button", { name: "+ New Chat" }).click();
await page.waitForTimeout(1000);

const input = page.getByPlaceholder("Ask about your papers, verify a claim, or search the web…");
await input.fill("What is cosine similarity?");
await input.press("Enter");
await page.getByText("Graph state · turn 1").waitFor({ timeout: 180000 });
await page.waitForTimeout(1000);
await page.screenshot({
  path: "docs/assets/screenshots/05-direct-answer.png",
  fullPage: true,
});

await browser.close();
console.log("Captured completed direct-answer response.");
