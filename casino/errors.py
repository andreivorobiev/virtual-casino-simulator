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
