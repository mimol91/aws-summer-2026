# Project Conventions

This project is an agentic AI solution built with the Strands Agents SDK and the AgentCore CLI.

## Python Style

- Always include type hints on function signatures and variable declarations where the type is not obvious.
- Add short explanatory comments that describe *why*, not just *what*, especially for non-obvious logic.
- Keep code minimal and focused on the concept being demonstrated — avoid boilerplate, unnecessary abstractions, or premature generalization.

```python
# Good: type hints + brief why-comment
def fetch_document(bucket: str, key: str) -> str:
    # retrieve raw text so the agent can reason over it
    ...
```

## Strands Agent Tools

- Define all agent tools using the Strands `@tool` decorator pattern.
- The docstring on a `@tool` function is the tool description surfaced to the model — keep it clear and concise.

```python
from strands import tool

@tool
def get_weather(city: str) -> str:
    """Return current weather conditions for the given city."""
    ...
```

## AWS Configuration

- All AWS operations must target the **us-west-2** region.
- Every AWS CLI command must include the `--no-cli-pager` flag to prevent output from blocking execution.

```bash
# Always include --region and --no-cli-pager
aws s3 ls s3://my-bucket --region us-west-2 --no-cli-pager
```

- In Python (boto3), set the region explicitly on each client/resource:

```python
import boto3

s3 = boto3.client("s3", region_name="us-west-2")
```

## Code Focus

- Each script or module should demonstrate one clear concept.
- Avoid mixing concerns — keep agent definition, tool definitions, and invocation in separate, clearly labelled sections or files.
