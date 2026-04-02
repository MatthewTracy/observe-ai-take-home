"""Tests for the Airtable service layer."""

from app.services.airtable import normalize_phone


def test_normalize_phone_with_parentheses():
    assert normalize_phone("(555) 123-4567") == "5551234567"


def test_normalize_phone_with_dashes():
    assert normalize_phone("555-123-4567") == "5551234567"


def test_normalize_phone_digits_only():
    assert normalize_phone("5551234567") == "5551234567"


def test_normalize_phone_with_spaces():
    assert normalize_phone("555 123 4567") == "5551234567"


def test_normalize_phone_with_country_code():
    assert normalize_phone("+1 (555) 123-4567") == "15551234567"


def test_normalize_phone_empty():
    assert normalize_phone("") == ""
