"""Generate synthetic Dubai-flavoured documents for the demo citizen (CIT-03, Omar Haddad).

Dates are chosen relative to today so the story holds: the trade license is inside its
30-day renewal window, the Ejari is fresh proof of the new address, and the tax clearance
certificate has quietly expired, which is the rejection the agent must catch.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

from fpdf import FPDF

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "data/samples")
TODAY = date.today()


def fmt(d: date) -> str:
    return d.strftime("%d %B %Y")


def build(name: str, title: str, ref: str, rows: list[tuple[str, str]], footer: str) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "GOVERNMENT OF DUBAI - DIGITAL SERVICES (SYNTHETIC SAMPLE)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, f"Reference No: {ref}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    for label, value in rows:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, f"{label}:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 5, footer + " Synthetic sample for workshop use. Not a real person or document.")
    OUT.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT / name))


OWNER = "Omar Haddad"
BUSINESS = "Deira Corner Bakery LLC"
OLD_ADDRESS = "Shop 4, Al Muraqqabat Street, Deira, Dubai"
NEW_ADDRESS = "Shop 12, Al Quoz Industrial Area 3, Dubai"

build(
    "emirates-id.pdf",
    "Emirates Identity Card",
    "EID-784-1986-2231",
    [
        ("Full Name", OWNER),
        ("ID Number", "784-1986-2231045-7"),
        ("Date of Birth", "03 May 1986"),
        ("Nationality", "Resident"),
        ("Issue Date", fmt(TODAY - timedelta(days=560))),
        ("Expiry Date", fmt(TODAY + timedelta(days=530))),
        ("Place of Issue", "Federal Authority for Identity and Citizenship, Dubai"),
    ],
    "A valid Emirates ID is required for all government services.",
)

build(
    "trade-license.pdf",
    "Trade License",
    "TL-771234",
    [
        ("Business Name", BUSINESS),
        ("License Type", "Commercial - Food Service"),
        ("License Holder", OWNER),
        ("National ID", "784-1986-2231045-7 (see ID document)"),
        ("Issue Date", fmt(TODAY - timedelta(days=345))),
        ("Expiry Date", fmt(TODAY + timedelta(days=20))),
        ("Issuing Department", "Department of Commerce"),
        ("Registered Address", OLD_ADDRESS),
        ("Status", "Active - eligible for renewal within 30 days of expiry"),
    ],
    "Renewal requires national ID, this existing license, and a current tax clearance certificate. A late fee applies after expiry and the license lapses after 90 days.",
)

build(
    "ejari-tenancy-contract.pdf",
    "Ejari Tenancy Contract",
    "EJ-2026-458812",
    [
        ("Tenant", OWNER),
        ("Landlord", "Al Quoz Commercial Properties LLC"),
        ("Property Address", NEW_ADDRESS),
        ("Property Use", "Commercial - Bakery"),
        ("Lease Term", "12 months"),
        ("Start Date", fmt(TODAY - timedelta(days=46))),
        ("End Date", fmt(TODAY + timedelta(days=319))),
        ("Annual Rent", "84,000"),
        ("Ejari Registration Date", fmt(TODAY - timedelta(days=45))),
    ],
    "A registered Ejari contract dated within the last 3 months is accepted as proof of address for an address change.",
)

build(
    "tax-clearance-certificate.pdf",
    "Tax Clearance Certificate",
    "TCC-2025-993104",
    [
        ("Issued To", BUSINESS),
        ("Tax Registration No", "TRN-100234567800003"),
        ("Assessment Period", "Fiscal Year 2025"),
        ("Outstanding Balance", "0.00"),
        ("Status", "Cleared - no outstanding liabilities"),
        ("Issue Date", fmt(TODAY - timedelta(days=383))),
        ("Valid Until", fmt(TODAY - timedelta(days=18))),
        ("Issuing Authority", "Federal Tax Authority"),
    ],
    "A valid tax clearance certificate is required to renew a trade license.",
)
print(f"Wrote 4 documents to {OUT}")
