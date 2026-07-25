import { chromium } from "/tmp/scholarlens-playwright/node_modules/playwright-core/index.mjs";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const baseUrl = process.env.SCHOLARLENS_DEMO_URL || "http://127.0.0.1:8503";
const videoDir = path.join(root, "docs", "assets", "video");
const screenshotDir = path.join(root, "docs", "assets", "screenshots");
const rawDir = path.join(videoDir, "raw");
const timelinePath = "/tmp/scholarlens-e2e-timeline.json";
await Promise.all([mkdir(rawDir, { recursive: true }), mkdir(screenshotDir, { recursive: true })]);

const startedAt = Date.now();
const timeline = {};
function mark(name) {
  const seconds = Number(((Date.now() - startedAt) / 1000).toFixed(3));
  timeline[name] = seconds;
  process.stdout.write(`${name}=${seconds}\n`);
}

const browser = await chromium.launch({
  executablePath: "/usr/bin/google-chrome",
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  recordVideo: { dir: rawDir, size: { width: 1440, height: 900 } },
});
const page = await context.newPage();
const video = page.video();

await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.getByText("ScholarLens — Research Paper Assistant").waitFor({ timeout: 60000 });
mark("workspace_ready");
await page.waitForTimeout(1500);

await page.getByRole("button", { name: "+ New Chat" }).click();
mark("new_session_created");
await page.waitForTimeout(1200);

await page.locator('input[type="file"]').setInputFiles(
  path.join(root, "documents", "Openclaw_Research_Report.pdf"),
);
await page.waitForTimeout(1000);
await page.getByRole("button", { name: "Add Files", exact: true }).click();
mark("report_ingestion_started");
await page.getByText("Loaded Documents").scrollIntoViewIfNeeded();
await page.getByText("Openclaw_Research_Report").last().waitFor({ timeout: 240000 });
mark("report_ingestion_done");
await page.waitForTimeout(1800);

const sidebar = page.locator('[data-testid="stSidebar"]');
await sidebar.evaluate((element) => { element.scrollTop = 0; });
const input = page.getByPlaceholder("Ask about your papers, verify a claim, or search the web…");
const graphInspectors = page.locator('[data-testid="stExpander"]').filter({ hasText: /Graph state · turn/ });
let inspectorCount = await graphInspectors.count();

await input.fill("What are the key security findings in the uploaded research report?");
await page.waitForTimeout(700);
await input.press("Enter");
mark("paper_query_sent");
await page.waitForFunction(() => {
  const messages = document.querySelectorAll('[data-testid="stChatMessage"]');
  return messages.length >= 2 && (messages[messages.length - 1]?.innerText?.length || 0) > 120;
}, { timeout: 300000 });
mark("paper_response_started");
await page.waitForFunction(
  (count) => document.querySelectorAll('[data-testid="stExpander"]').length > count,
  inspectorCount,
  { timeout: 300000 },
);
mark("paper_response_done");
await page.waitForTimeout(1200);

for (let index = 0; index < 4; index += 1) {
  await page.mouse.wheel(0, 430);
  await page.waitForTimeout(700);
}
for (let index = 0; index < 2; index += 1) {
  await page.mouse.wheel(0, -350);
  await page.waitForTimeout(500);
}

const answerInspector = graphInspectors.last();
await answerInspector.locator("summary").click();
await page.waitForTimeout(800);
await answerInspector.locator("summary").scrollIntoViewIfNeeded();
await page.mouse.wheel(0, -300);
await page.waitForTimeout(500);
mark("graph_state_opened");
await page.screenshot({ path: path.join(screenshotDir, "04-graph-state.png") });
await page.waitForTimeout(3200);
await answerInspector.locator("summary").click();

await page.getByText("Web Pages").scrollIntoViewIfNeeded();
const urlArea = page.getByPlaceholder("https://example.com/paper");
await urlArea.fill("https://en.wikipedia.org/wiki/Retrieval-augmented_generation");
await page.waitForTimeout(700);
await page.getByRole("button", { name: "Load URLs", exact: true }).click();
mark("webpage_ingestion_started");
await page.getByText("Retrieval-augmented generation").last().waitFor({ timeout: 240000 });
mark("webpage_ingestion_done");
await page.getByText("Loaded Documents").scrollIntoViewIfNeeded();
await page.waitForTimeout(1800);

const arxivInput = page.getByPlaceholder("1706.03762  or  Attention Is All You Need");
await arxivInput.fill("1706.03762");
await page.waitForTimeout(700);
await page.getByRole("button", { name: "Load ArXiv Paper", exact: true }).click();
mark("arxiv_ingestion_started");
await page.getByText("Attention Is All You Need").last().waitFor({ timeout: 240000 });
mark("arxiv_ingestion_done");
await page.getByText("Loaded Documents").scrollIntoViewIfNeeded();
await page.waitForTimeout(2200);

await sidebar.evaluate((element) => { element.scrollTop = 0; });
await page.getByPlaceholder("Ask about your papers, verify a claim, or search the web…").scrollIntoViewIfNeeded();
inspectorCount = await graphInspectors.count();
await input.fill("Verify this claim: Transformer attention mechanisms remain the dominant foundation for modern language models.");
await input.press("Enter");
mark("claim_verification_sent");
await page.getByText("Claim Verification Result", { exact: true }).first().waitFor({ timeout: 300000 });
mark("claim_verification_started");
await page.waitForFunction(
  (count) => document.querySelectorAll('[data-testid="stExpander"]').length > count,
  inspectorCount,
  { timeout: 300000 },
);
mark("claim_verification_done");
await page.waitForTimeout(1000);
await page.screenshot({ path: path.join(screenshotDir, "07-claim-verification.png") });
await page.waitForTimeout(2600);

inspectorCount = await graphInspectors.count();
await input.fill("What is cosine similarity?");
await input.press("Enter");
mark("direct_answer_sent");
await page.waitForFunction(
  (count) => document.querySelectorAll('[data-testid="stExpander"]').length > count,
  inspectorCount,
  { timeout: 240000 },
);
mark("direct_answer_done");
await page.waitForTimeout(1800);

await page.getByRole("button", { name: "+ New Chat" }).click();
await page.waitForTimeout(900);
await input.fill("/btw What is cosine similarity?");
await input.press("Enter");
mark("btw_direct_sent");
await page.getByText("Cosine similarity is").waitFor({ timeout: 120000 });
await page.waitForTimeout(7000);
mark("btw_direct_done");

await input.fill("/btw What is the latest news about OpenAI today?");
await input.press("Enter");
mark("btw_web_sent");
await page.waitForFunction(() => {
  const messages = document.querySelectorAll('[data-testid="stChatMessage"]');
  return messages.length >= 4 && (messages[messages.length - 1]?.innerText?.length || 0) > 180;
}, { timeout: 240000 });
await page.waitForTimeout(7000);
mark("btw_web_done");

await page.waitForTimeout(1200);
mark("recording_done");
await writeFile(timelinePath, JSON.stringify(timeline, null, 2));
await page.close();
await context.close();
const rawVideoPath = path.join(videoDir, "scholarlens-e2e-raw.webm");
await video.saveAs(rawVideoPath);
await browser.close();
process.stdout.write(`raw_video=${rawVideoPath}\n`);
process.stdout.write(`timeline=${timelinePath}\n`);
