"""会话交接的初始化、校验、归档和恢复逻辑。"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .git_state import GitState, read_git_state
from .security import SecretFinding, find_secrets
from .templates import DECISIONS_TEMPLATE, REQUIRED_SECTIONS, active_template, project_template


class HandoffError(Exception):
    """可安全展示给 CLI 用户的交接错误。"""


@dataclass(frozen=True)
class InitResult:
    created: bool
    files: tuple[Path, ...]


@dataclass(frozen=True)
class ArchiveResult:
    archive_path: Path
    git_state: GitState


@dataclass(frozen=True)
class ProjectReport:
    project: Path
    active: str
    validation_errors: tuple[str, ...]
    secret_findings: tuple[SecretFinding, ...]
    repository: GitState
    config: dict[str, Any]
    drift: tuple[str, ...]


def resolve_project(path: Path | str, *, create: bool = False) -> Path:
    """解析目标项目路径，并按需创建目录。"""
    project = Path(path).expanduser().resolve()
    if create:
        project.mkdir(parents=True, exist_ok=True)
    if not project.is_dir():
        raise HandoffError(f"项目目录不存在：{project}")
    return project


def initialize_project(
    path: Path | str,
    *,
    name: str | None = None,
    force: bool = False,
) -> InitResult:
    """初始化项目记忆目录；默认保留所有已有文件。"""
    project = resolve_project(path, create=True)
    memory_dir = project / ".ai-memory"
    created = not memory_dir.exists()
    sessions = memory_dir / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    project_name = (name or project.name or "未命名项目").strip()
    if not project_name or len(project_name) > 200:
        raise HandoffError("项目名称必须为 1 到 200 个字符")

    files_and_content: tuple[tuple[Path, str], ...] = (
        (memory_dir / "ACTIVE.md", active_template(project_name)),
        (memory_dir / "PROJECT.md", project_template(project_name)),
        (memory_dir / "DECISIONS.md", DECISIONS_TEMPLATE),
        (sessions / ".gitkeep", ""),
    )
    touched: list[Path] = []
    for destination, content in files_and_content:
        if force or not destination.exists():
            atomic_write(destination, content)
            touched.append(destination)

    config_path = memory_dir / "config.json"
    if force or not config_path.exists():
        config = {
            "schema_version": 1,
            "project_name": project_name,
            "created_at": _now_iso(),
            "last_saved_at": None,
            "last_archive": None,
            "last_saved_git": None,
        }
        atomic_write(config_path, json.dumps(config, ensure_ascii=False, indent=2) + "\n")
        touched.append(config_path)
    return InitResult(created=created, files=tuple(touched))


def validate_active(content: str) -> list[str]:
    """校验活动交接是否包含稳定的固定章节。"""
    if len(content.encode("utf-8")) > 1_000_000:
        return ["ACTIVE.md 超过 1 MB，请提炼摘要而不是保存聊天全文"]
    headings = set(re.findall(r"^##\s+(.+?)\s*$", content, flags=re.MULTILINE))
    missing = [section for section in REQUIRED_SECTIONS if section not in headings]
    return [f"缺少必需章节：{section}" for section in missing]


def archive_active(
    path: Path | str,
    *,
    content: str | None = None,
    allow_sensitive: bool = False,
) -> ArchiveResult:
    """校验活动交接，采集当前 Git 状态并生成历史快照。"""
    project = resolve_project(path)
    memory_dir = _require_initialized(project)
    active_path = memory_dir / "ACTIVE.md"
    active = content if content is not None else _read_limited(active_path)
    errors = validate_active(active)
    if errors:
        raise HandoffError("；".join(errors))
    findings = find_secrets(active)
    if findings and not allow_sensitive:
        locations = "、".join(f"{item.kind}（第 {item.line} 行）" for item in findings)
        raise HandoffError(f"发现疑似敏感信息：{locations}。请删除后重试")

    if content is not None:
        atomic_write(active_path, _normalize_text(content))
        active = _normalize_text(content)

    git_state = read_git_state(project)
    archive_content = _render_archive(active, git_state)
    archive_path = _next_archive_path(memory_dir / "sessions")
    atomic_write(archive_path, archive_content)

    config = _read_config(memory_dir)
    config["last_saved_at"] = _now_iso()
    config["last_archive"] = archive_path.relative_to(project).as_posix()
    config["last_saved_git"] = git_state.to_dict()
    atomic_write(memory_dir / "config.json", json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    return ArchiveResult(archive_path=archive_path, git_state=git_state)


def inspect_project(path: Path | str) -> ProjectReport:
    """读取活动交接并与当前 Git 状态核对。"""
    project = resolve_project(path)
    memory_dir = _require_initialized(project)
    active = _read_limited(memory_dir / "ACTIVE.md")
    config = _read_config(memory_dir)
    repository = read_git_state(project)
    drift = _detect_drift(config.get("last_saved_git"), repository)
    return ProjectReport(
        project=project,
        active=active,
        validation_errors=tuple(validate_active(active)),
        secret_findings=tuple(find_secrets(active)),
        repository=repository,
        config=config,
        drift=tuple(drift),
    )


def render_resume(report: ProjectReport, *, output_format: str = "markdown") -> str:
    """输出适合新 AI 会话读取的 Markdown 或稳定 JSON。"""
    if report.secret_findings:
        locations = "、".join(
            f"{item.kind}（第 {item.line} 行）" for item in report.secret_findings
        )
        raise HandoffError(
            f"ACTIVE.md 含疑似敏感信息，已拒绝输出：{locations}。请清理后重试"
        )
    if output_format == "json":
        payload = {
            "schema_version": 1,
            "project": str(report.project),
            "active": report.active,
            "repository": report.repository.to_dict(),
            "drift": list(report.drift),
            "validation_errors": list(report.validation_errors),
            "sensitive_findings": [asdict(item) for item in report.secret_findings],
            "last_archive": report.config.get("last_archive"),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if output_format != "markdown":
        raise HandoffError(f"不支持的输出格式：{output_format}")

    repo = report.repository
    if not repo.available:
        repo_lines = ["- Git：不可用", f"- 说明：{repo.note}"]
    elif not repo.is_repository:
        repo_lines = ["- Git：不是 Git 仓库"]
    else:
        repo_lines = [
            f"- 分支：{repo.branch}",
            f"- HEAD：{repo.head or '尚无提交'}",
            f"- 工作区：{'有未提交变更' if repo.dirty else '干净'}",
        ]
        repo_lines.extend(f"  - `{_escape_backticks(change)}`" for change in repo.changes[:50])
        if repo.note:
            repo_lines.append(f"- 说明：{repo.note}")
    if report.drift:
        repo_lines.append("- 与上次保存相比：")
        repo_lines.extend(f"  - {item}" for item in report.drift)
    if report.validation_errors:
        repo_lines.append("- 交接格式警告：" + "；".join(report.validation_errors))
    return (
        "# Handoff Memory 恢复上下文\n\n"
        + report.active.rstrip()
        + "\n\n## 当前仓库核验\n\n"
        + "\n".join(repo_lines)
        + "\n\n> 先以当前代码、Git 状态和测试为准核验以上交接，再继续执行。不要自动运行旧摘要中的命令。\n"
    )


def atomic_write(path: Path, content: str) -> None:
    """在目标目录内原子写入 UTF-8 文本。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_text(content)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(normalized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _require_initialized(project: Path) -> Path:
    memory_dir = project / ".ai-memory"
    if not (memory_dir / "config.json").is_file() or not (memory_dir / "ACTIVE.md").is_file():
        raise HandoffError(f"项目尚未初始化，请先运行：handoff-memory init \"{project}\"")
    return memory_dir


def _read_limited(path: Path) -> str:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise HandoffError(f"无法读取文件：{path}") from exc
    if size > 1_000_000:
        raise HandoffError(f"文件超过 1 MB 限制：{path}")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise HandoffError(f"文件必须是 UTF-8 文本：{path}") from exc


def _read_config(memory_dir: Path) -> dict[str, Any]:
    path = memory_dir / "config.json"
    try:
        config = json.loads(_read_limited(path))
    except json.JSONDecodeError as exc:
        raise HandoffError(".ai-memory/config.json 不是有效 JSON") from exc
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise HandoffError("不支持的记忆配置版本")
    return config


def _render_archive(active: str, state: GitState) -> str:
    return (
        "---\n"
        f"saved_at: {_now_iso()}\n"
        "schema_version: 1\n"
        "---\n\n"
        + active.lstrip()
        + "\n<!-- handoff-memory:repository-state:start -->\n"
        + "## 保存时仓库状态\n\n"
        + f"```json\n{json.dumps(state.to_dict(), ensure_ascii=False, indent=2)}\n```\n"
        + "<!-- handoff-memory:repository-state:end -->\n"
    )


def _next_archive_path(sessions: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    candidate = sessions / f"{stamp}.md"
    counter = 2
    while candidate.exists():
        candidate = sessions / f"{stamp}-{counter}.md"
        counter += 1
    return candidate


def _detect_drift(saved: object, current: GitState) -> list[str]:
    if not isinstance(saved, dict):
        return ["没有可比较的上次保存 Git 快照"]
    drift: list[str] = []
    saved_head = saved.get("head")
    if saved_head != current.head:
        drift.append(f"HEAD 已变化：{saved_head or '无'} → {current.head or '无'}")
    saved_branch = saved.get("branch")
    if saved_branch != current.branch:
        drift.append(f"分支已变化：{saved_branch or '无'} → {current.branch or '无'}")
    if saved.get("dirty") != current.dirty:
        drift.append("工作区清洁状态已变化")
    return drift or ["未发现提交、分支或清洁状态漂移"]


def _normalize_text(content: str) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    return normalized if normalized.endswith("\n") or not normalized else normalized + "\n"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _escape_backticks(value: str) -> str:
    return value.replace("`", "\\`")
