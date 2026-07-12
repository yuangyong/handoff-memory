"""自动识别并只读采集 Git 或 SVN 版本库状态。"""

from __future__ import annotations

import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


@dataclass(frozen=True)
class RepositoryState:
    """恢复上下文所需的统一版本库状态。

    `branch`、`head` 等字段兼容 0.1 的 Git 状态输出；SVN 使用
    `branch` 表示仓库相对位置，使用 `head` 与 `revision` 表示工作副本修订号。
    """

    available: bool
    is_repository: bool
    branch: str | None = None
    head: str | None = None
    dirty: bool = False
    changes: tuple[str, ...] = ()
    note: str | None = None
    provider: str = "none"
    revision: str | None = None
    url: str | None = None
    root: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def read_repository_state(project: Path) -> RepositoryState:
    """自动选择离项目最近的 Git 或 SVN 工作副本并读取状态。"""
    project = project.expanduser().resolve()
    git_marker = _nearest_marker(project, ".git")
    svn_marker = _nearest_marker(project, ".svn")

    if git_marker and (not svn_marker or git_marker[0] <= svn_marker[0]):
        return read_git_state(project, marker_root=git_marker[1])
    if svn_marker:
        return read_svn_state(project, marker_root=svn_marker[1])

    git_state = read_git_state(project)
    if git_state.is_repository:
        return git_state
    svn_state = read_svn_state(project)
    if svn_state.is_repository:
        return svn_state

    available = git_state.available or svn_state.available
    note = (
        "未识别 Git 或 SVN 工作副本"
        if available
        else "未找到 Git 或 SVN 可执行文件"
    )
    return RepositoryState(available, False, note=note)


def read_git_state(project: Path, *, marker_root: Path | None = None) -> RepositoryState:
    """使用固定的只读 Git 命令读取状态。"""
    git = shutil.which("git")
    if git is None:
        return RepositoryState(
            False,
            marker_root is not None,
            note="未找到 Git 可执行文件",
            provider="git",
            root=str(marker_root) if marker_root else None,
        )

    probe = _run([git, "-C", str(project), "rev-parse", "--is-inside-work-tree"], project)
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        return RepositoryState(True, False, note="不是 Git 仓库", provider="git")

    branch_result = _run(
        [git, "-C", str(project), "symbolic-ref", "--quiet", "--short", "HEAD"],
        project,
    )
    branch = branch_result.stdout.strip() or "DETACHED"
    head_result = _run([git, "-C", str(project), "rev-parse", "--short=12", "HEAD"], project)
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    root_result = _run([git, "-C", str(project), "rev-parse", "--show-toplevel"], project)
    repository_root = root_result.stdout.strip() if root_result.returncode == 0 else None
    url_result = _run([git, "-C", str(project), "config", "--get", "remote.origin.url"], project)
    url = (
        _sanitize_repository_url(url_result.stdout.strip())
        if url_result.returncode == 0
        else None
    )
    status_result = _run(
        [git, "-C", str(project), "status", "--porcelain=v1", "--untracked-files=normal"],
        project,
    )
    all_changes = tuple(line for line in status_result.stdout.splitlines() if line)
    changes, note = _bounded_changes(all_changes, status_result.returncode, "Git")
    return RepositoryState(
        True,
        True,
        branch,
        head,
        bool(changes),
        changes,
        note,
        "git",
        head,
        url,
        repository_root,
    )


