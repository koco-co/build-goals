from __future__ import annotations

import re
from typing import Any

from .curriculum import ContractError


SECRET_MARKERS = (
    "authorization:", "cookie:", "bearer ", "sk-", "ghp_", "github_pat_",
)
MACHINE_PATH = re.compile(
    r"(?:file:(?:/{2,3})?|(?:^|[\s=:\"'(`\[]))"
    r"(?:/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.~@%+,:=-]+)+|[A-Za-z]:\\[^\s]+)",
    re.IGNORECASE,
)


def validate_persisted_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ContractError(f"{label} must be a normalized non-empty string")
    folded = value.casefold()
    if any(marker in folded for marker in SECRET_MARKERS) or MACHINE_PATH.search(value):
        raise ContractError(f"{label} contains secret-like or machine-local data")
    return value


def validate_persisted_value(value: Any, label: str) -> None:
    if isinstance(value, str):
        validate_persisted_text(value, label)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            validate_persisted_value(item, f"{label}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            validate_persisted_text(str(key), f"{label} key")
            validate_persisted_value(item, f"{label}.{key}")
