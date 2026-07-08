// Import a CommonJS bridge so the bundled Playwright package can be resolved from NODE_PATH.
import { createRequire } from 'node:module';
// Import file URL conversion so screenshot paths are written beside this script.
import { fileURLToPath } from 'node:url';

// Create a local require function for the Playwright dependency.
const require = createRequire(import.meta.url);
// Load Playwright through NODE_PATH supplied by the Codex workspace runtime.
const { chromium } = require('playwright');
// List every static mockup section that becomes a PNG artifact.
const shots = [
  'roulette-betting-setup', // Capture Roulette with open bets and stable slip regions.
  'roulette-spinning-reveal', // Capture Roulette while the wheel and ball are resolving.
  'roulette-settled-result', // Capture Roulette after the selected pocket and settlement display.
  'blackjack-initial-deal', // Capture Blackjack immediately after the two-card initial deal.
  'blackjack-active-decision', // Capture Blackjack with the full action rail and insurance state.
  'blackjack-split-multi-hand', // Capture Blackjack with split hands in reserved lanes.
  'blackjack-settled-result', // Capture Blackjack after dealer resolution and payout summary.
  'baccarat-wager-setup', // Capture Baccarat before the deal with standing wagers.
  'baccarat-card-reveal', // Capture Baccarat during card peel and tableau reveal.
  'baccarat-result-road-history', // Capture Baccarat after settlement and road update.
];
// Resolve the static HTML source relative to this render helper.
const htmlUrl = new URL('./table-game-prerenders.html', import.meta.url).href;
// Launch Chromium in headless mode for deterministic local captures.
const browser = await chromium.launch();
// Create a 1600 by 900 viewport matching the approved reference image size.
const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
// Open the static source once because every state is rendered as a fixed article.
await page.goto(htmlUrl, { waitUntil: 'networkidle' });
// Wait for browser font readiness before taking any screenshots.
await page.evaluate(() => document.fonts.ready);
// Capture each named article as an individual PNG proposal artifact.
for (const shot of shots) {
  // Find the fixed-size article that represents this state.
  const locator = page.locator(`#${shot}`);
  // Ensure Playwright can scroll the target article into the capture viewport.
  await locator.scrollIntoViewIfNeeded();
  // Write the screenshot beside the mock source using the task packet file names.
  await locator.screenshot({ path: fileURLToPath(new URL(`./${shot}.png`, import.meta.url)), animations: 'disabled' });
  // Print progress so the worker handback can confirm every state rendered.
  console.log(`rendered ${shot}.png`);
}
// Close the browser after all proposal images have been written.
await browser.close();
