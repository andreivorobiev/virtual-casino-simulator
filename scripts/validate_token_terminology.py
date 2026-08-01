# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import json
# Import required dependency so this module can use its public functions or constants.
import pathlib
# Import required dependency so this module can use its public functions or constants.
import re

# Set ROOT to the repository root for stable path resolution.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Set TOKEN_MARK to the approved play-token display mark.
TOKEN_MARK = "◈"
# Set BANNED_TEXT_RE to phrases that must not appear in active user-facing token copy.
BANNED_TEXT_RE = re.compile(r"\b(fake[- ]money|dollars?|usd)\b", re.IGNORECASE)
# Set DOLLAR_AMOUNT_RE to detect visible dollar-prefixed amounts without matching JS interpolation.
DOLLAR_AMOUNT_RE = re.compile(r"(?<!\{)\$\s*\d")
# Set TEXT_PATHS to active owned source/resource files for this terminology worker.
TEXT_PATHS = [
    # Include the README summary because it is a current user-facing entry point.
    ROOT / "README.md",
    # Include the shell HTML where wallet and status labels are static.
    ROOT / "web" / "index.html",
    # Include the shell controller where lobby and toast copy are rendered.
    ROOT / "web" / "app.js",
    # Include the Admin shell where static subtitle copy is rendered.
    ROOT / "web" / "admin.html",
    # Include the Admin controller where preview strings are rendered.
    ROOT / "web" / "admin.js",
    # Include the legacy shared amount formatter used by game modules.
    ROOT / "web" / "core" / "ui.js",
    # Include the i18n amount formatter used by localized game modules.
    ROOT / "web" / "core" / "i18n.js",
]
# Set JSON_ROOT to the manifest-owned i18n resource tree.
JSON_ROOT = ROOT / "web" / "i18n"

# Define iter_json_values to traverse nested JSON resources.
def iter_json_values(value, path):
    # Branch when the current JSON node is a dictionary.
    if isinstance(value, dict):
        # Iterate through object entries so keys can be reported precisely.
        for key, child in value.items():
            # Yield all values below this key with a dotted location.
            yield from iter_json_values(child, f"{path}.{key}" if path else key)
    # Branch when the current JSON node is a list.
    elif isinstance(value, list):
        # Iterate through list entries so array positions can be reported.
        for index, child in enumerate(value):
            # Yield all values below this index with a bracketed location.
            yield from iter_json_values(child, f"{path}[{index}]")
    # Branch when the current JSON node is a string.
    elif isinstance(value, str):
        # Yield the string value and its logical location.
        yield path, value

# Define check_text_file to validate one source file.
def check_text_file(path):
    # Set errors to collect every terminology issue in this file.
    errors = []
    # Read the text file with UTF-8 so the token mark is preserved.
    text = path.read_text(encoding="utf-8")
    # Iterate through source lines with stable line numbers.
    for number, line in enumerate(text.splitlines(), start=1):
        # Branch when banned real-money wording appears in active UI source.
        if BANNED_TEXT_RE.search(line):
            # Record the banned wording with its file and line.
            errors.append(f"{path.relative_to(ROOT)}:{number}: replace real-money wording")
        # Branch when a visible dollar amount appears outside JS interpolation.
        if DOLLAR_AMOUNT_RE.search(line):
            # Record the dollar-mark amount with its file and line.
            errors.append(f"{path.relative_to(ROOT)}:{number}: replace dollar amount with token mark")
    # Return all issues found in this file.
    return errors

# Define check_json_file to validate one i18n resource file.
def check_json_file(path):
    # Set errors to collect every terminology issue in this resource.
    errors = []
    # Parse the JSON resource so only player-facing values are checked.
    data = json.loads(path.read_text(encoding="utf-8"))
    # Iterate through every string value in the resource.
    for key, value in iter_json_values(data, ""):
        # Branch when banned real-money wording appears in localized copy.
        if BANNED_TEXT_RE.search(value):
            # Record the resource key that still uses real-money wording.
            errors.append(f"{path.relative_to(ROOT)}:{key}: replace real-money wording")
        # Branch when a visible dollar amount appears in localized copy.
        if DOLLAR_AMOUNT_RE.search(value):
            # Record the resource key that still uses a dollar amount.
            errors.append(f"{path.relative_to(ROOT)}:{key}: replace dollar amount with token mark")
    # Return all issues found in this resource.
    return errors

# Define check_required_token_mark to verify shared formatting helpers use the token mark.
def check_required_token_mark():
    # Set errors to collect missing-token-mark problems.
    errors = []
    # Read the legacy shared UI formatter.
    ui_text = (ROOT / "web" / "core" / "ui.js").read_text(encoding="utf-8")
    # Read the i18n numeric formatter.
    i18n_text = (ROOT / "web" / "core" / "i18n.js").read_text(encoding="utf-8")
    # Accept either an inline token-mark template or delegation to the i18n formatter, whose own mark is checked below.
    if f"`{TOKEN_MARK}${{" not in ui_text and "formatMoney(" not in ui_text:
        # Record the missing mark in the legacy formatter.
        errors.append("web/core/ui.js: money() must prefix amounts with ◈ or delegate to formatMoney()")
    # Branch when the i18n formatter is missing the approved mark.
    if f"`{TOKEN_MARK}${{" not in i18n_text:
        # Record the missing mark in the i18n formatter.
        errors.append("web/core/i18n.js: formatMoney() must prefix amounts with ◈")
    # Return all shared formatter issues.
    return errors

# Define main as the command-line entry point.
def main():
    # Set errors to collect every terminology issue before reporting.
    errors = []
    # Iterate through every active source file this task owns.
    for path in TEXT_PATHS:
        # Extend the aggregate errors with this file's scan result.
        errors.extend(check_text_file(path))
    # Iterate through every JSON i18n resource under the manifest tree.
    for path in sorted(JSON_ROOT.rglob("*.json")):
        # Extend the aggregate errors with this resource's scan result.
        errors.extend(check_json_file(path))
    # Verify shared formatters explicitly use the approved token mark.
    errors.extend(check_required_token_mark())
    # Branch when any terminology issue was found.
    if errors:
        # Write diagnostic output so the current operation can be inspected.
        print("Token terminology validation failed:")
        # Iterate through all errors so fixes can be targeted.
        for error in errors:
            # Write each terminology issue on its own line.
            print(f" - {error}")
        # Return failure to the calling validation command.
        return 1
    # Write diagnostic output so successful validation is visible.
    print("Token terminology validation passed.")
    # Return success to the calling validation command.
    return 0

# Branch when the script is invoked directly.
if __name__ == "__main__":
    # Raise SystemExit with main's return code for shell integration.
    raise SystemExit(main())
