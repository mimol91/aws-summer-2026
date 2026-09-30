from __future__ import annotations

from functools import lru_cache

import boto3

REGION = "us-west-2"
SSM_PREFIX = "/app/workshop"


@lru_cache(maxsize=None)
def client(service: str):
    """One boto3 client per service, pinned to the workshop region."""
    return boto3.client(service, region_name=REGION)


@lru_cache(maxsize=None)
def param(name: str) -> str:
    """Resolve a resource identifier from SSM so nothing is hardcoded."""
    return client("ssm").get_parameter(Name=f"{SSM_PREFIX}/{name}")["Parameter"]["Value"]
