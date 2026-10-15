"""Domain errors (rules.md section 6). Each has a stable `code`; routers map them to problem+json later."""
from __future__ import annotations


class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message or self.code)
        if code:
            self.code = code


class NotFound(DomainError):
    code = "not_found"


class ValidationFailed(DomainError):
    code = "validation_failed"


class InvalidTransition(DomainError):
    code = "invalid_transition"


class ExternalServiceError(DomainError):
    code = "external_service_error"
