# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Executable proof that localized browser copy has one resource-owned source."""

# Import JSON support for exact locale dictionary comparisons.
import json
# Import regular expressions for JavaScript call discovery and Cyrillic evidence.
import re
# Import unittest for the repository's standard focused runner.
import unittest
# Import portable paths for repository-owned source and resource discovery.
from pathlib import Path

# Resolve the repository root independently of the invoking shell.
ROOT = Path(__file__).resolve().parents[1]
# Bind every shell key introduced for the named localized surfaces in issue #709.
SHELL_KEYS = {
    "autoplay.stopped",
    "lobby.trust.autoplayDetail",
    "lobby.trust.autoplayTitle",
    "lobby.trust.ledgerDetail",
    "lobby.trust.ledgerTitle",
    "lobby.trust.localDetail",
    "lobby.trust.localTitle",
    "route.backToLobby",
    "route.loadFailed",
    "startup.loadFailed",
}
# Bind every Admin key required by the named mixed-language table surfaces.
ADMIN_KEYS = {
    "autoplay.completed",
    "autoplay.game",
    "autoplay.id",
    "autoplay.limit",
    "autoplay.player",
    "autoplay.sessions",
    "autoplay.speed",
    "autoplay.status",
    "autoplay.stopRequested",
    "autoplay.updated",
    "bots.controllers",
    "bots.enabled",
    "bots.save",
    "bots.stake",
    "bots.strategy",
    "players.id",
    "players.name",
    "players.type",
    "requirements.description",
    "requirements.id",
    "requirements.module",
    "requirements.status",
    "requirements.subtitle",
    "requirements.tests",
    "users.actions",
    "users.accessControls",
    "users.email",
    "users.format",
    "users.language",
    "users.name",
    "users.terms",
    "users.tokenBalance",
    "users.tokenState",
    "users.subtitle",
    "users.tableTitle",
    "users.title",
}


# Load one checked-in locale dictionary as exact UTF-8 JSON.
def resource(locale: str, domain: str) -> dict[str, str]:
    # Read the complete domain mapping so key parity cannot be hidden by test fixtures.
    return json.loads((ROOT / "web" / "i18n" / locale / f"{domain}.json").read_text(encoding="utf-8"))


# Count top-level arguments in one JavaScript call without evaluating browser code.
def call_argument_count(source: str, open_index: int) -> int:
    # Start inside the opening parenthesis selected by the caller.
    depth = 1
    # Track string and template delimiters so embedded punctuation is ignored.
    quote = ""
    # Track escaped delimiters inside the active JavaScript string.
    escaped = False
    # Count separators belonging only to the current tx call.
    commas = 0
    # Walk source until the matching closing parenthesis is reached.
    for index in range(open_index + 1, len(source)):
        # Read one source character for deterministic lexical classification.
        character = source[index]
        # Handle string and template content before structural punctuation.
        if quote:
            # Consume one escaped character without changing string state.
            if escaped:
                escaped = False
            # Mark the next character as escaped after a backslash.
            elif character == "\\":
                escaped = True
            # Leave string mode only at the matching unescaped delimiter.
            elif character == quote:
                quote = ""
            # Continue because punctuation inside a string is not call structure.
            continue
        # Enter JavaScript string or template mode at a quote delimiter.
        if character in {"'", '"', "`"}:
            quote = character
        # Increase nesting for parentheses, arrays, and object literals.
        elif character in "([{":
            depth += 1
        # Decrease nesting at the paired structural closer.
        elif character in ")]}":
            depth -= 1
            # Return zero for an empty call or separators plus one for a populated call.
            if depth == 0:
                return 0 if not source[open_index + 1:index].strip() else commas + 1
        # Count only commas directly inside this call rather than nested values.
        elif character == "," and depth == 1:
            commas += 1
    # Reject malformed checked-in JavaScript instead of silently skipping it.
    raise AssertionError(f"unterminated tx call at offset {open_index}")


