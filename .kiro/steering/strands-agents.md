# Strands Agents SDK Patterns

## Documentation First

Before using any Strands SDK feature, look up the current API via MCP tools. The SDK is under active development — decorator signatures, agent config options, and built-in tool names change between releases.

---

## Tool Definition: @tool Decorator

All agent tools must use the `@tool` decorator from the Strands SDK. The function's docstring drives the tool description shown to the model, so make it clear and accurate.

```python
from strands import tool

@tool
def get_weather(location: str) -> str:
    """Return the current weather for the given location as a plain-text summary."""
    # Call an external weather API and return a short string
    return fetch_weather_api(location)
```

### Rules for tools

- **Type-hint every parameter and the return value** — Strands uses these to build the tool schema.
- **Docstring is required** — it becomes the tool's description; keep it one or two sentences.
- Keep each tool focused on a single action. Avoid multi-purpose tools.
- Return plain strings or JSON-serializable dicts. Avoid returning complex objects.

---

## Agent Initialization

```python
from strands import Agent
from strands.models import BedrockModel

# Point at the correct region and model
model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name="us-west-2",
)

agent = Agent(
    model=model,
    tools=[get_weather],          # pass tool functions directly
    system_prompt="You are a helpful assistant.",
)
```

- Always specify `region_name="us-west-2"` on the model.
- Pass only the tools the agent actually needs — keep the tool list minimal.
- Look up available built-in tools (file I/O, HTTP, code execution) via MCP docs before adding them.

---

## Invoking the Agent

```python
# Simple single-turn call
response = agent("What is the weather in Seattle?")
print(response)
```

- For streaming or multi-turn conversations, look up the current Strands API before implementing.

---

## AgentCore Deployment

When deploying with AgentCore, the entry point exposed to the runtime must match what `agentcore.yaml` specifies. Look up the current handler signature via MCP tools before wiring up the deployment config.
