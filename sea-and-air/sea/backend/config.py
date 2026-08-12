"""Every tunable value for the sea tracker lives here, never as a literal
inline where it's used -- changing a timeout, a cache window, or a provider
URL is an environment change, not a code change.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Browser origins allowed to call this API. In practice the air
    # frontend's dev server proxies /sea-api/* to this backend server-side
    # (see air/frontend/vite.config.ts), so the browser itself never makes
    # a cross-origin request here -- this exists as a direct-access
    # safeguard/default, not something the normal request path depends on.
    cors_origins: str = "http://localhost:5173"

    # SAPT (South Asia Pakistan Terminals) is the first tracking provider.
    # Its base URL is configurable rather than hardcoded in the connector so
    # it can be pointed at a staging endpoint, or swapped for an official
    # API base URL later, without a code change (see integrations/tracking/sapt.py).
    sapt_base_url: str = "https://www.sapt.com.pk/Enquiries/ContainerHistory"
    # The per-voyage detail table (owner, BL, vessel/voyage, ETA/ETD, seals,
    # commodity, ...) is a second, separate endpoint keyed by the `pid` each
    # ContainerHistory record carries -- not part of the history response.
    sapt_details_url: str = "https://www.sapt.com.pk/Enquiries/ContainerDetails"
    sapt_request_timeout_seconds: float = 10.0

    # How long an identical container lookup is served from cache before
    # hitting the provider again. Short by design (Phase 9: on-demand
    # tracking, not polling) -- just enough to absorb a user refreshing or
    # double-submitting the same query.
    tracking_cache_ttl_seconds: int = 120

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
