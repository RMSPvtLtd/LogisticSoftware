"""Every business-tunable value used by pricing, quoting, and job numbering lives
here as a single named setting, never as a literal inline where it is used.
Changing a markup, a validity window, or a volumetric factor is an environment
change, not a code change.
"""

from functools import lru_cache
from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # PostgreSQL in production. Tests override this with a file-backed SQLite URL
    # via the get_settings dependency override in tests/conftest.py — nothing in
    # application code assumes which database is behind DATABASE_URL.
    database_url: str = "postgresql+psycopg://raaziq:raaziq@localhost:5432/raaziq"

    # Uniform markup applied to every applicable quote line item.
    #
    # This uniform markup across all charge kinds is an MVP simplification. A
    # future pricing model should support markup rules per charge kind.
    default_markup_percent: Decimal = Decimal("20")

    # How many days a freshly generated quote stays valid before lazy-expiry
    # treats it as expired.
    quote_validity_days: int = 14

    # Volumetric (dimensional) weight factors, expressed as kg per CBM. Mode-
    # specific because air, sea, and road carriers price dimensional weight
    # differently.
    volumetric_factor_air: Decimal = Decimal("167")
    volumetric_factor_sea: Decimal = Decimal("1000")
    volumetric_factor_road: Decimal = Decimal("333")

    # Job number format: {prefix}-{year}-{sequence zero-padded to `padding`}.
    job_number_prefix: str = "RAZ"
    job_number_padding: int = 5

    # Browser origins allowed to call the API.
    cors_origins: str = "http://localhost:5173"

    # Actor name recorded on manually-triggered status events until real
    # authentication replaces the current_actor dependency.
    default_actor: str = "ops"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
