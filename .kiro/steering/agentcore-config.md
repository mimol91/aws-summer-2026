# AgentCore Configuration Rules

- Always run `agentcore validate` after editing `agentcore/agentcore.json`.
- In `agentcore.json`, runtime `envVars` are arrays: `[{ "name": "KEY", "value": "VALUE" }]`.
- Never write `${VARIABLE}` placeholders into `agentcore.json`. The CLI does not expand them, so the literal text ends up in the deployed policy and causes AccessDenied errors at invoke time. Resolve the real value first and write it literally.
- Resource identifiers (tables, buckets, knowledge base ids, roles) come from SSM parameters under `/app/workshop/`. Never hardcode an ARN.
- Never commit `cognito_config.json`, `.env.local`, `credentials`, or any token.

## Deployment reality in the workshop account (verified 2026-09-30)

- The participant role can only create IAM roles named `workshop-*`, `AgentCore*`, `AmazonBedrockAgentCore*` or `BedrockAgentCore*`, so `agentcore deploy` (Node CLI, CDK) fails at CDK bootstrap. Do not retry it.
- `bedrock-agentcore:CreateGateway` is denied. Tools run in-process (`GOVEASE_TOOL_MODE=local`); the Lambda `workshop-govease-tools` and `tool_specs/govease.json` stay Gateway-ready.
- Deploy the runtime from `GovEase/app/GovEaseAgent` with the Python starter toolkit:
  `uvx --from bedrock-agentcore-starter-toolkit agentcore deploy --env AGENTCORE_MEMORY_ID=govease_memory-K1OZQD4TfG --env GOVEASE_TOOL_MODE=local --auto-update-on-conflict`
- Runtime role: `AgentCore-govease-runtime`. Memory: `govease_memory-K1OZQD4TfG`. Config lives in `.bedrock_agentcore.yaml`.
- Local port 8080 is used by another app on this machine; test locally on 8090: `uv run python -c "import main; main.app.run(port=8090)"`.
