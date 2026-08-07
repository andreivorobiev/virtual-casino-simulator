# Comment policy: comments state intent and constraints; self-evident lines stay bare.
# This file is on the audited-quality exemption list in check_comment_density.py (issue #555).
import pathlib
import re
# sys.path manipulation below needs sys before any casino import resolves.
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Add the repository root before importing the runtime catalog facade.
sys.path.insert(0, str(ROOT))
# Boundaries are derived from the same descriptors that drive runtime registration,
# so this gate can never drift from the catalog games actually being served.
from casino.config import GAMES as GAME_CATALOG
GAMES = [game["id"] for game in GAME_CATALOG]
# Match real import syntax, not substrings, so string literals cannot trip or dodge the gate.
PY_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z0-9_.]+)")
JS_IMPORT_RE = re.compile(r"import\s+.*?from\s+['\"]([^'\"]+)['\"]")
# Match every forbidden game-owned import of the public ledger implementation. (LEDGER-032, TEST-157)
GAME_LEDGER_IMPORT_RE = re.compile(r"^\s*(?:from\s+casino\.core(?:\.ledger)?\s+import\s+ledger|from\s+casino\.core\.ledger\s+import\s+|import\s+casino\.core\.ledger)\b")
# Match direct calls through a variable named ledger so aliases cannot preserve the old money boundary. (LEDGER-032, TEST-157)
DIRECT_GAME_LEDGER_CALL_RE = re.compile(r"\bledger\.(?:debit|credit|debit_once|credit_once)\s*\(")

# Fail on any cross-game Python import: games may share code only through casino.core,
# and bot strategies must stay behind the controller so games cannot read bot intent.
def check_python_game_imports(errors):
    for game in GAMES:
        for path in (ROOT / "casino" / "games" / game).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), 1):
                m = PY_IMPORT_RE.match(line)
                if not m:
                    continue
                imported = m.group(1)
                for other in GAMES:
                    if other != game and f"casino.games.{other}" in imported:
                        errors.append(f"{path}:{lineno} imports other game module {other}")
                if "casino.bots.strategies" in imported:
                    errors.append(f"{path}:{lineno} imports bot strategies directly")


# Reject game-owned access to ledger mutation functions after the catalog-wide adapter migration. (LEDGER-032, TEST-157)
def check_game_settlement_boundary(errors):
    # Inspect every registered game's executable Python sources rather than a hand-maintained list.
    for game in GAMES:
        # Walk the complete module because money movement may live in an API or service file.
        for path in (ROOT / "casino" / "games" / game).rglob("*.py"):
            # Read the source once so import and call diagnostics share exact line numbers.
            text = path.read_text(encoding="utf-8")
            # Check each executable line independently for focused CI output.
            for lineno, line in enumerate(text.splitlines(), 1):
                # Ignore comments so historical documentation cannot trip the executable gate.
                if line.lstrip().startswith("#"):
                    continue
                # Require games to obtain money movement only through casino.core.settlement.
                if GAME_LEDGER_IMPORT_RE.search(line):
                    errors.append(f"{path}:{lineno} imports the legacy ledger boundary; use GameSettlementGateway")
                # Reject aliases that still call the old public mutation functions directly.
                if DIRECT_GAME_LEDGER_CALL_RE.search(line):
                    errors.append(f"{path}:{lineno} calls the legacy ledger boundary directly; use GameSettlementGateway")

# Match player-visible outcome draws routed through the seedable global Mersenne Twister. (issue #420)
GLOBAL_RNG_RE = re.compile(r"\brandom\.(shuffle|choice|choices|sample|randint|randrange|random|uniform|betavariate|gauss)\s*\(")


# Reject global-module randomness in game outcome code so entropy always comes from a CSPRNG or an injected generator. (issue #420)
def check_game_rng(errors):
    for game in GAMES:
        for path in (ROOT / "casino" / "games" / game).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            # Line-scoped scanning keeps every diagnostic clickable in editors and CI logs.
            for lineno, line in enumerate(text.splitlines(), 1):
                # Ignore comment lines so documentation cannot trip the gate.
                if line.lstrip().startswith("#"):
                    continue
                # Flag only direct global-module draws; SystemRandom instances and Random(seed) constructions never match.
                if GLOBAL_RNG_RE.search(line):
                    # Name the exact draw site so the swap to a SystemRandom receiver is mechanical.
                    errors.append(f"{path}:{lineno} draws outcomes from the seedable global random module")


# Fail on any cross-game frontend import: shared browser code belongs under web/core/.
def check_js_game_imports(errors):
    game_dir = ROOT / "web" / "games"
    for game in GAMES:
        path = game_dir / f"{game}.js"
        # Frontend files are optional during game bring-up; the catalog validator owns existence.
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            m = JS_IMPORT_RE.search(line)
            if not m:
                continue
            target = m.group(1)
            for other in GAMES:
                if other != game and f"{other}.js" in target:
                    errors.append(f"{path}:{lineno} imports other game frontend {other}")

def main():
    errors = []
    check_python_game_imports(errors)
    # Enforce the one catalog-wide exactly-once money interface. (LEDGER-032, TEST-157)
    check_game_settlement_boundary(errors)
    # Enforce CSPRNG-or-injected entropy for every game outcome draw. (issue #420)
    check_game_rng(errors)
    check_js_game_imports(errors)
    if errors:
        print("Module boundary validation failed:")
        for err in errors:
            print(f" - {err}")
        return 1
    print("Module boundary validation passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
