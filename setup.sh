#!/usr/bin/env bash
# Predefined sample agent setup. Fixed sequence so everyone gets the same neutral
# Strands code agent with two tools. Requires the AgentCore CLI (@aws/agentcore,
# Node 20+) and AWS credentials for us-west-2 (see Getting Started). The default
# CodeZip build runs in the cloud (AWS CodeBuild), so no local Docker is needed.
# Validate end to end against the shipped CLI version during event prep.
set -euo pipefail

REGION="us-west-2"; PROJECT="AgentCoreProject"; AGENT="AssistantAgent"
export AWS_DEFAULT_REGION="$REGION"

echo ">> 1/3 Scaffold a Strands code agent (project $PROJECT, agent $AGENT)"
# --project-name sets the folder ($PROJECT); --name sets the agent (app/$AGENT).
# Explicit flags (not --defaults, which builds a config-only harness) so this is a
# code-based Strands agent with an editable app/$AGENT/main.py entrypoint.
if [ ! -d "$PROJECT" ]; then
  agentcore create \
    --project-name "$PROJECT" \
    --name "$AGENT" \
    --framework Strands \
    --model-provider Bedrock \
    --protocol HTTP \
    --build CodeZip \
    --memory none
fi
cd "$PROJECT"

echo ">> 2/3 Write the agent code and add its tool dependency"
cat > "app/$AGENT/main.py" <<'PY'
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands_tools import current_time

@tool
def word_count(text: str) -> str:
    """Return the number of words in the given text."""
    return f"{len(text.split())} words"

app = BedrockAgentCoreApp()
agent = Agent(
    system_prompt="You are a concise, helpful assistant.",
    tools=[current_time, word_count],
)

@app.entrypoint
def handler(event):
    return agent(event.get("prompt", ""))

app.run()
PY

# The agent imports strands-agents-tools (current_time); ensure it is a dependency
# so the CodeZip build includes it.
( cd "app/$AGENT" && uv add strands-agents-tools ) \
  || echo "NOTE: add 'strands-agents-tools' to app/$AGENT/pyproject.toml if deploy reports a missing import"

echo ">> 3/3 Deploy to AgentCore Runtime (CodeZip, cloud build)"
agentcore deploy

echo "Done. Verify with:"
echo "  agentcore status"
echo "  agentcore invoke --prompt \"What time is it, and how many words are in this sentence?\""
