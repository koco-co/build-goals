from __future__ import annotations

import re
from pathlib import PurePosixPath

from .curriculum import ContractError


def validate_vault_path(value: str, *, markdown: bool | None = None) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value:
        raise ContractError("Vault path must be non-empty and relative")
    path = PurePosixPath(value)
    if any(part in {"", ".", "..", ".obsidian"} for part in path.parts):
        raise ContractError("Vault path contains an unsafe segment")
    if markdown is True and not re.match(r"^§\d{2}-.*\.md$", path.name):
        raise ContractError("Markdown notes must use §NN-name.md")
    return path.as_posix()


def roadmap_base_path(root: str) -> str:
    root = validate_vault_path(root)
    name = PurePosixPath(root).name
    return f"{root}/{name}-Roadmap.base"
