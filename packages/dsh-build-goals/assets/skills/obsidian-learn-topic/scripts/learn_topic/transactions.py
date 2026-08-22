from __future__ import annotations

import hashlib

from .curriculum import ContractError


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def compare_and_swap(current: str, expected_sha256: str, replacement: str) -> str:
    if sha256_text(current) != expected_sha256:
        raise ContractError("compare-and-swap failed: current content changed")
    return replacement
