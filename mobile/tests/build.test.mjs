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
// Import the pure generated-path normalizer so Windows and Linux fixtures exercise identical bytes.
import { normalizeCapacitorPackageText } from "../scripts/normalize-capacitor-sync.mjs";

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
  assert.match(androidBuild, /versionName "0\.2\.0"/);
  // Confirm Android carries the stable application identifier from Capacitor configuration.
  assert.match(androidBuild, /applicationId "io\.github\.andreivorobiev\.virtualcasino"/);
  // Read iOS project metadata from the committed generated Xcode project.
  const iosProject = await readFile(path.join(mobileRoot, "ios", "App", "App.xcodeproj", "project.pbxproj"), "utf8");
  // Confirm iOS carries the same semantic version as the mobile package.
  assert.match(iosProject, /MARKETING_VERSION = 0\.2\.0;/);
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
  // Require debug cleartext to pass through one explicit loopback-only policy.
  assert.match(debugManifest, /android:networkSecurityConfig="@xml\/network_security_config"/);
  // Read the exact debug-only network security source.
  const debugNetworkPolicy = await readFile(path.join(mobileRoot, "android", "app", "src", "debug", "res", "xml", "network_security_config.xml"), "utf8");
  // Reject a permissive base policy and require only emulator/loopback domains.
  assert.match(debugNetworkPolicy, /base-config cleartextTrafficPermitted="false"/);
  // Require all and only the three reviewed local authorities.
  assert.deepEqual([...debugNetworkPolicy.matchAll(/<domain includeSubdomains="false">([^<]+)<\/domain>/g)].map(match => match[1]), ["localhost", "127.0.0.1", "10.0.2.2"]);
});

// Verify Capacitor's Windows and Unix Swift package output converges to one governed representation. (TEST-172)
test("Capacitor Swift package paths normalize across hosts", () => {
  // Build all exact declarations once with portable separators for the canonical oracle.
  const portableEntries = [
    // Model the App plugin's PNPM virtual-store path.
    '.package(name: "CapacitorApp", path: "../../../node_modules/.pnpm/@capacitor+app@8.1.0_@capacitor+core@8.4.2/node_modules/@capacitor/app"),',
    // Model the Browser plugin's PNPM virtual-store path.
    '.package(name: "CapacitorBrowser", path: "../../../node_modules/.pnpm/@capacitor+browser@8.0.3_@capacitor+core@8.4.2/node_modules/@capacitor/browser"),',
    // Model the Keyboard plugin's PNPM virtual-store path.
    '.package(name: "CapacitorKeyboard", path: "../../../node_modules/.pnpm/@capacitor+keyboard@8.0.5_@capacitor+core@8.4.2/node_modules/@capacitor/keyboard"),',
    // Model the Network plugin's PNPM virtual-store path.
    '.package(name: "CapacitorNetwork", path: "../../../node_modules/.pnpm/@capacitor+network@8.0.1_@capacitor+core@8.4.2/node_modules/@capacitor/network")',
  ].join("\n");
  // Convert only the local path values to the exact form emitted by Capacitor on Windows.
  const windowsEntries = portableEntries.replaceAll("../../../node_modules/", "..\\..\\..\\node_modules\\").replaceAll("/.pnpm/", "\\.pnpm\\").replaceAll("/node_modules/@capacitor/", "\\node_modules\\@capacitor\\");
  // Require Windows generation to converge byte-for-byte with the portable committed form.
  assert.equal(normalizeCapacitorPackageText(windowsEntries), portableEntries);
  // Require Linux generation to remain unchanged rather than accumulating formatter drift.
  assert.equal(normalizeCapacitorPackageText(portableEntries), portableEntries);
  // Reject a generated entry that escapes the exact mobile node_modules virtual store.
  assert.throws(() => normalizeCapacitorPackageText(portableEntries.replace("../../../node_modules/.pnpm/@capacitor+app@8.1.0_@capacitor+core@8.4.2/", "../../../node_modules/.pnpm/./")), /exact governed virtual-store entry/);
  // Reject a parent-directory virtual-store segment that could escape the PNPM package root.
  assert.throws(() => normalizeCapacitorPackageText(portableEntries.replace("../../../node_modules/.pnpm/@capacitor+app@8.1.0_@capacitor+core@8.4.2/", "../../../node_modules/.pnpm/../")), /exact governed virtual-store entry/);
  // Reject a syntactically bounded but foreign virtual-store package directory.
  assert.throws(() => normalizeCapacitorPackageText(portableEntries.replace("@capacitor+app@8.1.0_@capacitor+core@8.4.2", "foreign@0.0.0")), /exact governed virtual-store entry/);
  // Reject a partial generated inventory instead of silently committing an incomplete sync.
  assert.throws(() => normalizeCapacitorPackageText(portableEntries.split("\n").slice(0, 3).join("\n")), /missing governed Capacitor package entries/);
});
