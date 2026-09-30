from strands.models.bedrock import BedrockModel

from govease.config import REGION, param


def load_model() -> BedrockModel:
    """Bedrock model with the workshop baseline guardrail applied to input and output."""
    return BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        region_name=REGION,
        guardrail_id=param("guardrails/guardrail-id"),
        guardrail_version="DRAFT",
        guardrail_trace="enabled",
        temperature=0.2,
    )
