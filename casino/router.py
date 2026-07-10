# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import inspect
# Import required dependency so this module can use its public functions or constants.
import re
# Import required dependency so this module can use its public functions or constants.
from urllib.parse import urlparse, parse_qs
# Import required dependency so this module can use its public functions or constants.
from casino.errors import NotFoundError

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
        # Set parsed to the value needed for the next operation.
        parsed = urlparse(raw_path)
        # Set path to the value needed for the next operation.
        path = parsed.path
        # Set query to the value needed for the next operation.
        query = {k: v[-1] if v else "" for k, v in parse_qs(parsed.query).items()}
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
                    return route.handler(body or {}, query, context=context or {}, **kwargs)
                # Return the computed value to the caller.
                return route.handler(body or {}, query, **kwargs)
        # Raise an error so invalid input or state is reported explicitly.
        raise NotFoundError(f"No route for {method} {path}")
