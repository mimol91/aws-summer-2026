# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Hackathon project (AWS AgentCore workshop, Future Vision / GovEase track). **GovEase** is a Strands agent on Amazon Bedrock AgentCore Runtime that reads a citizen's documents, catches rejection causes, plans linked government services in dependency order, and submits them only after explicit consent. See `README.md` for the product story and "real vs mocked" table.

Top-level directories:

- `GovEase/` — the real project (AgentCore project + agent code + Gateway Lambda + demo scripts).
- `AgentCoreProject/` — throwaway sample agent produced by `setup.sh` (workshop warm-up). Not part of GovEase.
- `web-ui/lambda/` — current hosted web UI. `web-lambda/` is an older copy that has diverged (its `deploy.sh` reads `../GovEase/...`); confirm which one is wanted before editing either.
- `deliverables/` — submission artifacts (architecture diagram, demo script, `build_deck.py` → `demo.pptx`).
- `docs/workshop-build-path.md` — condensed workshop reference (CLI flow, Memory/Gateway/Guardrail wiring).
- `.kiro/steering/` — Kiro rules (Python style, Strands tools, AWS config); the conventions below come from there.

There is no test suite for the agent or the web UI. The only tests are the CDK template tests in `GovEase/agentcore/cdk/test/` (`npm test` there, jest).

## Conventions (from `.kiro/steering/`)

- **Region is always `us-west-2`.** Set `region_name` explicitly on every boto3 client; every `aws` CLI call needs `--region us-west-2 --no-cli-pager`.
- Type hints on function signatures; comments explain *why*. Keep code minimal, one concept per module.
- Agent tools use the Strands `@tool` decorator; the docstring is the description the model sees, so keep it precise.
- Resource identifiers (tables, buckets, KB, guardrail) are **never hardcoded** — they are read from SSM under `/app/workshop/...` via `govease.config.param()`.

## Commands

All agent commands run from `GovEase/` (or `GovEase/app/GovEaseAgent/`). The participant IAM role cannot bootstrap CDK or create a Gateway, so the runtime is deployed with the **starter toolkit**, not `agentcore deploy`:

```bash
cd GovEase
./scripts/seed_extra.sh                 # upload CIT-03's sample PDFs to S3, add SVC-TAX-CLEARANCE service
./scripts/reset_demo.sh                 # delete CIT-03's applications between demo takes

cd app/GovEaseAgent
uvx --from bedrock-agentcore-starter-toolkit agentcore deploy \
  --env AGENTCORE_MEMORY_ID=<memory id> --env GOVEASE_TOOL_MODE=local
uvx --from bedrock-agentcore-starter-toolkit agentcore invoke \
  '{"prompt": "My citizen id is CIT-03. Renew my trade license and update my address."}'

# local run without deploying: POST /invocations on :8080
GOVEASE_TOOL_MODE=local uv run python main.py
```

Native AgentCore CLI (used for config/validation; `agentcore.json` is the source of truth): `agentcore validate` after every edit to `GovEase/agentcore/agentcore.json`, plus `agentcore dev|status|logs|traces list`. Do not hand-edit generated CDK in `agentcore/cdk/`. Renaming a resource in `agentcore.json` destroys and recreates it. Details in `GovEase/AGENTS.md`.

Web UI (`web-ui/lambda/`): run locally with `AWS_REGION=us-west-2 USER_POOL_ID=... RUNTIME_ARN=... COGNITO_CLIENT_ID=... python local_server.py` (serves :8502). Deploy by zipping `handler.py index.html` and `aws lambda update-function-code --function-name AgentCore-govease-web ...` (see `web-ui/lambda/README.md`).

Regenerate sample PDFs: `python GovEase/scripts/gen_sample_docs.py` (output in `GovEase/data/samples/`).

## Architecture

**One tool implementation, two transports.** All eight tools live in `GovEase/app/GovEaseAgent/govease/core.py` and return JSON strings. They are exposed two ways:

1. `govease/tools.py` wraps each with Strands `@tool` for **in-process** use.
2. `GovEase/lambda_functions/govease/handler.py` routes the Gateway's `bedrockAgentCoreToolName` (prefixed `target___tool`) to the same `core` functions, with `tool_specs/govease.json` as the Gateway schema.

Adding or changing a tool means touching `core.py`, `tools.py`, the `TOOLS` map in the Lambda handler, **and** `tool_specs/govease.json`, and updating the system prompt in `main.py` if the workflow changes. The Lambda packages `govease/` — keep `core.py` free of runtime-only imports.

**Tool mode switch (`main.py`).** `GOVEASE_TOOL_MODE` = `local` (in-process tools), `gateway` (MCP client to AgentCore Gateway using a cached Cognito client-credentials token; fails hard), or `auto` (default in `agentcore.json`: use Gateway if its URL/credentials are in the environment, else fall back to local, including when the Gateway errors). Gateway identifiers come from `AGENTCORE_GATEWAY_*` / `AGENTCORE_CREDENTIAL_*` env vars injected by the CLI, with `GATEWAY_*` fallbacks.

**Agent lifecycle.** `main.py` keeps a bounded LRU (128) of Strands `Agent`s keyed by `session_id`, each with `NullConversationManager` and the system prompt encoding the workflow (profile → policy KB → services → extract documents → plan → **ask consent** → submit → notify). AgentCore Memory (USER_PREFERENCE, namespace `/users/{actorId}/preferences`) is attached when `AGENTCORE_MEMORY_ID` is set; memory failures must not break a session. The entrypoint streams Strands events and requires a non-empty string `prompt`; `actor_id` and `session_id` come from the payload.

**Consent guard.** `submit_application` requires `citizen_confirmed=True`; this is enforced both in the prompt and in `core.py`. Don't weaken either.

**Auth chain.** Web UI Lambda → simulated UAE PASS sign-in creates a Cognito user per phone → `/chat` invokes the AgentCore Runtime with the user's Cognito access token (runtime uses a Cognito JWT authorizer). The Gateway uses a separate M2M Cognito app client (`workshop-gateway-auth`).

**Data plane** (all from SSM): DynamoDB tables (services, citizens, applications), S3 documents bucket (`citizens/<id>/`), Bedrock Knowledge Base on S3 Vectors, Textract for extraction, Translate + SNS for notifications, Bedrock Guardrail on the model (`model/load.py`, with `model/mantle_compat.py`).

## Gotchas

- Demo citizen is `CIT-03` (Omar Haddad); scripts and the demo prompt assume it.
- `cognito_config.json`, `.env.local`, `credentials` are gitignored — never commit them. Memory IDs must be written as literals in `agentcore.json` env vars / `.env.local`, not `${VAR}` placeholders.
- `web-lambda/web.zip` is a committed build artifact; regenerate rather than hand-edit.
- Guardrails mask model output but logs keep originals: keep sensitive document fields out of prompts and logs.
