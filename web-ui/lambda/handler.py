"""Hosted GovEase web UI: one Lambda behind a function URL.

GET  /      -> the bilingual, right-to-left chat page
POST /upload-url -> validates the token, returns a presigned S3 PUT URL for a citizen's new PDF
POST /chat  -> validates the Cognito access token, invokes the AgentCore runtime, returns the reply
The browser signs in directly with Cognito, so this function never sees a password.
"""
from __future__ import annotations

import base64
import json
import os
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config

REGION = os.environ["AWS_REGION"]
RUNTIME_ARN = os.environ["RUNTIME_ARN"]
CLIENT_ID = os.environ["COGNITO_CLIENT_ID"]
USER_POOL_ID = os.environ.get("USER_POOL_ID", "")
HTML = Path(__file__).with_name("index.html").read_text(encoding="utf-8")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
CITIZEN_ID = re.compile(r"^CIT-\d{1,6}$")

cognito = boto3.client("cognito-idp", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION, config=Config(signature_version="s3v4"))
ssm = boto3.client("ssm", region_name=REGION)


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


def _invoke_runtime(token: str, session_id: str, payload: dict[str, Any]) -> str:
    """Call the runtime's HTTPS endpoint with the caller's Cognito token (the runtime uses a JWT authorizer, not SigV4)."""
    url = (
        f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/"
        f"{urllib.parse.quote(RUNTIME_ARN, safe='')}/invocations?qualifier=DEFAULT"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
        },
    )
    with urllib.request.urlopen(req, timeout=110) as resp:
        return resp.read().decode("utf-8")


def _bearer_user(event: dict[str, Any]) -> dict[str, Any] | None:
    """Return the Cognito user for the request's bearer token, or None."""
    auth = (event.get("headers") or {}).get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        return cognito.get_user(AccessToken=auth[7:])
    except Exception:
        return None


def _upload_url(event: dict[str, Any]) -> dict[str, Any]:
    """Presign a PUT into the documents bucket under citizens/<id>/, so the browser uploads straight to S3."""
    if _bearer_user(event) is None:
        return _json(401, {"error": "Sign in first"})
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    data = json.loads(raw)
    citizen_id = str(data.get("citizen_id", "")).strip().upper()
    if not CITIZEN_ID.match(citizen_id):
        return _json(400, {"error": "Enter a valid citizen id, for example CIT-03"})
    name = re.sub(r"[^A-Za-z0-9._-]", "_", str(data.get("filename", "document")))[-80:]
    if not name.lower().endswith(".pdf"):
        return _json(400, {"error": "Only PDF files are accepted"})
    bucket = ssm.get_parameter(Name="/app/workshop/govease/documents-bucket")["Parameter"]["Value"]
    key = f"citizens/{citizen_id}/{secrets.token_hex(4)}-{name}"
    url = s3.generate_presigned_url(
        "put_object", Params={"Bucket": bucket, "Key": key, "ContentType": "application/pdf"}, ExpiresIn=300)
    return _json(200, {"url": url, "key": key})


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
    try:
        body = _invoke_runtime(auth[7:], session_id, {"prompt": prompt, "actor_id": actor})
    except urllib.error.HTTPError as exc:
        return _json(502, {"error": f"Agent returned {exc.code}"})
    reply, tools = _collect(body)
    return _json(200, {"reply": reply or body[:2000], "tools": tools})


def _uaepass_login(event: dict[str, Any]) -> dict[str, Any]:
    """Simulated UAE PASS sign-in: create (or reuse) a Cognito user for the phone number and return a real token."""
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    digits = re.sub(r"\D", "", str(json.loads(raw).get("phone", "")))
    if not 8 <= len(digits) <= 15:
        return _json(400, {"error": "Enter a valid mobile number"})
    email = f"{digits}@uaepass.demo"
    # a fresh random password on every sign-in, so nothing reusable is stored anywhere
    password = "Aa1!" + secrets.token_urlsafe(24)
    try:
        cognito.admin_create_user(UserPoolId=USER_POOL_ID, Username=email, MessageAction="SUPPRESS",
                                  UserAttributes=[{"Name": "email", "Value": email}, {"Name": "email_verified", "Value": "true"}])
    except cognito.exceptions.UsernameExistsException:
        pass
    cognito.admin_set_user_password(UserPoolId=USER_POOL_ID, Username=email, Password=password, Permanent=True)
    auth = cognito.initiate_auth(ClientId=CLIENT_ID, AuthFlow="USER_PASSWORD_AUTH",
                                 AuthParameters={"USERNAME": email, "PASSWORD": password})
    return _json(200, {"token": auth["AuthenticationResult"]["AccessToken"], "actor": digits})


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "/")
    if method == "POST" and path.rstrip("/").endswith("/uaepass") and USER_POOL_ID:
        return _uaepass_login(event)
    if method == "POST" and path.rstrip("/").endswith("/upload-url"):
        return _upload_url(event)
    if method == "POST" and path.rstrip("/").endswith("/chat"):
        return _chat(event)
    if method == "GET":
        return _page()
    return _json(404, {"error": "Not found"})
