import pytest

from utils.errors import InvalidContainerNumber
from utils.validation import normalize_container_number


@pytest.mark.parametrize(
    "raw",
    [
        "CAAU2314798",
        "caau2314798",  # lowercase, normalized to upper
        "  CAAU2314798  ",  # surrounding whitespace, trimmed
    ],
)
def test_accepts_valid_container_numbers(raw):
    assert normalize_container_number(raw) == "CAAU2314798"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "CAAU231479",  # one digit short
        "CAAU23147980",  # one digit too many
        "CAA2314798",  # only 3 letters
        "12345678901",  # all digits, no letters
        "CAAU-2314-798",  # punctuation
        "CAAU 2314798",  # embedded whitespace
        "container",
    ],
)
def test_rejects_invalid_container_numbers(raw):
    with pytest.raises(InvalidContainerNumber):
        normalize_container_number(raw)
