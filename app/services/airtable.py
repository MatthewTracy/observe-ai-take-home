import logging
from datetime import datetime, timezone
from pyairtable import Api
from app.config import AIRTABLE_PAT, AIRTABLE_BASE_ID, AIRTABLE_CALLERS_TABLE, AIRTABLE_INTERACTIONS_TABLE
from app.models.schemas import CallerRecord, InteractionRecord, Sentiment

logger = logging.getLogger(__name__)

_api = Api(AIRTABLE_PAT)


def _callers_table():
    return _api.table(AIRTABLE_BASE_ID, AIRTABLE_CALLERS_TABLE)


def _interactions_table():
    return _api.table(AIRTABLE_BASE_ID, AIRTABLE_INTERACTIONS_TABLE)


def normalize_phone(phone: str) -> str:
    """Strip non-digit characters for consistent matching."""
    return "".join(c for c in phone if c.isdigit())


def lookup_caller(phone: str) -> CallerRecord | None:
    """Look up a caller by phone number in the Callers table."""
    table = _callers_table()
    normalized = normalize_phone(phone)

    # Search with Airtable formula — try exact match first
    formula = f"SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({{Phone}}, '-', ''), '(', ''), ')', ''), ' ', '') = '{normalized}'"
    records = table.all(formula=formula)

    if not records:
        logger.info(f"No caller found for phone: {normalized}")
        return None

    fields = records[0]["fields"]
    return CallerRecord(
        first_name=fields.get("First Name", ""),
        last_name=fields.get("Last Name", ""),
        phone=fields.get("Phone", ""),
        claim_status=fields.get("Claim Status", "Unknown"),
        claim_id=fields.get("Claim ID", ""),
        policy_number=fields.get("Policy Number", ""),
    )


def log_interaction(
    caller_name: str,
    phone: str,
    summary: str,
    sentiment: Sentiment,
    authenticated: bool,
) -> str:
    """Write a post-call interaction record to the Interactions table."""
    table = _interactions_table()
    record = table.create(
        {
            "Caller Name": caller_name,
            "Phone": phone,
            "Summary": summary,
            "Sentiment": sentiment.value.capitalize(),
            "Timestamp": datetime.now(timezone.utc).isoformat(),
            "Authenticated": authenticated,
        }
    )
    record_id = record["id"]
    logger.info(f"Logged interaction {record_id} for {caller_name}")
    return record_id
