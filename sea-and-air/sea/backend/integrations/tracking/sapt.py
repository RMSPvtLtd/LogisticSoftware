"""SAPT (South Asia Pakistan Terminals) connector. Isolates every SAPT-
specific detail -- its endpoint shape, its HTML-wrapped-JSON response
format, its field names, its status codes -- behind the `TrackingProvider`
protocol. Nothing outside this module knows SAPT exists.

SAPT's ContainerHistory endpoint doesn't return clean JSON: it returns an
HTML fragment with a `<script>` block containing `var data = {...};`, where
`data._jsonArray` is itself a JSON-encoded string containing the actual
records (double-encoded). This has been manually verified to work with a
plain server-side GET carrying no cookies and no browser session state.
"""

import json
import logging
import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from config import get_settings
from schemas.tracking import ContainerDetail, TrackingEvent, TrackingResult
from utils.errors import ContainerNotFound, ProviderResponseInvalid, ProviderUnavailable

logger = logging.getLogger(__name__)

TERMINAL_NAME = "South Asia Pakistan Terminals"

# Only mappings that have been genuinely verified against SAPT belong here
# (Phase 5). Until a code's meaning is confirmed, the raw code is shown
# as-is rather than guessed at -- see `_display_status`.
SAPT_STATUS_MAP: dict[str, str] = {}

# SAPT's own field names, kept private to this module. `_FIELD_TO_EVENT_TYPE`
# is deliberately narrow -- "pid" and "formatter" are SAPT-internal and are
# never surfaced (Phase 4).
_FIELD_TO_EVENT_TYPE: dict[str, str] = {
    "GATE In TIME": "Gate In",
    "GATE OUT TIME": "Gate Out",
    "LOADING TIME": "Loading",
    "DISCHARGING TIME": "Discharging",
}

_DATA_OBJECT_RE = re.compile(r"var\s+data\s*=\s*")

