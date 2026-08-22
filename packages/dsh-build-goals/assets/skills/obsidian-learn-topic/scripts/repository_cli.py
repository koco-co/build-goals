#!/usr/bin/env python3
"""Safely prepare and verify an isolated GitHub repository learning workspace.

The driver never writes to an Obsidian Vault.  Vault notes and assets remain
the responsibility of roadmap_cli.py through the Obsidian CLI.  Repository
mutations are dry-run by default and operate on one explicitly planned path.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any, Iterable

from learn_topic.curriculum import SPDX_LICENSE_VALUES


REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
COMMIT_RE = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")
SHELL_INTERPRETERS = {"bash", "cmd", "fish", "powershell", "pwsh", "sh", "zsh"}
SECRET_MARKERS = ("--api-key", "--password", "--token", "authorization:", "sk-")
UNKNOWN_LICENSES = {"noassertion", "none", "unknown"}
UPSTREAM_STATES = {"unchanged", "fixed-baseline", "changed", "blocked", "archived"}


class ContractError(RuntimeError):
    """Raised when a repository plan or observed result violates the contract."""


def emit(value: dict[str, Any], *, stream: Any = sys.stdout) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True), file=stream)


def require_keys(mapping: dict[str, Any], keys: Iterable[str], *, label: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise ContractError(f"{label} missing keys: {', '.join(missing)}")


def ensure_text(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ContractError(f"{label} must be a normalized non-empty string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ContractError(f"{label} contains a control character")
    return value


def resolve_absolute_path(value: Any, *, label: str, must_exist: bool = False) -> Path:
    text = ensure_text(value, label=label)
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        raise ContractError(f"{label} must be absolute")
    if candidate.is_symlink():
        raise ContractError(f"{label} must not be a symbolic link")
    try:
        return candidate.resolve(strict=must_exist)
    except OSError as error:
        raise ContractError(f"cannot resolve {label}: {error}") from error


def ensure_outside(path: Path, boundary: Path, *, label: str) -> None:
    try:
        path.relative_to(boundary)
    except ValueError:
        return
    raise ContractError(f"{label} must stay outside the Vault")


def ensure_not_inside_checkout(path: Path, checkout: Path, *, label: str) -> None:
    try:
        path.relative_to(checkout)
    except ValueError:
        return
    raise ContractError(f"{label} must stay outside checkout_path")


def normalize_target_ref(value: Any) -> str:
    target_ref = ensure_text(value, label="target_ref")
    if COMMIT_RE.fullmatch(target_ref):
        return target_ref.lower()
    if not target_ref.startswith(("refs/heads/", "refs/tags/")):
        raise ContractError(
            "target_ref must be a full commit or canonical refs/heads/... or refs/tags/..."
        )
    ref_name = target_ref.split("/", 2)[2]
    invalid = (
        not ref_name
        or ref_name.startswith("/")
        or ref_name.endswith(("/", ".", ".lock"))
        or ".." in ref_name
        or "//" in ref_name
        or "@{" in ref_name
        or any(character in ref_name for character in " ~^:?*[\\")
        or any(part.startswith(".") or part.endswith(".lock") for part in ref_name.split("/"))
    )
    if invalid:
        raise ContractError("target_ref is not a safe canonical Git ref")
    return target_ref


def normalize_default_branch(value: Any) -> str:
    branch = ensure_text(value, label="default_branch")
    invalid = (
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", branch)
        or branch.endswith(("/", ".", ".lock"))
        or ".." in branch or "//" in branch or "@{" in branch
        or any(part.startswith(".") or part.endswith(".lock") for part in branch.split("/"))
    )
    if invalid:
        raise ContractError("default_branch is not a safe Git branch name")
    return branch


def normalize_approved_files(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ContractError("approved_files must be a non-empty array")
    result: list[str] = []
    for index, item in enumerate(value):
        text = ensure_text(item, label=f"approved_files[{index}]")
        if "\\" in text or text.startswith("/"):
            raise ContractError(f"approved_files[{index}] must be repository-relative")
        parts = PurePosixPath(text).parts
        if not parts or any(part in {"", ".", ".."} for part in parts):
            raise ContractError(f"approved_files[{index}] contains an unsafe segment")
        if parts[0] == ".git":
            raise ContractError("approved_files must not target .git")
        normalized = PurePosixPath(*parts).as_posix()
        if normalized in result:
            raise ContractError(f"duplicate approved file {normalized}")
        result.append(normalized)
    return result


def normalize_test_argv(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ContractError("test_argv must be a non-empty argv array")
    argv = [ensure_text(item, label=f"test_argv[{index}]") for index, item in enumerate(value)]
    executable = Path(argv[0]).name.casefold()
    if executable in SHELL_INTERPRETERS and any(argument in {"-c", "/c"} for argument in argv[1:]):
        raise ContractError("test_argv must not execute a shell command string")
    lowered = " ".join(argv).casefold()
    if any(marker in lowered for marker in SECRET_MARKERS):
        raise ContractError("test_argv must not contain credentials or secret flags")
    return argv


def load_plan(path_value: str) -> dict[str, Any]:
    plan_path = Path(path_value).expanduser()
    if plan_path.is_symlink():
        raise ContractError("repository plan must not be a symbolic link")
    try:
        plan_path = plan_path.resolve(strict=True)
        raw = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractError(f"cannot read repository plan: {error}") from error
    if not isinstance(raw, dict):
        raise ContractError("repository plan must contain a JSON object")
    require_keys(
        raw,
        (
            "provider",
            "repository",
            "repository_url",
            "default_branch",
            "target_ref",
            "baseline_commit",
            "license_spdx",
            "upstream_status",
            "verified_at",
            "vault_path",
            "source_mode",
            "checkout_path",
            "approved_files",
            "test_argv",
            "patch_file",
            "evidence_file",
        ),
        label="repository plan",
    )
    if raw["provider"] != "github":
        raise ContractError("provider must be github")
    repository = ensure_text(raw["repository"], label="repository")
    if not REPOSITORY_RE.fullmatch(repository):
        raise ContractError("repository must use canonical owner/repo form")
    repository_url = ensure_text(raw["repository_url"], label="repository_url")
    expected_url = f"https://github.com/{repository}"
    if repository_url != expected_url:
        raise ContractError(f"repository_url must be {expected_url}")
    baseline_commit = ensure_text(raw["baseline_commit"], label="baseline_commit").lower()
    if not COMMIT_RE.fullmatch(baseline_commit):
        raise ContractError("baseline_commit must be a full 40- or 64-character commit id")
    verified_at = ensure_text(raw["verified_at"], label="verified_at")
    try:
        date.fromisoformat(verified_at)
    except ValueError as error:
        raise ContractError("verified_at must be an ISO date") from error
    vault_path = resolve_absolute_path(raw["vault_path"], label="vault_path", must_exist=True)
    checkout_path = resolve_absolute_path(raw["checkout_path"], label="checkout_path")
    patch_file = resolve_absolute_path(raw["patch_file"], label="patch_file")
    evidence_file = resolve_absolute_path(raw["evidence_file"], label="evidence_file")
    for label, candidate in (
        ("checkout_path", checkout_path),
        ("patch_file", patch_file),
        ("evidence_file", evidence_file),
        ("repository plan", plan_path),
    ):
        ensure_outside(candidate, vault_path, label=label)
    for label, candidate in (("patch_file", patch_file), ("evidence_file", evidence_file)):
        try:
            candidate.relative_to(plan_path.parent)
        except ValueError as error:
            raise ContractError(f"{label} must stay inside the repository plan directory") from error
    if patch_file == evidence_file:
        raise ContractError("patch_file and evidence_file must differ")
    for label, candidate in (
        ("repository plan", plan_path),
        ("patch_file", patch_file),
        ("evidence_file", evidence_file),
        ("test home", evidence_file.parent / ".test-home"),
    ):
        ensure_not_inside_checkout(candidate, checkout_path, label=label)
    source_mode = raw["source_mode"]
    if source_mode not in {"existing", "isolated"}:
        raise ContractError("source_mode must be existing or isolated")
    upstream_status = ensure_text(raw["upstream_status"], label="upstream_status")
    if upstream_status not in UPSTREAM_STATES:
        raise ContractError("upstream_status is not a supported repository state")
    license_spdx = ensure_text(raw["license_spdx"], label="license_spdx")
    if license_spdx not in SPDX_LICENSE_VALUES:
        raise ContractError("license_spdx must be a supported SPDX license identifier")
    return {
        "provider": "github",
        "repository": repository,
        "repository_url": repository_url,
        "default_branch": normalize_default_branch(raw["default_branch"]),
        "target_ref": normalize_target_ref(raw["target_ref"]),
        "baseline_commit": baseline_commit,
        "license_spdx": license_spdx,
        "upstream_status": upstream_status,
        "verified_at": verified_at,
        "vault_path": str(vault_path),
        "source_mode": source_mode,
        "checkout_path": str(checkout_path),
        "approved_files": normalize_approved_files(raw["approved_files"]),
        "test_argv": normalize_test_argv(raw["test_argv"]),
        "patch_file": str(patch_file),
        "evidence_file": str(evidence_file),
    }


def run(
    argv: list[str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    text: bool = True,
    check: bool = True,
    shell: bool = False,
) -> subprocess.CompletedProcess[Any]:
    if shell:
        raise ContractError("repository commands must never use a shell")
    completed = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        text=text,
        capture_output=True,
        check=False,
        shell=False,
    )
    if check and completed.returncode != 0:
        stderr = completed.stderr if isinstance(completed.stderr, str) else completed.stderr.decode("utf-8", "replace")
        raise ContractError(f"command failed ({completed.returncode}): {stderr[-500:].strip()}")
    return completed


def canonical_remote_repository(remote: str) -> str | None:
    patterns = (
        r"^https?://(?:[^/@]+@)?github\.com/([^/]+/[^/]+?)(?:\.git)?/?$",
        r"^ssh://(?:[^/@]+@)?github\.com/([^/]+/[^/]+?)(?:\.git)?/?$",
        r"^(?:[^/@]+@)?github\.com:([^/]+/[^/]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, remote, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def clean_test_environment(plan: dict[str, Any]) -> dict[str, str]:
    environment: dict[str, str] = {}
    for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "SYSTEMROOT", "PATHEXT"):
        value = os.environ.get(key)
        if value:
            environment[key] = value
    isolated_home = Path(plan["evidence_file"]).parent / ".test-home"
    isolated_home.mkdir(parents=True, exist_ok=True)
    environment.update(
        {
            "HOME": str(isolated_home),
            "XDG_CONFIG_HOME": str(isolated_home / ".config"),
            "CI": "true",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "NPM_CONFIG_USERCONFIG": os.devnull,
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return environment


def audit(plan: dict[str, Any]) -> dict[str, Any]:
    checkout = Path(plan["checkout_path"])
    if not checkout.is_dir():
        raise ContractError("existing checkout_path is not a directory")
    remote = run(["git", "-C", str(checkout), "remote", "get-url", "origin"]).stdout.strip()
    remote_repository = canonical_remote_repository(remote)
    if remote_repository is None or remote_repository.casefold() != plan["repository"].casefold():
        raise ContractError("existing checkout origin does not match the planned repository")
    head = run(["git", "-C", str(checkout), "rev-parse", "HEAD"]).stdout.strip().lower()
    status = run(
        ["git", "-C", str(checkout), "status", "--porcelain=v1", "--untracked-files=all"]
    ).stdout
    return {
        "ok": True,
        "op": "audit",
        "repository": plan["repository"],
        "remote_repository": remote_repository,
        "remote_sha256": hashlib.sha256(remote.encode("utf-8")).hexdigest(),
        "remote_match": True,
        "head": head,
        "baseline_match": head == plan["baseline_commit"],
        "dirty": bool(status.strip()),
        "status_sha256": hashlib.sha256(status.encode("utf-8")).hexdigest(),
    }


def prepare(plan: dict[str, Any], *, apply: bool) -> dict[str, Any]:
    checkout = Path(plan["checkout_path"])
    if plan["source_mode"] == "existing":
        raise ContractError("existing source must be audited and is never prepared over")
    if checkout.exists():
        raise ContractError("isolated checkout_path already exists")
    if not apply:
        return {
            "ok": True,
            "op": "prepare",
            "mode": "dry-run",
            "checkout_path": str(checkout),
            "baseline_commit": plan["baseline_commit"],
        }
    environment = os.environ.copy()
    environment["GIT_LFS_SKIP_SMUDGE"] = "1"
    run(
        [
            "git",
            "clone",
            "--no-checkout",
            "--filter=blob:none",
            "--",
            plan["repository_url"],
            str(checkout),
        ],
        env=environment,
    )
    run(
        [
            "git",
            "-C",
            str(checkout),
            "-c",
            "core.hooksPath=/dev/null",
            "checkout",
            "--detach",
            plan["baseline_commit"],
        ],
        env=environment,
    )
    head = run(["git", "-C", str(checkout), "rev-parse", "HEAD"]).stdout.strip().lower()
    if head != plan["baseline_commit"]:
        raise ContractError("prepared checkout HEAD does not match baseline_commit")
    return {
        "ok": True,
        "op": "prepare",
        "mode": "apply",
        "checkout_path": str(checkout),
        "head": head,
    }


def parse_changed_files(output: str) -> tuple[list[str], set[str]]:
    changed: list[str] = []
    untracked: set[str] = set()
    records = [record for record in output.split("\0") if record]
    for record in records:
        if len(record) >= 4 and record[2] == " ":
            status, path = record[:2], record[3:]
        else:
            status, path = " M", record
        if status.startswith(("R", "C")):
            raise ContractError("renames and copies are outside the minimal patch contract")
        normalized = normalize_approved_files([path])[0]
        changed.append(normalized)
        if status == "??":
            untracked.add(normalized)
    return changed, untracked


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(content)
    temporary.replace(path)


def patch_snapshot(plan: dict[str, Any]) -> dict[str, Any]:
    checkout = Path(plan["checkout_path"])
    head = run(["git", "-C", str(checkout), "rev-parse", "HEAD"]).stdout.strip().lower()
    if head != plan["baseline_commit"]:
        raise ContractError("checkout HEAD changed from baseline_commit")
    status_output = run(
        ["git", "-C", str(checkout), "status", "--porcelain=v1", "-z", "--untracked-files=all"]
    ).stdout
    changed, untracked = parse_changed_files(status_output)
    if not changed:
        raise ContractError("minimal patch is empty")
    unexpected = sorted(set(changed) - set(plan["approved_files"]))
    if unexpected:
        raise ContractError(f"patch changed unapproved files: {', '.join(unexpected)}")
    run(
        [
            "git", "-C", str(checkout), "diff", "--check",
            plan["baseline_commit"], "--", *plan["approved_files"],
        ]
    )
    tracked_files = [path for path in plan["approved_files"] if path not in untracked]
    patch_parts: list[bytes] = []
    if tracked_files:
        patch_parts.append(
            run(
                [
                    "git", "-C", str(checkout), "diff", "--binary", "--no-ext-diff",
                    plan["baseline_commit"], "--", *tracked_files,
                ],
                text=False,
            ).stdout
        )
    for relative in sorted(untracked):
        whitespace = run(
            ["git", "diff", "--no-index", "--check", "--", "/dev/null", relative],
            cwd=str(checkout),
            check=False,
        )
        if whitespace.returncode not in {0, 1} or whitespace.stdout.strip():
            raise ContractError(f"untracked file fails diff --check: {relative}")
        untracked_patch = run(
            ["git", "diff", "--no-index", "--binary", "--", "/dev/null", relative],
            cwd=str(checkout),
            text=False,
            check=False,
        )
        if untracked_patch.returncode not in {0, 1}:
            raise ContractError(f"cannot render patch for new file {relative}")
        patch_parts.append(untracked_patch.stdout)
    patch = b"".join(patch_parts)
    if not patch.strip():
        raise ContractError("minimal patch is empty")
    return {
        "head": head,
        "changed": changed,
        "patch": patch,
        "patch_sha256": hashlib.sha256(patch).hexdigest(),
    }


def verify_patch(plan: dict[str, Any], *, apply: bool) -> dict[str, Any]:
    if plan["license_spdx"].casefold() in UNKNOWN_LICENSES:
        raise ContractError("Patch graduation is blocked until the repository license is known")
    if plan["upstream_status"] not in {"unchanged", "fixed-baseline"}:
        raise ContractError("Patch graduation requires a confirmed upstream baseline")
    checkout = Path(plan["checkout_path"])
    if not checkout.is_dir():
        raise ContractError("checkout_path is not an existing directory")
    before = patch_snapshot(plan)
    if not apply:
        return {
            "ok": True,
            "op": "verify-patch",
            "mode": "dry-run",
            "baseline_commit": before["head"],
            "changed_files": before["changed"],
            "patch_sha256": before["patch_sha256"],
            "graduation_status": "pending-evidence",
        }
    tested = run(
        plan["test_argv"],
        cwd=str(checkout),
        env=clean_test_environment(plan),
        shell=False,
        check=False,
    )
    if tested.returncode != 0:
        raise ContractError(f"approved relevant test failed with exit code {tested.returncode}")
    after = patch_snapshot(plan)
    if (
        after["head"] != before["head"]
        or after["changed"] != before["changed"]
        or after["patch_sha256"] != before["patch_sha256"]
    ):
        raise ContractError("test command changed HEAD, files, or the approved Patch")
    stdout_bytes = tested.stdout.encode("utf-8") if isinstance(tested.stdout, str) else tested.stdout
    stderr_bytes = tested.stderr.encode("utf-8") if isinstance(tested.stderr, str) else tested.stderr
    evidence = {
        "repository": plan["repository"],
        "repository_url": plan["repository_url"],
        "baseline_commit": after["head"],
        "target_ref": plan["target_ref"],
        "license_spdx": plan["license_spdx"],
        "upstream_status": plan["upstream_status"],
        "verified_at": plan["verified_at"],
        "changed_files": after["changed"],
        "approved_files": plan["approved_files"],
        "patch_sha256": after["patch_sha256"],
        "test": {
            "argv": plan["test_argv"],
            "returncode": tested.returncode,
            "stdout_sha256": hashlib.sha256(stdout_bytes).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr_bytes).hexdigest(),
        },
        "graduation_status": "passed",
    }
    atomic_write(Path(plan["patch_file"]), after["patch"])
    atomic_write(
        Path(plan["evidence_file"]),
        (json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return {"ok": True, "op": "verify-patch", **evidence}


def upstream_check(plan: dict[str, Any]) -> dict[str, Any]:
    metadata_result = run(["gh", "api", f"repos/{plan['repository']}"])
    try:
        metadata = json.loads(metadata_result.stdout)
    except json.JSONDecodeError as error:
        raise ContractError("GitHub repository metadata is not valid JSON") from error
    if not isinstance(metadata, dict):
        raise ContractError("GitHub repository metadata must be an object")
    default_branch = metadata.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch:
        raise ContractError("GitHub metadata is missing default_branch")
    default_remote = run(
        ["git", "ls-remote", plan["repository_url"], f"refs/heads/{default_branch}"]
    ).stdout.strip()
    default_commit = default_remote.split()[0].lower() if default_remote else ""
    if not COMMIT_RE.fullmatch(default_commit):
        raise ContractError("cannot resolve the current upstream default-branch commit")
    target_ref = plan["target_ref"]
    if COMMIT_RE.fullmatch(target_ref):
        target_commit = target_ref.lower()
        target_exists = True
    elif target_ref.startswith("refs/tags/"):
        target_remote = run(
            [
                "git",
                "ls-remote",
                plan["repository_url"],
                target_ref,
                f"{target_ref}^{{}}",
            ]
        ).stdout
        candidates: dict[str, str] = {}
        for line in target_remote.splitlines():
            parts = line.split()
            if len(parts) == 2 and COMMIT_RE.fullmatch(parts[0].lower()):
                candidates[parts[1]] = parts[0].lower()
        preference = (
            f"{target_ref}^{{}}",
            target_ref,
        )
        target_commit = next(
            (candidates[reference] for reference in preference if reference in candidates),
            "",
        )
        target_exists = bool(target_commit)
    else:
        target_remote = run(
            ["git", "ls-remote", plan["repository_url"], target_ref]
        ).stdout.strip()
        parts = target_remote.split()
        target_commit = (
            parts[0].lower()
            if len(parts) >= 2 and parts[1] == target_ref and COMMIT_RE.fullmatch(parts[0].lower())
            else ""
        )
        target_exists = bool(target_commit)
    default_branch_changed = default_branch != plan["default_branch"]
    default_branch_advanced = default_commit != plan["baseline_commit"]
    target_changed = not target_exists or target_commit != plan["baseline_commit"]
    archived = metadata.get("archived") is True
    disabled = metadata.get("disabled") is True
    requires_decision = (
        target_changed
        or default_branch_changed
        or archived
        or disabled
        or (
            default_branch_advanced
            and plan["upstream_status"] != "fixed-baseline"
        )
    )
    return {
        "ok": True,
        "op": "upstream-check",
        "repository": plan["repository"],
        "baseline_commit": plan["baseline_commit"],
        "target_ref": target_ref,
        "target_commit": target_commit or None,
        "target_exists": target_exists,
        "target_changed": target_changed,
        "default_branch_commit": default_commit,
        "default_branch_changed": default_branch_changed,
        "default_branch_advanced": default_branch_advanced,
        "changed": target_changed or default_branch_changed or default_branch_advanced,
        "requires_decision": requires_decision,
        "default_branch": default_branch,
        "archived": archived,
        "disabled": disabled,
        "pushed_at": metadata.get("pushed_at"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("audit", "prepare", "verify-patch", "upstream-check"):
        child = subparsers.add_parser(command)
        child.add_argument("--plan", required=True)
        if command in {"prepare", "verify-patch"}:
            child.add_argument("--apply", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        plan = load_plan(args.plan)
        if args.command == "audit":
            report = audit(plan)
        elif args.command == "prepare":
            report = prepare(plan, apply=args.apply)
        elif args.command == "verify-patch":
            report = verify_patch(plan, apply=args.apply)
        else:
            report = upstream_check(plan)
    except ContractError as error:
        emit({"ok": False, "op": args.command, "error": str(error)}, stream=sys.stderr)
        return 1
    emit(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
