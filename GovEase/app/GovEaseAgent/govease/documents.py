from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, TypedDict

from .config import client, param

# Fields whose date tells us whether a document is still usable.
EXPIRY_KEYS = ("expiry date", "valid until", "end date")
ISSUE_KEYS = ("issue date", "start date", "registration date", "date registered")
DATE_FORMATS = ("%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y")


class ExtractedDocument(TypedDict):
    document_key: str
    document_type: str
    fields: dict[str, str]
    flags: list[str]
    days_until_expiry: int | None
    days_since_issue: int | None


def parse_date(text: str) -> date | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def textract_lines(bucket: str, key: str) -> list[str]:
    """Run synchronous Textract OCR over a single-page PDF in S3."""
    resp = client("textract").detect_document_text(Document={"S3Object": {"Bucket": bucket, "Name": key}})
    return [b["Text"] for b in resp["Blocks"] if b["BlockType"] == "LINE"]


def lines_to_fields(lines: list[str]) -> dict[str, str]:
    """Government forms print 'Label:' then the value on the next line, or 'Label: value' inline."""
    fields: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.endswith(":") and i + 1 < len(lines):
            fields[line[:-1].strip()] = lines[i + 1].strip()
            i += 2
            continue
        m = re.match(r"^([A-Za-z /()]+):\s+(.+)$", line)
        if m:
            fields[m.group(1).strip()] = m.group(2).strip()
        i += 1
    return fields


PROOF_OF_ADDRESS_TYPES = ("tenancy", "lease", "deed", "contract")


def evaluate_dates(fields: dict[str, str], today: date, doc_type: str = "") -> tuple[list[str], int | None, int | None]:
    """Derive validity flags so the agent does not have to do date arithmetic itself."""
    flags: list[str] = []
    days_until_expiry: int | None = None
    days_since_issue: int | None = None
    for label, value in fields.items():
        key = label.lower()
        parsed = parse_date(value)
        if parsed is None:
            continue
        if any(k in key for k in EXPIRY_KEYS):
            days_until_expiry = (parsed - today).days
        elif any(k in key for k in ISSUE_KEYS):
            days_since_issue = (today - parsed).days
    if days_until_expiry is not None:
        if days_until_expiry < 0:
            flags.append(f"EXPIRED {abs(days_until_expiry)} days ago")
        elif days_until_expiry <= 30:
            flags.append(f"EXPIRES_WITHIN_30_DAYS ({days_until_expiry} days left)")
        else:
            flags.append("VALID")
    # The 3-month freshness rule only applies to documents used as proof of address.
    is_proof_of_address = any(t in doc_type.lower() for t in PROOF_OF_ADDRESS_TYPES)
    if is_proof_of_address and days_since_issue is not None and days_since_issue > 90:
        flags.append("ISSUED_MORE_THAN_3_MONTHS_AGO (not acceptable as proof of address)")
    elif is_proof_of_address and days_since_issue is not None:
        flags.append("FRESH_PROOF_OF_ADDRESS (dated within 3 months)")
    return flags, days_until_expiry, days_since_issue


def extract(document_key: str, today: date | None = None) -> ExtractedDocument:
    bucket = param("govease/documents-bucket")
    lines = textract_lines(bucket, document_key)
    fields = lines_to_fields(lines)
    # The title is the first non-header line, e.g. "Trade License" or "Ejari Tenancy Contract".
    doc_type = next((l for l in lines[1:] if not l.startswith("Reference")), "Unknown")
    flags, until, since = evaluate_dates(fields, today or date.today(), doc_type)
    return ExtractedDocument(
        document_key=document_key,
        document_type=doc_type,
        fields=fields,
        flags=flags,
        days_until_expiry=until,
        days_since_issue=since,
    )
