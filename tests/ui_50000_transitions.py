# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Response-and-generation transition helpers for the TEST-092 browser harness."""


# Reset Bingo only from an active generation and require its replacement purchase generation.
async def bingo_reset_to_purchase(page, activated_counts, *, wait_any_enabled, locator_ready, click_control, operation_timeout_ms, action_timeout_ms):
    await wait_any_enabled(page, ['[data-testid="bingo-buy"]', '[data-testid="bingo-reset"]'])  # Let any dispatched Buy or Call reach one authoritative actionable boundary.
    old_buy = page.locator('[data-testid="bingo-buy"]').first  # Capture the current purchase-generation node before deciding whether Reset is a no-op.
    if await locator_ready(old_buy):  # Preserve a genuinely fresh purchase-ready state without launching an unnecessary reset request.
        return False  # Report the truthful no-op while leaving activation evidence unchanged.
    old_buy_handle = await old_buy.element_handle()  # Retain the disabled active-generation node so stale readiness cannot satisfy completion.
    if old_buy_handle is None:  # Refuse a malformed active surface without a public Buy generation.
        raise AssertionError("Bingo active state exposed no Buy generation")  # Keep the public-state failure bounded.
    await wait_any_enabled(page, ['[data-testid="bingo-reset"]'])  # Require the active generation's real Reset control before destructive inspection.
    call = page.locator('[data-testid="bingo-call"]').first  # Resolve the public active-session signal without reading private game state.
    called_balls = page.locator('[data-testid="bingo-called-ball"]')  # Resolve rendered call history that makes reset destructive.
    requires_confirmation = await locator_ready(call) and await called_balls.count() > 0  # Distinguish active called sessions from completed history still shown on the board.
    accepted_dialog_types = []  # Record the one dialog handled by this exact destructive reset.

    async def accept_reset_confirmation(dialog):
        accepted_dialog_types.append(dialog.type)  # Preserve the public browser-dialog type before accepting it.
        await dialog.accept()  # Confirm the same abandonment prompt a player must accept.

    if requires_confirmation:  # Install a handler only when the rendered state proves reset will prompt.
        page.once("dialog", accept_reset_confirmation)  # Scope confirmation authority to the next dialog from this reset click.
    try:  # Guarantee temporary confirmation authority is removed on response, pointer, or prompt failure.
        async with page.expect_response(lambda response: response.url.partition("?")[0].endswith("/api/v1/games/bingo/reset") and response.request.method == "POST", timeout=operation_timeout_ms(action_timeout_ms)) as response_info:  # Bind completion to the exact public reset mutation.
            await click_control(page, '[data-testid="bingo-reset"]', activated_counts)  # Activate the visible Reset control through Playwright's real pointer path.
    finally:  # Revoke any unconsumed one-shot handler before another unrelated browser dialog can occur.
        if requires_confirmation:  # Remove only authority installed by this exact helper invocation.
            page.remove_listener("dialog", accept_reset_confirmation)  # Keep missing-prompt and error paths least-authority.
    response = await response_info.value  # Resolve the authoritative reset response before accepting replacement readiness.
    if not response.ok:  # Reject a reset that the server did not accept.
        raise AssertionError("Bingo reset request failed")  # Preserve only the public action identity.
    if requires_confirmation and accepted_dialog_types != ["confirm"]:  # Require exactly one expected confirmation to have unblocked the click.
        raise AssertionError(f"Bingo reset confirmation mismatch: {accepted_dialog_types}")  # Reject a missing or wrong browser-dialog boundary.
    await page.wait_for_function("node => !node.isConnected", arg=old_buy_handle, timeout=operation_timeout_ms(action_timeout_ms))  # Require the reset-owned render to detach the stale Buy generation.
    await wait_any_enabled(page, ['[data-testid="bingo-buy"]'])  # Require authoritative fresh-card readiness after reset.
    return True  # Report one real generation-replacing reset.


