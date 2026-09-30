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
