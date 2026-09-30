from __future__ import annotations

from strands import tool

from . import core


@tool
def get_citizen_profile(citizen_id: str) -> str:
    """Return the citizen's profile: name, preferred language (ar or en) and contact. Call this first."""
    return core.get_citizen_profile(citizen_id)


@tool
def list_services() -> str:
    """List every government service with its department, required documents, fee and processing time in business days."""
    return core.list_services()


@tool
def search_service_policy(query: str) -> str:
    """Search the official requirements Knowledge Base for eligibility rules, linked-process ordering and rejection reasons."""
    return core.search_service_policy(query)


@tool
def list_citizen_documents(citizen_id: str) -> str:
    """List the documents a citizen has uploaded to the secure documents bucket. Returns S3 keys to pass to extract_document."""
    return core.list_citizen_documents(citizen_id)


@tool
def extract_document(document_key: str) -> str:
    """Read an uploaded PDF with Amazon Textract and return its type, fields, and validity flags (EXPIRED, EXPIRES_WITHIN_30_DAYS, VALID, FRESH_PROOF_OF_ADDRESS, ISSUED_MORE_THAN_3_MONTHS_AGO)."""
    return core.extract_document(document_key)


@tool
def submit_application(
    citizen_id: str,
    service_id: str,
    document_keys: list[str],
    citizen_confirmed: bool,
    notes: str = "",
) -> str:
    """FINAL ACTION: submit an application to the responsible department and return the tracking id and expected completion date.
    Only call after the citizen has explicitly confirmed the plan; citizen_confirmed must be true."""
    return core.submit_application(citizen_id, service_id, document_keys, citizen_confirmed, notes)


@tool
def check_application_status(citizen_id: str) -> str:
    """Return all applications for a citizen with days open and whether each one is overdue and needs a follow-up."""
    return core.check_application_status(citizen_id)


@tool
def notify_citizen(citizen_id: str, message: str, language: str = "en") -> str:
    """Send a status update to the citizen through the notification service, translating with Amazon Translate to the citizen's language (ar or en) when needed."""
    return core.notify_citizen(citizen_id, message, language)


ALL_TOOLS = [
    get_citizen_profile,
    list_services,
    search_service_policy,
    list_citizen_documents,
    extract_document,
    submit_application,
    check_application_status,
    notify_citizen,
]
