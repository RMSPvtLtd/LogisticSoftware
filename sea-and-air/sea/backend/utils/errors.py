"""Domain exceptions raised by the service/provider layer. Each maps to
exactly one HTTP status, and that mapping is registered once in `main.create_app`
as a centralized exception handler -- no route wraps a call in its own
try/except. Provider connectors and the tracking service raise these instead
of doing HTTP-flavored things themselves.
"""


class DomainError(Exception):
    """Base for all domain errors. Not raised directly."""

    http_status: int = 400


class InvalidContainerNumber(DomainError):
    """The container number failed format validation before any provider
    was even contacted."""

    http_status = 422


class ContainerNotFound(DomainError):
    """The provider was contacted successfully and returned zero tracking
    records for this container -- a legitimate "nothing to show" result,
    not a failure."""

    http_status = 404


class ProviderUnavailable(DomainError):
    """The provider could not be reached or reported a failure at the
    transport level: DNS failure, connection refused, timeout, or a non-2xx
    HTTP status. Distinct from ProviderResponseInvalid, which means the
    provider *did* respond but its response couldn't be understood."""

    http_status = 503


class ProviderResponseInvalid(DomainError):
    """The provider responded successfully at the transport level, but its
    response didn't match the expected shape (missing data object, missing
    _jsonArray, malformed JSON, unexpected structure). Raised so the parser
    fails gracefully instead of letting an unrelated exception type (KeyError,
    JSONDecodeError, ...) leak past the provider boundary."""

    http_status = 503
