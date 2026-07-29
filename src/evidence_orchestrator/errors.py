"""Domain-specific exceptions."""


class EFOError(Exception):
    """Base error for user-facing orchestration failures."""


class ConfigurationError(EFOError):
    """Workspace or agent configuration is invalid."""


class AuthorizationError(EFOError):
    """An actor attempted an operation outside its role."""


class TransitionError(EFOError):
    """A task state transition is not permitted."""


class LeaseError(EFOError):
    """A task lease is absent, expired, or owned by another worker."""


class EvidenceError(EFOError):
    """A report or evidence bundle does not satisfy its preregistered gates."""


class IntegrityError(EFOError):
    """The append-only ledger or a projected task record is inconsistent."""


class LockTimeout(EFOError):
    """A workspace lock could not be acquired in time."""
