---
inclusion: auto
name: documentation-lookup
description: Activated whenever writing or reviewing code that uses AWS services, AgentCore CLI, or the Strands Agents SDK — ensures current documentation is consulted before implementation.
---

# Documentation Lookup Policy

Before writing or modifying any code that involves AWS services, AgentCore CLI, or the Strands Agents SDK, **always look up the current official documentation using available MCP tools**. Do not rely on prior training knowledge alone — APIs, CLI flags, and SDK interfaces change frequently.

## When This Applies

- Creating or editing Strands agent definitions, tools, or workflows
- Using any AWS SDK (boto3) or AWS CLI command
- Using any AgentCore CLI command (`agentcore ...`)
- Configuring AWS resources (IAM, S3, Lambda, Bedrock, etc.)

## Required Steps Before Writing Code

1. **Strands SDK** — search for the relevant class, decorator, or method in the Strands Agents SDK docs.
2. **AgentCore CLI** — look up the specific subcommand and its flags before using it.
3. **AWS Service** — confirm the current API shape, required permissions, and any regional availability notes for us-west-2.

## Rationale

These tools are new and evolving. Using stale knowledge risks generating code with deprecated interfaces, missing required parameters, or incorrect CLI syntax. A quick documentation lookup before writing saves debugging time downstream.
