# Python Coding Standards

## Type Hints

All functions and methods must include type hints on parameters and return values.

```python
def fetch_document(url: str, timeout: int = 10) -> dict[str, str]:
    ...
```

- Use `from __future__ import annotations` at the top of files when forward references are needed.
- Prefer built-in generic types (`list[str]`, `dict[str, Any]`) over `typing.List`, `typing.Dict` (Python 3.10+).
- Use `Optional[X]` or `X | None` for nullable values.

## Comments

Add short, explanatory comments that describe **why** something is done, not just what.

```python
# Retry with backoff to handle transient Bedrock throttling
response = call_with_retry(client.invoke_model, payload)
```

- One comment per logical block, not per line.
- Avoid restating the code in plain English — only comment when intent isn't obvious.

## Code Style

- **Keep code minimal and focused** on the concept being demonstrated. No boilerplate beyond what the example needs.
- Prefer flat, readable logic over clever one-liners.
- Use `dataclasses` or `TypedDict` for structured data instead of raw dicts when shape is known.
- Avoid premature abstractions — only extract helpers when they're reused or significantly improve clarity.

## Imports

Group imports in this order, separated by blank lines:

1. Standard library
2. Third-party packages (boto3, strands, etc.)
3. Local modules

```python
import json
from typing import Any

import boto3
from strands import Agent

from .tools import my_tool
```
