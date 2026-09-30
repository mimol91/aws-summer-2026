"""GovEase agent entry point for AgentCore Runtime (POST /invocations, GET /ping)."""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from collections import OrderedDict
from typing import Any

from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager
from strands.tools.mcp import MCPClient
from strands_tools import current_time

from govease.config import REGION
from govease.tools import ALL_TOOLS
from model.load import load_model

app = BedrockAgentCoreApp()
log = app.logger


def _env_by_affix(prefix: str, suffix: str) -> str:
    """The AgentCore CLI injects resource identifiers as AGENTCORE_<KIND>_<NAME>_<FIELD>; find one by shape."""
    for key, value in os.environ.items():
        if key.startswith(prefix) and key.endswith(suffix) and value:
            return value
    return ""


GATEWAY_URL = _env_by_affix("AGENTCORE_GATEWAY_", "_URL") or os.environ.get("GATEWAY_URL", "")
CLIENT_ID = _env_by_affix("AGENTCORE_CREDENTIAL_", "_CLIENT_ID") or os.environ.get("GATEWAY_CLIENT_ID", "")
CLIENT_SECRET = _env_by_affix("AGENTCORE_CREDENTIAL_", "_CLIENT_SECRET") or os.environ.get("GATEWAY_CLIENT_SECRET", "")
TOKEN_ENDPOINT = os.environ.get("GATEWAY_TOKEN_ENDPOINT", "")
SCOPE = os.environ.get("GATEWAY_SCOPE", "")
MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID") or _env_by_affix("AGENTCORE_MEMORY_", "_ID") or os.environ.get("MEMORY_ID", "")
TOOL_MODE = os.environ.get("GOVEASE_TOOL_MODE", "auto")  # auto | gateway | local

DEFAULT_SYSTEM_PROMPT = """You are GovEase, a Dubai government services assistant. You help residents and business
owners complete government services end to end so they never make a wasted trip to a service centre.

Language: reply in the citizen's preferred language from their profile (Arabic for "ar", English for "en"),
unless the citizen writes in the other language. Keep answers short and structured.

Always follow this workflow, calling tools yourself rather than asking the citizen for information a tool can provide:
1. get_citizen_profile to learn their name and language.
2. search_service_policy to find the linked processes, ordering rules, eligibility and rejection reasons.
3. list_services for fees, timelines and required documents.
4. list_citizen_documents then extract_document on every uploaded document. Trust the validity flags: an EXPIRED
   supporting document or an address mismatch would cause a rejection, so add the prerequisite service that fixes it.
5. Build the plan: services in dependency order (identity, then address, then certificates, then the dependent
   service), total fees, and an end-to-end timeline in business days. Say plainly which rejection you prevented.
6. Present the plan and ask for explicit confirmation. Do NOT call submit_application until the citizen confirms.
7. After confirmation, submit every application in order, then notify_citizen with the tracking ids in their language.
8. For status questions use check_application_status and recommend a follow-up only for overdue applications.

Boundaries: you never alter, backdate or fabricate document contents or dates, never submit on someone's behalf
without confirmation, and never guess a fee or rule you did not retrieve. If a request crosses these lines, say so in
one sentence and offer the legitimate alternative. Do not repeat ID numbers back in full; show only the last 4 digits.
Fees are in AED.
"""

# ---------------------------------------------------------------------------
# Gateway (MCP) tools with a cached client-credentials token
# ---------------------------------------------------------------------------
_token_cache: dict[str, Any] = {"value": "", "expires_at": 0.0}


def _gateway_token() -> str:
    # Refresh a minute early so a token never expires mid-conversation.
    if _token_cache["value"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["value"]
    body = urllib.parse.urlencode(
        {"grant_type": "client_credentials", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "scope": SCOPE}
    ).encode()
    req = urllib.request.Request(TOKEN_ENDPOINT, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)
    _token_cache["value"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + int(data.get("expires_in", 3600))
    return _token_cache["value"]


def _gateway_client() -> MCPClient:
    return MCPClient(
        lambda: streamablehttp_client(GATEWAY_URL, headers={"Authorization": f"Bearer {_gateway_token()}"})
    )


def _build_tools() -> list[Any]:
    """Prefer Gateway tools; fall back to the identical in-process tools if the Gateway is unreachable."""
    gateway_configured = all([GATEWAY_URL, CLIENT_ID, CLIENT_SECRET, TOKEN_ENDPOINT, SCOPE])
    if TOOL_MODE == "local" or (TOOL_MODE == "auto" and not gateway_configured):
        log.info("Tool mode: local (%d tools)", len(ALL_TOOLS))
        return [current_time, *ALL_TOOLS]
    try:
        client = _gateway_client()
        with client:
            names = [t.tool_name for t in client.list_tools_sync()]
        log.info("Tool mode: gateway (%d tools)", len(names))
        return [current_time, client]
    except Exception as exc:  # a broken Gateway must not take the demo down
        log.warning("Gateway unavailable (%s); using local tools", type(exc).__name__)
        if TOOL_MODE == "gateway":
            raise
        return [current_time, *ALL_TOOLS]


def _session_manager(session_id: str, actor_id: str) -> AgentCoreMemorySessionManager | None:
    if not MEMORY_ID:
        return None
    config = AgentCoreMemoryConfig(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id=actor_id,
        retrieval_config={"/users/{actorId}/preferences": RetrievalConfig(top_k=5, relevance_score=0.4)},
    )
    return AgentCoreMemorySessionManager(agentcore_memory_config=config, region_name=REGION)


# ---------------------------------------------------------------------------
# One Agent per session (bounded LRU) so each conversation keeps its own history
# ---------------------------------------------------------------------------
def agent_factory():
    cache: OrderedDict[str, Agent] = OrderedDict()

    def get_or_create_agent(session_id: str, actor_id: str) -> Agent:
        if session_id in cache:
            cache.move_to_end(session_id)
            return cache[session_id]
        if len(cache) >= 128:
            cache.popitem(last=False)
        kwargs: dict[str, Any] = {}
        session_manager = None
        try:
            session_manager = _session_manager(session_id, actor_id)
        except Exception as exc:  # memory is an enhancement, never a hard dependency
            log.warning("Memory unavailable (%s); continuing without it", type(exc).__name__)
        if session_manager is not None:
            kwargs["session_manager"] = session_manager
        else:
            kwargs["conversation_manager"] = NullConversationManager()
        cache[session_id] = Agent(model=load_model(), system_prompt=DEFAULT_SYSTEM_PROMPT, tools=_build_tools(), **kwargs)
        return cache[session_id]

    return get_or_create_agent


get_or_create_agent = agent_factory()


def _extract_prompt(payload: dict) -> str:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")
    return prompt


@app.entrypoint
async def invoke(payload: dict, context: Any):
    session_id = getattr(context, "session_id", None) or "default-session"
    # The web UI sends the signed-in user's id so memory stays scoped per citizen.
    actor_id = str(payload.get("actor_id") or "user")
    log.info("Invoking agent for session %s", session_id)
    agent = get_or_create_agent(session_id, actor_id)
    prompt = _extract_prompt(payload)
    async for event in agent.stream_async(prompt):
        if not isinstance(event, dict) or "event" not in event:
            continue
        cbs = event["event"].get("contentBlockStart")
        if cbs is not None and not cbs.get("start"):
            continue
        yield event


if __name__ == "__main__":
    app.run()
