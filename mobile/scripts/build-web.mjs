// Import filesystem primitives used to stage a deterministic native web bundle.
import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
// Import path helpers used to prove all generated writes stay inside the mobile workspace.
import path from "node:path";
// Import URL conversion for stable repository-relative paths on every host platform.
import { fileURLToPath } from "node:url";
// Import the pinned bundler used to package Capacitor plugin imports for the WebView.
import { build } from "esbuild";
// Import the shared fail-closed configuration validator.
import { validateMobileConfig } from "../runtime/config.js";

// Resolve the mobile workspace from this script instead of the caller's current directory.
const mobileRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// Resolve the repository root containing the unchanged shared browser product.
const repositoryRoot = path.resolve(mobileRoot, "..");
// Resolve the only directory this build is allowed to replace recursively.
const outputRoot = path.resolve(mobileRoot, "dist");
// Resolve the configuration path from the explicit argument or environment variable.
const configuredPath = process.argv[2] || process.env.CASINO_MOBILE_CONFIG;

// Stop before any generated write when environment configuration is missing.
if (!configuredPath) throw new Error("Provide a config path argument or CASINO_MOBILE_CONFIG.");
// Resolve relative configuration paths from the mobile workspace for reproducible commands.
const configPath = path.resolve(mobileRoot, configuredPath);
// Read the public environment configuration without printing its values.
const configText = await readFile(configPath, "utf8");
// Validate and normalize the configuration before staging any application asset.
const config = validateMobileConfig(JSON.parse(configText));
// Prove the recursive replacement target is exactly the owned mobile dist directory.
if (outputRoot !== path.join(mobileRoot, "dist")) throw new Error("Refusing to replace an unowned output path.");
// Remove stale generated assets only after the owned target assertion passes.
await rm(outputRoot, { recursive: true, force: true });
// Recreate the deterministic output root for the current environment build.
await mkdir(outputRoot, { recursive: true });
// Copy the unchanged shared browser product into the native-only staging directory.
await cp(path.join(repositoryRoot, "web"), outputRoot, { recursive: true });
// Bundle native-only plugin imports from a scoped working directory for portable Windows resolution.
await build({ absWorkingDir: mobileRoot, entryPoints: ["./runtime/mobile-runtime.js"], outfile: "dist/mobile-runtime.js", bundle: true, format: "esm", platform: "browser", target: ["safari17", "chrome120"], sourcemap: false, logLevel: "warning" });
// Copy native-only safe-area, keyboard, and status styling beside the bundled runtime.
await cp(path.join(mobileRoot, "runtime", "mobile-runtime.css"), path.join(outputRoot, "mobile-runtime.css"));
// Write only normalized public values into the generated environment configuration.
await writeFile(path.join(outputRoot, "mobile-config.json"), `${JSON.stringify(config, null, 2)}\n`, "utf8");
// Read the staged shared entry point so its app loader can be replaced only in generated output.
const indexPath = path.join(outputRoot, "index.html");
// Load the staged entry point without touching the browser source file.
const originalIndex = await readFile(indexPath, "utf8");
// Define the exact shared app loader expected in the current browser entry point.
const sharedLoader = "  <script type=\"module\" src=\"/app.js\"></script>";
// Stop when upstream markup changes so injection cannot silently land in the wrong location.
if (!originalIndex.includes(sharedLoader)) throw new Error("Shared app loader was not found in staged index.html.");
// Replace only the staged loader with native-only CSS and bootstrap sequencing.
const mobileLoader = "  <!-- Native-only safe-area and connectivity presentation for the Capacitor shell. -->\n  <link rel=\"stylesheet\" href=\"/mobile-runtime.css\">\n  <!-- Native bootstrap validates configuration before loading the unchanged shared app. -->\n  <script type=\"module\" src=\"/mobile-runtime.js\"></script>";
// Persist the staged native entry point with the shared browser source still untouched.
await writeFile(indexPath, originalIndex.replace(sharedLoader, mobileLoader), "utf8");
