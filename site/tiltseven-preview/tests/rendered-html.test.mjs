import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render(pathname = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request(`http://localhost${pathname}`, {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the English TiltSeven landing page", async () => {
  // Render the root route from the worker build.
  const response = await render("/");
  // Confirm the route returns an HTML document.
  assert.equal(response.status, 200);
  // Confirm the response content type stays browser-renderable.
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  // Read the rendered body for stable brand and safety assertions.
  const html = await response.text();
  // Require the TiltSeven brand to render.
  assert.match(html, /TiltSeven/);
  // Require the polished first-version headline to render.
  assert.match(html, /The casino floor, sharpened into a simulator/);
  // Require the only external app lane to remain the casino origin.
  assert.match(html, /https:\/\/casino\.tiltseven\.com\//);
  // Require fake-money safety copy to remain visible.
  assert.match(html, /No deposits/);
  // Reject starter preview artifacts.
  assert.doesNotMatch(html, /codex-preview|SkeletonPreview|react-loading-skeleton/);
});

test("server-renders the Russian TiltSeven landing page", async () => {
  // Render the localized route from the worker build.
  const response = await render("/ru");
  // Confirm the localized route is available.
  assert.equal(response.status, 200);

  // Read the rendered body for localized safety assertions.
  const html = await response.text();
  // Require the polished Russian headline to render.
  assert.match(html, /Казино как стильный программный симулятор/);
  // Require fake-money safety copy to remain visible.
  assert.match(html, /Без пополнений/);
  // Require the only external app lane to remain the casino origin.
  assert.match(html, /https:\/\/casino\.tiltseven\.com\//);
  // Reject starter preview artifacts.
  assert.doesNotMatch(html, /codex-preview|SkeletonPreview|react-loading-skeleton/);
});

test("removes the disposable starter preview surface", async () => {
  // Read source files that commonly retain starter references.
  const [page, layout, packageJson] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  // Reject starter page imports and metadata markers.
  assert.doesNotMatch(page, /_sites-preview|SkeletonPreview|codex-preview/);
  // Reject starter layout imports and starter titles.
  assert.doesNotMatch(layout, /Starter Project|next\/font\/google/);
  // Reject the removed skeleton dependency.
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
});
