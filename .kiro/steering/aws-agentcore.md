# AWS, AgentCore & Strands Documentation Lookup

## Always Look Up Current Documentation First

Before writing any code that involves AWS services, AgentCore, or the Strands Agents SDK, **always use MCP tools to retrieve current documentation**. Do not rely on prior training knowledge for APIs, CLI commands, configuration schemas, or SDK method signatures — these change frequently.

### What to look up before coding

- **Strands Agents SDK**: tool decorator usage, agent initialization, built-in tools, memory/session config
- **AgentCore CLI**: `agentcore` commands, deployment config (`agentcore.yaml`), runtime options, observability setup
- **AWS services**: Bedrock model IDs, IAM policy syntax, service endpoint availability, SDK client constructors

### Why this matters

AgentCore and Strands are actively developed. Documentation retrieved at the time of coding reflects the actual current API, not a snapshot from training data.

---

## AWS Region

All AWS operations target **us-west-2**.

- Set the region explicitly in every AWS SDK client:
  ```python
  import boto3
  client = boto3.client("bedrock-runtime", region_name="us-west-2")
  ```
- Do not rely on environment defaults or profile-level region settings.

---

## AWS CLI

Always include `--no-cli-pager` on every AWS CLI command to prevent output from pausing in a pager:

```bash
aws bedrock list-foundation-models --region us-west-2 --no-cli-pager
aws iam get-role --role-name MyRole --no-cli-pager
```

---

## AgentCore CLI

Use the `agentcore` CLI for all deployment, runtime, and configuration tasks. Look up current subcommands via MCP tools before use. Example pattern:

```bash
agentcore deploy --config agentcore.yaml
agentcore status
agentcore logs --tail
```