def read_svn_state(project: Path, *, marker_root: Path | None = None) -> RepositoryState:
    """使用 SVN XML 输出读取工作副本状态，避免本地化文本解析。"""
    svn = shutil.which("svn")
    if svn is None:
        return RepositoryState(
            False,
            marker_root is not None,
            note="未找到 SVN 可执行文件",
            provider="svn",
            root=str(marker_root) if marker_root else None,
        )

    info_result = _run([svn, "info", "--xml", str(project)], project, timeout=10)
    if info_result.returncode != 0:
        return RepositoryState(True, False, note="不是 SVN 工作副本", provider="svn")
    try:
        info_root = ET.fromstring(info_result.stdout)
        entry = info_root.find("entry")
        if entry is None:
            raise ValueError("缺少 entry")
        revision = entry.get("revision")
        raw_url = entry.findtext("url")
        url = _sanitize_repository_url(raw_url) if raw_url else None
        relative_url = entry.findtext("relative-url")
        wc_root = entry.findtext("wc-info/wcroot-abspath")
    except (ET.ParseError, ValueError):
        return RepositoryState(
            True,
            True,
            note="无法解析 SVN info XML",
            provider="svn",
            root=str(marker_root) if marker_root else None,
        )

    status_result = _run([svn, "status", "--xml", str(project)], project, timeout=15)
    if status_result.returncode != 0:
        return RepositoryState(
            True,
            True,
            relative_url,
            revision,
            False,
            (),
            "无法读取 SVN 工作副本状态",
            "svn",
            revision,
            url,
            wc_root,
        )
    try:
        all_changes = _parse_svn_status(status_result.stdout, project)
        changes, note = _bounded_changes(all_changes, 0, "SVN")
    except ET.ParseError:
        changes, note = (), "无法解析 SVN status XML"
    return RepositoryState(
        True,
        True,
        relative_url,
        revision,
        bool(changes),
        changes,
        note,
        "svn",
        revision,
        url,
        wc_root,
    )


def _parse_svn_status(xml_text: str, project: Path) -> tuple[str, ...]:
    status_root = ET.fromstring(xml_text)
    changes: list[str] = []
    item_codes = {
        "modified": "M",
        "added": "A",
        "deleted": "D",
        "replaced": "R",
        "conflicted": "C",
        "unversioned": "?",
        "missing": "!",
        "obstructed": "~",
        "ignored": "I",
        "external": "X",
        "incomplete": "!",
    }
    for entry in status_root.findall(".//entry"):
        wc_status = entry.find("wc-status")
        if wc_status is None:
            continue
        item = wc_status.get("item", "normal")
        props = wc_status.get("props", "none")
        if item == "normal" and props in {"none", "normal"}:
            continue
        item_code = item_codes.get(item, " ")
        props_code = "M" if props == "modified" else " "
        display_path = _relative_display_path(entry.get("path", ""), project)
        changes.append(f"{item_code}{props_code} {display_path}")
    return tuple(changes)


def _relative_display_path(raw_path: str, project: Path) -> str:
    path = Path(raw_path)
    try:
        resolved = path.resolve() if path.is_absolute() else (project / path).resolve()
        relative = resolved.relative_to(project)
        return relative.as_posix() or "."
    except (OSError, ValueError):
        return raw_path.replace("\\", "/") or "."


def _nearest_marker(project: Path, marker_name: str) -> tuple[int, Path] | None:
    for distance, candidate in enumerate((project, *project.parents)):
        if (candidate / marker_name).exists():
            return distance, candidate
    return None


def _sanitize_repository_url(url: str) -> str:
    """移除标准 URL 中可能包含用户名或令牌的 userinfo。"""
    parsed = urlsplit(url)
    if not parsed.netloc or "@" not in parsed.netloc:
        return url
    safe_netloc = parsed.netloc.rsplit("@", 1)[1]
    return urlunsplit((parsed.scheme, safe_netloc, parsed.path, parsed.query, parsed.fragment))


def _bounded_changes(
    all_changes: tuple[str, ...], returncode: int, provider: str
) -> tuple[tuple[str, ...], str | None]:
    changes = all_changes[:200]
    if returncode != 0:
        return changes, f"无法读取 {provider} 工作区状态"
    if len(all_changes) > len(changes):
        return changes, f"工作区共有 {len(all_changes)} 条变更，仅保留前 {len(changes)} 条"
    return changes, None


def _run(
    command: list[str], cwd: Path, *, timeout: int = 5
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(command, 1, "", str(exc))
