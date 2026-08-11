// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Load path helpers so output and source paths resolve from the workspace root.
const path = require("node:path");
// Load filesystem helpers so the PNG output folder exists before screenshots run.
const fs = require("node:fs");
// Load URL conversion so Playwright can open the local HTML file reliably.
const { pathToFileURL } = require("node:url");
// Load Chromium from Playwright for deterministic browser screenshots.
const { chromium } = require("playwright");

// Define the ordered state captures requested by the machine/draw task packet.
const states = [
  { id: "slots-idle", file: "slots-idle-reels.png" },
  { id: "slots-spin", file: "slots-spin-in-progress.png" },
  { id: "slots-win", file: "slots-win-payline-reveal.png" },
  { id: "slots-free-progressive", file: "slots-free-spin-progressive-context.png" },
  { id: "keno-selection", file: "keno-spot-selection.png" },
  { id: "keno-draw", file: "keno-draw-in-progress.png" },
  { id: "keno-result", file: "keno-result-paytable-comparison.png" },
  { id: "bingo-ready", file: "bingo-card-purchase-ready.png" },
  { id: "bingo-call", file: "bingo-ball-call-in-progress.png" },
  { id: "bingo-win", file: "bingo-winning-pattern-highlight.png" },
];

// Run the renderer as a short-lived async task.
(async () => {
  // Resolve the artifact root from the current workspace.
  const artifactRoot = path.join(process.cwd(), "codex", "tasks", "artifacts", "premium-redesign-prerenders", "machine-draw-games");
  // Resolve the static HTML source path used for every capture.
  const sourcePath = path.join(artifactRoot, "source", "mockup.html");
  // Resolve the PNG output directory named in the task packet.
  const outputDir = path.join(artifactRoot, "png");
  // Ensure rerenders succeed even when the PNG folder was removed.
  fs.mkdirSync(outputDir, { recursive: true });
  // Launch Chromium headlessly for local static rendering.
  const browser = await chromium.launch({ headless: true });
  // Open a fixed-size page matching the design canvas.
  const page = await browser.newPage({ viewport: { width: 2048, height: 1152 }, deviceScaleFactor: 1 });
  // Load the local source mockup and wait for assets to settle.
  await page.goto(pathToFileURL(sourcePath).href, { waitUntil: "networkidle" });
  // Wait for web font fallback resolution before screenshots.
  await page.evaluate(() => document.fonts && document.fonts.ready);
  // Capture each requested state as a standalone PNG.
  for (const state of states) {
    // Locate the exact state frame by stable id.
    const frame = page.locator(`#${state.id}`);
    // Write the state PNG into the artifact output folder.
    await frame.screenshot({ path: path.join(outputDir, state.file) });
  }
  // Close Chromium so the script exits cleanly.
  await browser.close();
})();
