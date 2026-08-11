"""Container number validation. ISO 6346 shipping containers are identified
by 4 uppercase letters (owner code + equipment category) followed by 7
digits (serial + check digit) -- e.g. CAAU2314798. This validates the
*format* only, not the ISO 6346 check-digit algorithm: a format-valid but
check-digit-wrong number should still reach the provider and come back
"not found" rather than being rejected client-side on a heuristic we're not
fully confident in.
"""

import re

from utils.errors import InvalidContainerNumber

_CONTAINER_NUMBER_RE = re.compile(r"^[A-Z]{4}[0-9]{7}$")


def normalize_container_number(raw: str) -> str:
    """Validates and normalizes (trims, uppercases) a container number.
    Raises InvalidContainerNumber if the format doesn't match ISO 6346's
    4-letters-then-7-digits shape -- covers empty input, wrong length, and
    obviously malformed strings without needing separate checks for each.
    """
    candidate = (raw or "").strip().upper()
    if not _CONTAINER_NUMBER_RE.match(candidate):
        raise InvalidContainerNumber("Please enter a valid container number.")
    return candidate
