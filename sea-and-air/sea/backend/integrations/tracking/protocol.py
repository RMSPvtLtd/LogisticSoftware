"""The contract every tracking provider connector implements. The tracking
service (`services.tracking_service`) only ever calls `get_container_history`
through this shape -- it has no idea SAPT, or any other provider, exists.
Adding KICT, QICT, a shipping line, or customs later means writing a new
module here that satisfies this same Protocol and registering it in the
service's provider selection, nothing else in the application changes.
"""

from typing import Protocol

from schemas.tracking import TrackingResult


class TrackingProvider(Protocol):
    """A provider that can look up a container's tracking history.
    `get_container_history` returns a fully normalized `TrackingResult` --
    normalization is the connector's responsibility, not the caller's, so
    the service layer never touches provider-specific field names.

    Raises (from `utils.errors`):
        ContainerNotFound        -- reached the provider; it has no records
                                     for this container.
        ProviderUnavailable       -- couldn't reach the provider at all
                                     (DNS/connection/timeout/HTTP error).
        ProviderResponseInvalid   -- reached the provider; its response
                                     didn't match the expected shape.
    """

    name: str

    def get_container_history(self, container_number: str) -> TrackingResult: ...
