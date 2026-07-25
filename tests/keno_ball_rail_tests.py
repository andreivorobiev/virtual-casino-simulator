"""Focused Keno drawn-ball rail layout regression test. (#320-adjacent, KENO-026)

After a draw, the twenty result balls render in a single horizontal rail. The rail is a flex
container inside a fixed stage whose ancestor clips overflow, so without an explicit min-width:0 the
rail expanded to its content width and the rightmost drawn balls were clipped off the page and could
not be reached. This test pins the CSS contract that keeps the rail bounded to its column and
scrollable, so the clipping defect cannot silently return.
"""

# Import filesystem paths for locating the tracked Keno client.
import pathlib
# Import regular expressions for extracting the tracked rail rule.
import re
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Resolve the repository root without depending on the process working directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Point at the tracked Keno client module that owns the ball-rail styling.
KENO_PATH = ROOT / "web" / "games" / "keno.js"


# Verify the drawn-ball rail stays bounded and scrollable rather than clipping.
class KenoBallRailTests(unittest.TestCase):
    # Read the tracked Keno client once.
    def setUp(self) -> None:
        # Load the module text without executing it.
        self.text = KENO_PATH.read_text(encoding="utf-8")

    # Extract the CSS body of the .keno-ball-rail rule.
    def _rail_rule(self) -> str:
        # Locate the tracked rail declaration block.
        match = re.search(r"\.keno-ball-rail\{([^}]*)\}", self.text)
        # Fail loudly if the rail rule this test guards was renamed or removed.
        self.assertIsNotNone(match, "the .keno-ball-rail rule is missing from the tracked Keno client")
        # Return the rule body.
        return match.group(1)

    # Require the rail to be allowed to shrink below its content so it cannot expand and clip.
    def test_rail_can_shrink_below_content(self) -> None:
        # Read the rail rule body.
        body = self._rail_rule()
        # Require the min-width:0 that lets a flex or grid child shrink to its column.
        self.assertIn("min-width:0", body, "the ball rail lacks min-width:0, so it expands to its content and the rightmost balls clip off the page")
        # Require the rail to be bounded to its container width.
        self.assertIn("max-width:100%", body, "the ball rail is not bounded to its container width")

    # Require the rail to scroll horizontally rather than clip when the balls exceed its width.
    def test_rail_scrolls_horizontally(self) -> None:
        # Read the rail rule body.
        body = self._rail_rule()
        # Require an explicit horizontal-scroll overflow so hidden balls remain reachable.
        self.assertTrue("overflow-x:auto" in body or re.search(r"overflow:\s*auto", body), "the ball rail does not enable horizontal scrolling, so overflowing balls are unreachable")

    # Require each ball to keep its fixed size inside the scrolling rail rather than shrinking.
    def test_balls_keep_fixed_size(self) -> None:
        # Require the balls to opt out of flex shrinking so they stay circular and legible.
        self.assertIsNotNone(re.search(r"\.keno-ball-rail \.ball\{[^}]*flex:0 0 auto", self.text), "drawn balls are allowed to shrink inside the rail instead of scrolling")

    # Require the intentional scroll surface to expose keyboard and assistive-technology ownership.
    def test_rail_is_keyboard_reachable_and_named(self) -> None:
        # Locate the rendered rail markup without executing the browser client.
        markup = re.search(r'return `<div class="keno-ball-rail"([^>]*)>', self.text)
        # Fail loudly if the owned rail markup is renamed or removed.
        self.assertIsNotNone(markup, "the rendered .keno-ball-rail markup is missing")
        # Read the attribute fragment once for the complete accessibility contract.
        attributes = markup.group(1)
        # Require keyboard focus, region semantics, and localized naming on the intentional scroller.
        self.assertIn('tabindex="0"', attributes)
        self.assertIn('role="region"', attributes)
        self.assertIn('aria-label="${safe(tx(\'drawer.drawnBalls\'))}"', attributes)
