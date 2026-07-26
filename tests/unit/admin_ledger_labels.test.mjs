// Import strict assertions for deterministic Admin-label verification.
import assert from "node:assert/strict";
// Import repository file access for executing the exact production helper block.
import { readFile } from "node:fs/promises";
// Import the built-in dependency-free Node test runner.
import test from "node:test";
// Import URL conversion so repository paths resolve independently of the caller's working directory.
import { fileURLToPath } from "node:url";
// Import the exact listener-free production helpers under test.
import { humanLabel, ledgerEventLabel } from "../../web/core/admin_labels.js";

// Resolve the repository root from this tracked test file.
const ROOT = fileURLToPath(new URL("../..", import.meta.url));
// Read the exact Admin source once for helper extraction and wiring assertions.
const ADMIN_SOURCE = await readFile(`${ROOT}/web/admin.js`, "utf8");
// Read the exact listener-free helper source once for resource-wiring assertions.
const HELPER_SOURCE = await readFile(`${ROOT}/web/core/admin_labels.js`, "utf8");
// Load the source-locale Admin resource pack.
const ENGLISH = JSON.parse(await readFile(`${ROOT}/web/i18n/en-US/admin.json`, "utf8"));
// Load the Russian Admin resource pack.
const RUSSIAN = JSON.parse(await readFile(`${ROOT}/web/i18n/ru-RU/admin.json`, "utf8"));
// Build a translator compatible with the production helper's injected seam.
const translate = resources => (key) => resources[key] ?? key;

// Verify all-caps API identifiers become readable while reviewed acronyms retain their spelling.
test("ADMIN-027 normalizes all-caps identifiers without damaging acronyms", () => {
  // Normalize the exact payout example reported in the Admin polish audit.
  assert.equal(humanLabel("BINGO_PAYOUT_CREDIT"), "Bingo Payout Credit");
  // Preserve a technical field name used by Admin diagnostics.
  assert.equal(humanLabel("request_id"), "Request ID");
  // Normalize mixed separator input through the same deterministic path.
  assert.equal(humanLabel("oauth-provider_URL"), "OAuth Provider URL");
});

// Verify representative game movements use explicit locale resources instead of raw source enums.
test("ADMIN-027 localizes representative ledger actions in both installed locales", () => {
  // Define debit, credit, purchase, placed-bet, token, and unknown examples.
  const cases = [
    ["BINGO_PAYOUT_CREDIT", "bingo", "Bingo · Payout credited", "Bingo · Выплата начислена"],
    ["KENO_TICKET_PURCHASED", "keno", "Keno · Ticket purchased", "Keno · Билет приобретён"],
    ["BACCARAT_BET_PLACED", "baccarat", "Baccarat · Bet placed", "Baccarat · Ставка принята"],
    ["BLACKJACK_INSURANCE_DEBIT", "blackjack", "Blackjack · Insurance reserved", "Blackjack · Страховка зарезервирована"],
    ["PLAY_TOKENS_ADDED", "wallet", "Wallet · Play tokens credited", "Wallet · Игровые токены зачислены"],
    ["FUTURE_LEDGER_EVENT", "future_game", "Future Game · Ledger operation", "Future Game · Операция журнала"],
  ];
  // Exercise every representative identity through the exact production helper.
  for (const [eventType, game, english, russian] of cases) {
    // Require the source locale to render reviewed readable copy.
    assert.equal(ledgerEventLabel(eventType, game, translate(ENGLISH)), english);
    // Require Russian to render reviewed action copy without an English enum fallback.
    assert.equal(ledgerEventLabel(eventType, game, translate(RUSSIAN)), russian);
  }
});

// Verify every production event label key has an installed EN/RU value and both Admin surfaces use the helper.
test("TEST-132 keeps locale resources and Dashboard/Ledger wiring fail-closed", () => {
  // Collect each locale-backed key referenced by the ordered production rules and fallback.
  const referencedKeys = [...new Set([...HELPER_SOURCE.matchAll(/'((?:ledger\.events\.)[^']+)'/g)].map(match => match[1]))];
  // Require a non-empty English and Russian value for every referenced event label.
  for (const key of referencedKeys) {
    // Require the canonical English resource.
    assert.equal(typeof ENGLISH[key], "string", `${key} must exist in en-US`);
    // Require the reviewed Russian resource.
    assert.equal(typeof RUSSIAN[key], "string", `${key} must exist in ru-RU`);
    // Reject empty source copy.
    assert.ok(ENGLISH[key].trim(), `${key} must not be empty in en-US`);
    // Reject empty localized copy.
    assert.ok(RUSSIAN[key].trim(), `${key} must not be empty in ru-RU`);
  }
  // Require Dashboard and the full Ledger tab to expose stable localized-event evidence cells.
  assert.equal((ADMIN_SOURCE.match(/data-testid="admin-ledger-event"/g) || []).length, 2);
  // Require both event cells to derive visible copy through the locale-backed helper.
  assert.equal((ADMIN_SOURCE.match(/ledgerEventLabel\(row\.transaction_type, row\.game\)/g) || []).length, 2);
  // Leave only the separately mapped practice-opponent fallback outside the two governed ledger surfaces.
  assert.equal((ADMIN_SOURCE.match(/humanLabel\(row\.transaction_type\)/g) || []).length, 1);
});
