"""Plain-Python implementations of the GovEase tools.

Shared by the in-process Strands tools (govease/tools.py) and the Gateway Lambda
(lambda_functions/govease/handler.py) so both paths run identical logic.
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from typing import Any

from boto3.dynamodb.types import TypeDeserializer

from . import documents
from .config import client, param

_deser = TypeDeserializer()


def _items(table_param: str, **scan_kwargs: Any) -> list[dict[str, Any]]:
    resp = client("dynamodb").scan(TableName=param(table_param), **scan_kwargs)
    return [{k: _deser.deserialize(v) for k, v in item.items()} for item in resp["Items"]]


def _business_days_after(start: date, days: int) -> date:
    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        # UAE weekend is Saturday and Sunday.
        if current.weekday() < 5:
            remaining -= 1
    return current


def get_citizen_profile(citizen_id: str) -> str:
    """Return the citizen's profile: name, preferred language (ar or en) and contact. Call this first."""
    resp = client("dynamodb").get_item(TableName=param("govease/citizens-table"), Key={"citizen_id": {"S": citizen_id}})
    if "Item" not in resp:
        return json.dumps({"error": f"No citizen with id {citizen_id}"})
    return json.dumps({k: _deser.deserialize(v) for k, v in resp["Item"].items()}, ensure_ascii=False)


def list_services() -> str:
    """List every government service with its department, required documents, fee and processing time in business days."""
    rows = _items("govease/services-table")
    for r in rows:
        r["fee"] = int(r["fee"])
        r["timeline_days"] = int(r["timeline_days"])
    return json.dumps(sorted(rows, key=lambda r: r["service_id"]), ensure_ascii=False)


def search_service_policy(query: str) -> str:
    """Search the official requirements Knowledge Base for eligibility rules, linked-process ordering and rejection reasons."""
    resp = client("bedrock-agent-runtime").retrieve(
        knowledgeBaseId=param("govease/knowledge-base-id"),
        retrievalQuery={"text": query},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 3}},
    )
    chunks = [r["content"]["text"] for r in resp["retrievalResults"]]
    return "\n\n---\n\n".join(chunks) or "No policy text found."


def list_citizen_documents(citizen_id: str) -> str:
    """List the documents a citizen has uploaded to the secure documents bucket. Returns S3 keys to pass to extract_document."""
    resp = client("s3").list_objects_v2(Bucket=param("govease/documents-bucket"), Prefix=f"citizens/{citizen_id}/")
    keys = [o["Key"] for o in resp.get("Contents", []) if o["Key"].lower().endswith(".pdf")]
    return json.dumps({"citizen_id": citizen_id, "documents": keys})


def extract_document(document_key: str) -> str:
    """Read an uploaded PDF with Amazon Textract and return its type, fields, and validity flags (EXPIRED, EXPIRES_WITHIN_30_DAYS, VALID, ISSUED_MORE_THAN_3_MONTHS_AGO)."""
    try:
        result = documents.extract(document_key)
    except Exception as exc:  # surface the failure to the model instead of crashing the turn
        return json.dumps({"error": f"Could not extract {document_key}: {type(exc).__name__}"})
    return json.dumps(result, ensure_ascii=False)


def submit_application(
    citizen_id: str,
    service_id: str,
    document_keys: list[str],
    citizen_confirmed: bool,
    notes: str = "",
) -> str:
    """Submit an application to the responsible department and return the tracking id and expected completion date.
    Only call after the citizen has explicitly confirmed the plan; citizen_confirmed must be true."""
    if not citizen_confirmed:
        return json.dumps({"error": "Citizen has not confirmed. Present the plan, fees and timeline and ask for confirmation first."})
    services = {s["service_id"]: s for s in _items("govease/services-table")}
    if service_id not in services:
        return json.dumps({"error": f"Unknown service {service_id}"})
    svc = services[service_id]
    today = date.today()
    expected = _business_days_after(today, int(svc["timeline_days"]))
    application_id = f"APP-{random.randint(6000, 9999)}"
    item = {
        "application_id": {"S": application_id},
        "citizen_id": {"S": citizen_id},
        "service_id": {"S": service_id},
        "department": {"S": svc["department"]},
        "status": {"S": "SUBMITTED"},
        "submitted_date": {"S": today.isoformat()},
        "expected_completion": {"S": expected.isoformat()},
        "fee": {"N": str(int(svc["fee"]))},
        "documents": {"S": ",".join(document_keys)},
        "notes": {"S": notes[:500]},
    }
    client("dynamodb").put_item(TableName=param("govease/applications-table"), Item=item)
    return json.dumps(
        {
            "application_id": application_id,
            "service": svc["name"],
            "department": svc["department"],
            "status": "SUBMITTED",
            "fee": int(svc["fee"]),
            "submitted_date": today.isoformat(),
            "expected_completion": expected.isoformat(),
        },
        ensure_ascii=False,
    )


def check_application_status(citizen_id: str) -> str:
    """Return all applications for a citizen with days open and whether each one is overdue and needs a follow-up."""
    services = {s["service_id"]: s for s in _items("govease/services-table")}
    apps = _items(
        "govease/applications-table",
        FilterExpression="citizen_id = :c",
        ExpressionAttributeValues={":c": {"S": citizen_id}},
    )
    today = date.today()
    out = []
    for a in apps:
        svc = services.get(a["service_id"], {})
        days_open = (today - date.fromisoformat(str(a["submitted_date"]))).days
        timeline = int(svc.get("timeline_days", 0))
        overdue = a["status"] != "COMPLETED" and days_open > timeline
        out.append(
            {
                "application_id": a["application_id"],
                "service": svc.get("name", a["service_id"]),
                "department": a.get("department"),
                "status": a["status"],
                "submitted_date": a["submitted_date"],
                "expected_completion": a.get("expected_completion"),
                "days_open": days_open,
                "overdue": overdue,
                "action": "follow up with department" if overdue else "wait",
            }
        )
    return json.dumps(sorted(out, key=lambda x: x["submitted_date"], reverse=True), ensure_ascii=False)


def notify_citizen(citizen_id: str, message: str, language: str = "en") -> str:
    """Send a status update to the citizen through the notification service, translating with Amazon Translate to the citizen's language (ar or en) when needed."""
    text = message
    if language == "ar":
        text = client("translate").translate_text(Text=message, SourceLanguageCode="auto", TargetLanguageCode="ar")["TranslatedText"]
    client("sns").publish(
        TopicArn=param("govease/status-topic-arn"),
        Subject=f"GovEase update for {citizen_id}"[:100],
        Message=text,
    )
    return json.dumps({"sent": True, "language": language, "message": text}, ensure_ascii=False)

