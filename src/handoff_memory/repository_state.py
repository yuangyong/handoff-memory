"""自动识别并只读采集 Git 或 SVN 版本库状态。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit


class _Digest(Protocol):
    def update(self, data: bytes) -> object:
        """加入摘要数据。"""


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
    status_available: bool | None = None
    worktree_sha256: str | None = None
    worktree_change_count: int | None = None

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
            status_available=False if marker_root else None,
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
        [
            git,
            "-C",
            str(project),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            ".",
            ":(exclude).ai-memory/config.json",
            ":(exclude,glob).ai-memory/sessions/**",
            ":(exclude,glob).ai-memory/**/*.tmp",
            ":(exclude,glob).ai-memory/**/*.lock",
        ],
        project,
    )
    all_changes = tuple(line for line in status_result.stdout.splitlines() if line)
    changes, note = _bounded_changes(all_changes, status_result.returncode, "Git")
    status_available = status_result.returncode == 0
    fingerprint_paths: tuple[str, ...] = ()
    index_payload = ""
    fingerprint_available = status_available
    if status_available:
        pathspec = [
            "--",
            ".",
            ":(exclude).ai-memory/config.json",
            ":(exclude,glob).ai-memory/sessions/**",
            ":(exclude,glob).ai-memory/**/*.tmp",
            ":(exclude,glob).ai-memory/**/*.lock",
        ]
        path_results = [
            _run([git, "-C", str(project), "diff", "--name-only", "-z", *pathspec], project),
            _run([git, "-C", str(project), "diff", "--cached", "--name-only", "-z", *pathspec], project),
            _run([git, "-C", str(project), "ls-files", "--others", "--exclude-standard", "-z", *pathspec], project),
        ]
        index_result = _run(
            [git, "-C", str(project), "diff", "--cached", "--raw", "--no-abbrev", "-z", *pathspec],
            project,
        )
        fingerprint_available = all(item.returncode == 0 for item in path_results) and index_result.returncode == 0
        if fingerprint_available:
            fingerprint_paths = tuple(
                sorted(
                    {
                        path
                        for result in path_results
                        for path in result.stdout.split("\0")
                        if path and not _is_internal_handoff_path(path)
                    }
                )
            )
            index_payload = index_result.stdout
    worktree_sha256, worktree_change_count = _worktree_metadata(
        all_changes if fingerprint_available else None,
        project=project,
        changed_paths=fingerprint_paths,
        extra_payload=index_payload,
    )
    if status_available and worktree_sha256 is None:
        note = _join_note(note, "无法完整计算 Git 工作区内容指纹")
    return RepositoryState(
        available=True,
        is_repository=True,
        branch=branch,
        head=head,
        dirty=bool(changes),
        changes=changes,
        note=note,
        provider="git",
        revision=head,
        url=url,
        root=repository_root,
        status_available=status_available,
        worktree_sha256=worktree_sha256,
        worktree_change_count=worktree_change_count,
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
            status_available=False if marker_root else None,
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
            status_available=False,
        )

    status_result = _run([svn, "status", "--xml", str(project)], project, timeout=15)
    if status_result.returncode != 0:
        return RepositoryState(
            available=True,
            is_repository=True,
            branch=relative_url,
            head=revision,
            note="无法读取 SVN 工作副本状态",
            provider="svn",
            revision=revision,
            url=url,
            root=wc_root,
            status_available=False,
        )
    try:
        all_changes = _parse_svn_status(status_result.stdout, project)
        changes, note = _bounded_changes(all_changes, 0, "SVN")
        status_available = True
    except ET.ParseError:
        all_changes = ()
        changes, note = (), "无法解析 SVN status XML"
        status_available = False
    property_payload = ""
    property_available = status_available
    if status_available:
        property_paths = tuple(
            sorted(line[3:] for line in all_changes if len(line) > 3 and line[1] == "M")
        )
        property_parts: list[str] = []
        for relative in property_paths:
            property_result = _run(
                [svn, "proplist", "--verbose", "--xml", str(project / relative)],
                project,
                timeout=10,
            )
            if property_result.returncode != 0:
                property_available = False
                break
            property_parts.append(f"{relative}\0{property_result.stdout}")
        property_payload = "\0".join(property_parts)
    worktree_sha256, worktree_change_count = _worktree_metadata(
        all_changes if property_available else None,
        project=project,
        changed_paths=_paths_from_display_changes(all_changes),
        extra_payload=property_payload,
    )
    if status_available and worktree_sha256 is None:
        note = _join_note(note, "无法完整计算 SVN 工作区内容指纹")
    return RepositoryState(
        available=True,
        is_repository=True,
        branch=relative_url,
        head=revision,
        dirty=bool(changes),
        changes=changes,
        note=note,
        provider="svn",
        revision=revision,
        url=url,
        root=wc_root,
        status_available=status_available,
        worktree_sha256=worktree_sha256,
        worktree_change_count=worktree_change_count,
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
        if item == "unversioned" and display_path.rstrip("/") == ".ai-memory":
            active_path = project / ".ai-memory" / "ACTIVE.md"
            if active_path.is_file():
                changes.append(f"{item_code}{props_code} .ai-memory/ACTIVE.md")
            continue
        if _is_internal_handoff_path(display_path):
            continue
        changes.append(f"{item_code}{props_code} {display_path}")
    return tuple(changes)


def _is_internal_handoff_path(display_path: str) -> bool:
    """识别不应参与工作区漂移判断的 Handoff Memory 内部文件。"""
    normalized = display_path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized.startswith(".ai-memory/"):
        return False
    relative = normalized.removeprefix(".ai-memory/")
    return (
        relative == "config.json"
        or relative.startswith("sessions/")
        or relative.endswith(".tmp")
        or relative.endswith(".lock")
    )


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
    """移除标准 URL 的 userinfo、查询参数和片段，避免凭据进入快照。"""
    parsed = urlsplit(url)
    # scp-like SSH 没有标准 URL netloc；常见 git/ssh 用户名可保留，
    # 其他身份位保守脱敏，并移除可能携带凭据的问号或井号后缀。
    if not parsed.netloc and "://" not in url:
        match = re.fullmatch(r"([^/@:]+)@(\[[^]]+\]|[^:]+):(.+)", url)
        if match:
            safe_path = re.split(r"[?#]", match.group(3), maxsplit=1)[0]
            user = (
                match.group(1)
                if match.group(1).casefold() in {"git", "ssh", "svn", "hg"}
                else "redacted"
            )
            return f"{user}@{match.group(2)}:{safe_path}"
        return url
    safe_netloc = parsed.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parsed.scheme, safe_netloc, parsed.path, "", ""))


def _bounded_changes(
    all_changes: tuple[str, ...], returncode: int, provider: str
) -> tuple[tuple[str, ...], str | None]:
    changes = all_changes[:200]
    if returncode != 0:
        return changes, f"无法读取 {provider} 工作区状态"
    if len(all_changes) > len(changes):
        return changes, f"工作区共有 {len(all_changes)} 条变更，仅保留前 {len(changes)} 条"
    return changes, None


def _worktree_metadata(
    all_changes: tuple[str, ...] | None,
    *,
    project: Path | None = None,
    changed_paths: tuple[str, ...] = (),
    extra_payload: str = "",
) -> tuple[str | None, int | None]:
    """基于完整状态、索引信息和变更文件内容计算稳定摘要。"""
    if all_changes is None:
        return None, None
    normalized = tuple(sorted(all_changes))
    digest = hashlib.sha256()
    digest.update(
        json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    digest.update(b"\0index\0")
    digest.update(extra_payload.encode("utf-8", errors="replace"))
    if project is not None:
        for relative in sorted(set(changed_paths)):
            if not _update_path_digest(digest, project, relative):
                return None, len(normalized)
    return digest.hexdigest(), len(normalized)


def _paths_from_display_changes(changes: tuple[str, ...]) -> tuple[str, ...]:
    """从统一状态展示行提取路径，供 SVN 内容摘要使用。"""
    return tuple(
        line[3:]
        for line in changes
        if len(line) > 3 and not _is_internal_handoff_path(line[3:])
    )


def _update_path_digest(digest: _Digest, project: Path, relative: str) -> bool:
    """流式加入单个变更路径；读取不稳定或越界时返回未知。"""
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return False
    path = project / relative_path
    try:
        path.resolve(strict=False).relative_to(project)
        stat_before = path.lstat()
    except FileNotFoundError:
        digest.update(f"\0missing\0{relative}".encode("utf-8"))
        return True
    except (OSError, ValueError):
        return False
    digest.update(f"\0path\0{relative}\0{stat_before.st_mode}".encode("utf-8"))
    try:
        if path.is_symlink():
            digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
        elif path.is_file():
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
        elif path.is_dir():
            for child in sorted(path.iterdir(), key=lambda item: item.name):
                if child.name in {".git", ".svn"}:
                    continue
                child_relative = child.relative_to(project).as_posix()
                if _is_internal_handoff_path(child_relative):
                    continue
                if not _update_path_digest(digest, project, child_relative):
                    return False
        stat_after = path.lstat()
    except (OSError, UnicodeError):
        return False
    return (
        stat_before.st_size == stat_after.st_size
        and stat_before.st_mtime_ns == stat_after.st_mtime_ns
        and stat_before.st_mode == stat_after.st_mode
    )


def _join_note(current: str | None, addition: str) -> str:
    return f"{current}；{addition}" if current else addition


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
