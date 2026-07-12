"""向不同 AI 客户端写入幂等的项目级接入规则。"""

from __future__ import annotations

from pathlib import Path

from .core import atomic_write, resolve_project
from .templates import CURSOR_RULE, GENERIC_RULE, SKILL_TEMPLATE


TARGETS = ("generic", "codex", "claude", "cursor", "gemini", "skill", "all")
_START = "<!-- handoff-memory:start -->"
_END = "<!-- handoff-memory:end -->"


def integrate(path: Path | str, target: str) -> list[Path]:
    """生成指定 AI 工具适配；重复执行只更新受管区块。"""
    project = resolve_project(path)
    if target not in TARGETS:
        raise ValueError(f"未知接入目标：{target}")
    targets = ("generic", "codex", "claude", "cursor", "gemini", "skill") if target == "all" else (target,)
    changed: list[Path] = []
    for item in targets:
        destination, content, managed_block = _adapter(project, item)
        before = destination.read_text(encoding="utf-8") if destination.exists() else ""
        after = _merge_managed_block(before, content) if managed_block else content
        if before != after:
            atomic_write(destination, after)
            changed.append(destination)
    return changed


def _adapter(project: Path, target: str) -> tuple[Path, str, bool]:
    if target == "generic":
        return project / "AI-HANDOFF.md", "# AI 会话交接\n\n" + GENERIC_RULE + "\n", True
    if target == "codex":
        return project / "AGENTS.md", GENERIC_RULE + "\n", True
    if target == "claude":
        return project / "CLAUDE.md", GENERIC_RULE + "\n", True
    if target == "gemini":
        return project / "GEMINI.md", GENERIC_RULE + "\n", True
    if target == "cursor":
        return project / ".cursor/rules/handoff-memory.mdc", CURSOR_RULE, False
    if target == "skill":
        return project / ".agents/skills/session-handoff/SKILL.md", SKILL_TEMPLATE, False
    raise ValueError(f"未知接入目标：{target}")


def _merge_managed_block(existing: str, content: str) -> str:
    payload = _extract_managed_block(content)
    start = existing.find(_START)
    end = existing.find(_END)
    if start >= 0 and end >= start:
        end += len(_END)
        merged = existing[:start].rstrip() + "\n\n" + payload + existing[end:]
        return merged.strip() + "\n"
    if not existing.strip():
        return content.strip() + "\n"
    return existing.rstrip() + "\n\n" + content.strip() + "\n"


def _extract_managed_block(content: str) -> str:
    """从带前言的模板中提取唯一受管区块。"""
    start = content.find(_START)
    end = content.find(_END)
    if start < 0 or end < start:
        raise ValueError("接入模板缺少 Handoff Memory 受管标记")
    return content[start : end + len(_END)].strip()