_TIMESTAMP_RE = re.compile(
    r"^(?P<day>\d{2})-(?P<mon>[A-Za-z]{3})-(?P<yr>\d{2})\s+"
    r"(?P<hh>\d{2})\.(?P<mm>\d{2})\.(?P<ss>\d{2})\s*(?P<ampm>AM|PM)$",
    re.IGNORECASE,
)

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _parse_sapt_timestamp(value: object) -> datetime | None:
    """Parses SAPT's "08-AUG-26 10.22.33 AM" format into a naive datetime.
    Returns None for null/"N/A"/empty/unparseable input rather than raising
    -- a timestamp SAPT can't give us is a normal "hasn't happened yet"
    case, not an error.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text.upper() in ("N/A", "NA"):
        return None
    match = _TIMESTAMP_RE.match(text)
    if not match:
        return None
    month = _MONTHS.get(match.group("mon").lower())
    if month is None:
        return None
    hour = int(match.group("hh")) % 12
    if match.group("ampm").upper() == "PM":
        hour += 12
    try:
        return datetime(
            year=2000 + int(match.group("yr")),
            month=month,
            day=int(match.group("day")),
            hour=hour,
            minute=int(match.group("mm")),
            second=int(match.group("ss")),
        )
    except ValueError:
        return None


def _display_status(status_code: str | None) -> str:
    if status_code is None:
        return "Unknown"
    return SAPT_STATUS_MAP.get(status_code, status_code)


def _extract_data_object(html: str) -> dict:
    """Locates `var data = {...};` in the response and parses just the
    JSON object value -- not the whole script, not a regex guess at where
    the object ends. Using json.JSONDecoder.raw_decode to parse from the
    matched position hands the "where does this JSON value end" problem to
    a real JSON parser (which correctly handles nested braces/strings)
    instead of a fragile HTML/regex assumption, per Phase 3.
    """
    match = _DATA_OBJECT_RE.search(html)
    if match is None:
        raise ProviderResponseInvalid("SAPT response did not contain the expected data object.")
    try:
        value, _ = json.JSONDecoder().raw_decode(html, match.end())
    except json.JSONDecodeError as exc:
        raise ProviderResponseInvalid("SAPT response's data object was not valid JSON.") from exc
    if not isinstance(value, dict):
        raise ProviderResponseInvalid("SAPT response's data object was not a JSON object.")
    return value


def _extract_records(data_object: dict) -> list[dict]:
    raw_json_array = data_object.get("_jsonArray")
    if not isinstance(raw_json_array, str):
        raise ProviderResponseInvalid("SAPT response was missing _jsonArray.")
    try:
        records = json.loads(raw_json_array)
    except json.JSONDecodeError as exc:
        raise ProviderResponseInvalid("SAPT's _jsonArray was not valid JSON.") from exc
    if not isinstance(records, list):
        raise ProviderResponseInvalid("SAPT's _jsonArray did not decode to a list.")
    return records


def _record_latest_timestamp(record: dict) -> datetime | None:
    """The most recent of a ContainerHistory record's own GATE/LOADING/
    DISCHARGING timestamps -- used both to pick which record's STATUS
    represents "current status" and to order per-voyage detail cards
    most-recent-first, so both agree on what "recent" means.
    """
    latest: datetime | None = None
    for field_name in _FIELD_TO_EVENT_TYPE:
        parsed = _parse_sapt_timestamp(record.get(field_name))
        if parsed is not None and (latest is None or parsed > latest):
            latest = parsed
    return latest


def _build_result(container_number: str, records: list[dict]) -> TrackingResult:
    events: list[tuple[datetime, TrackingEvent]] = []
    latest_status_code: str | None = None
    latest_status_at: datetime | None = None
    resolved_container_number = container_number

    for record in records:
        if not isinstance(record, dict):
            continue
        record_container_number = record.get("CONTAINER NO")
        if isinstance(record_container_number, str) and record_container_number.strip():
            resolved_container_number = record_container_number.strip()

        for field_name, event_type in _FIELD_TO_EVENT_TYPE.items():
            parsed = _parse_sapt_timestamp(record.get(field_name))
            if parsed is not None:
                events.append((parsed, TrackingEvent(type=event_type, timestamp=parsed.isoformat())))

        record_latest = _record_latest_timestamp(record)
        status_code = record.get("STATUS")
        if isinstance(status_code, str) and record_latest is not None:
            if latest_status_at is None or record_latest > latest_status_at:
                latest_status_at = record_latest
                latest_status_code = status_code

    # Most-recent-first, matching the rest of Raaziq's activity timelines.
    events.sort(key=lambda pair: pair[0], reverse=True)

    return TrackingResult(
        provider="SAPT",
        terminal=TERMINAL_NAME,
        container_number=resolved_container_number,
        status=_display_status(latest_status_code),
        status_code=latest_status_code,
        events=[event for _, event in events],
    )


# SAPT's own detail-table labels (exact text, including punctuation), kept
# private to this module -- maps to ContainerDetail's field names. This
# "Status" is per-voyage (each detail is one voyage/cycle) and can differ
# from TrackingResult's top-level status, which is the *overall* most
# recent one across every voyage -- both are kept, deliberately not merged.
_DETAIL_LABEL_TO_FIELD: dict[str, str] = {
    "Owner": "owner",
    "BL/ Shipping Bill No.": "bl_number",
    "Container Size/Type": "container_size_type",
    "Category": "category",
    "Status": "status_code",
    "Vessel Voyage": "vessel_voyage",
    "VIR No": "vir_number",
    "ETA": "eta",
    "ETD": "etd",
    "Discharge Time": "discharge_time",
    "Load Time": "load_time",
    "DO Issuance Date": "do_issuance_date",
    "DO Expiry Date": "do_expiry_date",
    "Gate In Time": "gate_in_time",
    "Gate Out Time": "gate_out_time",
    "Origin": "origin",
    "Destination": "destination",
    "Custom Seal No.": "custom_seal_number",
    "Line Seal No.": "line_seal_number",
    "Security Seal No.": "security_seal_number",
    "Other Seal No.": "other_seal_number",
    "Custom Status": "custom_status",
    "Current Position": "current_position",
    "Commodity": "commodity",
    "Weight": "weight",
    "Weighment": "weighment",
    "Scanning": "scanning",
    "Present Holds": "present_holds",
}


def _clean(value: str | None) -> str | None:
    """SAPT uses "N/A" (and sometimes a bare ",") for "no value" -- normalize
    every such placeholder to None so the frontend has one consistent way to
    tell "not applicable" from "a real value", rather than needing to know
    SAPT's specific placeholder spellings.
    """
    if value is None:
        return None
    text = value.strip()
    if not text or text.upper() in ("N/A", "NA") or text.strip(",") == "":
        return None
    return text


def _parse_container_detail_table(html: str) -> ContainerDetail | None:
    """Parses the ContainerDetails endpoint's response -- genuine HTML (not
    JS-wrapped JSON like ContainerHistory), so a real HTML parser is used
    rather than a regex over markup, per Phase 3. Each row holds up to two
    label/value pairs: [label1, value1, spacer, label2, value2].
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="tblcntr")
    if table is None:
        return None

    fields: dict[str, str] = {}
    for row in table.find_all("tr"):
        cells = [cell.get_text(strip=True) for cell in row.find_all("td")]
        if len(cells) >= 2 and cells[0]:
            fields[cells[0]] = cells[1]
        if len(cells) >= 5 and cells[3]:
            fields[cells[3]] = cells[4]

    if not fields:
        return None

    return ContainerDetail(**{
        field_name: _clean(fields.get(label))
        for label, field_name in _DETAIL_LABEL_TO_FIELD.items()
    })


