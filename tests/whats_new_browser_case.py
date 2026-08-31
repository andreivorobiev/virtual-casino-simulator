# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Browser journeys over real eligibility/dismissal functions with an isolated route adapter. (TOUR-003)"""

# Encode only bounded public envelopes for the page-local test adapter.
import json
# Own disposable provider state outside tracked runtime files.
import tempfile
# Resolve isolated files and checked localization resources.
from pathlib import Path
# Replace only the tour authority's dependencies for each fixture request.
from unittest.mock import patch
# Reuse production eligibility, version ordering, and durable acknowledgement.
from casino.core import whats_new
# Retain production JSON persistence without injecting a global test provider.
from casino.core.storage import JsonStorageProvider
# Keep all waits on the existing governed Browser budget.
from tests.browser_timing import WAIT_MS


# Exercise the real modal against production tour logic without activating the shipped catalog.
def run_whats_new_browser_case(page, base, root, visual_matrix, game_evidence):
    # Hold only test-owned identities inside the adapter, never in the browser response.
    owner = {"user_id": "tour-browser-owner", "role": "player"}
    # Begin at a canonical fixture release with three meaningful enabled entries.
    state = {"version": "0.9.5.86", "saves": 0, "fail_save": False}
    # Use existing reviewed EN/RU copy rather than invented fixture text.
    entries = [{"version": version, "show_in_whats_new": True, "title_key": f"whatsNew.entry.{version.replace('.', '_')}.title", "body_key": f"whatsNew.entry.{version.replace('.', '_')}.body"} for version in ("0.9.5.81", "0.9.5.82", "0.9.5.86")]
    # Keep generated artifacts and persistence under explicit owners.
    with tempfile.TemporaryDirectory(prefix="casino-tour-browser-") as temporary:
        # Construct one real isolated provider for the exact production functions.
        provider = JsonStorageProvider(Path(temporary) / "data")

        # Adapt browser API calls to the production authority using scoped dependencies only.
        def route_tour(route):
            # Scope the fixture to the two existing self-service paths.
            path = route.request.url.split("?", 1)[0]
            # Forward every unrelated route without modifying it.
            if path not in (base + "/api/v2/me/whats-new", base + "/api/v2/me/whats-new/dismiss"):
                # Preserve unrelated API traffic and real authentication.
                route.continue_()
                # Do not run any fixture authority for other paths.
                return
            # Exercise real version selection and persistence without changing tracked metadata.
            with patch.object(whats_new, "get_storage_provider", return_value=provider), patch.object(whats_new, "APP_VERSION", state["version"]), patch.object(whats_new, "load_catalog", return_value={"entries": entries, "max_merged_entries": 3, "changelog_path": "RELEASE_NOTES.md"}):
                # Acknowledgement must have the exact empty-body contract.
                if route.request.method == "POST":
                    # Reject any client attempt to choose identity or version.
                    assert route.request.post_data_json == {}
                    # Count explicit actions, including the controlled failure proof.
                    state["saves"] += 1
                    # Return an unconfirmed success envelope to test failure without polluting HTTP telemetry.
                    result = {"dismissed": False, "persisted": False, "dismissed_at": None} if state["fail_save"] else whats_new.dismiss(owner)
                else:
                    # Read committed eligibility with the production server function.
                    result = whats_new.tour_for(owner)
            # Return only the existing public envelope; no fixture identity crosses the boundary.
            route.fulfill(status=200, content_type="application/json", body=json.dumps({"ok": True, "data": result}))

        # Install one page-local adapter; production endpoints and global providers remain unchanged.
        page.route("**/api/v2/me/whats-new**", route_tour)
        # Guarantee adapter removal and neutral browser restoration on assertion failure too.
        try:
            # Require first-load eligibility to mount one merged tour.
            page.goto(base, wait_until="networkidle")
            # Wait on semantic native modal state, not arbitrary timing.
            dialog = page.get_by_test_id("whats-new-dialog")
            # Confirm real Chromium executed showModal and the feature is visible.
            dialog.wait_for(timeout=WAIT_MS)
            # Require all three release entries in the same modal.
            assert page.get_by_test_id("whats-new-entries").locator("li").count() == 3
            # Exercise both locales at all four governed viewport sizes.
            for locale in ("en-US", "ru-RU"):
                # Switch the real installed localization runtime without replacing dialog nodes.
                page.evaluate("locale => window.CasinoI18n.setLocale(locale)", locale)
                # Read the shipped resource as the visible-copy oracle.
                copy = json.loads((root / "web" / "i18n" / locale / "shell.json").read_text(encoding="utf-8"))
                # Require localized heading and action labels before retaining visual evidence.
                assert dialog.locator("h2").inner_text() == copy["whatsNew.title"]
                # Keep essential controls localized independently from entry text.
                assert page.get_by_test_id("whats-new-dismiss").inner_text() == copy["whatsNew.dismiss"]
                # Cover reduced motion with the same no-animation surface.
                page.emulate_media(reduced_motion="reduce")
                # Test the exact machine-readable viewport inventory.
                for viewport in visual_matrix["viewports"]:
                    # Resize before measuring the native modal and its document containment.
                    page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
                    # Require bounded modal geometry and one designed overflow surface.
                    geometry = dialog.evaluate("el => { const r=el.getBoundingClientRect(); return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:innerWidth,height:innerHeight,overflow:document.documentElement.scrollWidth-innerWidth}; }")
                    # Reject clipping or horizontal page overflow at every named viewport.
                    assert geometry["left"] >= 0 and geometry["right"] <= geometry["width"] and geometry["top"] >= 0 and geometry["bottom"] <= geometry["height"] and geometry["overflow"] <= 1, geometry
                    # Keep the title and acknowledgement visible outside the one deliberate list scroll.
                    assert dialog.locator("h2").evaluate("el => { const r=el.getBoundingClientRect(); return r.top>=0 && r.bottom<=innerHeight; }")
                    # Enforce the adopted touch floor and visible primary action at every viewport.
                    assert page.get_by_test_id("whats-new-dismiss").evaluate("el => { const r=el.getBoundingClientRect(); return r.top>=0 && r.bottom<=innerHeight && r.height>=42 && r.width>=42; }")
                    # Native keyboard navigation must remain in the modal top layer.
                    page.get_by_test_id("whats-new-dismiss").focus()
                    # Exercise a complete forward and backward focus cycle.
                    for key in ("Tab", "Tab", "Tab", "Shift+Tab"):
                        # Use actual keyboard navigation, not synthetic click dispatch.
                        page.keyboard.press(key)
                        # Require focus containment in the real browser implementation.
                        assert dialog.evaluate("el => el.contains(document.activeElement)")
                    # Reject unresolved release keys and raw fixture release labels.
                    visible = dialog.inner_text()
                    # All presentation must come from resolved user-facing resources.
                    assert "whatsNew." not in visible and "0.9.5.86" not in visible
                    # Capture actual implemented branch bytes with the shared evidence helper.
                    game_evidence(f"after-pass-whats-new-{locale}-{viewport['id']}.png", "whats_new", ["merged_updates", "keyboard_focus", "reduced_motion"], locale, viewport["id"])
            # Prove unconfirmed acknowledgement remains visible with honest localized failure copy.
            state["fail_save"] = True
            # Submit one real pointer click and await its exact API response.
            with page.expect_response(lambda response: response.url.endswith("/me/whats-new/dismiss")):
                # Exercise the persistent acknowledgement control.
                page.get_by_test_id("whats-new-dismiss").click()
            # Wait for visible error text through a bounded condition.
            page.wait_for_function("() => Boolean(document.querySelector('[data-testid=whats-new-error]')?.textContent)", timeout=WAIT_MS)
            # Retain the honest failed-save state with exact visual-matrix metadata.
            game_evidence("after-pass-whats-new-save-error-ru-RU-mobile.png", "whats_new", ["save_error"], "ru-RU", "mobile")
            # Deferring with Escape must never submit a hidden retry.
            page.keyboard.press("Escape")
            # Require the native modal to be removed and keyboard focus returned to the shell.
            dialog.wait_for(state="detached", timeout=WAIT_MS)
            # Require the active keyboard target to return to the persistent shell.
            assert page.get_by_test_id("nav-lobby").evaluate("el => el === document.activeElement")
            # Keep the explicit failed-attempt count exact.
            assert state["saves"] == 1
            # Re-enable the fixture authority for the next explicit action.
            state["fail_save"] = False
            # Local deferral must not masquerade as persistent dismissal on refresh.
            page.reload(wait_until="networkidle")
            # Require the unacknowledged tour to return.
            dialog.wait_for(timeout=WAIT_MS)
            # Save through the real controller and production dismissal function.
            page.get_by_test_id("whats-new-dismiss").click()
            # Close only after the committed response.
            dialog.wait_for(state="detached", timeout=WAIT_MS)
            # Reconstruct the provider to prove dismissal survives its in-memory cache.
            provider = JsonStorageProvider(Path(temporary) / "data")
            # Require a reload read to report no eligible entries for this release.
            with page.expect_response(lambda response: response.url.endswith("/me/whats-new")) as acknowledged:
                # Start a fresh document with the same authenticated shell.
                page.reload(wait_until="networkidle")
            # Require persisted eligibility, not a browser-local hidden flag.
            assert acknowledged.value.json()["data"]["show"] is False
            # No second dialog may appear for the acknowledged release.
            assert dialog.count() == 0
            # Advance only the test catalog's canonical release for an actual version-transition journey.
            state["version"] = "0.9.5.87"
            # Reuse reviewed copy while giving it a new fixture release version.
            entries.append({**entries[-1], "version": state["version"]})
            # Refresh after the fixture release transition.
            page.reload(wait_until="networkidle")
            # Require only the newly eligible entry, not the three dismissed predecessors.
            dialog.wait_for(timeout=WAIT_MS)
            # Preserve the bounded merged-release contract after a real saved dismissal.
            assert page.get_by_test_id("whats-new-entries").locator("li").count() == 1
            # Retain next-release proof independently from the initial three-entry tour.
            game_evidence("after-pass-whats-new-next-release-ru-RU-mobile.png", "whats_new", ["next_release"], "ru-RU", "mobile")
            # Keep the changelog fixed and opener-isolated.
            assert page.get_by_test_id("whats-new-changelog").get_attribute("rel") == "noopener noreferrer"
            # Return to the restored route without another durable acknowledgement.
            page.keyboard.press("Escape")
            # Wait for removal before exercising the previously covered route and game controls.
            dialog.wait_for(state="detached", timeout=WAIT_MS)
            # Return localized evidence and subsequent cases to the canonical English shell.
            page.evaluate("() => window.CasinoI18n.setLocale('en-US')")
            # Use the required shared-layout review viewport after mobile tour coverage.
            page.set_viewport_size({"width": 1920, "height": 1080})
            # Require the preserved Lobby controls before retaining after-dismissal evidence.
            page.get_by_test_id("catalog-search").wait_for(timeout=WAIT_MS)
            # Capture the shared shell after optional modal teardown.
            game_evidence("after-pass-whats-new-dismissed-shell-en-US-desktop_primary.png", "shell_lobby", ["authenticated"], "en-US", "desktop_primary")
            # Navigate through a real persistent control to prove the tour leaves gameplay usable.
            page.get_by_test_id("nav-roulette").click()
            # Require the affected game route to mount inside the preserved shell.
            page.get_by_test_id("roulette-premium").wait_for(timeout=WAIT_MS)
            # Retain the required shared-shell/game review image without placing a wager.
            game_evidence("after-pass-whats-new-dismissed-roulette-en-US-desktop_primary.png", "roulette", ["betting"], "en-US", "desktop_primary")
        finally:
            # Remove only the page-local tour adapter.
            page.unroute("**/api/v2/me/whats-new**", route_tour)
            # Restore normal motion and the canonical desktop for following Browser cases.
            page.emulate_media(reduced_motion="no-preference")
            # Keep the existing suite's shared viewport contract.
            page.set_viewport_size({"width": 1920, "height": 1080})
            # Reload against the real disabled catalog before subsequent tests execute.
            page.goto(base, wait_until="networkidle")
