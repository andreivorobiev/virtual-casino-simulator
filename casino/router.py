# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import inspect
# Import required dependency so this module can use its public functions or constants.
import re
# Import required dependency so this module can use its public functions or constants.
from urllib.parse import urlparse, parse_qs
# Import required dependency so this module can use its public functions or constants.
from casino.errors import NotFoundError
# Import the shared resolver so every current and future game route is session-bound centrally.
from casino.core.request_player import resolve_authenticated_player

# Define the Route class that groups related behavior.
class Route:
    # Define the __init__ function used by this module.
    def __init__(self, method: str, pattern: str, handler):
        # Set self.method to the value needed for the next operation.
        self.method = method.upper()
        # Set self.pattern to the value needed for the next operation.
        self.pattern = pattern
        # Set self.handler to the value needed for the next operation.
        self.handler = handler
        # Set self.regex to the value needed for the next operation.
        self.regex = re.compile("^" + pattern + "$")

    # Define the match function used by this module.
    def match(self, method: str, path: str):
        # Branch when the following condition is true.
        if self.method != method.upper():
            # Return the computed value to the caller.
            return None
        # Return the computed value to the caller.
        return self.regex.match(path)

# Define the Router class that groups related behavior.
class Router:
    # Define the __init__ function used by this module.
    def __init__(self):
        # Set self.routes to the value needed for the next operation.
        self.routes = []

    # Define the add function used by this module.
    def add(self, method: str, pattern: str, handler):
        # Execute this statement as part of the module's documented control flow.
        self.routes.append(Route(method, pattern, handler))
        # Return the computed value to the caller.
        return handler

    # Define the get function used by this module.
    def get(self, pattern: str):
        # Define the deco function used by this module.
        def deco(fn):
            # Execute this statement as part of the module's documented control flow.
            self.add("GET", pattern, fn); return fn
        # Return the computed value to the caller.
        return deco

    # Define the post function used by this module.
    def post(self, pattern: str):
        # Define the deco function used by this module.
        def deco(fn):
            # Execute this statement as part of the module's documented control flow.
            self.add("POST", pattern, fn); return fn
        # Return the computed value to the caller.
        return deco

    # Define patch so v2 Admin updates can use their published HTTP method.
    def patch(self, pattern: str):
        # Define the decorator that registers a PATCH route.
        def deco(fn):
            # Register the handler and return it unchanged.
            self.add("PATCH", pattern, fn); return fn
        # Return the route decorator to the caller.
        return deco

    # Define the delete function used by this module.
    def delete(self, pattern: str):
        # Define the deco function used by this module.
        def deco(fn):
            # Execute this statement as part of the module's documented control flow.
            self.add("DELETE", pattern, fn); return fn
        # Return the computed value to the caller.
        return deco

    # Define the dispatch function used by this module.
    def dispatch(self, method: str, raw_path: str, body: dict | None = None, context: dict | None = None):
        # Normalize the mutable request body before shared resolver and route handlers use it.
        body = body or {}
        # Normalize request context so direct router tests receive the same resolver behavior.
        context = context or {}
        # Set parsed to the value needed for the next operation.
        parsed = urlparse(raw_path)
        # Set path to the value needed for the next operation.
        path = parsed.path
        # Set query to the value needed for the next operation.
        query = {k: v[-1] if v else "" for k, v in parse_qs(parsed.query).items()}
        # Apply the shared authenticated-player resolver to every game endpoint before dispatch.
        if path.startswith("/api/v1/games/"):
            # Resolve the session-bound player while preserving explicit Admin/test compatibility.
            player_id = resolve_authenticated_player(context, body, query)
            # Replace stale or malicious payload player ids with the resolved identity.
            body["player_id"] = player_id
            # Replace stale or malicious query player ids with the same resolved identity.
            query["player_id"] = player_id
            # Publish the resolution for future context-aware game handlers.
            context["resolved_player_id"] = player_id
        # Iterate through the collection to process each item.
        for route in self.routes:
            # Set m to the value needed for the next operation.
            m = route.match(method, path)
            # Branch when the following condition is true.
            if m:
                # Set kwargs to the value needed for the next operation.
                kwargs = m.groupdict()
                # Return the computed value to the caller.
                # Branch when the route handler accepts the request context.
                if "context" in inspect.signature(route.handler).parameters:
                    # Return the computed value to the caller.
                    return route.handler(body, query, context=context, **kwargs)
                # Return the computed value to the caller.
                return route.handler(body, query, **kwargs)
        # Raise an error so invalid input or state is reported explicitly.
        raise NotFoundError(f"No route for {method} {path}")
