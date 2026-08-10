# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import argparse
# Import required dependency so this module can use its public functions or constants.
import json
# Import required dependency so this module can use its public functions or constants.
import mimetypes
# Import required dependency so this module can use its public functions or constants.
import os
# Import regular expressions so player resource paths can be authorization-checked.
import re
# Import required dependency so this module can use its public functions or constants.
import sys
# Import required dependency so this module can use its public functions or constants.
import threading
# Import required dependency so this module can use its public functions or constants.
import webbrowser
# Import required dependency so this module can use its public functions or constants.
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
# Import required dependency so this module can use its public functions or constants.
from pathlib import Path
# Import required dependency so this module can use its public functions or constants.
from urllib.parse import urlparse

# Import required dependency so this module can use its public functions or constants.
from casino.config import DEFAULT_HOST, DEFAULT_PORT, OPENAPI_DIR, WEB_DIR, APP_VERSION, GUEST_AUTOPLAY_MAX_ROUNDS, GUEST_BINGO_AUTOPLAY_MAX_CALLS, validate_bootstrap_for_startup, PASSKEYS_ENABLED
# Import required dependency so this module can use its public functions or constants.
from casino.router import Router
# Import required dependency so this module can use its public functions or constants.
from casino.errors import CasinoError, ConflictError, ForbiddenError, ValidationError
# Import strict JSON-number handling shared with the production WSGI adapter.
from casino.core.validation import reject_nonfinite_json_constant, require_amount
# Import host-only CSRF bootstrap helpers shared with the production adapter. (OAUTH-008)
from casino.core.security import CSRF_COOKIE, cookie_value, csrf_cookie_header, new_csrf_token
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import ensure_dirs, migrate_from_v7_if_needed
# Import required dependency so this module can bootstrap whichever storage provider is configured.
from casino.core.storage import bootstrap_players, get_storage_provider
# Import required dependency so this module can use its public functions or constants.
from casino.core import logger, players, ledger, history, auth, feedback, guest_analytics, guest_settings, invitations, password_reset, receipts, user_settings, wellness, whats_new, replay, table_profiles, game_compare, guest_conversion, enrollment_policy
# Import required dependency so this module can use its public functions or constants.
from casino.games.registry import catalog_summary, list_games, register_games
# Import required dependency so this module can use its public functions or constants.
from casino.admin import register as register_admin
# Import required dependency so this module can use its public functions or constants.
from casino.bots.api import register as register_bots
# Import the disabled OAuth registrar for Admin-only secret-safe diagnostics.
from casino.core.oauth.api import register as register_oauth
# Import the disabled-by-default transactional-mail Admin readiness registrar. (MAIL-003)
from casino.core.mail import register as register_mail
# Import the approved Operations registrar for liveness, readiness, and Admin telemetry.
from casino.operations import register as register_operations
# Import required dependency so this module can use its public functions or constants.
from casino.core import autoplay

# Keep development and browser-test Admin static protection aligned with the production WSGI adapter. (AUTH-008)
ADMIN_STATIC_PATHS = frozenset({"/admin", "/admin.html", "/admin.js", "/web/admin.js"})
# Name the exact credential-free worker request marker for cookie-free public shell bytes. (PWA-002)
PWA_PUBLIC_SHELL_HEADER = "X-Casino-Public-Shell"
# Define one cache contract consumed by both supported HTTP adapters. (CORE-026)
CACHE_CONTROL_NO_STORE = "no-store"
# Bound the development/test listener backlog above the governed 138-context navigation burst. (CORE-021, TEST-142)
CONCURRENT_REQUEST_QUEUE_SIZE = 256
# Classify only transport errors that prove the peer can no longer receive a response. (LOG-006)
PEER_DISCONNECT_ERRORS = (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)


# Keep concurrent lazy-module requests queued without changing production WSGI behavior. (CORE-021, TEST-142)
class CasinoThreadingHTTPServer(ThreadingHTTPServer):
    # Accept the complete governed browser burst plus bounded API fan-out before the OS rejects a socket.
    request_queue_size = CONCURRENT_REQUEST_QUEUE_SIZE

