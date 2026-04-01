"""
Seed the Airtable Callers table with sample data.

Usage:
    python -m scripts.seed_airtable

Requires AIRTABLE_PAT and AIRTABLE_BASE_ID in .env.
The Callers table must already exist in your Airtable base with these fields:
  - First Name (Single line text)
  - Last Name (Single line text)
  - Phone (Phone number)
  - Claim Status (Single select: Approved, Pending, Requires Documentation)
  - Claim ID (Single line text)
  - Policy Number (Single line text)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from pyairtable import Api

AIRTABLE_PAT = os.getenv("AIRTABLE_PAT", "")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "")
TABLE_NAME = os.getenv("AIRTABLE_CALLERS_TABLE", "Callers")

SAMPLE_CALLERS = [
    {
        "First Name": "Sarah",
        "Last Name": "Johnson",
        "Phone": "(555) 123-4567",
        "Claim Status": "Approved",
        "Claim ID": "CLM-2024-001",
        "Policy Number": "POL-88210",
    },
    {
        "First Name": "Michael",
        "Last Name": "Chen",
        "Phone": "(555) 234-5678",
        "Claim Status": "Pending",
        "Claim ID": "CLM-2024-002",
        "Policy Number": "POL-77432",
    },
    {
        "First Name": "Emily",
        "Last Name": "Rodriguez",
        "Phone": "(555) 345-6789",
        "Claim Status": "Requires Documentation",
        "Claim ID": "CLM-2024-003",
        "Policy Number": "POL-66198",
    },
    {
        "First Name": "James",
        "Last Name": "Williams",
        "Phone": "(555) 456-7890",
        "Claim Status": "Approved",
        "Claim ID": "CLM-2024-004",
        "Policy Number": "POL-55321",
    },
    {
        "First Name": "Priya",
        "Last Name": "Patel",
        "Phone": "(555) 567-8901",
        "Claim Status": "Pending",
        "Claim ID": "CLM-2024-005",
        "Policy Number": "POL-44567",
    },
    {
        "First Name": "David",
        "Last Name": "Thompson",
        "Phone": "(555) 678-9012",
        "Claim Status": "Requires Documentation",
        "Claim ID": "CLM-2024-006",
        "Policy Number": "POL-33890",
    },
]


def main():
    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        print("Error: Set AIRTABLE_PAT and AIRTABLE_BASE_ID in your .env file.")
        sys.exit(1)

    api = Api(AIRTABLE_PAT)
    table = api.table(AIRTABLE_BASE_ID, TABLE_NAME)

    print(f"Seeding {len(SAMPLE_CALLERS)} callers into '{TABLE_NAME}'...")

    for caller in SAMPLE_CALLERS:
        record = table.create(caller)
        print(f"  Created: {caller['First Name']} {caller['Last Name']} -> {record['id']}")

    print("Done! Sample callers have been added to Airtable.")


if __name__ == "__main__":
    main()
