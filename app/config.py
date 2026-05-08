import os
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")
VAPI_WEBHOOK_SECRET = os.getenv("VAPI_WEBHOOK_SECRET", "")
AIRTABLE_PAT = os.getenv("AIRTABLE_PAT", "")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "")
AIRTABLE_CALLERS_TABLE = os.getenv("AIRTABLE_CALLERS_TABLE", "Callers")
AIRTABLE_INTERACTIONS_TABLE = os.getenv("AIRTABLE_INTERACTIONS_TABLE", "Interactions")
