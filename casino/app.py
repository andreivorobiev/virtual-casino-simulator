# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import argparse
# Import required dependency so this module can use its public functions or constants.
import json
# Import required dependency so this module can use its public functions or constants.
import mimetypes
# Import required dependency so this module can use its public functions or constants.
import os
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
from casino.config import DEFAULT_HOST, DEFAULT_PORT, WEB_DIR, DATA_DIR, APP_VERSION
# Import required dependency so this module can use its public functions or constants.
from casino.router import Router
# Import required dependency so this module can use its public functions or constants.
from casino.errors import CasinoError, ValidationError
# Import required dependency so this module can use its public functions or constants.
from casino.core.state_store import ensure_dirs, migrate_from_v7_if_needed
# Import required dependency so this module can bootstrap whichever storage provider is configured.
from casino.core.storage import bootstrap_players, get_storage_provider
# Import required dependency so this module can use its public functions or constants.
from casino.core import logger, players, ledger, history, auth
# Import required dependency so this module can use its public functions or constants.
from casino.games.registry import list_games
# Import required dependency so this module can use its public functions or constants.
from casino.games.roulette.api import register as register_roulette
# Import required dependency so this module can use its public functions or constants.
from casino.games.slots.api import register as register_slots
# Import required dependency so this module can use its public functions or constants.
from casino.games.blackjack.api import register as register_blackjack
# Import required dependency so this module can use its public functions or constants.
from casino.games.baccarat.api import register as register_baccarat
# Import required dependency so this module can use its public functions or constants.
from casino.games.keno.api import register as register_keno
# Import required dependency so this module can use its public functions or constants.
from casino.games.bingo.api import register as register_bingo
# Import required dependency so this module can use its public functions or constants.
from casino.admin import register as register_admin
# Import required dependency so this module can use its public functions or constants.
from casino.bots.api import register as register_bots
# Import required dependency so this module can use its public functions or constants.
from casino.core import autoplay

