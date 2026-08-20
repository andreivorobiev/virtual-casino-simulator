# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused Roulette rotor and ball motion-quality tests. (#169, ROU-069, ROU-070)

The shipped spin used a heavily front-loaded easing that advanced the rotor by as much as
17 pockets between consecutive 60 Hz frames. A pocket ring is rotationally near-periodic, so a
step that large aliases: the wheel reads as strobing or jumping backwards rather than turning.
These tests pin the motion profile itself rather than a screenshot, so the defect cannot return
through a future easing tweak.
"""

# Import filesystem paths for locating the tracked game module.
import pathlib
# Import regular expressions for extracting the tracked keyframe blocks.
import re
# Import the standard unittest framework used by the repository's focused suites.
import unittest

# Resolve the repository root without depending on the process working directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Point at the tracked Roulette stylesheet that owns the spin animation.
ROULETTE_PATH = ROOT / "web" / "games" / "roulette.css"
# Assume the refresh rate the motion budget is expressed against.
FRAMES_PER_SECOND = 60
# Derive one pocket of angular width from the canonical 37-pocket European wheel.
POCKET_DEGREES = 360 / 37
# Keep the animation duration the client already waits on before revealing settlement.
SPIN_SECONDS = 16.5


# Read the tracked Roulette stylesheet once for every assertion.
def source() -> str:
    # Return the stylesheet text without loading it in a browser.
    return ROULETTE_PATH.read_text(encoding="utf-8")


# Extract one balanced CSS block by its exact declaration prefix.
def css_block(declaration: str) -> str:
    # Read the external stylesheet once for this focused lookup.
    text = source()
    # Locate the declaration whose block owns the guarded behavior.
    declaration_index = text.find(declaration)
    # Fail loudly when the tracked rule or at-rule has moved or disappeared.
    if declaration_index < 0:
        # Name the missing declaration in the deterministic assertion failure.
        raise AssertionError(f"{declaration} is missing from the tracked Roulette stylesheet")
    # Locate the opening brace after the exact declaration.
    opening_index = text.find("{", declaration_index + len(declaration))
    # Reject a malformed declaration instead of scanning into a later rule.
    if opening_index < 0:
        # Name the declaration that lacks a block opener.
        raise AssertionError(f"{declaration} has no CSS block")
    # Track nested keyframe and media-rule braces from the owning opener.
    depth = 0
    # Walk each remaining stylesheet character in source order.
    for index in range(opening_index, len(text)):
        # Increase nesting when a child rule begins.
        if text[index] == "{":
            # Count the newly opened block.
            depth += 1
        # Decrease nesting when the current rule ends.
        elif text[index] == "}":
            # Count the block that just closed.
            depth -= 1
            # Return only the declaration's body when its owner closes.
            if depth == 0:
                # Exclude the owning braces while preserving child rules.
                return text[opening_index + 1:index]
    # Reject unterminated CSS instead of returning a partial motion profile.
    raise AssertionError(f"{declaration} CSS block is unterminated")


# Extract the ordered (offset, degrees) stops of one named keyframe block.
def keyframe_stops(name: str) -> list:
    # Locate the tracked keyframe declaration in the external stylesheet.
    block = css_block(f"@keyframes {name}")
    # Collect every percentage stop and its rotation.
    stops = []
    # Walk each declared stop in source order.
    for percent, body in re.findall(r"(\d+)%\s*\{([^}]*)\}", block):
        # Read the rotation this stop declares.
        rotation = re.search(r"rotate\((-?[\d.]+)deg\)", body)
        # Keep only stops that actually declare a rotation.
        if rotation:
            # Record the normalized offset and its absolute angle.
            stops.append((int(percent) / 100.0, float(rotation.group(1))))
    # Return the stops ordered by offset.
    return sorted(stops)


# Compute the per-frame angular steps implied by one keyframe curve at the assumed refresh rate.
def per_frame_steps(stops: list) -> list:
    # Collect one step magnitude per keyframe segment.
    steps = []
    # Compare each consecutive pair of stops.
    for (offset_a, degrees_a), (offset_b, degrees_b) in zip(stops, stops[1:]):
        # Convert the offset span into wall-clock seconds.
        seconds = (offset_b - offset_a) * SPIN_SECONDS
        # Skip a zero-length segment rather than dividing by zero.
        if seconds <= 0:
            # Move to the next segment.
            continue
        # Record the mean angular velocity of the segment expressed per frame.
        steps.append(abs(degrees_b - degrees_a) / seconds / FRAMES_PER_SECOND)
    # Return every segment step.
    return steps


# Verify the bounded legacy rotor and ball fix without claiming the full planned motion contract.
class RouletteMotionTests(unittest.TestCase):
    # Require the rotor to advance slowly enough that a pocket ring cannot alias.
    def test_rotor_never_aliases_between_frames(self) -> None:
        # Read the tracked rotor curve.
        steps = per_frame_steps(keyframe_stops("roulettePremiumWheelSpin"))
        # Require the fastest segment to stay under one pocket per frame.
        self.assertLess(max(steps) / POCKET_DEGREES, 1.0, "rotor advances a whole pocket or more between frames, which reads as strobing")

    # Require the rotor to only ever slow down, the way a rotor coasting on friction does.
    def test_rotor_only_decelerates(self) -> None:
        # Read the tracked rotor curve.
        steps = per_frame_steps(keyframe_stops("roulettePremiumWheelSpin"))
        # Compare every neighbouring pair of segments.
        for index in range(1, len(steps)):
            # Isolate each comparison so a failure names the offending segment.
            with self.subTest(segment=index):
                # Require the curve never to speed back up mid-spin.
                self.assertLessEqual(steps[index], steps[index - 1] + 1e-6, "rotor speeds up mid-spin instead of coasting down")

    # Require the rotor to come to rest rather than stopping while still moving quickly.
    def test_rotor_comes_to_rest(self) -> None:
        # Read the tracked rotor curve.
        steps = per_frame_steps(keyframe_stops("roulettePremiumWheelSpin"))
        # Require the final segment to be a small fraction of the opening speed.
        self.assertLess(steps[-1], steps[0] * 0.2, "rotor still carries most of its speed at the end of the spin")

    # Require both curves to finish on a whole turn so the ball lands on its authoritative pocket.
    def test_curves_end_on_a_whole_turn(self) -> None:
        # Check the rotor and the counter-rotating ball.
        for name in ("roulettePremiumWheelSpin", "roulettePremiumBallSpin"):
            # Isolate each animation so a failure names it.
            with self.subTest(animation=name):
                # Read the final declared rotation.
                total = keyframe_stops(name)[-1][1]
                # Require a whole number of turns so no visible jump occurs when the animation ends.
                self.assertEqual(abs(total) % 360, 0, f"{name} ends mid-turn, so the element pops when the animation finishes")

    # Require the ball to counter-rotate against the rotor rather than drifting with it.
    def test_ball_counter_rotates(self) -> None:
        # Read the final rotation of each curve.
        rotor = keyframe_stops("roulettePremiumWheelSpin")[-1][1]
        ball = keyframe_stops("roulettePremiumBallSpin")[-1][1]
        # Require the two directions to be opposite so the reveal reads as a real wheel.
        self.assertLess(rotor * ball, 0, "ball and rotor turn the same way, so the ball never crosses the pockets")

    # Require the keyframes rather than a timing function to carry the deceleration.
    def test_timing_function_does_not_reshape_the_curve(self) -> None:
        # Check both spin declarations.
        for selector in (".wheel-ring.spinning", ".ball-dot.spinning"):
            # Isolate each declaration so a failure names it.
            with self.subTest(selector=selector):
                # Locate the tracked animation shorthand inside this external selector rule.
                rule = re.search(r"animation:\s*([^;}]+)", css_block(selector))
                # Require the declaration to exist.
                self.assertIsNotNone(rule, f"{selector} no longer declares a spin animation")
                # Require linear timing so the sampled keyframes above are the real motion profile.
                self.assertIn("linear", rule.group(1), f"{selector} reshapes its sampled curve with an easing function")

    # Require the spin to be suppressed for players who ask for reduced motion.
    def test_reduced_motion_disables_the_spin(self) -> None:
        # Locate the complete nested reduced-motion block in the external stylesheet.
        block = css_block("@media (prefers-reduced-motion: reduce)")
        # Require every tracked decorative animation channel to be switched off inside it.
        for selector in ("wheel-ring.spinning", "ball-dot.spinning", "ball-dot.settled", "roulette-spin-orbit::after"):
            # Isolate each selector so a failure names it.
            with self.subTest(selector=selector):
                # Require the selector to appear in the tracked reduced-motion block.
                self.assertIn(selector, block)

    # Require the curve to be sampled finely enough that linear interpolation stays smooth.
    def test_curve_is_finely_sampled(self) -> None:
        # Read the tracked rotor curve.
        stops = keyframe_stops("roulettePremiumWheelSpin")
        # Require enough stops that each segment is a short, near-linear slice of the coast-down.
        self.assertGreaterEqual(len(stops), 12, "too few keyframe stops to approximate a smooth coast-down")
