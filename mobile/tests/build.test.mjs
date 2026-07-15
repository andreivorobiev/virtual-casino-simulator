// Import strict assertions for mobile build configuration tests.
import assert from "node:assert/strict";
// Import filesystem access used to inspect committed project configuration.
import { readFile } from "node:fs/promises";
// Import path helpers used to resolve the mobile workspace reliably.
import path from "node:path";
// Import the built-in test runner used on every supported CI host.
import test from "node:test";
// Import URL conversion for stable test paths on Windows and Unix hosts.
import { fileURLToPath } from "node:url";

// Resolve the mobile workspace independently of the caller's current directory.
const mobileRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// Verify production configuration bundles local assets and never a remote executable site.
test("Capacitor configuration uses bundled web assets", async () => {
  // Parse the committed static Capacitor configuration.
  const config = JSON.parse(await readFile(path.join(mobileRoot, "capacitor.config.json"), "utf8"));
  // Confirm native projects consume the generated local asset directory.
  assert.equal(config.webDir, "dist");
  // Confirm no production server URL can replace the signed local application bundle.
  assert.equal(config.server.url, undefined);
  // Confirm both native platforms share one stable application identifier.
  assert.equal(config.appId, "io.github.andreivorobiev.virtualcasino");
});

// Verify dependency and package-manager versions are exact rather than floating ranges.
test("mobile dependencies and package manager are pinned", async () => {
  // Parse the committed package metadata used for native generation and sync.
  const manifest = JSON.parse(await readFile(path.join(mobileRoot, "package.json"), "utf8"));
  // Collect every declared runtime and development dependency version.
  const versions = Object.values({ ...manifest.dependencies, ...manifest.devDependencies });
  // Assert every dependency uses an exact semantic version without ranges or tags.
  assert.ok(versions.every(version => /^\d+\.\d+\.\d+$/.test(version)));
  // Assert the package-manager implementation is pinned for lockfile reproducibility.
  assert.match(manifest.packageManager, /^pnpm@\d+\.\d+\.\d+$/);
});

// Verify committed configuration examples contain no credential-bearing fields or URLs.
test("committed examples remain secret free", async () => {
  // Read the CI example used for host-runnable deterministic validation.
  const example = await readFile(path.join(mobileRoot, "config", "ci.example.json"), "utf8");
  // Assert common credential field names are absent from committed examples.
  assert.doesNotMatch(example, /password|secret|token|api[_-]?key/i);
  // Assert URL user-information syntax is absent from committed examples.
  assert.doesNotMatch(example, /:\/\/[^/\s]+:[^/\s]+@/);
});

// Verify generated native sources carry the bounded mobile-foundation version and app id.
test("native project metadata matches the mobile foundation", async () => {
  // Read Android application metadata from the committed generated project.
  const androidBuild = await readFile(path.join(mobileRoot, "android", "app", "build.gradle"), "utf8");
  // Confirm Android carries the same semantic version as the mobile package.
  assert.match(androidBuild, /versionName "0\.1\.0"/);
  // Confirm Android carries the stable application identifier from Capacitor configuration.
  assert.match(androidBuild, /applicationId "io\.github\.andreivorobiev\.virtualcasino"/);
  // Read iOS project metadata from the committed generated Xcode project.
  const iosProject = await readFile(path.join(mobileRoot, "ios", "App", "App.xcodeproj", "project.pbxproj"), "utf8");
  // Confirm iOS carries the same semantic version as the mobile package.
  assert.match(iosProject, /MARKETING_VERSION = 0\.1\.0;/);
  // Confirm iOS carries the stable application identifier from Capacitor configuration.
  assert.match(iosProject, /PRODUCT_BUNDLE_IDENTIFIER = io\.github\.andreivorobiev\.virtualcasino;/);
});

// Verify Android release metadata fails closed while debug keeps the explicit emulator path usable.
test("Android cleartext and backup settings are build scoped", async () => {
  // Read the release-bearing main manifest from the committed generated project.
  const mainManifest = await readFile(path.join(mobileRoot, "android", "app", "src", "main", "AndroidManifest.xml"), "utf8");
  // Confirm application data backup is disabled before later secure-session work begins.
  assert.match(mainManifest, /android:allowBackup="false"/);
  // Confirm the release-bearing manifest never enables cleartext transport.
  assert.doesNotMatch(mainManifest, /usesCleartextTraffic="true"/);
  // Read the debug-only manifest used for explicit loopback and emulator development.
  const debugManifest = await readFile(path.join(mobileRoot, "android", "app", "src", "debug", "AndroidManifest.xml"), "utf8");
  // Confirm cleartext transport is enabled only in the debug source set.
  assert.match(debugManifest, /android:usesCleartextTraffic="true"/);
});