class SAPTProvider:
    name = "SAPT"

    def __init__(self) -> None:
        settings = get_settings()
        self._history_url = settings.sapt_base_url
        self._details_url = settings.sapt_details_url
        self._timeout = settings.sapt_request_timeout_seconds

    def get_container_history(self, container_number: str) -> TrackingResult:
        html = self._fetch_history(container_number)
        data_object = _extract_data_object(html)
        records = _extract_records(data_object)
        result = _build_result(container_number, records)
        # SAPT doesn't signal "no data" with an empty array -- for an
        # unrecognized container it returns one sentinel record instead
        # (observed: {"container_no": "N/A", "formatter": "yes"}, no
        # STATUS or timestamp fields). Rather than pattern-matching that
        # exact undocumented shape, treat "nothing usable came out of any
        # record" as the not-found signal, which covers both the empty-array
        # case and the sentinel-record case the same way.
        if not records or (result.status_code is None and not result.events):
            raise ContainerNotFound(f"No SAPT tracking records found for container {container_number}.")

        result.details = self._fetch_details(records)
        return result

    def _fetch_details(self, records: list[dict]) -> list[ContainerDetail]:
        """One ContainerDetails request per ContainerHistory record (each
        `pid` is a distinct voyage/cycle), ordered most-recent-first to
        match the events timeline. A single voyage's detail failing to
        fetch or parse doesn't fail the whole lookup -- the events/status
        already gathered from ContainerHistory are still returned; that
        voyage's card is just omitted (logged, not raised).
        """
        ordered_records = sorted(
            (r for r in records if isinstance(r, dict)),
            key=lambda r: _record_latest_timestamp(r) or datetime.min,
            reverse=True,
        )
        details: list[ContainerDetail] = []
        for record in ordered_records:
            pid = record.get("pid")
            if not isinstance(pid, str) or not pid.strip():
                continue
            try:
                detail_html = self._fetch_detail(pid.strip())
                detail = _parse_container_detail_table(detail_html)
            except (ProviderUnavailable, ProviderResponseInvalid) as exc:
                logger.warning("Skipping SAPT container detail for pid %s: %s", pid, exc)
                continue
            if detail is not None:
                details.append(detail)
        return details

    def _fetch_history(self, container_number: str) -> str:
        return self._request(
            "GET",
            self._history_url,
            params={"cntrNum": container_number, "BL": "_1", "method": "", "pTId": "SAPT"},
        )

    def _fetch_detail(self, pid: str) -> str:
        return self._request(
            "POST",
            self._details_url,
            data={"cntrPK": pid, "method": "C", "BU": "SAPT"},
        )

    def _request(self, method: str, url: str, **kwargs) -> str:
        # A fresh, unauthenticated client per request -- no cookie jar is
        # ever reused across calls, so there is structurally no way for a
        # SAPT-issued cookie (ARRAffinity, ApplicationGatewayAffinity, ...)
        # to be carried on a later request (Phase 10).
        try:
            with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                response = client.request(
                    method,
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; RaaziqTracker/1.0)",
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "text/html, */*",
                    },
                    **kwargs,
                )
        except httpx.TimeoutException as exc:
            logger.warning("SAPT request to %s timed out", url)
            raise ProviderUnavailable("Tracking information is temporarily unavailable.") from exc
        except httpx.HTTPError as exc:
            logger.warning("SAPT request to %s failed: %s", url, exc)
            raise ProviderUnavailable("Tracking information is temporarily unavailable.") from exc

        if response.status_code >= 400:
            logger.warning("SAPT returned HTTP %s for %s", response.status_code, url)
            raise ProviderUnavailable("Tracking information is temporarily unavailable.")

        return response.text
