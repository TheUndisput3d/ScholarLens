import { chromium } from "/tmp/scholarlens-playwright/node_modules/playwright-core/index.mjs";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const screenshots = path.join(root, "docs", "assets", "screenshots");
await mkdir(screenshots, { recursive: true });

const browser = await chromium.launch({
  executablePath: "/usr/bin/google-chrome",
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
await page.goto("http://127.0.0.1:8502", { waitUntil: "domcontentloaded" });
await page.getByText("ScholarLens — Research Paper Assistant").waitFor({ timeout: 60000 });

async function newChat() {
  await page.getByRole("button", { name: "+ New Chat" }).click();
  await page.waitForTimeout(1000);
}

async function ask(prompt, filename, readyText) {
  const input = page.getByPlaceholder("Ask about your papers, verify a claim, or search the web…");
  await input.fill(prompt);
  await input.press("Enter");
  await page.getByText(readyText).waitFor({ timeout: 180000 });
  await page.waitForTimeout(750);
  await page.screenshot({ path: path.join(screenshots, filename), fullPage: true });
}

await newChat();
await ask("What is cosine similarity?", "05-direct-answer.png", "Cosine similarity is");
await newChat();
await ask("/btw What is cosine similarity?", "06-btw-direct.png", "Cosine similarity is");
await newChat();
await ask(
  "Verify this claim: Transformer attention mechanisms remain the dominant foundation for modern language models.",
  "07-claim-verification.png",
  "Claim Verification Result",
);

console.log("Captured direct answer, /btw, and claim-verification UI evidence.");
await browser.close();
