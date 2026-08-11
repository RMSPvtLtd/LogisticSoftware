from integrations.tracking.sapt import _parse_container_detail_table
from conftest import fixture_html


def test_parses_real_export_voyage_detail():
    detail = _parse_container_detail_table(fixture_html("sapt_container_details_xf.html"))

    assert detail is not None
    assert detail.owner == "EMC"
    assert detail.bl_number == "KPEXEF19204070826"
    assert detail.category == "EXPORT"
    assert detail.status_code == "XF"
    assert detail.vessel_voyage == "TS MUMBAI /   2605E"
    assert detail.eta == "20-AUG-26 02.30.00 AM"
    assert detail.gate_in_time == "08-AUG-26 10.22.33 AM"
    assert detail.origin == "PKSAP"
    assert detail.destination == "AUSYD"
    assert detail.line_seal_number == "EMCTKC4113"
    assert detail.current_position == "In Yard"
    assert detail.commodity == "MADE UPS"
    assert detail.weight == "13120"
    # SAPT's "N/A" placeholders normalize to None, not the literal string.
    assert detail.vir_number is None
    assert detail.discharge_time is None
    assert detail.custom_seal_number is None
    assert detail.present_holds is None
    # SAPT also uses a bare "," as a placeholder for this field specifically
    # -- must normalize to None too, not the literal comma.
    assert detail.security_seal_number is None


def test_parses_real_import_voyage_detail():
    detail = _parse_container_detail_table(fixture_html("sapt_container_details_if.html"))

    assert detail is not None
    assert detail.bl_number == "HZF2026050227"
    assert detail.category == "IMPORT"
    assert detail.status_code == "IF"
    assert detail.vir_number == "PKKHISAPT_300626171006"
    assert detail.discharge_time == "18-JUL-26 10.59.04 AM"
    assert detail.gate_out_time == "23-JUL-26 08.55.55 AM"
    assert detail.security_seal_number == "567890"
    assert detail.current_position == "Gate Out"
    assert detail.commodity == "POLISHED MARBLE SLABS  HS CODE: 68022100"


def test_missing_table_returns_none():
    assert _parse_container_detail_table("<html><body>Session expired</body></html>") is None


def test_empty_table_returns_none():
    html = '<table id="tblcntr"><tbody></tbody></table>'
    assert _parse_container_detail_table(html) is None
