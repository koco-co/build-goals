"""Data models and issue collection helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    path: str
    message: str


@dataclass
class Report:
    project_root: str
    mode: str
    phase: str
    issues: list[Issue]

    @property
    def errors(self) -> list[Issue]:
        return [item for item in self.issues if item.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [item for item in self.issues if item.severity == "warning"]

    @property
    def infos(self) -> list[Issue]:
        return [item for item in self.issues if item.severity == "info"]

    def failed(self, *, strict: bool = False) -> bool:
        return bool(self.errors or (strict and self.warnings))

    def to_dict(self, *, strict: bool = False) -> dict[str, object]:
        return {
            "project_root": self.project_root,
            "mode": self.mode,
            "phase": self.phase,
            "status": "fail" if self.failed(strict=strict) else "pass",
            "strict": strict,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "info_count": len(self.infos),
            "issues": [asdict(item) for item in self.issues],
        }


def add_issue(
    issues: list[Issue],
    severity: str,
    code: str,
    path: Path,
    message: str,
    root: Path,
) -> None:
    try:
        display = str(path.relative_to(root)) or "."
    except ValueError:
        display = str(path)
    issues.append(Issue(severity, code, display, message))
