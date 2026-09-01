"""Domain exceptions raised by the service layer. Each maps to exactly one
HTTP status, and that mapping is registered once in `main` as centralized
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
    """Missing, invalid, or expired worker/customer credentials or token, or
    the account is deactivated."""

    http_status = 401


class InvalidDocument(DomainError):
    """An uploaded document failed validation (wrong content type, not a
    real PDF, empty, or exceeds the size limit)."""

    http_status = 422


class InvalidPasswordChange(DomainError):
    """A password-change request failed validation: current password wrong,
    confirmation mismatch, or new password too weak."""

    http_status = 422


class ShipmentHasInvoice(DomainError):
    """A shipment cannot be permanently deleted while any quote on its
    inquiry has an invoice (draft, issued, or cancelled) -- invoices are
    financial records that must never silently disappear. Cancel the
    shipment instead if it needs to stop being active."""

    http_status = 409


class InvalidCancellation(DomainError):
    """A cancellation was attempted with a blank reason, on an entity that's
    already cancelled/not cancellable, or on an invalid state otherwise."""

    http_status = 409


class TooManyAttempts(DomainError):
    """Too many failed sign-in attempts from this source for this account
    within the lockout window (see utils.rate_limit)."""

    http_status = 429


class DuplicateCustomerEmail(DomainError):
    """A customer with this email already exists. Raised proactively by
    `services.customers.create_customer` so the caller gets a specific,
    actionable message (and the existing customer's id) instead of the
    generic IntegrityError 409."""

    http_status = 409

    def __init__(self, message: str, *, customer_id: int, customer_name: str):
        super().__init__(message)
        self.customer_id = customer_id
        self.customer_name = customer_name


class InvalidRateCard(DomainError):
    """A rate card was created or updated with invalid data: no breaks, an
    empty description on a charge, or valid_until before valid_from."""

    http_status = 422


class InvalidMoneyAmount(DomainError):
    """A combination of individually-valid monetary values produces an
    invalid result -- e.g. a discount larger than the amount being
    discounted, which would yield a negative total. 422 rather than 409:
    the request body is what's unprocessable, not the entity's state."""

    http_status = 422


class EmailNotConfigured(DomainError):
    """No RESEND_API_KEY is configured for this deployment -- emailing a
    quote/invoice is unavailable. Deliberately not a boot-time failure (see
    config.Settings.resend_api_key); every other route still works fine."""

    http_status = 422


class EmailSendFailed(DomainError):
    """The configured email provider rejected the send or was unreachable."""

    http_status = 502
