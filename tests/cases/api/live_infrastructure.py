# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own live infrastructure API registrations for #727 without owning the listener."""

# Import canonical JSON encoding and strict persisted-document parsing.
import json


# Register the money-boundary case before the runner-owned reset boundary.
def run_money_boundary_case(run_case, base, api, raw_api, root):
    """Register the cross-game non-finite money case at its historical point."""
    # Prove every affected game route rejects decoded and string non-finite wagers without mutation.
    def nonfinite_money_api():
        # Read the authenticated wallet identity and finite baseline.
        current = api(base, "/api/v2/auth/session")
        # Select the session-owned player for ledger and wallet comparisons.
        player_id = current["player"]["player_id"]
        # Capture the original finite wallet balance.
        balance_before = current["player"]["balance"]
        # Capture every existing ledger row before hostile requests.
        ledger_before = api(base, f"/api/v1/players/{player_id}/ledger")["ledger"]
        # Snapshot game-state bytes so validation cannot create partial rounds or bets.
        games_root = root / "data" / "games"
        # Build a relative-path map for any pre-existing reset fixtures.
        state_before = {str(path.relative_to(games_root)): path.read_bytes() for path in games_root.rglob("*") if path.is_file()}
        # Define each route and the minimum valid non-wager fields needed after validation.
        routes = (
            ("/api/v1/games/roulette/bets", "amount", {"bet_type": "red", "covered_numbers": []}),  # Cover Roulette shared amount validation.
            ("/api/v1/games/blackjack/rounds", "bet_amount", {}),  # Cover Blackjack initial wagers.
            ("/api/v1/games/baccarat/bets", "amount", {"bet_type": "player"}),  # Cover Baccarat bets.
            ("/api/v1/games/keno/tickets", "amount", {"spots": [1]}),  # Cover Keno tickets.
            ("/api/v1/games/slots/spin", "line_bet", {"active_lines": 1}),  # Cover Slots line bets.
            ("/api/v1/games/bingo/cards", "amount", {"pattern": "line"}),  # Cover Bingo cards.
            ("/api/v1/games/multi-hand-video-poker/rounds", "wager_per_hand", {"request_id": "nonfinite-regression", "hand_count": 3}),  # Cover the independent MHVP wager helper.
        )
        # Exercise string values that pass strict JSON parsing but must fail route validation.
        for path, field, base_body in routes:
            # Cover NaN and both infinity spellings accepted by Python float conversion.
            for value in ("nan", "inf", "-inf"):
                # Copy the valid auxiliary fields for one isolated request.
                body = dict(base_body)
                # Place the non-finite string into the route's public wager field.
                body[field] = value
                # Require a standard client validation envelope.
                rejected = api(base, path, "POST", body, ok=False)
                # Require the stable error code without route execution.
                assert rejected["error"]["code"] == "VALIDATION_ERROR", f"{path} accepted {value}"
        # Exercise raw JSON constants against every route at the shared parser boundary.
        for path, field, base_body in routes:
            # Cover every non-standard numeric token accepted by default json.loads.
            for constant in ("NaN", "Infinity", "-Infinity"):
                # Serialize only finite auxiliary fields through the strict standard encoder.
                members = [f"{json.dumps(key)}:{json.dumps(value, separators=(',', ':'))}" for key, value in base_body.items()]
                # Append the exact unquoted hostile numeric constant.
                members.append(f"{json.dumps(field)}:{constant}")
                # Build one exact JSON object without letting json.dumps rewrite the constant.
                raw_body = ("{" + ",".join(members) + "}").encode("utf-8")
                # Require the development adapter to return the standard failure envelope.
                rejected = raw_api(base, path, raw_body)
                # Require parser rejection before authentication-bound route dispatch.
                assert rejected["ok"] is False and rejected["error"]["code"] == "VALIDATION_ERROR", f"{path} parser accepted {constant}"
        # Read the wallet after every rejected request.
        current_after = api(base, "/api/v2/auth/session")
        # Require the finite balance to remain exactly unchanged.
        assert current_after["player"]["balance"] == balance_before
        # Require no rejected request to append any ledger event.
        assert api(base, f"/api/v1/players/{player_id}/ledger")["ledger"] == ledger_before
        # Snapshot state again after all validation failures.
        state_after = {str(path.relative_to(games_root)): path.read_bytes() for path in games_root.rglob("*") if path.is_file()}
        # Require no game state creation or mutation.
        assert state_after == state_before
        # Parse the retained player document with non-standard constants forbidden.
        persisted = json.loads((root / "data" / "players.json").read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(AssertionError(f"persisted {value}")))
        # Require the exact session wallet to remain finite in durable storage.
        assert next(player["balance"] for player in persisted["players"] if player["player_id"] == player_id) == balance_before

    # Record cross-game API, parser, wallet, ledger, state, and persistence evidence.
    run_case("API-MONEY-NONFINITE-001", ["CORE-025", "LEDGER-027", "MHVP-006", "TEST-055"], nonfinite_money_api)


