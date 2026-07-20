# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Define the CasinoError class that groups related behavior.
class CasinoError(Exception):
    # Define the __init__ function used by this module.
    def __init__(self, code: str, message: str, status: int = 400, details=None):
        # Execute this statement as part of the module's documented control flow.
        super().__init__(message)
        # Set self.code to the value needed for the next operation.
        self.code = code
        # Set self.message to the value needed for the next operation.
        self.message = message
        # Set self.status to the value needed for the next operation.
        self.status = status
        # Set self.details to the value needed for the next operation.
        self.details = details or {}

# Define the NotFoundError class that groups related behavior.
class NotFoundError(CasinoError):
    # Define the __init__ function used by this module.
    def __init__(self, message="Not found", details=None):
        # Execute this statement as part of the module's documented control flow.
        super().__init__("NOT_FOUND", message, 404, details)

# Define the ValidationError class that groups related behavior.
class ValidationError(CasinoError):
    # Define the __init__ function used by this module.
    def __init__(self, message="Invalid request", details=None):
        # Execute this statement as part of the module's documented control flow.
        super().__init__("VALIDATION_ERROR", message, 400, details)

# Define the UnauthorizedError class that groups related behavior.
class UnauthorizedError(CasinoError):
    # Define the __init__ function used by this module.
    def __init__(self, message="Authentication is required", details=None):
        # Execute this statement as part of the module's documented control flow.
        super().__init__("UNAUTHORIZED", message, 401, details)

# Define the ForbiddenError class that groups related behavior.
class ForbiddenError(CasinoError):
    # Define the __init__ function used by this module.
    def __init__(self, message="Permission denied", details=None):
        # Execute this statement as part of the module's documented control flow.
        super().__init__("FORBIDDEN", message, 403, details)

# Define the InsufficientFundsError class that groups related behavior.
class InsufficientFundsError(CasinoError):
    # Define the __init__ function used by this module.
    def __init__(self, message="Not enough balance for this action", details=None):
        # Execute this statement as part of the module's documented control flow.
        super().__init__("INSUFFICIENT_FUNDS", message, 400, details)

# Define the ConflictError class that groups related behavior.
class ConflictError(CasinoError):
    # Define the __init__ function used by this module.
    def __init__(self, message="Request conflicts with current state", details=None):
        # Execute this statement as part of the module's documented control flow.
        super().__init__("CONFLICT", message, 409, details)

# Define the RequestTooLargeError class for bounded production request bodies.
class RequestTooLargeError(CasinoError):
    # Initialize the fixed secret-safe payload-too-large response.
    def __init__(self, message="Request body is too large", details=None):
        # Publish HTTP 413 without reflecting the supplied length or body.
        super().__init__("REQUEST_TOO_LARGE", message, 413, details)

# Define the RateLimitError class for bounded restricted-preview request rates.
class RateLimitError(CasinoError):
    # Initialize the fixed secret-safe rate-limit response.
    def __init__(self, message="Request rate limit exceeded", details=None):
        # Publish HTTP 429 without exposing client identity or limiter state.
        super().__init__("RATE_LIMITED", message, 429, details)

# Define a stable provider-unavailable error without exposing transport or token details.
class ProviderUnavailableError(CasinoError):
    # Initialize the fixed retryable provider failure envelope.
    def __init__(self, message="Identity provider is temporarily unavailable", details=None):
        # Publish HTTP 503 while keeping provider responses and exception text private.
        super().__init__("PROVIDER_UNAVAILABLE", message, 503, details)
