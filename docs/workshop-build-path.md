# Workshop build path (condensed reference)

Source: hackathon workshop pages. Region: us-west-2. Account resources are pre-provisioned; identifiers live in SSM under `/app/workshop/...`.

## Core loop (AgentCore CLI 0.31)

```bash
agentcore create --project-name <Name> --name <AgentName> --language Python --build CodeZip --protocol HTTP --framework Strands --model-provider Bedrock --memory none
cd <Name>
agentcore dev                      # local hot-reload server on :8080 with inspector
agentcore dev "one-shot prompt"    # no browser
agentcore deploy                   # CodeBuild builds image, provisions runtime (first run: minutes)
agentcore invoke --prompt "..."    # hits the deployed agent
agentcore validate                 # run after every edit to agentcore/agentcore.json
agentcore status
agentcore logs --since 30m --query "tool"
agentcore traces list && agentcore traces get <traceId>
```

Layout: `agentcore/` (deployment config + CDK), `app/<AgentName>/main.py` (entry point). Runtime contract: POST /invocations, GET /ping on port 8080.

## Tools and prompt
- `from strands import Agent, tool`; `@tool` functions need docstring + type hints. Built-ins from `strands_tools` (e.g. `current_time`).
- Keep `pyproject.toml` in sync; run `uv sync` after dependency changes.

## Memory
- `agentcore add` -> Memory (expiry 7d, strategy User preference), then `agentcore deploy`.
- Wire with `AgentCoreMemoryConfig(memory_id, session_id=context.session_id, actor_id=...)` and `AgentCoreMemorySessionManager` from `bedrock_agentcore.memory.integrations.strands`.
- Write the literal memory ID into `agentcore/.env.local` and runtime envVars in `agentcore/agentcore.json`. Never `${VAR}` placeholders.
- If AccessDenied on memory ops: runtime role may need `bedrock-agentcore:namespacePath` condition (StringLike) scoped to the memory ARN.

## Gateway (Lambda tools over MCP)
1. Lambda in `lambda_functions/<name>/handler.py` following the Gateway Lambda input/output format; identify tool via `bedrockAgentCoreToolName` in context. Deploy with role from SSM `/app/workshop/lambda/execution-role-arn`.
2. `tool_specs/<name>.json`: array of `{name, description, inputSchema}` (no outputSchema).
3. Cognito user pool `workshop-gateway-auth` with domain, resource server + custom scope, M2M app client (client_credentials). Save to `cognito_config.json` (gitignored).
4. `agentcore add` -> Gateway `workshop-gateway`, Custom JWT authorizer (discovery URL + client id). `agentcore add` -> Gateway Target (Lambda ARN + schema path). `agentcore deploy`.
5. Agent connects as MCP client: env `GATEWAY_CLIENT_ID/SECRET/TOKEN_ENDPOINT/SCOPE`, fetch JWT via client_credentials, Bearer token, cache/refresh.
- Gateway action names for policies: `TargetName___tool_name`.

## Web UI
- Shared Streamlit app (bilingual, RTL, accessible) downloaded to `web-ui/app.py`. Needs Runtime ARN, Cognito pool + client id. actor_id = email local-part; stable session id per browser session.
- Create a Cognito user in the same pool. Run: `streamlit run app.py --server.port 8501`.
- Hosted option: Lambda function URL (API Gateway is outside participant permissions). Keep it behind Cognito.

## Observability
- Enable CloudWatch Transaction Search (Application Signals -> Transaction Search, span ingestion) once, or the traces view stays empty.
- CloudWatch GenAI Observability -> Amazon Bedrock AgentCore tab -> Traces. Show a trajectory in the demo.

## Guardrails
- Guardrail id in SSM `/app/workshop/guardrails/guardrail-id`; pass id + version on the Bedrock model config (filters input and output).
- Guardrails mask model output but logs still hold originals: keep sensitive fields out of prompts and tool outputs.

## Optional depth (Technical Execution)
- Evaluations: `agentcore run eval --evaluator "Builtin.GoalSuccessRate" --evaluator "Builtin.Helpfulness" --evaluator "Builtin.ToolSelectionAccuracy"`; custom LLM-judge evaluator via `agentcore add evaluator`.
- Policies (Cedar, default deny, forbid overrides permit): `agentcore add policy-engine --name X --attach-to-gateways workshop-gateway --attach-mode LOG_ONLY|ENFORCE`; `agentcore add policy --name Y --engine X --source policies/y.cedar`.

## Submission
Required: source repo, 3-minute demo video, architecture diagram PDF. Optional: running URL, "what we would build next" note.

## Rubric
Customer Impact 30, Technical Execution and Agentic Depth 25, Innovation 20, Demo Quality 15, Regional Relevance 10.
