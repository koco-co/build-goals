#!/usr/bin/env python3
"""Run one validation command and write a compact structured evidence record."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

SCHEMA_VERSION = "1.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summary(data: bytes) -> dict[str, object]:
    return {
        "bytes": len(data),
        "lines": data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _write_record(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        # Non-POSIX platforms may not expose POSIX permission semantics.
        pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "执行一条验证命令并记录 cwd、命令、时间、退出码和 stdout/stderr 摘要。"
            "记录可帮助复核，但不是不可篡改的执行证明。"
        )
    )
    parser.add_argument("--output", type=Path, required=True, help="结构化证据 JSON 文件")
    parser.add_argument("--summary", default="", help="可选的人类可读验证摘要；不要填写秘密或敏感数据")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="在 -- 后提供要运行的命令及参数")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("ERROR: 必须在 -- 后提供验证命令。", file=sys.stderr)
        return 2

    started_at = _utc_now()
    try:
        completed = subprocess.run(command, check=False, capture_output=True)
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
        launch_error = None
    except OSError as exc:
        exit_code = 127
        stdout = b""
        stderr = str(exc).encode("utf-8", errors="replace")
        launch_error = type(exc).__name__
    finished_at = _utc_now()

    if stdout:
        sys.stdout.buffer.write(stdout)
        sys.stdout.buffer.flush()
    if stderr:
        sys.stderr.buffer.write(stderr)
        sys.stderr.buffer.flush()

    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "cwd": str(Path.cwd().resolve()),
        "command": command,
        "started_at": started_at,
        "finished_at": finished_at,
        "exit_code": exit_code,
        "stdout": _summary(stdout),
        "stderr": _summary(stderr),
        "summary": args.summary,
        "note": "该记录说明包装器观察到的执行结果，可被后续修改；它不是不可篡改的执行证明。",
    }
    if launch_error is not None:
        payload["launch_error"] = launch_error

    _write_record(args.output.expanduser(), payload)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
