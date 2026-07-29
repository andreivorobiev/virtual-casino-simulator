#!/usr/bin/env python3
# Map a pull request's changed files to the games whose browser coverage must run. (issue #468 item 4)
#
# Output contract (stdout, one line):
#   FULL                      -> run the whole browser suite (a shared or unrecognized path changed)
#   <gid>[,<gid>...]          -> run only these affected games' dedicated browser cases plus shared cases
#   NONE                      -> no browser-relevant files changed at all
#
# The rule is deliberately conservative: any changed path that is not unambiguously owned by a single
# catalog game forces FULL, so a shared-code change can never silently skip cross-game coverage.
import re
import sys
from pathlib import Path

# Resolve the repository root from this script's location so catalog import works from any CWD.
ROOT = Path(__file__).resolve().parents[1]
# Make the backend package importable so the catalog game ids stay the single source of truth.
sys.path.insert(0, str(ROOT))
# Import the canonical catalog rather than re-declaring game ids here.
from casino import config as casino_config  # noqa: E402

# Load the exact catalog game ids once.
GAME_IDS = {game["id"] for game in casino_config.GAMES}

# Declare the per-game path patterns; each captures the owning game id in group 1.
GAME_PATH_PATTERNS = [
    re.compile(r"^casino/games/([^/]+)/"),
    re.compile(r"^tests/games/([^/]+)/"),
    re.compile(r"^tests/game_drivers/([^/]+)\.py$"),
    re.compile(r"^web/games/([^/]+)\.js$"),
    re.compile(r"^web/i18n/[^/]+/games/([^/]+)\.json$"),
    re.compile(r"^contracts/openapi/([^/.]+)\.v1\.yaml$"),
    re.compile(r"^modules/([^/]+)\.json$"),
    re.compile(r"^docs/games/([^/]+)\.md$"),
    re.compile(r"^docs/evidence/([^/]+)/"),
]

# Paths that never affect browser behavior, so they neither add a game nor force a full run.
BROWSER_IRRELEVANT_PATTERNS = [
    re.compile(r"^docs/games/[^/]+\.md$"),
    re.compile(r"^docs/evidence/[^/]+/"),
    re.compile(r"^casino/games/[^/]+/(?:AGENTS|README)\.md$"),
]


# Resolve one changed path to a game id, "SHARED" when it forces a full run, or None when browser-irrelevant.
def classify(path):
    # Normalize Windows separators so the patterns match on either platform.
    path = path.replace("\\", "/").strip()
    # Ignore empty lines from the diff input.
    if not path:
        return None
    # Documentation and evidence changes never change rendered behavior, so they gate nothing.
    if any(pattern.match(path) for pattern in BROWSER_IRRELEVANT_PATTERNS):
        return None
    # A path owned by exactly one catalog game contributes that game.
    for pattern in GAME_PATH_PATTERNS:
        match = pattern.match(path)
        if match and match.group(1) in GAME_IDS:
            return match.group(1)
    # Any other changed path is shared or unrecognized and must force the full suite.
    return "SHARED"


# Reduce all changed paths to the output contract token.
def resolve(paths):
    # Collect the specific games touched and whether any shared path appeared.
    games = set()
    saw_shared = False
    saw_any = False
    # Classify every changed path once.
    for path in paths:
        verdict = classify(path)
        # Skip browser-irrelevant paths without affecting the decision.
        if verdict is None:
            continue
        # Record that at least one browser-relevant path changed.
        saw_any = True
        # A shared path forces the full suite regardless of any game paths.
        if verdict == "SHARED":
            saw_shared = True
        else:
            games.add(verdict)
    # A shared change always wins: run everything.
    if saw_shared:
        return "FULL"
    # No browser-relevant change at all.
    if not saw_any:
        return "NONE"
    # Only unambiguous single-game paths changed: restrict to those games.
    return ",".join(sorted(games))


# Read changed paths from argv when provided, otherwise from stdin (one path per line).
def main(argv):
    # Prefer explicit argv paths for testability; fall back to piped diff output.
    paths = argv[1:] if len(argv) > 1 else sys.stdin.read().splitlines()
    # Emit the single decision token for the workflow to consume.
    print(resolve(paths))
    return 0


# Run as a CLI when invoked directly.
if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
