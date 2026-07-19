import { chromium } from "/tmp/scholarlens-playwright/node_modules/playwright-core/index.mjs";
import path from "node:path";

const output = path.join(process.cwd(), "docs", "assets", "screenshots");
const browser = await chromium.launch({ executablePath: "/usr/bin/google-chrome", headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
await page.goto("http://127.0.0.1:8502", { waitUntil: "domcontentloaded" });
await page.getByText("ScholarLens — Research Paper Assistant").waitFor({ timeout: 60000 });
await page.getByRole("button", { name: /Key Security Findings in Research Report/ }).first().click();
await page.waitForTimeout(1000);

const urlArea = page.getByPlaceholder("https://example.com/paper");
await urlArea.fill("https://en.wikipedia.org/wiki/Retrieval-augmented_generation");
await page.getByRole("button", { name: "Load URLs", exact: true }).click();
await page.getByText("Retrieval-augmented generation").last().waitFor({ timeout: 180000 });
await page.getByText("Loaded Documents").scrollIntoViewIfNeeded();
await page.screenshot({ path: path.join(output, "05-webpage-ingestion.png") });

const arxivInput = page.getByPlaceholder("1706.03762  or  Attention Is All You Need");
await arxivInput.fill("1706.03762");
await page.getByRole("button", { name: "Load ArXiv Paper", exact: true }).click();
await page.getByText("Attention Is All You Need").last().waitFor({ timeout: 180000 });
await page.getByText("Loaded Documents").scrollIntoViewIfNeeded();
await page.screenshot({ path: path.join(output, "06-arxiv-ingestion.png") });

console.log("Captured completed webpage and ArXiv ingestion.");
await browser.close();