# Define the build_router function used by this module.
def build_router() -> Router:
    # Set router to the value needed for the next operation.
    router = Router()

    # Define authorize_autoplay so session identifiers cannot cross authenticated player boundaries.
    def authorize_autoplay(context, autoplay_id):
        # Load the referenced server-side autoplay session.
        session = autoplay.get_session(autoplay_id)
        # Reject normal users addressing another player's autoplay session.
        if not auth.is_admin(context["user"]) and session.get("player_id") != context["user"].get("player_id"):
            # Raise the standard forbidden response without mutating the foreign session.
            raise ForbiddenError("Autoplay session is outside the authenticated player")
        # Return the authorized session for callers that need it.
        return session

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/casino/games")
    # Define the games function used by this module.
    def games(body, query):
        # Return the computed value to the caller.
        return {"games": list_games(), "catalog": catalog_summary()}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/casino/state")
    # Define the casino_state function used by this module.
    def casino_state(body, query, context):
        # Recognize only the exact new shell projection so malformed or duplicate query values retain legacy behavior. (TEST-166)
        shell_projection = query.get("projection") == "shell"
        # Count unique recently active sessions for both the compact shell and full compatibility response. (issue #570)
        online_player_count = auth.online_user_count()
        # Return only fields consumed by the shell when the caller explicitly opts into the compact projection. (TEST-166)
        if shell_projection:
            # Preserve descriptor-driven navigation while avoiding unrelated player, history, ledger, and catalog work.
            return {"version": APP_VERSION, "games": list_games(), "online_player_count": online_player_count}
        # Read the bound player so non-Admin state never exposes another wallet.
        player_id = context.get("bound_player_id")
        # Publish all players only to Admins and the authenticated player otherwise.
        visible_players = players.list_players() if auth.is_admin(context["user"]) else [players.get_player(player_id)]
        # Read recent history before applying the session privacy boundary.
        recent_history = history.recent_history(25)
        # Filter history records when they carry a player id and the caller is not Admin.
        visible_history = recent_history if auth.is_admin(context["user"]) else [row for row in recent_history if row.get("player_id") == player_id]
        # Read only the bound player's ledger for normal authenticated users.
        recent_ledger = ledger.read_recent(None if auth.is_admin(context["user"]) else player_id, 25)
        # Return the session-scoped casino summary with privacy-safe aggregate presence.
        return {"version": APP_VERSION, "games": list_games(), "catalog": catalog_summary(), "players": visible_players, "online_player_count": online_player_count, "recent_history": visible_history, "recent_ledger": recent_ledger}

    # Register additive v2 authenticated manual problem-report submission. (CORE-027, issue #349)
    @router.post(r"/api/v2/feedback/reports")
    # Persist one privacy-safe report through the provider-neutral recovery state machine.
    def submit_feedback_report_v2(body, query, context):
        # Bind the reporter from the authenticated session rather than accepting caller identity.
        return feedback.submit(context["user"], body)

    # Register additive v2 current-reporter status visibility for converted and registered users.
    @router.get(r"/api/v2/me/feedback/reports")
    # Return only the authenticated reporter's own summaries without retained screenshot pixels.
    def current_user_feedback_reports_v2(body, query, context):
        # Delegate reporter scoping to the feedback service so guest trials stay non-durable until conversion.
        return {"reports": feedback.list_reporter_reports(context["user"])}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/casino/reset")
    # Define the reset function used by this module.
    def reset(body, query, context):
        # Require an Admin role before destroying shared local casino state.
        auth.require_admin(context["user"])
        # Resolve the configured provider once for one stable reset identity.
        provider = get_storage_provider()
        # Hold the provider reset boundary through recreation and bootstrap visibility.
        with provider.reset_transaction():
            # Recreate shared runtime folders while the reset boundary remains held.
            ensure_dirs()
            # Bootstrap only missing default rows under the same provider-owned reset boundary.
            provider.bootstrap_players(players.default_players())
            # Bootstrap the default administrator before releasing reset visibility.
            auth.bootstrap_admin_from_env()
            # Build the unchanged success payload while reset visibility remains private.
            result = {"games": list_games(), "players": players.list_players()}
        # Execute this statement as part of the module's documented control flow.
        logger.info("casino_reset")
        # Return the computed value to the caller.
        return result

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/casino/history")
    # Define the get_history function used by this module.
    def get_history(body, query, context):
        # Read recent history for the requested game before applying privacy filters.
        rows = history.recent_history(int(query.get("limit", 100)), query.get("game") or None)
        # Return global history to Admins and session-player records to normal users.
        return {"history": rows if auth.is_admin(context["user"]) else [row for row in rows if row.get("player_id") == context["bound_player_id"]]}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/casino/logs/recent")
    # Define the get_logs function used by this module.
    def get_logs(body, query, context):
        # Require Admin authorization before returning application log records.
        auth.require_admin(context["user"])
        # Set kind to the value needed for the next operation.
        kind = query.get("kind", "app")
        # Return the computed value to the caller.
        return {"logs": logger.recent(kind, int(query.get("limit", 50)))}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/players")
    # Define the get_players function used by this module.
    def get_players(body, query, context):
        # Return every player to Admins and only the session-bound player otherwise.
        return {"players": players.list_players() if auth.is_admin(context["user"]) else [players.get_player(context["bound_player_id"])]}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/players/(?P<player_id>[^/]+)")
    # Define the get_player function used by this module.
    def get_player(body, query, player_id):
        # Return the computed value to the caller.
        return {"player": players.get_player(player_id)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/players")
    # Define the create_player function used by this module.
    def create_player(body, query, context):
        # Keep arbitrary player creation behind the Admin authorization boundary.
        auth.require_admin(context["user"])
        # Return the computed value to the caller.
        return {"player": players.create_player(body.get("display_name", "Player"), body.get("type", "human"), float(body.get("balance", 5000)))}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/players/(?P<player_id>[^/]+)/add-money")
    # Define the add_money function used by this module.
    def add_money(body, query, context, player_id):
        # Apply the same guest wallet freeze the v2 token route enforces. Without the context parameter
        # this legacy route received no session at all, so a guest could top up its own disposable
        # wallet through it and defeat the non-purchasable guest design. (issues #317, #410)
        if auth.is_guest(context.get("user") or {}):
            # Reject even play-token-only credits because guest value must stay disposable.
            raise ForbiddenError("Guest trial balances cannot be increased")
        # Bound the credit through the shared money gate so this route cannot mint an amount no wager
        # could ever produce, and so NaN and infinity are rejected before reaching the ledger. (#410)
        amount = require_amount(body.get("amount", 0))
        # Set ev to the value needed for the next operation.
        ev = ledger.credit(player_id, amount, "FAKE_MONEY_ADDED", None, None, {})
        # Return the computed value to the caller.
        return {"ledger": ev, "player": players.get_player(player_id)}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/players/(?P<player_id>[^/]+)/ledger")
    # Define the get_ledger function used by this module.
    def get_ledger(body, query, player_id):
        # Return the computed value to the caller.
        return {"ledger": ledger.read_recent(player_id, int(query.get("limit", 100)))}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/log/client")
    # Define the client_log function used by this module.
    def client_log(body, query):
        # Reject non-object payloads before they can enter persistent diagnostics. (LOG-006)
        if not isinstance(body, dict):
            # Return the published validation envelope instead of an internal server error.
            raise ValidationError("Client log payload must be an object")
        # Read the public low-cardinality client event name.
        client_event = body.get("event")
        # Require one bounded nonempty string so malformed diagnostics stay fail-closed.
        if not isinstance(client_event, str) or not client_event.strip() or len(client_event) > 100:
            # Reject absent, non-string, blank, or unbounded event names.
            raise ValidationError("Client log event must be a nonempty string of at most 100 characters")
        # Normalize absent diagnostic details to one empty object.
        details = body.get("details", {})
        # Refuse scalar or collection details that cannot preserve the documented object shape.
        if not isinstance(details, dict):
            # Reject malformed details through the standard validation response.
            raise ValidationError("Client log details must be an object")
        # Normalize the already client-sanitized location field.
        href = body.get("href", "")
        # Require a string location marker without interpreting or expanding it server-side.
        if not isinstance(href, str):
            # Reject malformed location evidence before persistence.
            raise ValidationError("Client log href must be a string")
        # Normalize the browser-owned user-agent field.
        user_agent = body.get("user_agent", "")
        # Require the same string shape emitted by the published browser helper.
        if not isinstance(user_agent, str):
            # Reject malformed agent evidence before persistence.
            raise ValidationError("Client log user_agent must be a string")
        # Persist the fixed backend record type and retain the browser event under a non-colliding field.
        logged = logger.client("client_event", client_event=client_event.strip(), details=details, href=href, user_agent=user_agent)
        # Return the existing success shape only after persistence completes.
        return {"logged": logged}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v2/auth/login")
    # Define the auth_login function used by this module.
    def auth_login(body, query, context):
        # Prefer the explicit email field while preserving the published username alias for compatible clients.
        email = body.get("email") or body.get("username", "")
        # Authenticate the normalized email credential through the backend auth service.
        result = auth.login(email, body.get("password", ""), context.get("client", ""))
        # Execute this statement as part of the module's documented control flow.
        # Extend the response with host-only session and production CSRF cookies under context policy.
        context.setdefault("response_headers", []).extend(auth.session_cookie_headers(result["session"], context.get("session_samesite", "Lax"), bool(context.get("secure_cookie")), bool(context.get("include_csrf_cookie"))))
        # Return the computed value to the caller.
        return result

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v2/auth/logout")
    # Define the auth_logout function used by this module.
    def auth_logout(body, query, context):
        # Set token to the value needed for the next operation.
        token = auth.extract_bearer_token(context.get("headers", {})) or auth.extract_cookie_token(context.get("headers", {}))
        # Execute this statement as part of the module's documented control flow.
        # Expire both session and production CSRF cookies using the same governed attributes.
        context.setdefault("response_headers", []).extend(auth.clear_cookie_headers(context.get("session_samesite", "Lax"), bool(context.get("secure_cookie")), bool(context.get("include_csrf_cookie"))))
        # Return the computed value to the caller.
        return auth.logout(token)

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v2/auth/guest")
    # Start one account-free disposable guest trial from the login surface. (issue #317)
    def auth_guest(body, query, context):
        # Reject caller-authored identity, wallet, role, expiry, or other fields outside the exact v2 contract.
        if set(body) - {"accepted", "terms_version", "locale", "device"}:
            # Fail closed before creating any disposable principal or analytics state.
            raise ValidationError("Guest trial request contains unsupported fields")
        # Create one isolated principal only after explicit current-version guest terms acceptance.
        guest = auth.create_guest(context.get("client", ""), body.get("accepted") is True, body.get("terms_version", ""), body.get("locale", "en-US"), body.get("device", "unknown"))
        # Set a browser-session cookie with no durable credential so closing the browser drops the trial.
        context.setdefault("response_headers", []).extend(auth.guest_cookie_headers(guest["session"], context.get("session_samesite", "Lax"), bool(context.get("secure_cookie")), bool(context.get("include_csrf_cookie"))))
        # Build the same current-user payload shape the shell already consumes for registered logins.
        payload = auth.current_user_payload(guest["session"], guest["user"])
        # Return the raw browser-context proof exactly once so the shell can keep it in sessionStorage.
        payload["guest_browser_nonce"] = guest["browser_nonce"]
        # Return the guest session payload without exposing any durable credential or internal identifier.
        return payload

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v2/auth/redeem-invitation")
    # Redeem an email invitation through the disabled recoverable enrollment boundary. (INVITE-003)
    def auth_redeem_invitation(body, query):
        # Reject any field outside the exact v2 redemption contract before consuming the bearer.
        if set(body or {}) - {"token", "email", "password", "display_name", "locale", "terms_version", "accepted", "idempotency_key"}:
            # Fail closed through the same generic envelope used for every public rejection.
            raise ValidationError("invitation could not be redeemed", dict(invitations.GENERIC_REDEMPTION_DETAILS))
        # Start a fixed logging-failure boundary before bearer inspection or invitation mutation.
        try:
            # Enforce the same resolved invitation capability published by the read-only policy route. (AUTH-013)
            invitation_decision = enrollment_policy.evaluate(enrollment_policy.ROUTE_INVITATION)
        # Keep operational logger failures indistinguishable from every other public redemption denial.
        except (enrollment_policy.EnrollmentAuditError, ValidationError):
            # Return the existing identifier-free generic envelope without exposing logger details.
            raise ValidationError("invitation could not be redeemed", dict(invitations.GENERIC_REDEMPTION_DETAILS)) from None
        # Deny a closed or invitation-disabled policy before the bearer reaches the service.
        if invitation_decision["allowed"] is not True:
            # Reuse the exact generic envelope so policy state cannot become an invitation oracle.
            raise ValidationError("invitation could not be redeemed", dict(invitations.GENERIC_REDEMPTION_DETAILS))
        # Redeem through the invitation lifecycle; disabled enrollment and every abuse case fail closed generically.
        return invitations.redeem(str((body or {}).get("token", "")), str((body or {}).get("email", "")), str((body or {}).get("password", "")), str((body or {}).get("display_name", "")), str((body or {}).get("locale", "en-US")), str((body or {}).get("terms_version", "")), (body or {}).get("accepted") is True, str((body or {}).get("idempotency_key", "")))

    # Attach a public read-only enrollment policy so browser controls can show disabled gates honestly.
    @router.get(r"/api/v2/auth/enrollment-policy")
    # Publish signup, invitation, guest, conversion, and passkey availability without creating identity state.
    def auth_enrollment_policy(body, query):
        # Resolve the read-only durable policy so the endpoint and future enforcement share one source. (AUTH-013)
        enrollment = enrollment_policy.capabilities()
        # Return feature gates only, never environment names, credentials, or operator settings.
        return {"signup_enabled": enrollment["signup_enabled"], "guest_trials_enabled": guest_settings.trials_enabled(), "invitation_enrollment_enabled": enrollment["invitation_enrollment_enabled"], "enrollment_mode": enrollment["mode"], "guest_conversion_enabled": True, "passkeys_enabled": PASSKEYS_ENABLED, "canonical_identity": "casino_user_id", "shared_auth_origin": "tiltseven_first_party"}

    # Attach a public CSRF bootstrap so a cookie-less sign-in surface can recover without a shell reload. (issue #224)
    @router.get(r"/api/v2/auth/csrf")
    # Re-issue the host-only double-submit cookie exactly like the packaged shell bootstrap.
    def auth_csrf_bootstrap(body, query, context):
        # Read request headers only to select the correct existing proof.
        headers = context.get("headers", {})
        # Reuse an active session's distinct CSRF value without authenticating a context-bound guest cookie.
        token = auth.csrf_token_for_session_cookie(headers)
        # Fall back to the browser's existing bounded anonymous double-submit value when no session is active.
        if not token:
            # Read only the named cookie rather than reflecting the complete Cookie header.
            existing = cookie_value(headers, CSRF_COOKIE)
            # Accept only token-url-safe lengths generated by this application.
            token = existing if 32 <= len(existing) <= 128 else new_csrf_token()
        # Set or refresh the double-submit cookie under the adapter's governed cookie attributes.
        context.setdefault("response_headers", []).append(csrf_cookie_header(token, context.get("session_samesite", "Lax"), bool(context.get("secure_cookie"))))
        # Return an empty public envelope so no token material enters the response body.
        return {}

    # Attach a gated public full-account signup endpoint for the owner-approved future enrollment form.
    @router.post(r"/api/v2/auth/signup")
    # Create a local first-party user only when the explicit signup gate is enabled.
    def auth_signup(body, query, context):
        # Start a fixed logging-failure boundary before validating or creating an account.
        try:
            # Enforce the same resolved email-signup capability published by the read-only policy route. (AUTH-013)
            signup_decision = enrollment_policy.evaluate(enrollment_policy.ROUTE_SIGNUP)
        # Preserve the existing disabled-signup envelope when operational decision logging is unavailable.
        except (enrollment_policy.EnrollmentAuditError, ValidationError):
            # Reveal no logger path, exception, or policy internals to the anonymous caller.
            raise ForbiddenError("Full account signup is disabled") from None
        # Keep the route present but fail closed until the resolved policy explicitly allows signup.
        if signup_decision["allowed"] is not True:
            # Reject disabled signup before validating account fields to avoid account enumeration.
            raise ForbiddenError("Full account signup is disabled")
        # Reject unsupported fields so public signup cannot smuggle roles, status, wallet, or provider identity.
        if set(body or {}) - {"email", "password", "display_name", "locale", "terms_version", "accepted"}:
            # Fail closed through the standard validation envelope.
            raise ValidationError("Signup request contains unsupported fields")
        # Require explicit terms acceptance for every full account created through public signup.
        if (body or {}).get("accepted") is not True:
            # Reject silent signup attempts.
            raise ValidationError("Signup requires explicit terms acceptance")
        # Validate password policy before creating a durable identity.
        auth.validate_enrollment_password(str((body or {}).get("password", "")))
        # Create a normal local player account with no Admin privileges and no provider identity.
        user = auth.create_user(str((body or {}).get("email", "")), str((body or {}).get("password", "")), str((body or {}).get("display_name", "")), role="player", terms_required=False, locale=str((body or {}).get("locale", "en-US")))
        # Store the accepted terms version on the created account.
        auth.accept_terms(user["user_id"], str((body or {}).get("terms_version", "")), True, "self_signup")
        # Create a browser session immediately so the enrollment form can continue into the lobby.
        result = auth.login(user["email"], str((body or {}).get("password", "")), context.get("client", ""))
        # Add session and CSRF cookies using the same policy as password login.
        context.setdefault("response_headers", []).extend(auth.session_cookie_headers(result["session"], context.get("session_samesite", "Lax"), bool(context.get("secure_cookie")), bool(context.get("include_csrf_cookie"))))
        # Return the current-user payload rather than any raw password or signup internals.
        return result

    # Register enumeration-safe password-recovery initiation on the additive public v2 boundary. (RESET-004)
    @router.post(r"/api/v2/auth/password-reset/initiate")
    # Accept one mailbox recovery request without revealing account existence or delivery state.
    def auth_password_reset_initiate(body, query):
        # Reject fields outside the exact locale and caller-idempotency contract.
        if not isinstance(body, dict) or set(body) - {"email", "locale", "idempotency_key"}:
            # Fail closed before passing any recipient value to the recovery service.
            raise ValidationError("Password reset request contains unsupported fields")
        # Delegate recipient normalization, release gating, delivery, and enumeration safety.
        return password_reset.initiate(str(body.get("email") or ""), locale=str(body.get("locale") or "en-US"), idempotency_key=str(body.get("idempotency_key") or ""))

    # Register an explicit resend alias that uses the same single-active-token state machine. (RESET-004)
    @router.post(r"/api/v2/auth/password-reset/resend")
    # Replace any prior active recovery bearer while returning the same generic acknowledgement.
    def auth_password_reset_resend(body, query):
        # Reuse the initiation validator and service so resend cannot become a separate account oracle.
        return auth_password_reset_initiate(body, query)

    # Register password-recovery completion on the additive public v2 boundary. (RESET-004)
    @router.post(r"/api/v2/auth/password-reset/complete")
    # Consume one purpose-bound bearer and revoke predecessor sessions after credential rotation.
    def auth_password_reset_complete(body, query):
        # Reject fields outside the exact bearer, mailbox, replacement, and idempotency contract.
        if not isinstance(body, dict) or set(body) - {"token", "email", "new_password", "idempotency_key"}:
            # Preserve one generic public request shape before service validation.
            raise ValidationError("Password reset request contains unsupported fields")
        # Delegate generic rejection, token consumption, password policy, and session revocation.
        return password_reset.complete(str(body.get("token") or ""), str(body.get("email") or ""), str(body.get("new_password") or ""), idempotency_key=str(body.get("idempotency_key") or ""))

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v2/auth/guest/end")
    # Irreversibly end the authenticated guest's own trial. (issue #317)
    def auth_guest_end(body, query, context):
        # Reject registered identities so this lifecycle route cannot masquerade as ordinary logout.
        if not auth.is_guest(context.get("user") or {}):
            # Preserve the published forbidden envelope without changing the registered session.
            raise ForbiddenError("Guest trial is required")
        # End only the authenticated guest principal, revoking every resumable credential and state pointer.
        auth.end_guest_trial(context.get("user") or {})
        # Expire the guest session cookie so the browser stops presenting it.
        context.setdefault("response_headers", []).extend(auth.clear_cookie_headers(context.get("session_samesite", "Lax"), bool(context.get("secure_cookie")), bool(context.get("include_csrf_cookie"))))
        # Return a simple ended acknowledgement with no recoverable material.
        return {"ended": True}

    # Attach a lifecycle signal used to distinguish same-context reloads from later cookie replay.
    @router.post(r"/api/v2/auth/guest/depart")
    # Record a best-effort browser page departure without making reloads lose the active trial. (issue #317)
    def auth_guest_depart(body, query, context):
        # Reject registered identities so this lifecycle route cannot alter normal sessions.
        if not auth.is_guest(context.get("user") or {}):
            # Preserve the standard authorization envelope for the guest-only operation.
            raise ForbiddenError("Guest trial is required")
        # Mark the authenticated session as departed; nonce validation still governs any resumption.
        auth.mark_guest_departed(context["session"], context["user"])
        # Return an identifier-free acknowledgement suitable for keepalive delivery.
        return {"departed": True}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v2/auth/session")
    # Define the auth_session function used by this module.
    def auth_session(body, query, context):
        # Record the first authenticated lobby journey milestone for a guest without client-authored telemetry.
        if auth.is_guest(context.get("user") or {}):
            # Bind only through the server-stored unrelated analytics id.
            guest_analytics.record_event(context["user"].get("guest_analytics_id"), "lobby_reached")
        # Return the computed value to the caller.
        return auth.current_user_payload(context["session"], context["user"])

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v2/me")
    # Define the current_user function used by this module.
    def current_user(body, query, context):
        # Record the first authenticated lobby journey milestone for a guest without client-authored telemetry.
        if auth.is_guest(context.get("user") or {}):
            # Bind only through the server-stored unrelated analytics id.
            guest_analytics.record_event(context["user"].get("guest_analytics_id"), "lobby_reached")
        # Return the computed value to the caller.
        return auth.current_user_payload(context["session"], context["user"])

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v2/me/terms")
    # Define the current_user_terms function used by this module.
    def current_user_terms(body, query, context):
        # Return the computed value to the caller.
        return {"terms": auth.terms_status(context["user"])}

    # Attach the published terms acceptance route to the canonical user store.
    @router.post(r"/api/v2/auth/terms/accept")
    # Define current_user_accept_terms for authenticated browser terms completion.
    def current_user_accept_terms(body, query, context):
        # Store the accepted version on the authenticated identity only.
        user = auth.accept_terms(context["user"]["user_id"], body.get("terms_version"), body.get("accepted", True) is not False)
        # Return the published v2 terms status shape.
        return auth.terms_status(user)

    # Preserve the frontend draft alias while clients move to the published auth path.
    @router.post(r"/api/v2/me/terms/accept")
    # Define current_user_accept_terms_alias as a compatibility shim.
    def current_user_accept_terms_alias(body, query, context):
        # Delegate the alias to the same canonical acceptance operation.
        return current_user_accept_terms(body, query, context)

    # Register additive opt-in session-wellness preference reads. (WELL-001, issue #167)
    @router.get(r"/api/v2/me/wellness")
    # Return the authenticated session's own reminder configuration and accepted bounds.
    def current_user_wellness(body, query, context):
        # Publish only the session-derived subject's opt-in record.
        return {"wellness": wellness.read_wellness(context["user"])}

    # Register additive field-allowlisted session-wellness preference updates. (WELL-001, issue #167)
    @router.patch(r"/api/v2/me/wellness")
    # Apply one validated reminder change to the session's own record only.
    def update_current_user_wellness(body, query, context):
        # Bind the subject from the authenticated session rather than accepting caller identity.
        return {"wellness": wellness.update_wellness(context["user"], body)}

    # Register additive neutral summaries of committed movements in the active login session. (WELL-002, issue #167)
    @router.get(r"/api/v2/me/wellness/summary")
    # Return plain committed totals for the active session without evaluating them.
    def current_user_wellness_summary(body, query, context):
        # Use the server-owned login-session boundary rather than a caller-authored timestamp.
        return wellness.session_summary(context["user"], since=str(context.get("session", {}).get("created_at") or ""))

    # Register additive version-aware What's New eligibility reads. (TOUR-001, issue #165)
    @router.get(r"/api/v2/me/whats-new")
    # Return only curated localization keys for releases this session has not acknowledged.
    def current_user_whats_new(body, query, context):
        # Derive the subject from the session and publish no raw version key.
        return whats_new.tour_for(context["user"])

    # Register additive server-stamped tour dismissal. (TOUR-002, issue #165)
    @router.post(r"/api/v2/me/whats-new/dismiss")
    # Acknowledge the running release without trusting any caller-supplied version.
    def dismiss_current_user_whats_new(body, query, context):
        # Reject every caller-authored field so subject and release identity remain server-owned.
        if body:
            # Fail closed instead of silently accepting hostile or future payload authority.
            raise ValidationError("What's New dismissal accepts no fields", {"reason": "unsupported_fields", "fields": sorted(body)})
        # Stamp the acknowledgement from the canonical application version.
        return whats_new.dismiss(context["user"])

    # Register additive personal-preference reads outside the frozen v1 surface. (USER-006, issue #352)
    @router.get(r"/api/v2/me/settings")
    # Return the authenticated session's own preferences and the supported locale catalog.
    def current_user_settings(body, query, context):
        # Publish the subject's record together with the catalog a client needs to render choices.
        return {"settings": user_settings.read_settings(context["user"]), "supported_locales": list(user_settings.SUPPORTED_LOCALES)}

    # Register additive field-allowlisted personal-preference updates. (USER-006, issue #352)
    @router.patch(r"/api/v2/me/settings")
    # Apply one validated preference change to the session's own record only.
    def update_current_user_settings(body, query, context):
        # Bind the subject from the authenticated session rather than accepting caller identity.
        return {"settings": user_settings.update_settings(context["user"], body)}

    # Register the disabled-by-default passkey foundation status for My Settings.
    @router.get(r"/api/v2/me/passkeys")
    # Publish passkey readiness without starting a WebAuthn ceremony.
    def current_user_passkeys(body, query, context):
        # Return no credential inventory until the certified passkey implementation lands.
        return {"passkeys": {"enabled": PASSKEYS_ENABLED, "registration_available": False, "authentication_available": False, "credentials": [], "canonical_identity": "casino_user_id"}}

    # Register a fail-closed passkey registration entrypoint so future UI buttons have a governed endpoint.
    @router.post(r"/api/v2/me/passkeys/register")
    # Reject registration until WebAuthn challenges, attestation, recovery, and browser evidence are implemented.
    def current_user_passkey_register(body, query, context):
        # Preserve the disabled foundation rather than accepting a partial browser credential.
        raise ForbiddenError("Passkey registration is disabled")

    # Register additive self-only bounded activity reads. (USER-007, issue #352)
    @router.get(r"/api/v2/me/history")
    # Return only the authenticated session's own paginated activity.
    def current_user_history(body, query, context):
        # Derive the subject from the session and accept only pagination and filter inputs.
        return user_settings.self_history(context["user"], page=query.get("page", 1), page_size=query.get("page_size", user_settings.DEFAULT_PAGE_SIZE), game=query.get("game", ""))

    # Register additive self-only explained ledger movements. (RECEIPT-001, RECEIPT-002, issue #161)
    @router.get(r"/api/v2/me/receipts")
    # Return only the authenticated session's own bounded play-token movement explanations.
    def current_user_receipts(body, query, context):
        # Bind the subject from the session and pass only shared pagination values to the receipt mapper.
        return receipts.self_receipts(context["user"], page=query.get("page", 1), page_size=query.get("page_size", receipts.DEFAULT_PAGE_SIZE))

    # Register additive self-only bounded round-replay artifacts. (REPLAY-001, issue #162)
    @router.get(r"/api/v2/me/replays")
    # Return only the authenticated session's own bounded, in-retention replay artifacts.
    def current_user_replays(body, query, context):
        # Derive the subject from the session and accept only pagination and filter inputs.
        return replay.self_replays(context["user"], page=query.get("page", 1), page_size=query.get("page_size", replay.DEFAULT_PAGE_SIZE), game=query.get("game", ""))

    # Register additive per-game personal table-profile reads. (PROFILE-001, issue #164)
    @router.get(r"/api/v2/me/table-profiles/(?P<game>[a-z0-9_-]+)")
    # Return the authenticated session's own stored profile for one game.
    def current_user_table_profile(body, query, context, game):
        # Publish the subject's per-game profile only.
        return {"profile": table_profiles.read_profile(context["user"], game)}

    # Register additive field-allowlisted per-game table-profile updates. (PROFILE-001, issue #164)
    @router.patch(r"/api/v2/me/table-profiles/(?P<game>[a-z0-9_-]+)")
    # Apply one validated profile change to the session's own record for one game only.
    def update_current_user_table_profile(body, query, context, game):
        # Bind the subject from the authenticated session rather than accepting caller identity.
        return {"profile": table_profiles.update_profile(context["user"], game, body)}

    # Register additive product-safe game comparison reads. (COMPARE-001, issue #160)
    @router.get(r"/api/v2/games/compare")
    # Return a product-safe comparison of the requested games without any money-math attribute.
    def compare_games(body, query, context):
        # Accept only the requested games and locale; the comparison derives from the read-only catalog.
        return game_compare.compare(query.get("games", ""), locale=query.get("locale", "en-US"))

    # Register additive authenticated guest-to-account conversion. (CONVERT-001, issue #378)
    @router.post(r"/api/v2/me/convert-guest")
    # Convert the authenticated guest's own trial into a durable full account, preserving its wallet.
    def convert_guest(body, query, context):
        # Reject unsupported fields so conversion cannot smuggle roles, status, wallet, or provider identity.
        if set(body or {}) - {"email", "password", "display_name", "locale", "terms_version", "accepted", "idempotency_key"}:
            # Fail closed before touching conversion state.
            raise ValidationError("Guest conversion request contains unsupported fields")
        # Bind the guest principal from the authenticated session rather than any caller-supplied identity.
        return guest_conversion.convert(context.get("user") or {}, str((body or {}).get("email", "")), str((body or {}).get("password", "")), str((body or {}).get("display_name", "")), terms_version=str((body or {}).get("terms_version", "")), accepted=(body or {}).get("accepted") is True, locale=str((body or {}).get("locale", "en-US")), idempotency_key=str((body or {}).get("idempotency_key", "")))

    # Attach the published current-user token credit endpoint.
    @router.post(r"/api/v2/me/tokens/add")
    # Define current_user_add_tokens for ledger-backed session wallet credits.
    def current_user_add_tokens(body, query, context):
        # Keep the guest wallet fixed to its one server-issued trial grant with no top-up path. (issue #317)
        if auth.is_guest(context.get("user") or {}):
            # Reject even play-token-only credits because guest value must stay disposable and non-purchasable.
            raise ForbiddenError("Guest trial balances cannot be increased")
        # Validate the requested play-token amount through the canonical bounded finite-amount gate. (issue #410 residual)
        amount = require_amount(body.get("amount", 0))
        # Credit exactly one ledger event to the authenticated user's bound player.
        ledger.credit(context["user"]["player_id"], amount, "PLAY_TOKENS_ADDED", "wallet", None, {"reason": body.get("reason") or "current_user_add", "user_id": context["user"]["user_id"]})
        # Return the contract's updated player summary from the canonical current-user source.
        return auth.current_user_payload(context["session"], context["user"])["player"]

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/autoplay/start")
    # Define the autoplay_start function used by this module.
    def autoplay_start(body, query, context):
        # Bind every non-Admin autoplay registration to the authenticated player's wallet.
        player_id = body.get("player_id", "human") if auth.is_admin(context["user"]) else context["user"].get("player_id")
        # Parse the requested round limit before applying guest-specific ceilings.
        round_limit = int(body.get("round_limit", 25))
        # Apply disposable-session resource controls without changing registered-player behavior.
        if auth.is_guest(context.get("user") or {}):
            # Reject a second concurrent guest autoplay registration.
            if any(session.get("player_id") == player_id for session in autoplay.list_sessions(active_only=True)):
                # Return the standard conflict envelope without creating shared control-plane state.
                raise ConflictError("Guest trial already has an active autoplay session")
            # Detect the bounded Bingo call plan without broadening other guest autoplay loops. (BINGO-027)
            bingo_call_plan = body.get("game_id") == "bingo" and (body.get("plan") or {}).get("type") == "auto_call_stepwise"
            # Select the complete 75-call ceiling only for the governed Bingo plan. (BINGO-027)
            guest_limit = GUEST_BINGO_AUTOPLAY_MAX_CALLS if bingo_call_plan else GUEST_AUTOPLAY_MAX_ROUNDS
            # Clamp the disposable registration to the applicable configured bounded count.
            round_limit = max(1, min(round_limit, guest_limit))
        # Return the authenticated, bounded autoplay registration.
        return {"session": autoplay.start(body.get("game_id"), player_id, body.get("speed", "medium"), round_limit, body.get("plan") or {}, body.get("limits") or {})}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/autoplay/stop")
    # Define the autoplay_stop function used by this module.
    def autoplay_stop(body, query, context):
        # Authorize the requested autoplay session before mutating it.
        authorize_autoplay(context, body.get("autoplay_id"))
        # Return the computed value to the caller.
        return {"session": autoplay.stop(body.get("autoplay_id"))}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/autoplay/complete")
    # Define the autoplay_complete function used by this module.
    def autoplay_complete(body, query, context):
        # Authorize the requested autoplay session before mutating it.
        authorize_autoplay(context, body.get("autoplay_id"))
        # Return the computed value to the caller.
        return {"session": autoplay.complete(body.get("autoplay_id"))}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/autoplay/tick")
    # Define the autoplay_tick function used by this module.
    def autoplay_tick(body, query, context):
        # Authorize the requested autoplay session before mutating it.
        authorize_autoplay(context, body.get("autoplay_id"))
        # Return the computed value to the caller.
        return {"session": autoplay.tick(body.get("autoplay_id"))}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/autoplay/finish-stop")
    # Define the autoplay_finish_stop function used by this module.
    def autoplay_finish_stop(body, query, context):
        # Authorize the requested autoplay session before mutating it.
        authorize_autoplay(context, body.get("autoplay_id"))
        # Return the computed value to the caller.
        return {"session": autoplay.finish_stop(body.get("autoplay_id"))}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/autoplay/stop-all")
    # Define the autoplay_stop_all function used by this module.
    def autoplay_stop_all(body, query, context):
        # Reserve global autoplay mutation for authenticated Admins.
        auth.require_admin(context["user"])
        # Return the computed value to the caller.
        return {"sessions": autoplay.stop_all()}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/autoplay/sessions")
    # Define the autoplay_sessions function used by this module.
    def autoplay_sessions(body, query, context):
        # Read the requested server-side sessions before applying the player scope.
        sessions = autoplay.list_sessions(query.get("active") == "1")
        # Return all sessions to Admins and only the authenticated player's sessions otherwise.
        return {"sessions": sessions if auth.is_admin(context["user"]) else [session for session in sessions if session.get("player_id") == context["user"].get("player_id")]}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/autoplay/sessions/(?P<autoplay_id>[^/]+)")
    # Define the autoplay_get_session function used by this module.
    def autoplay_get_session(body, query, autoplay_id, context):
        # Return only an autoplay session authorized for the current identity.
        return {"session": authorize_autoplay(context, autoplay_id)}

    # Execute this statement as part of the module's documented control flow.
    register_bots(router)
    # Register every game API from the canonical per-module catalog descriptors.
    register_games(router)
    # Register the reviewed disabled-by-default OAuth status, start, callback, account-link, and Admin routes. (OAUTH-007)
    register_oauth(router)
    # Register only the Admin readiness route; mail consumer flows remain outside this scope.
    register_mail(router)
    # Register Operations probes after game routes and before the Admin API surface.
    register_operations(router)
    # Execute this statement as part of the module's documented control flow.
    register_admin(router)
    # Return the computed value to the caller.
    return router

# Set ROUTER to the value needed for the next operation.
ROUTER = build_router()

# Define the Handler class that groups related behavior.
class Handler(BaseHTTPRequestHandler):
    # Set server_version to the value needed for the next operation.
    server_version = f"VirtualCasinoV9/{APP_VERSION}"

    # Define the log_message function used by this module.
    def log_message(self, fmt, *args):
        # Record only method and parsed route so callback queries, headers, and request lines never enter logs. (OAUTH-008)
        logger.info("http_access", client=self.client_address[0], method=self.command, path=urlparse(self.path).path)

    # Define the _read_body function used by this module.
    def _read_body(self):
        # Set length to the value needed for the next operation.
        length = int(self.headers.get("Content-Length") or 0)
        # Branch when the following condition is true.
        if not length:
            # Return the computed value to the caller.
            return {}
        # Set raw to the value needed for the next operation.
        raw = self.rfile.read(length)
        # Branch when the following condition is true.
        if not raw:
            # Return the computed value to the caller.
            return {}
        # Start protected logic so failures can be handled safely.
        try:
            # Return the computed value to the caller.
            return json.loads(raw.decode("utf-8"), parse_constant=reject_nonfinite_json_constant)
        # Handle the expected failure path for the protected logic.
        except (UnicodeDecodeError, json.JSONDecodeError):
            # Return the computed value to the caller.
            return {"_raw": raw.decode("utf-8", errors="replace")}

    # Finish one buffered response without turning a peer disconnect into a second HTTP response.
    def _finish_response(self, raw):
        # Start protected transport completion after status and headers have been selected.
        try:
            # Flush the buffered headers exactly once.
            self.end_headers()
            # Write the complete selected body while the peer remains connected.
            self.wfile.write(raw)
        # Handle only closed-peer transport boundaries; application failures still propagate.
        except PEER_DISCONNECT_ERRORS:
            # Record a fixed secret-safe diagnostic without query, body, header, or exception content.
            logger.warning("http_peer_disconnect", method=self.command, path=urlparse(self.path).path)
            # Report that no complete response reached the peer.
            return False
        # Report successful response delivery to focused regressions and future callers.
        return True

    # Define the _send_json function used by this module.
    def _send_json(self, status, payload, extra_headers=None):
        # Set raw to the value needed for the next operation.
        raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        # Execute this statement as part of the module's documented control flow.
        self.send_response(status)
        # Set self.send_header("Content-Type", "application/json; charset to the value needed for the next operation.
        self.send_header("Content-Type", "application/json; charset=utf-8")
        # Execute this statement as part of the module's documented control flow.
        self.send_header("Content-Length", str(len(raw)))
        # Execute this statement as part of the module's documented control flow.
        self.send_header("Cache-Control", CACHE_CONTROL_NO_STORE)
        # Iterate through the collection to process each item.
        for name, value in extra_headers or []:
            # Execute this statement as part of the module's documented control flow.
            self.send_header(name, value)
        # Finish once so a peer disconnect cannot re-enter the generic API 500 path. (LOG-006)
        return self._finish_response(raw)

    # Send one same-origin OAuth completion redirect without serializing callback data.
    def _send_redirect(self, location: str, extra_headers=None):
        # Encode an empty response body because the reviewed destination is carried only in Location.
        raw = b""
        # Publish the post-callback redirect status.
        self.send_response(303)
        # Return only the prevalidated same-origin completion location.
        self.send_header("Location", location)
        # Prevent callback responses from entering browser or intermediary caches.
        self.send_header("Cache-Control", CACHE_CONTROL_NO_STORE)
        # Publish an explicit empty-body length.
        self.send_header("Content-Length", str(len(raw)))
        # Preserve hardened session and CSRF cookies when provider sign-in succeeds.
        for name, value in extra_headers or []:
            # Forward only application-owned response headers.
            self.send_header(name, value)
        # Finish the redirect headers without returning callback fields.
        self.end_headers()

    # Define the _handle_api function used by this module.
    def _handle_api(self):
        # Set request_id to the value needed for the next operation.
        request_id = os.urandom(4).hex()
        # Start protected logic so failures can be handled safely.
        try:
            # Set path to the value needed for the next operation.
            path = urlparse(self.path).path
            # Set body to the value needed for the next operation.
            body = self._read_body() if self.command in ("POST", "PUT", "PATCH", "DELETE") else {}
            # Set context to the value needed for the next operation.
            context = {"headers": self.headers, "client": self.client_address[0], "response_headers": [], "secure_cookie": False, "include_csrf_cookie": True, "session_samesite": "Lax"}
            # Branch when the request targets a protected API route.
            if not auth.is_public_api_path(path):
                # Resolve a root-managed monitor token only for the two read-only deployment probes.
                monitor_identity = auth.authenticate_monitor_headers(self.headers, path) if self.command == "GET" else None
                # Set session,user to the monitor identity or the normal browser/API session.
                session, user = monitor_identity or auth.authenticate_headers(self.headers)
                # Set context["session"] to the value needed for the next operation.
                context["session"] = session
                # Set context["user"] to the value needed for the next operation.
                context["user"] = user
                # Enforce Admin authorization centrally for every current and future Admin API.
                if path.startswith("/api/v1/admin/") or path.startswith("/api/v2/admin/"):
                    # Reject normal authenticated users before route dispatch can expose data or mutate state.
                    auth.require_admin(user)
                # Bind normal-user game and autoplay payloads to their authenticated player.
                if not auth.is_admin(user):
                    # Store the binding so query parsing also replaces stale player ids.
                    context["bound_player_id"] = user["player_id"]
                    # Block gameplay, autoplay, and wallet mutation until required terms are accepted.
                    if auth.terms_status(user)["required"] and (path.startswith("/api/v1/games/") or path.startswith("/api/v1/autoplay/") or path == "/api/v2/me/tokens/add"):
                        # Raise a forbidden response while leaving read-only terms/current-user routes available.
                        raise ForbiddenError("Terms acceptance is required before play")
                    # Keep global bot configuration and bot-account actions behind the Admin role.
                    if self.command != "GET" and path.startswith("/api/v1/bots/"):
                        # Reject normal users before shared bot configuration can be changed.
                        raise ForbiddenError("Admin role is required for bot account configuration")
                    # Replace caller-provided player ids for autoplay actions outside the game router.
                    if path.startswith("/api/v1/autoplay/"):
                        # Force the public action to operate on the authenticated player's wallet and state.
                        body["player_id"] = user["player_id"]
                    # Match player-resource paths so cross-user wallet reads and writes fail closed.
                    player_match = re.match(r"^/api/v1/players/([^/]+)", path)
                    # Reject a normal user attempting to address another player's resource.
                    if player_match and player_match.group(1) != user["player_id"]:
                        # Raise the standard forbidden envelope without confirming private player details.
                        raise ForbiddenError("Player resource is outside the authenticated session")
            # Set logger.info("api_request", request_id to the value needed for the next operation.
            logger.info("api_request", request_id=request_id, method=self.command, path=path)
            # Set data to the value needed for the next operation.
            data = ROUTER.dispatch(self.command, self.path, body, context)
            # Return a callback completion redirect without placing callback query data in a JSON envelope.
            if context.get("redirect"):
                # Send only the prevalidated same-origin location and application cookies.
                return self._send_redirect(str(context["redirect"]), context.get("response_headers"))
            # Execute this statement as part of the module's documented control flow.
            self._send_json(200, {"ok": True, "data": data}, context.get("response_headers"))
        # Handle the expected failure path for the protected logic.
        except CasinoError as e:
            # Set logger.warning("api_error", request_id to the value needed for the next operation.
            logger.warning("api_error", request_id=request_id, code=e.code, path=path)
            # Execute this statement as part of the module's documented control flow.
            self._send_json(e.status, {"ok": False, "error": {"code": e.code, "message": e.message, "details": e.details}})
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Record no exception text, callback query, body, header, or credential value.
            logger.error("api_exception", request_id=request_id, path=locals().get("path", "/api"))
            # Return a sanitized envelope so filesystem paths and exception text never reach the client. (SESSION-007, SEC-010)
            self._send_json(500, {"ok": False, "error": {"code": "INTERNAL_ERROR", "message": "Internal server error", "details": {"request_id": request_id}}})

    # Define the do_GET function used by this module.
    def do_GET(self):
        # Branch when the following condition is true.
        if urlparse(self.path).path.startswith("/api/") or urlparse(self.path).path in {"/healthz", "/readyz"}:
            # Return the computed value to the caller.
            return self._handle_api()
        # Return the computed value to the caller.
        return self._serve_static()

    # Define the do_POST function used by this module.
    def do_POST(self):
        # Return the computed value to the caller.
        return self._handle_api()

    # Define the do_DELETE function used by this module.
    def do_DELETE(self):
        # Return the computed value to the caller.
        return self._handle_api()

    # Define do_PATCH so published v2 Admin update routes are reachable.
    def do_PATCH(self):
        # Return the authenticated API response for the PATCH request.
        return self._handle_api()

    # Define the _serve_static function used by this module.
    def _serve_static(self):
        # Set parsed to the value needed for the next operation.
        parsed = urlparse(self.path)
        # Set path to the value needed for the next operation.
        path = parsed.path
        # Accept the public-shell marker only when no cookie or authorization proof accompanies it. (PWA-002)
        public_pwa_shell = self.headers.get(PWA_PUBLIC_SHELL_HEADER) == "1" and not self.headers.get("Cookie") and not self.headers.get("Authorization")
        # Enforce Admin authorization before reading any dedicated Admin HTML or JavaScript bytes. (AUTH-008)
        if path in ADMIN_STATIC_PATHS:
            # Start protected authentication so static authorization failures use the standard envelope.
            try:
                # Resolve the active browser session from the same cookie contract used by APIs.
                _session, user = auth.authenticate_headers(self.headers)
                # Reject normal players before the filesystem target is selected or read.
                auth.require_admin(user)
            # Convert missing, expired, or non-Admin sessions into the canonical public error response.
            except CasinoError as error:
                # Return no Admin bytes while preserving the standard failure-envelope contract.
                self._send_json(error.status, {"ok": False, "error": {"code": error.code, "message": error.message, "details": error.details}})
                # Stop static routing after the authorization boundary returns its response.
                return
        # Branch when the following condition is true.
        if path in ("/", ""):
            # Set path to the value needed for the next operation.
            path = "/index.html"
        # Map the stable API-documentation URL to its same-origin packaged Swagger shell.
        elif path in ("/api-docs", "/api-docs/"):
            # Select the dedicated documentation entry document without a redirect.
            path = "/api-docs.html"
        # Branch when the prior condition failed and this condition is true.
        elif path == "/admin":
            # Set path to the value needed for the next operation.
            path = "/admin.html"
        # Identify a reviewed public OpenAPI contract request before choosing its root.
        openapi_request = path.startswith("/openapi/")
        # Resolve the relative path beneath only the selected immutable root.
        rel = Path(path.removeprefix("/openapi/") if openapi_request else path.lstrip("/"))
        # Branch when the following condition is true.
        if rel.parts and rel.parts[0] == "web":
            # Set rel to the value needed for the next operation.
            rel = Path(*rel.parts[1:])
        # Resolve the target beneath contracts/openapi or packaged web assets as requested.
        target = ((OPENAPI_DIR if openapi_request else WEB_DIR) / rel).resolve()
        # Start protected logic so failures can be handled safely.
        try:
            # Execute this statement as part of the module's documented control flow.
            target.relative_to((OPENAPI_DIR if openapi_request else WEB_DIR).resolve())
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Execute this statement as part of the module's documented control flow.
            self.send_error(403); return
        # Return missing or non-YAML contracts without falling back to the application shell.
        if openapi_request and (not target.is_file() or target.suffix != ".yaml"):
            # Publish one ordinary not-found response without exposing filesystem structure.
            self.send_error(404)
            # Stop before any unrelated packaged file is read.
            return
        # Fall back only ordinary application routes to the public shell.
        if not target.exists() or not target.is_file():
            # Set target to the value needed for the next operation.
            target = WEB_DIR / "index.html"
        # Set content to the value needed for the next operation.
        content = target.read_bytes()
        # Publish YAML contracts explicitly while retaining ordinary MIME discovery.
        ctype = "application/yaml; charset=utf-8" if openapi_request else (mimetypes.guess_type(str(target))[0] or "application/octet-stream")
        # Execute this statement as part of the module's documented control flow.
        self.send_response(200)
        # Execute this statement as part of the module's documented control flow.
        self.send_header("Content-Type", ctype)
        # Execute this statement as part of the module's documented control flow.
        self.send_header("Content-Length", str(len(content)))
        # Prevent HTML and lazy JavaScript from surviving a source or route reload. (CORE-026)
        self.send_header("Cache-Control", CACHE_CONTROL_NO_STORE)
        # Bootstrap or refresh one host-only CSRF cookie on the non-Admin application shell. (OAUTH-008)
        if target.name == "index.html" and urlparse(self.path).path not in ADMIN_STATIC_PATHS and not public_pwa_shell:
            # Reuse an active session's distinct CSRF value without authenticating a context-bound guest cookie.
            bootstrap_token = auth.csrf_token_for_session_cookie(self.headers)
            # Reuse a bounded anonymous double-submit cookie when no session is active.
            if not bootstrap_token:
                # Read only the named host cookie rather than the complete Cookie header.
                existing = cookie_value(self.headers, CSRF_COOKIE)
                # Accept only generated-shape bounded proof lengths.
                bootstrap_token = existing if 32 <= len(existing) <= 128 else new_csrf_token()
            # Emit the local-development non-Secure host-only CSRF cookie.
            cookie_name, cookie_header = csrf_cookie_header(bootstrap_token, "Lax", False)
            # Add the exact application-owned Set-Cookie header.
            self.send_header(cookie_name, cookie_header)
        # Finish once so an abandoned static request cannot destabilize sibling lazy-module delivery.
        return self._finish_response(content)

# Define the serve function used by this module.
def serve(host=DEFAULT_HOST, port=DEFAULT_PORT, open_browser=True):
    # Reject unsafe public bootstrap configuration before creating or migrating any runtime state.
    validate_bootstrap_for_startup(host)
    # Execute this statement as part of the module's documented control flow.
    ensure_dirs()
    # Execute this statement as part of the module's documented control flow.
    migrate_from_v7_if_needed()
    # Bootstrap default players through the active provider when storage is fresh.
    bootstrap_players(players.default_players)
    # Bootstrap the default administrator after player storage is initialized.
    auth.bootstrap_admin_from_env()
    # Set httpd to the value needed for the next operation.
    httpd = CasinoThreadingHTTPServer((host, port), Handler)
    # Set url to the value needed for the next operation.
    url = f"http://{host}:{port}/"
    # Set logger.info("server_start", url to the value needed for the next operation.
    logger.info("server_start", url=url, version=APP_VERSION)
    # Branch when the following condition is true.
    if open_browser:
        # Execute this statement as part of the module's documented control flow.
        threading.Timer(0.75, lambda: webbrowser.open(url)).start()
    # Write diagnostic output so the current operation can be inspected.
    print(f"Virtual Casino Simulator v{APP_VERSION} running at {url}")
    # Write diagnostic output so the current operation can be inspected.
    print(f"Admin console: {url}admin")
    # Write diagnostic output so the current operation can be inspected.
    print("Press Ctrl+C to stop.")
    # Start protected logic so failures can be handled safely.
    try:
        # Execute this statement as part of the module's documented control flow.
        httpd.serve_forever()
    # Handle the expected failure path for the protected logic.
    except KeyboardInterrupt:
        # Intentionally leave this block empty.
        pass
    # Run cleanup logic regardless of success or failure.
    finally:
        # Execute this statement as part of the module's documented control flow.
        logger.info("server_stop")
        # Execute this statement as part of the module's documented control flow.
        httpd.server_close()

# Define the main function used by this module.
def main(argv=None):
    # Set parser to the value needed for the next operation.
    parser = argparse.ArgumentParser()
    # Set parser.add_argument("--host", default to the value needed for the next operation.
    parser.add_argument("--host", default=DEFAULT_HOST)
    # Set parser.add_argument("--port", type to the value needed for the next operation.
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    # Set parser.add_argument("--no-browser", action to the value needed for the next operation.
    parser.add_argument("--no-browser", action="store_true")
    # Set args to the value needed for the next operation.
    args = parser.parse_args(argv)
    # Set serve(args.host, args.port, open_browser to the value needed for the next operation.
    serve(args.host, args.port, open_browser=not args.no_browser)

# Branch when the following condition is true.
if __name__ == "__main__":
    # Execute this statement as part of the module's documented control flow.
    main()
