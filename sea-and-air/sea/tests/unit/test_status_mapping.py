"""Phase 5: status codes are shown as-is (a "neutral display status") until
their meaning has been genuinely verified and added to SAPT_STATUS_MAP.
This test suite exists to catch anyone tempted to guess a mapping without
updating it here -- SAPT_STATUS_MAP must stay empty (or contain only
mappings this test explicitly documents as verified).
"""

from integrations.tracking.sapt import SAPT_STATUS_MAP, _display_status


def test_no_unverified_status_mappings_exist():
    assert SAPT_STATUS_MAP == {}, (
        "A mapping was added to SAPT_STATUS_MAP without updating this test to "
        "document it as verified -- see Phase 5 of the SAPT integration plan."
    )


def test_unmapped_status_code_displays_as_itself():
    assert _display_status("XF") == "XF"
    assert _display_status("IF") == "IF"


def test_none_status_code_displays_as_unknown():
    assert _display_status(None) == "Unknown"
