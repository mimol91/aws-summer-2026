"""Hosted GovEase web UI: one Lambda behind a function URL.

GET  /      -> the bilingual, right-to-left chat page
POST /chat  -> validates the Cognito access token, invokes the AgentCore runtime, returns the reply
The browser signs in directly with Cognito, so this function never sees a password.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import boto3

REGION = os.environ["AWS_REGION"]
RUNTIME_ARN = os.environ["RUNTIME_ARN"]
CLIENT_ID = os.environ["COGNITO_CLIENT_ID"]
HTML = Path(__file__).with_name("index.html").read_text(encoding="utf-8")

cognito = boto3.client("cognito-idp", region_name=REGION)
runtime = boto3.client("bedrock-agentcore", region_name=REGION)


def _page() -> dict[str, Any]:
    config = json.dumps({"region": REGION, "clientId": CLIENT_ID})
    body = HTML.replace("<script src=", f"<script>window.GOVEASE_CONFIG={config};</script>\n<script src=", 1)
    return {"statusCode": 200, "headers": {"Content-Type": "text/html; charset=utf-8"}, "body": body}


def _json(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status, "headers": {"Content-Type": "application/json"}, "body": json.dumps(payload, ensure_ascii=False)}


def _collect(body: str) -> tuple[str, list[str]]:
    text, tools = [], []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        try:
            event = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue
        inner = event.get("event", {}) if isinstance(event, dict) else {}
        start = inner.get("contentBlockStart", {}).get("start", {})
        if start.get("toolUse"):
            tools.append(start["toolUse"].get("name", ""))
        delta = inner.get("contentBlockDelta", {}).get("delta", {})
        if "text" in delta:
            text.append(delta["text"])
    return "".join(text).strip(), tools


def _chat(event: dict[str, Any]) -> dict[str, Any]:
    auth = (event.get("headers") or {}).get("authorization", "")
    if not auth.startswith("Bearer "):
        return _json(401, {"error": "Sign in first"})
    try:
        user = cognito.get_user(AccessToken=auth[7:])
    except Exception:
        return _json(401, {"error": "Session expired, sign in again"})
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    data = json.loads(raw)
    prompt = str(data.get("prompt", "")).strip()
    if not prompt:
        return _json(400, {"error": "Empty message"})
    # actor id comes from the verified token, never from the client, so memory stays per user
    email = next((a["Value"] for a in user["UserAttributes"] if a["Name"] == "email"), user["Username"])
    actor = email.split("@")[0]
    session_id = str(data.get("session_id") or "")[:100]
    if len(session_id) < 33:
        return _json(400, {"error": "Invalid session"})
    resp = runtime.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        runtimeSessionId=session_id,
        runtimeUserId=actor,
        payload=json.dumps({"prompt": prompt, "actor_id": actor}).encode("utf-8"),
    )
    body = resp["response"].read().decode("utf-8")
    reply, tools = _collect(body)
    return _json(200, {"reply": reply or body[:2000], "tools": tools})


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "/")
    if method == "POST" and path.rstrip("/").endswith("/chat"):
        return _chat(event)
    if method == "GET":
        return _page()
    return _json(404, {"error": "Not found"})