# Prove locale parity, translated named surfaces, and removal of inline game fallbacks. (I18N-014 TEST-187)
class I18nSingleSourceTests(unittest.TestCase):
    # Prove every game tx call has at most key and params arguments.
    def test_game_tx_calls_have_no_inline_fallback_argument(self):
        # Scan all game modules so later regressions outside the original eleven also fail.
        for path in sorted((ROOT / "web" / "games").glob("*.js")):
            # Read source without executing route-owned browser code.
            source = path.read_text(encoding="utf-8")
            # Inspect every tx call or function declaration with the same syntax.
            for match in re.finditer(r"\btx\s*\(", source):
                # Resolve the exact opening parenthesis selected by the match.
                open_index = source.index("(", match.start())
                # Reject a third inline fallback argument anywhere in the catalog.
                self.assertLessEqual(call_argument_count(source, open_index), 2, path.relative_to(ROOT).as_posix())
            # Reject the retired adapter parameter and fallback chain implementation.
            self.assertNotIn("params, fallback", source, path.relative_to(ROOT).as_posix())

    # Prove the named shell and Admin copy exists in both supported visual locales.
    def test_named_shell_and_admin_keys_have_russian_parity(self):
        # Load exact English and Russian dictionaries for each shared surface.
        dictionaries = {domain: {locale: resource(locale, domain) for locale in ("en-US", "ru-RU")} for domain in ("shell", "admin")}
        # Check every issue-owned key in its owning resource domain.
        for domain, keys in (("shell", SHELL_KEYS), ("admin", ADMIN_KEYS)):
            # Require complete shared-domain parity rather than checking only the newly introduced keys.
            self.assertEqual(set(dictionaries[domain]["en-US"]), set(dictionaries[domain]["ru-RU"]), domain)
            # Compare each localized value against the paired English source.
            for key in sorted(keys):
                # Require the same key to exist and carry visible text in both dictionaries.
                self.assertTrue(dictionaries[domain]["en-US"].get(key), f"missing en-US {domain}:{key}")
                self.assertTrue(dictionaries[domain]["ru-RU"].get(key), f"missing ru-RU {domain}:{key}")
                # Require Russian copy to differ from English except the language-neutral ID label.
                if key not in {"autoplay.id", "players.id", "requirements.id"}:
                    self.assertNotEqual(dictionaries[domain]["en-US"][key], dictionaries[domain]["ru-RU"][key], f"untranslated {domain}:{key}")

    # Prove all game dictionaries retain exact English/Russian key parity after fallback removal.
    def test_all_game_resource_keys_match_between_english_and_russian(self):
        # Enumerate every English game dictionary as the catalog-owned source set.
        for english_path in sorted((ROOT / "web" / "i18n" / "en-US" / "games").glob("*.json")):
            # Load the paired Russian dictionary at the same catalog-relative path.
            russian_path = ROOT / "web" / "i18n" / "ru-RU" / "games" / english_path.name
            # Require the paired Russian file to exist before comparing keys.
            self.assertTrue(russian_path.exists(), english_path.name)
            # Parse both exact resource objects as UTF-8 JSON.
            english = json.loads(english_path.read_text(encoding="utf-8"))
            russian = json.loads(russian_path.read_text(encoding="utf-8"))
            # Require exact key parity so the runtime never exposes a resource identifier.
            self.assertEqual(set(english), set(russian), english_path.name)

    # Prove the named browser sources no longer carry their retired English literals.
    def test_named_shell_and_admin_literals_are_resource_owned(self):
        # Read the shared shell and Admin modules after localization migration.
        app_source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        # Read Admin separately so its exact table expressions remain governed.
        admin_source = (ROOT / "web" / "admin.js").read_text(encoding="utf-8")
        # Reject every shell literal cited by the filed issue.
        for literal in ("Local Simulator", "Autoplay Ready", "Ledger-Backed", "games tracked", "Back to lobby", "Could not load state:", "Auto stopped"):
            # Report the specific retired literal if it reappears in executable shell source.
            self.assertNotIn(literal, app_source)
        # Require the named mixed header arrays to use resource lookups rather than literals.
        self.assertNotIn("table(['ID', 'Name', 'Type', 'Balance']", admin_source)
        # Require the managed-user header list to remain fully resource-owned.
        self.assertNotIn("table(['Email', 'Name'", admin_source)
        # Require the autoplay header list to remain fully resource-owned.
        self.assertNotIn("table(['ID', 'Game', 'Player', 'Status', 'Speed'", admin_source)
        # Require the requirements header list to remain fully resource-owned.
        self.assertNotIn("table(['ID', 'Module', 'Description', 'Status', 'Tests']", admin_source)


# Support direct focused execution outside the aggregate runner.
if __name__ == "__main__":
    # Run with normal unittest discovery and exit semantics.
    unittest.main()
