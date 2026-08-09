#!/usr/bin/env python3
"""Safely materialize the reviewed repository update from a temporary payload."""

from __future__ import annotations

import base64
import hashlib
import io
import tarfile
from pathlib import Path, PurePosixPath

EXPECTED_SHA256 = "3924b339394bcf74f294985c787ed70702d4b3ebf61bb68b4b82de5c441dec96"
EXPECTED_PARTS = 5


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    payload_dir = root / ".github" / "materialize"
    parts = sorted(payload_dir.glob("payload.*"))
    if len(parts) != EXPECTED_PARTS:
        raise RuntimeError(f"expected {EXPECTED_PARTS} payload parts, found {len(parts)}")

    encoded = "".join(path.read_text(encoding="ascii").strip() for path in parts)
    archive = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(archive).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError(f"payload sha256 mismatch: {digest}")

    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        for member in bundle.getmembers():
            member_path = PurePosixPath(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise RuntimeError(f"unsafe archive path: {member.name}")
            destination = (root / member_path).resolve(strict=False)
            if not is_within(destination, root):
                raise RuntimeError(f"archive path escapes repository: {member.name}")
            if member.issym() or member.islnk():
                link_target = PurePosixPath(member.linkname)
                if link_target.is_absolute():
                    raise RuntimeError(f"absolute link target: {member.name}")
                resolved_link = (root / member_path.parent / link_target).resolve(strict=False)
                if not is_within(resolved_link, root):
                    raise RuntimeError(f"link target escapes repository: {member.name}")
        bundle.extractall(root, filter="data")

    legacy_prompt = root / "skills" / "building-skills" / "prompts" / "independent-reviewer.prompt.md"
    legacy_prompt.unlink(missing_ok=True)
    print(f"materialized update from {len(parts)} parts; sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