# Define the build_router function used by this module.
def build_router() -> Router:
    # Set router to the value needed for the next operation.
    router = Router()

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/casino/games")
    # Define the games function used by this module.
    def games(body, query):
        # Return the computed value to the caller.
        return {"games": list_games()}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/casino/state")
    # Define the casino_state function used by this module.
    def casino_state(body, query):
        # Return the computed value to the caller.
        return {"version": APP_VERSION, "games": list_games(), "players": players.list_players(), "recent_history": history.recent_history(25), "recent_ledger": ledger.read_recent(limit=25)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/casino/reset")
    # Define the reset function used by this module.
    def reset(body, query):
        # Import required dependency so this module can use its public functions or constants.
        import shutil
        # Reset configured provider state before bootstrapping default players.
        get_storage_provider().reset()
        # Branch when the following condition is true.
        if DATA_DIR.exists():
            # Use this standard-library helper to perform the requested operation.
            shutil.rmtree(DATA_DIR)
        # Execute this statement as part of the module's documented control flow.
        ensure_dirs()
        # Bootstrap default players through the active provider after reset.
        players.save_players(players.default_players())
        # Execute this statement as part of the module's documented control flow.
        auth.bootstrap_admin_from_env()
        # Execute this statement as part of the module's documented control flow.
        logger.info("casino_reset")
        # Return the computed value to the caller.
        return {"games": list_games(), "players": players.list_players()}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/casino/history")
    # Define the get_history function used by this module.
    def get_history(body, query):
        # Return the computed value to the caller.
        return {"history": history.recent_history(int(query.get("limit", 100)), query.get("game") or None)}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/casino/logs/recent")
    # Define the get_logs function used by this module.
    def get_logs(body, query):
        # Set kind to the value needed for the next operation.
        kind = query.get("kind", "app")
        # Return the computed value to the caller.
        return {"logs": logger.recent(kind, int(query.get("limit", 50)))}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/players")
    # Define the get_players function used by this module.
    def get_players(body, query):
        # Return the computed value to the caller.
        return {"players": players.list_players()}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/players/(?P<player_id>[^/]+)")
    # Define the get_player function used by this module.
    def get_player(body, query, player_id):
        # Return the computed value to the caller.
        return {"player": players.get_player(player_id)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/players")
    # Define the create_player function used by this module.
    def create_player(body, query):
        # Return the computed value to the caller.
        return {"player": players.create_player(body.get("display_name", "Player"), body.get("type", "human"), float(body.get("balance", 5000)))}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/players/(?P<player_id>[^/]+)/add-money")
    # Define the add_money function used by this module.
    def add_money(body, query, player_id):
        # Set amount to the value needed for the next operation.
        amount = float(body.get("amount", 0))
        # Branch when the following condition is true.
        if amount <= 0:
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("Add-money amount must be positive")
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
        # Return the computed value to the caller.
        return {"logged": logger.client("client_event", **body)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v2/auth/login")
    # Define the auth_login function used by this module.
    def auth_login(body, query, context):
        # Prefer the explicit email field while preserving the published username alias for compatible clients.
        email = body.get("email") or body.get("username", "")
        # Authenticate the normalized email credential through the backend auth service.
        result = auth.login(email, body.get("password", ""), context.get("client", ""))
        # Execute this statement as part of the module's documented control flow.
        context.setdefault("response_headers", []).append(auth.cookie_header(result["session"]["token"]))
        # Return the computed value to the caller.
        return result

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v2/auth/logout")
    # Define the auth_logout function used by this module.
    def auth_logout(body, query, context):
        # Set token to the value needed for the next operation.
        token = auth.extract_bearer_token(context.get("headers", {})) or auth.extract_cookie_token(context.get("headers", {}))
        # Execute this statement as part of the module's documented control flow.
        context.setdefault("response_headers", []).append(auth.clear_cookie_header())
        # Return the computed value to the caller.
        return auth.logout(token)

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v2/auth/session")
    # Define the auth_session function used by this module.
    def auth_session(body, query, context):
        # Return the computed value to the caller.
        return auth.current_user_payload(context["session"], context["user"])

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v2/me")
    # Define the current_user function used by this module.
    def current_user(body, query, context):
        # Return the computed value to the caller.
        return auth.current_user_payload(context["session"], context["user"])

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v2/me/terms")
    # Define the current_user_terms function used by this module.
    def current_user_terms(body, query, context):
        # Return the computed value to the caller.
        return {"terms": auth.terms_status(context["user"])}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/autoplay/start")
    # Define the autoplay_start function used by this module.
    def autoplay_start(body, query):
        # Return the computed value to the caller.
        return {"session": autoplay.start(body.get("game_id"), body.get("player_id", "human"), body.get("speed", "medium"), int(body.get("round_limit", 25)), body.get("plan") or {}, body.get("limits") or {})}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/autoplay/stop")
    # Define the autoplay_stop function used by this module.
    def autoplay_stop(body, query):
        # Return the computed value to the caller.
        return {"session": autoplay.stop(body.get("autoplay_id"))}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/autoplay/complete")
    # Define the autoplay_complete function used by this module.
    def autoplay_complete(body, query):
        # Return the computed value to the caller.
        return {"session": autoplay.complete(body.get("autoplay_id"))}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/autoplay/tick")
    # Define the autoplay_tick function used by this module.
    def autoplay_tick(body, query):
        # Return the computed value to the caller.
        return {"session": autoplay.tick(body.get("autoplay_id"))}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/autoplay/finish-stop")
    # Define the autoplay_finish_stop function used by this module.
    def autoplay_finish_stop(body, query):
        # Return the computed value to the caller.
        return {"session": autoplay.finish_stop(body.get("autoplay_id"))}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/autoplay/stop-all")
    # Define the autoplay_stop_all function used by this module.
    def autoplay_stop_all(body, query):
        # Return the computed value to the caller.
        return {"sessions": autoplay.stop_all()}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/autoplay/sessions")
    # Define the autoplay_sessions function used by this module.
    def autoplay_sessions(body, query):
        # Return the computed value to the caller.
        return {"sessions": autoplay.list_sessions(query.get("active") == "1")}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/autoplay/sessions/(?P<autoplay_id>[^/]+)")
    # Define the autoplay_get_session function used by this module.
    def autoplay_get_session(body, query, autoplay_id):
        # Return the computed value to the caller.
        return {"session": autoplay.get_session(autoplay_id)}

    # Execute this statement as part of the module's documented control flow.
    register_bots(router)
    # Execute this statement as part of the module's documented control flow.
    register_roulette(router)
    # Execute this statement as part of the module's documented control flow.
    register_slots(router)
    # Execute this statement as part of the module's documented control flow.
    register_blackjack(router)
    # Execute this statement as part of the module's documented control flow.
    register_baccarat(router)
    # Execute this statement as part of the module's documented control flow.
    register_keno(router)
    # Execute this statement as part of the module's documented control flow.
    register_bingo(router)
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
        # Set logger.info("http_access", client to the value needed for the next operation.
        logger.info("http_access", client=self.client_address[0], message=fmt % args)

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
            return json.loads(raw.decode("utf-8"))
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Return the computed value to the caller.
            return {"_raw": raw.decode("utf-8", errors="replace")}

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
        self.send_header("Cache-Control", "no-store")
        # Iterate through the collection to process each item.
        for name, value in extra_headers or []:
            # Execute this statement as part of the module's documented control flow.
            self.send_header(name, value)
        # Execute this statement as part of the module's documented control flow.
        self.end_headers()
        # Execute this statement as part of the module's documented control flow.
        self.wfile.write(raw)

    # Define the _handle_api function used by this module.
    def _handle_api(self):
        # Set request_id to the value needed for the next operation.
        request_id = os.urandom(4).hex()
        # Start protected logic so failures can be handled safely.
        try:
            # Set body to the value needed for the next operation.
            body = self._read_body() if self.command in ("POST", "PUT", "DELETE") else {}
            # Set path to the value needed for the next operation.
            path = urlparse(self.path).path
            # Set context to the value needed for the next operation.
            context = {"headers": self.headers, "client": self.client_address[0], "response_headers": []}
            # Branch when the request targets a protected API route.
            if not auth.is_public_api_path(path):
                # Set session,user to the value needed for the next operation.
                session, user = auth.authenticate_headers(self.headers)
                # Set context["session"] to the value needed for the next operation.
                context["session"] = session
                # Set context["user"] to the value needed for the next operation.
                context["user"] = user
            # Set logger.info("api_request", request_id to the value needed for the next operation.
            logger.info("api_request", request_id=request_id, method=self.command, path=self.path)
            # Set data to the value needed for the next operation.
            data = ROUTER.dispatch(self.command, self.path, body, context)
            # Execute this statement as part of the module's documented control flow.
            self._send_json(200, {"ok": True, "data": data}, context.get("response_headers"))
        # Handle the expected failure path for the protected logic.
        except CasinoError as e:
            # Set logger.warning("api_error", request_id to the value needed for the next operation.
            logger.warning("api_error", request_id=request_id, code=e.code, message=e.message, path=self.path, details=e.details)
            # Execute this statement as part of the module's documented control flow.
            self._send_json(e.status, {"ok": False, "error": {"code": e.code, "message": e.message, "details": e.details}})
        # Handle the expected failure path for the protected logic.
        except Exception as e:
            # Set logger.error("api_exception", e, request_id to the value needed for the next operation.
            logger.error("api_exception", e, request_id=request_id, path=self.path)
            # Execute this statement as part of the module's documented control flow.
            self._send_json(500, {"ok": False, "error": {"code": "INTERNAL_ERROR", "message": str(e), "details": {"request_id": request_id}}})

    # Define the do_GET function used by this module.
    def do_GET(self):
        # Branch when the following condition is true.
        if urlparse(self.path).path.startswith("/api/"):
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

    # Define the _serve_static function used by this module.
    def _serve_static(self):
        # Set parsed to the value needed for the next operation.
        parsed = urlparse(self.path)
        # Set path to the value needed for the next operation.
        path = parsed.path
        # Branch when the following condition is true.
        if path in ("/", ""):
            # Set path to the value needed for the next operation.
            path = "/index.html"
        # Branch when the prior condition failed and this condition is true.
        elif path == "/admin":
            # Set path to the value needed for the next operation.
            path = "/admin.html"
        # Set rel to the value needed for the next operation.
        rel = Path(path.lstrip("/"))
        # Branch when the following condition is true.
        if rel.parts and rel.parts[0] == "web":
            # Set rel to the value needed for the next operation.
            rel = Path(*rel.parts[1:])
        # Set target to the value needed for the next operation.
        target = (WEB_DIR / rel).resolve()
        # Start protected logic so failures can be handled safely.
        try:
            # Execute this statement as part of the module's documented control flow.
            target.relative_to(WEB_DIR.resolve())
        # Handle the expected failure path for the protected logic.
        except Exception:
            # Execute this statement as part of the module's documented control flow.
            self.send_error(403); return
        # Branch when the following condition is true.
        if not target.exists() or not target.is_file():
            # Set target to the value needed for the next operation.
            target = WEB_DIR / "index.html"
        # Set content to the value needed for the next operation.
        content = target.read_bytes()
        # Set ctype to the value needed for the next operation.
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        # Execute this statement as part of the module's documented control flow.
        self.send_response(200)
        # Execute this statement as part of the module's documented control flow.
        self.send_header("Content-Type", ctype)
        # Execute this statement as part of the module's documented control flow.
        self.send_header("Content-Length", str(len(content)))
        # Execute this statement as part of the module's documented control flow.
        self.end_headers()
        # Execute this statement as part of the module's documented control flow.
        self.wfile.write(content)

# Define the serve function used by this module.
def serve(host=DEFAULT_HOST, port=DEFAULT_PORT, open_browser=True):
    # Execute this statement as part of the module's documented control flow.
    ensure_dirs()
    # Execute this statement as part of the module's documented control flow.
    migrate_from_v7_if_needed()
    # Bootstrap default players through the active provider when storage is fresh.
    bootstrap_players(players.default_players)
    # Bootstrap the default administrator after player storage is initialized.
    auth.bootstrap_admin_from_env()
    # Set httpd to the value needed for the next operation.
    httpd = ThreadingHTTPServer((host, port), Handler)
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
