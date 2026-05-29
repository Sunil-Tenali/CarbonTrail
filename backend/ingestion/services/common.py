import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation


def open_uploaded_csv(uploaded_file):
    """Open CSV file and return DictReader."""
    text_file = io.TextIOWrapper(uploaded_file.file, encoding="utf-8-sig")
    return csv.DictReader(text_file)


def get_first_value(row, possible_column_names):
    """
    Finds a value even if different CSVs use different column names.

    Example:
    facility_code, Facility Code, Plant, Werk
    may all mean the same thing.
    """
    normalized_row = {}

    for key, value in row.items():
        if key is None:
            continue

        normalized_row[key.strip().lower()] = value

    for column_name in possible_column_names:
        lookup_key = column_name.strip().lower()

        if lookup_key in normalized_row:
            value = normalized_row[lookup_key]
            return "" if value is None else str(value).strip()

    return ""


def parse_decimal(value):
    """Parse text numbers (handles comma/period variations). Returns None if invalid."""
    if value is None:
        return None

    cleaned = str(value).strip()

    if cleaned == "":
        return None

    try:
        if "," in cleaned and "." not in cleaned:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

        return Decimal(cleaned)

    except InvalidOperation:
        return None


def parse_date(value):
    """Parse date from multiple formats. Returns None if unparseable."""
    if value is None:
        return None

    cleaned = str(value).strip()

    if cleaned == "":
        return None

    supported_formats = [
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y%m%d",
    ]

    for date_format in supported_formats:
        try:
            return datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue

    return None


def status_from_issues(issues):
    """Map validation issues to record status: errors → invalid, warnings → suspicious, else valid."""
    if any(issue["severity"] == "error" for issue in issues):
        return "invalid"

    if any(issue["severity"] == "warning" for issue in issues):
        return "suspicious"

    return "valid"