# Register the five infrastructure cases after the runner-owned reset and login.
def run_service_cases(run_case, base, api, root):
    """Register Operations, OAuth, mail, and invitation cases in historical order."""
    # Define the Operations probe contract against the real loopback backend.
    def operations_api():
        # Require anonymous liveness to expose only the fixed process state.
        assert api(base, "/healthz", auth_token=None) == {"status": "live"}
        # Require readiness details to reject an anonymous caller.
        anonymous_ready = api(base, "/readyz", ok=False, auth_token=None)
        # Bind the exact unauthorized result separately for readable diagnostics.
        assert anonymous_ready["error"]["code"] == "UNAUTHORIZED"
        # Require the authenticated Admin session to see healthy readiness and telemetry.
        ready = api(base, "/readyz")
        # Read the matching Admin operations view from the same live server.
        admin_status = api(base, "/api/v2/admin/operations")
        # Bind healthy readiness and the isolated JSON provider.
        assert ready["ready"] is True and admin_status["ready"] is True and ready["storage_provider"] == "json"
        # Resolve only this worktree server's isolated primary storage document.
        players_path = root / "data" / "players.json"
        # Select one test-owned temporary outage path beside the isolated document.
        unavailable_path = root / "data" / "players.operations-test-unavailable.json"
        # Start a reversible post-start outage without touching shared or user-owned runtime data.
        players_path.replace(unavailable_path)
        # Always restore the isolated document even if an acceptance assertion fails.
        try:
            # Require protected readiness to return the sanitized not-ready envelope.
            degraded = api(base, "/readyz", ok=False)
            # Bind the stable degraded code and state.
            assert degraded["error"]["code"] == "OPERATIONS_NOT_READY" and degraded["error"]["details"]["status"] == "degraded"
            # Require Admin diagnostics to retain the prior heartbeat without leaking raw errors.
            admin_degraded = api(base, "/api/v2/admin/operations")
            # Bind the exact sanitized component reason and prior heartbeat.
            assert admin_degraded["ready"] is False and admin_degraded["last_successful_heartbeat_at"] == admin_status["checked_at"] and admin_degraded["reasons"] == [{"component": "storage", "code": "storage_unavailable"}]
        # Restore the isolated provider document before later casino tests continue.
        finally:
            # Move the test-owned file back to its canonical provider path.
            unavailable_path.replace(players_path)
        # Require readiness to recover on the same live backend after storage restoration.
        assert api(base, "/readyz")["ready"] is True

    # Record anonymous/authenticated/degraded/recovery Operations behavior under permanent IDs.
    run_case("API-OPS-001", ["OPS-001", "OPS-002", "OPS-003", "OPS-005", "TEST-044"], operations_api)

    # Define the disabled OAuth Admin diagnostic contract against the real loopback backend.
    def oauth_api():
        # Require unauthenticated callers to fail before the Admin route can disclose diagnostics.
        anonymous = api(base, "/api/v2/admin/oauth/providers", ok=False, auth_token=None)
        # Bind the exact protected result.
        assert anonymous["error"]["code"] == "UNAUTHORIZED"
        # Read the allowlisted provider diagnostics through the authenticated Admin session.
        diagnostic = api(base, "/api/v2/admin/oauth/providers")
        # Require the stable catalog order so UI and contract clients cannot confuse provider rows.
        assert [provider["provider"] for provider in diagnostic["providers"]] == ["local", "google", "facebook"]
        # Define the exact allowlisted schema published by the additive auth v2 contract.
        allowed_keys = {"provider", "flow", "status", "configuration_ready", "runtime_available", "enabled_requested", "network_released", "client_id_configured", "client_secret_configured", "callback_url", "missing_variables", "problems"}
        # Require every diagnostic row to contain no undeclared or action-bearing fields.
        assert all(set(provider) == allowed_keys for provider in diagnostic["providers"])
        # Index the three stable providers for explicit runtime assertions.
        providers = {provider["provider"]: provider for provider in diagnostic["providers"]}
        # Preserve local password login as the sole runtime-available provider.
        assert providers["local"]["runtime_available"] is True
        # Keep both external providers unavailable regardless of environment readiness.
        assert providers["google"]["runtime_available"] is False and providers["facebook"]["runtime_available"] is False
        # Read the boolean-only public provider catalog without authenticated configuration detail.
        public = api(base, "/api/v2/auth/oauth/providers", auth_token=None)
        # Require exactly two disabled external providers under repository-default flags.
        assert public == {"providers": [{"provider": "google", "available": False, "signup_available": False}, {"provider": "facebook", "available": False, "signup_available": False}]}
        # Require reviewed provider start routes to exist but remain inaccessible under both default gates.
        for held_provider in ("google", "facebook"):
            # Send one exact start request and require provider-unavailable without allocating a flow.
            held = api(base, f"/api/v2/auth/oauth/{held_provider}/start", "POST", {"action": "signin", "return_to": "/"}, ok=False)
            # Bind the held start response.
            assert held["error"]["code"] == "NOT_FOUND"
            # Require the callback route to remain equally inaccessible before parsing callback proof.
            callback = api(base, f"/api/v2/auth/oauth/{held_provider}/callback", ok=False)
            # Bind the held callback response.
            assert callback["error"]["code"] == "NOT_FOUND"
        # Require unreviewed generic linking and exchange surfaces to remain absent.
        for missing_path in ("/api/v2/auth/oauth/google/link", "/api/v2/auth/oauth/google/exchange"):
            # Dispatch only empty value-free reads and require a closed surface.
            missing = api(base, missing_path, ok=False)
            # Bind the closed generic surface.
            assert missing["error"]["code"] == "NOT_FOUND"
        # Require full signup to remain a disabled first-party path rather than an OAuth-created account.
        signup = api(base, "/api/v2/auth/signup", "POST", {"email": "oauth-held@example.invalid", "password": "OAuthHeldPassw0rd!", "display_name": "Held User", "accepted": True, "terms_version": "private-beta-1"}, ok=False, auth_token=None)
        # Require the disabled route to fail closed under repository defaults.
        assert signup["error"]["code"] == "FORBIDDEN"
        # Confirm OAuth diagnostics never extend the accepted Operations response shape.
        assert set(api(base, "/api/v2/admin/operations")) == {"schema_version", "probe", "status", "checked_at", "last_successful_heartbeat_at", "build", "ready", "storage_provider", "checks", "reasons"}

    # Record secret-safe Admin diagnostics, absent action routes, and unchanged readiness under permanent IDs.
    run_case("API-OAUTH-001", ["OAUTH-001", "OAUTH-002", "OAUTH-006", "OAUTH-007", "AUTH-007", "TEST-045", "TEST-093"], oauth_api)

    # Define additive current-user OAuth contract behavior under repository-default held gates.
    def oauth_runtime_api():
        # Read the public boolean catalog without an authenticated session.
        public = api(base, "/api/v2/auth/oauth/providers", auth_token=None)
        # Require fixed provider order and no configuration, callback, client, or release detail.
        assert public == {"providers": [{"provider": "google", "available": False, "signup_available": False}, {"provider": "facebook", "available": False, "signup_available": False}]}
        # Read current-user link status through the authenticated Admin's ordinary account identity.
        links = api(base, "/api/v2/me/oauth/providers")
        # Require boolean-only current-user state and held availability for both providers.
        assert links == {"providers": [{"provider": "google", "linked": False, "available": False}, {"provider": "facebook", "linked": False, "available": False}]}
        # Reject caller-selected account targets before any provider or persistence operation.
        targeted = api(base, "/api/v2/auth/oauth/google/start", "POST", {"action": "signin", "return_to": "/", "email": "target@example.invalid"}, ok=False)
        # Central restricted-preview integrity may fail before service validation, but no provider start can succeed.
        assert targeted["error"]["code"] in {"FORBIDDEN", "NOT_FOUND", "VALIDATION_ERROR"}
        # Preserve the frozen v1 surface without any OAuth path.
        assert api(base, "/api/v1/auth/oauth/providers", ok=False)["error"]["code"] == "NOT_FOUND"

    # Record additive v2, boolean privacy, current-user ownership, disabled gate, and frozen-v1 proof.
    run_case("API-OAUTH-002", ["OAUTH-007", "OAUTH-008", "OAUTH-009", "OAUTH-010", "OAUTH-012", "OAUTH-013", "AUTH-007", "AUTH-017", "TEST-093", "TEST-167", "TEST-168"], oauth_runtime_api)

    # Define the disabled transactional-mail Admin diagnostic contract against the real loopback backend.
    def mail_api():
        # Require unauthenticated callers to fail before mail diagnostics disclose configuration state.
        anonymous = api(base, "/api/v2/admin/mail/readiness", ok=False, auth_token=None)
        # Bind the exact protected response.
        assert anonymous["error"]["code"] == "UNAUTHORIZED"
        # Read the disabled-by-default diagnostic through the authenticated Admin session.
        diagnostic = api(base, "/api/v2/admin/mail/readiness")
        # Require the exact top-level secret-free contract shape.
        assert set(diagnostic) == {"schema_version", "provider", "status", "checks", "reasons", "delivery_summary", "suppressed_recipients"}
        # Require the repository feature and network release gates to remain false by default.
        assert diagnostic["status"] == "disabled" and diagnostic["checks"]["feature_enabled"] is False and diagnostic["checks"]["network_release_enabled"] is False
        # Require every lifecycle diagnostic to be an aggregate non-negative integer.
        assert set(diagnostic["delivery_summary"]) == {"sending", "sent", "retry_wait", "failed", "suppressed", "uncertain", "disabled", "release_held", "misconfigured"} and all(isinstance(value, int) and value >= 0 for value in diagnostic["delivery_summary"].values())
        # Serialize the diagnostic and reject raw configuration, credential, recipient, token, or URL surfaces.
        serialized = json.dumps(diagnostic)
        # Bind secret-safe serialized output.
        assert "CASINO_" not in serialized and "://" not in serialized and "@" not in serialized and "token=" not in serialized
        # Require likely consumer and provider event routes to remain absent from the application router.
        for held_path in ("/api/v2/mail/send", "/api/v2/mail/bounce", "/api/v2/auth/password-reset", "/api/v2/auth/invitations"):
            # Dispatch one empty request and require a closed route surface.
            missing = api(base, held_path, ok=False)
            # Bind the absent route response.
            assert missing["error"]["code"] == "NOT_FOUND"

    # Record Admin authorization, disabled gates, aggregate diagnostics, and absent consumer routes.
    run_case("API-MAIL-002", ["MAIL-001", "MAIL-002", "MAIL-003", "TEST-090"], mail_api)

    # Define the disabled private invitation API and frozen-v1 compatibility proof. (issue #332)
    def invitation_api():
        # Reject anonymous access before any Admin invitation readiness or lifecycle metadata is returned.
        anonymous = api(base, "/api/v2/admin/invitations", ok=False, auth_token=None)
        # Bind the protected diagnostic response.
        assert anonymous["error"]["code"] == "UNAUTHORIZED"
        # Read the repository-default disabled diagnostic through the authenticated Admin session.
        diagnostic = api(base, "/api/v2/admin/invitations")
        # Require the exact secret-free list contract with both independent gates held.
        assert set(diagnostic) == {"enabled", "redemption_enabled", "mail_status", "recovery_required", "invitations"} and diagnostic["enabled"] is False and diagnostic["redemption_enabled"] is False and diagnostic["invitations"] == []
        # Reject issuance before token, mail, invitation, account, or wallet state can be allocated.
        blocked = api(base, "/api/v2/admin/invitations", "POST", {"recipient": "api-invitation@example.invalid", "locale": "en-US", "idempotency_key": "api-invitation-create-key-0001"}, ok=False)
        # Bind the disabled issuance result.
        assert blocked["error"]["code"] == "FORBIDDEN"
        # Exercise a fully shaped disabled public request without an authenticated session.
        redemption = api(base, "/api/v2/auth/redeem-invitation", "POST", {"token": "synthetic-disabled-bearer", "email": "api-invitation@example.invalid", "password": "Synthetic-Invite-2026!", "display_name": "Invited Player", "locale": "en-US", "terms_version": "private-beta-1", "accepted": True, "idempotency_key": "api-invitation-redeem-key-0001"}, ok=False, auth_token=None)
        # Require one non-enumerating message and reason for the disabled request.
        assert redemption["error"] == {"code": "VALIDATION_ERROR", "message": "invitation could not be redeemed", "details": {"reason": "invitation_unavailable"}}
        # Require an unsupported field to receive the same generic public envelope.
        malformed = api(base, "/api/v2/auth/redeem-invitation", "POST", {"unexpected": "value"}, ok=False, auth_token=None)
        # Bind the identical non-enumerating error.
        assert malformed["error"] == redemption["error"]
        # Preserve every historical invitation-like v1 path as absent rather than adding a compatibility alias.
        for frozen_path in ("/api/v1/admin/invitations", "/api/v1/auth/redeem-invitation", "/api/v1/auth/invitations"):
            # Require the frozen router to expose no invitation surface.
            missing = api(base, frozen_path, ok=False)
            # Bind the absent v1 route response.
            assert missing["error"]["code"] == "NOT_FOUND"

    # Record authorization, disabled gates, generic public errors, and frozen-v1 compatibility.
    run_case("API-INVITE-002", ["INVITE-001", "INVITE-002", "INVITE-003", "INVITE-004", "TEST-091"], invitation_api)
