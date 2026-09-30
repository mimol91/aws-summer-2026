"""AgentCore Gateway Lambda target for the GovEase tools.

The Gateway passes the tool arguments as the event and the tool name in the client
context. Each tool delegates to govease.core so the Lambda and the in-process agent
share one implementation.
"""
from __future__ import annotations

import json
from typing import Any

from govease import core

TOOLS = {
    "get_citizen_profile": core.get_citizen_profile,
    "list_services": core.list_services,
    "search_service_policy": core.search_service_policy,
    "list_citizen_documents": core.list_citizen_documents,
    "extract_document": core.extract_document,
    "submit_application": core.submit_application,
    "check_application_status": core.check_application_status,
    "notify_citizen": core.notify_citizen,
}


def handler(event: dict[str, Any], context: Any) -> Any:
    raw = context.client_context.custom["bedrockAgentCoreToolName"]
    # Gateway prefixes the target name: "govease___extract_document".
    tool = raw.split("___")[-1] if "___" in raw else raw.split("__")[-1]
    if tool not in TOOLS:
        return {"error": f"Unknown tool {tool}"}
    result = TOOLS[tool](**(event or {}))
    # core functions return JSON strings; hand the Gateway structured JSON instead.
    try:
        return json.loads(result)
    except (TypeError, ValueError):
        return result
