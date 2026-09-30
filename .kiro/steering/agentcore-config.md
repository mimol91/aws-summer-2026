# AgentCore Configuration Rules

- Always run `agentcore validate` after editing `agentcore/agentcore.json`.
- In `agentcore.json`, runtime `envVars` are arrays: `[{ "name": "KEY", "value": "VALUE" }]`.
- Never write `${VARIABLE}` placeholders into `agentcore.json`. The CLI does not expand them, so the literal text ends up in the deployed policy and causes AccessDenied errors at invoke time. Resolve the real value first and write it literally.
- Resource identifiers (tables, buckets, knowledge base ids, roles) come from SSM parameters under `/app/workshop/`. Never hardcode an ARN.
- Never commit `cognito_config.json`, `.env.local`, `credentials`, or any token.