# Select one server-owned Roulette setting and require its exact response and replacement render before any later mutation.
async def select_roulette_setting(page, test_id, value, activated_counts, *, select_control, operation_timeout_ms, action_timeout_ms, number_counts, special_counts):
    if test_id not in {"roulette-mode", "roulette-zero"}:  # Restrict this authority to the two frozen server-owned setting controls.
        raise AssertionError(f"unsupported Roulette setting control: {test_id}")  # Refuse accidental reuse for client-only presentation fields.
    target = page.get_by_test_id(test_id)  # Resolve the current rendered setting generation.
    await target.wait_for(state="visible", timeout=operation_timeout_ms(action_timeout_ms))  # Require the real disclosed control before reading it.
    old_handle = await target.element_handle()  # Capture exact pre-request node identity so stale readiness cannot satisfy completion.
    if old_handle is None:  # Refuse a missing setting generation explicitly.
        raise AssertionError(f"Roulette {test_id} exposed no rendered generation")  # Preserve the bounded public identity.
    current_mode = await page.get_by_test_id("roulette-mode").input_value()  # Capture the mode included in every frozen settings payload.
    current_zero = await page.get_by_test_id("roulette-zero").input_value()  # Capture the zero rule included in every frozen settings payload.
    expected_mode = str(value) if test_id == "roulette-mode" else current_mode  # Derive the accepted post-response mode.
    expected_zero = str(value) if test_id == "roulette-zero" else current_zero  # Derive the accepted post-response zero rule.
    async with page.expect_response(lambda response: response.url.partition("?")[0].endswith("/api/v1/games/roulette/settings") and response.request.method == "POST", timeout=operation_timeout_ms(action_timeout_ms)) as response_info:  # Observe exactly the real settings POST triggered by this select.
        await select_control(target, value, activated_counts)  # Dispatch the real rendered change only after response observation is armed.
    response = await response_info.value  # Resolve the exact response before looking for its DOM generation.
    if not response.ok:  # Refuse conflicts or any other rejected settings mutation without retry or suppression.
        raise AssertionError(f"Roulette {test_id} settings request failed")  # Keep the failure bounded to the public control identity.
    await page.wait_for_function("node => !node.isConnected", arg=old_handle, timeout=operation_timeout_ms(action_timeout_ms))  # Require the response-owned render to detach the selected generation.
    expected = {"test_id": test_id, "value": str(value), "mode": expected_mode, "zero": expected_zero, "numbers": number_counts[expected_mode], "specials": special_counts[expected_mode]}  # Bind the new generation to exact accepted settings and source-owned inventories.
    expression = """expected => { const target = document.querySelector(`[data-testid="${expected.test_id}"]`); const mode = document.querySelector('[data-testid="roulette-mode"]')?.value; const zero = document.querySelector('[data-testid="roulette-zero"]')?.value; const numbers = document.querySelectorAll('[data-testid^="roulette-num-"]').length; const specials = document.querySelectorAll('[data-dozen],[data-column],[data-outside],[data-outbtn],[data-betid],[data-call]').length; return Boolean(target && !target.disabled && target.value === expected.value && mode === expected.mode && zero === expected.zero && numbers === expected.numbers && specials === expected.specials); }"""  # Require one fresh actionable setting generation plus the complete accepted catalog.
    await page.wait_for_function(expression, arg=expected, timeout=operation_timeout_ms(action_timeout_ms))  # Serialize the rerender and any mode-owned catalog load before returning.


# Exercise exact lower-pressure Roulette settings schedules without generic unobserved writes.
async def exercise_roulette_settings_controls(page, game_ordinal, activated_counts, *, should_rotate_zero, should_probe_mode, mode_for_ordinal, select_setting):
    ordinal = int(game_ordinal)  # Normalize the globally continuous schedule rank once.
    if should_rotate_zero(ordinal):  # Spend exactly one hundred real zero-rule activations across lower-pressure workers.
        zero = page.get_by_test_id("roulette-zero")  # Resolve the current fresh zero-rule generation.
        values = await zero.evaluate("node => [...node.options].filter(option => !option.disabled).map(option => option.value)")  # Read the closed rendered option vocabulary.
        current = await zero.input_value()  # Capture the accepted current value before choosing its deterministic successor.
        if current not in values or len(values) < 2:  # Reject a malformed server-owned setting surface.
            raise AssertionError("Roulette zero-rule options unavailable")  # Preserve the bounded public configuration failure.
        await select_setting(page, "roulette-zero", values[(values.index(current) + 1) % len(values)], activated_counts)  # Apply one real changed value through the serialized boundary.
    if should_probe_mode(ordinal):  # Spend fifty opposite-mode probes whose fifty scheduled restorations guarantee the literal floor.
        scheduled_mode = mode_for_ordinal(ordinal)  # Resolve the exact mode required for this formal cycle.
        opposite_mode = "single" if scheduled_mode == "double" else "double"  # Choose the only distinct supported wheel inventory.
        await select_setting(page, "roulette-mode", opposite_mode, activated_counts)  # Commit the probe fully before scheduled-mode enforcement.
