# Comment policy: comments state intent and constraints; self-evident lines stay bare.
# This file is on the audited-quality exemption list in check_comment_density.py (issue #555).
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
# The approved play-token display mark; amounts must never render as real currency.
TOKEN_MARK = "◈"
# Real-money phrases banned from active user-facing copy; the legal posture in
# README.md and docs/legal/ depends on the app never describing itself in cash terms.
BANNED_TEXT_RE = re.compile(r"\b(fake[- ]money|dollars?|usd)\b", re.IGNORECASE)
# Visible dollar-prefixed amounts; the negative lookbehind spares JS template
# interpolation like `${value}`, which is syntax rather than copy.
DOLLAR_AMOUNT_RE = re.compile(r"(?<!\{)\$\s*\d")
# Reject the retired Russian casino-chip stem so every locale uses the product term "token". (I18N-011)
RUSSIAN_LEGACY_TOKEN_RE = re.compile(r"жетон", re.IGNORECASE)
# Match only an exported money helper that passes its own argument directly to the approved formatter.
MONEY_DELEGATION_RE = re.compile(r"\bexport\s+const\s+money\s*=\s*([A-Za-z_$][\w$]*)\s*=>\s*formatMoney\s*\(\s*\1\s*\)\s*;")
# Only surfaces that render static user-facing copy are scanned; game copy lives in
# the i18n tree below, and generated or historical documents are deliberately out of scope.
TEXT_PATHS = [
    # The README summary is a current user-facing entry point.
    ROOT / "README.md",
    # The shell HTML carries static wallet and status labels.
    ROOT / "web" / "index.html",
    # The shell controller renders lobby and toast copy.
    ROOT / "web" / "app.js",
    # The Admin shell carries static subtitle copy.
    ROOT / "web" / "admin.html",
    # The Admin controller renders preview strings.
    ROOT / "web" / "admin.js",
    # The legacy shared amount formatter is still imported by game modules.
    ROOT / "web" / "core" / "ui.js",
    # The i18n amount formatter is the localized display path.
    ROOT / "web" / "core" / "i18n.js",
]
JSON_ROOT = ROOT / "web" / "i18n"

# Walk every string in a nested i18n resource, yielding dotted/bracketed locations
# so a violation report names the exact key a translator must fix.
def iter_json_values(value, path):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_json_values(child, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_json_values(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value

def check_text_file(path):
    errors = []
    # UTF-8 is explicit so the token mark survives on platforms with legacy default encodings.
    text = path.read_text(encoding="utf-8")
    for number, line in enumerate(text.splitlines(), start=1):
        if BANNED_TEXT_RE.search(line):
            errors.append(f"{path.relative_to(ROOT)}:{number}: replace real-money wording")
        if DOLLAR_AMOUNT_RE.search(line):
            errors.append(f"{path.relative_to(ROOT)}:{number}: replace dollar amount with token mark")
    return errors

def check_json_file(path):
    errors = []
    # Parsing (rather than grepping) keeps the scan to player-facing values, so JSON
    # keys and structural syntax can neither trip nor mask the gate.
    data = json.loads(path.read_text(encoding="utf-8"))
    for key, value in iter_json_values(data, ""):
        if BANNED_TEXT_RE.search(value):
            errors.append(f"{path.relative_to(ROOT)}:{key}: replace real-money wording")
        if DOLLAR_AMOUNT_RE.search(value):
            errors.append(f"{path.relative_to(ROOT)}:{key}: replace dollar amount with token mark")
        # Apply the locale-specific terminology guard only to Russian resources.
        if "ru-RU" in path.parts and RUSSIAN_LEGACY_TOKEN_RE.search(value):
            errors.append(f"{path.relative_to(ROOT)}:{key}: replace legacy Russian chip wording with token terminology")
    return errors

# The two shared formatters are the chokepoints every game's amount rendering flows
# through, so they are held to a stronger requirement than absence of banned copy:
# they must positively apply the token mark.
def check_required_token_mark():
    errors = []
    ui_text = (ROOT / "web" / "core" / "ui.js").read_text(encoding="utf-8")
    i18n_text = (ROOT / "web" / "core" / "i18n.js").read_text(encoding="utf-8")
    # Accept an inline token mark or exact argument-preserving delegation to the separately checked formatter.
    if f"`{TOKEN_MARK}${{" not in ui_text and not MONEY_DELEGATION_RE.search(ui_text):
        errors.append("web/core/ui.js: money() must prefix amounts with ◈ or directly delegate to formatMoney()")
    if f"`{TOKEN_MARK}${{" not in i18n_text:
        errors.append("web/core/i18n.js: formatMoney() must prefix amounts with ◈")
    return errors

def main():
    errors = []
    for path in TEXT_PATHS:
        errors.extend(check_text_file(path))
    # Every locale ships under one tree, so this single walk covers en-US and ru-RU
    # (and any future locale) without a per-locale list to forget to update.
    for path in sorted(JSON_ROOT.rglob("*.json")):
        errors.extend(check_json_file(path))
    errors.extend(check_required_token_mark())
    if errors:
        print("Token terminology validation failed:")
        for error in errors:
            print(f" - {error}")
        return 1
    print("Token terminology validation passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
