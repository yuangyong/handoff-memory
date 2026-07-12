"""只读采集 Git 仓库状态。"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitState:
    """恢复上下文所需的最小 Git 状态。"""

    available: bool
    is_repository: bool
    branch: str | None = None
    head: str | None = None
    dirty: bool = False
    changes: tuple[str, ...] = ()
    note: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def read_git_state(project: Path) -> GitState:
    """使用固定的只读命令读取 Git，不执行任何交接文件内容。"""
    git = shutil.which("git")
    if git is None:
        return GitState(False, False, note="未找到 Git 可执行文件")

    probe = _run(git, project, "rev-parse", "--is-inside-work-tree")
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        return GitState(True, False, note="不是 Git 仓库")

    branch_result = _run(git, project, "symbolic-ref", "--quiet", "--short", "HEAD")
    branch = branch_result.stdout.strip() or "DETACHED"
    head_result = _run(git, project, "rev-parse", "--short=12", "HEAD")
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    status_result = _run(git, project, "status", "--porcelain=v1", "--untracked-files=normal")
    all_changes = tuple(line for line in status_result.stdout.splitlines() if line)
    changes = all_changes[:200]
    if status_result.returncode != 0:
        note = "无法读取 Git 工作区状态"
    elif len(all_changes) > len(changes):
        note = f"工作区共有 {len(all_changes)} 条变更，仅保留前 {len(changes)} 条"
    else:
        note = None
    return GitState(True, True, branch, head, bool(changes), changes, note)


def _run(git: str, project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [git, "-C", str(project), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess([], 1, "", str(exc))
