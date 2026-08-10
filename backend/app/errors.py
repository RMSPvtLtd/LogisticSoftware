"""Domain exceptions raised by the service layer. Each maps to exactly one
HTTP status, and that mapping is registered once in `app.main` as centralized
exception handlers — no endpoint wraps a service call in its own try/except.
Services raise these instead of doing HTTP-flavored things themselves, so the
service layer stays usable outside of a request (seed script, tests).
"""


class DomainError(Exception):
    """Base for all domain errors. Not raised directly."""

    http_status: int = 400


class NotFound(DomainError):
    """The requested resource does not exist."""

    http_status = 404


class NoApplicableRate(DomainError):
    """No rate card / break exists that covers the inquiry's lane, mode,
    weight, and volume."""

    http_status = 422


class InvalidQuoteState(DomainError):
    """The requested operation is not allowed for the quote's current
    status (e.g. editing a sent quote, sending an accepted quote)."""

    http_status = 409


class QuoteExpired(DomainError):
    """The quote's valid_until date has passed."""

    http_status = 409


class InvalidTransition(DomainError):
    """The requested stage change is not the shipment's immediate next
    stage (or the shipment is already delivered)."""

    http_status = 409


class InvalidCorrection(DomainError):
    """A stage correction was attempted with an invalid target stage or a
    blank reason, or the target equals the current stage."""

    http_status = 409


class AmbiguousTrackingReference(DomainError):
    """More than one shipment matches the tracking reference; the caller
    must not have one arbitrarily selected for them."""

    http_status = 409


class TrackingIngestionFailed(DomainError):
    """A tracking adapter returned a status that cannot be applied to the
    shipment (invalid or backwards stage). The shipment is left unchanged."""

    http_status = 422


class Unauthorized(DomainError):
    """Missing, invalid, or expired worker credentials/token, or the
    account is deactivated."""

    http_status = 401
