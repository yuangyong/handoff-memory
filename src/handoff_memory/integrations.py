"""向不同 AI 客户端写入幂等的项目级接入规则。"""

from __future__ import annotations

from pathlib import Path

from .core import atomic_write, resolve_project
from .templates import (
    AGENTS_ROUTING_RULE,
    CURSOR_RULE,
    GENERIC_RULE,
    KIRO_RULE,
    SKILL_TEMPLATE,
    WINDSURF_RULE,
)


AI_TOOL_TARGETS = (
    "codex",
    "claude",
    "cursor",
    "gemini",
    "copilot",
    "windsurf",
    "cline",
    "kiro",
    "trae",
    "qoder",
    "opencode",
)
TARGETS = ("generic", *AI_TOOL_TARGETS, "skill", "all")
_START = "<!-- handoff-memory:start -->"
_END = "<!-- handoff-memory:end -->"


def integrate(
    path: Path | str,
    target: str,
    *,
    with_agents_rule: bool = False,
) -> list[Path]:
    """生成指定 AI 工具适配；重复执行只更新受管区块。"""
    project = resolve_project(path)
    if target not in TARGETS:
        raise ValueError(f"未知接入目标：{target}")
    if with_agents_rule and target not in {"codex", "opencode", "all"}:
        raise ValueError("--with-agents-rule 仅适用于 codex、opencode 或 all 接入目标")
    targets = ("generic", *AI_TOOL_TARGETS, "skill") if target == "all" else (target,)
    changed: list[Path] = []
    for item in targets:
        adapters = _adapters(
            project,
            item,
            with_agents_rule=(with_agents_rule and item in {"codex", "opencode"}),
        )
        for destination, content in adapters:
            before = destination.read_text(encoding="utf-8") if destination.exists() else ""
            after = _merge_managed_block(before, content)
            if before != after:
                atomic_write(destination, after)
                changed.append(destination)
    return changed


def _adapters(
    project: Path,
    target: str,
    *,
    with_agents_rule: bool = False,
) -> tuple[tuple[Path, str], ...]:
    if target == "generic":
        return ((project / "AI-HANDOFF.md", "# AI 会话交接\n\n" + GENERIC_RULE + "\n"),)
    if target == "codex":
        adapters = [
            (project / ".agents/skills/session-handoff/SKILL.md", SKILL_TEMPLATE)
        ]
        if with_agents_rule:
            adapters.append((project / "AGENTS.md", AGENTS_ROUTING_RULE + "\n"))
        return tuple(adapters)
    if target == "claude":
        return ((project / "CLAUDE.md", GENERIC_RULE + "\n"),)
    if target == "gemini":
        return ((project / "GEMINI.md", GENERIC_RULE + "\n"),)
    if target == "cursor":
        return ((project / ".cursor/rules/handoff-memory.mdc", CURSOR_RULE),)
    if target == "copilot":
        return ((project / ".github/copilot-instructions.md", GENERIC_RULE + "\n"),)
    if target == "windsurf":
        return ((project / ".windsurf/rules/handoff-memory.md", WINDSURF_RULE),)
    if target == "cline":
        return ((project / ".clinerules/handoff-memory.md", GENERIC_RULE + "\n"),)
    if target == "kiro":
        return ((project / ".kiro/steering/handoff-memory.md", KIRO_RULE),)
    if target == "trae":
        return ((project / ".trae/rules/project_rules.md", GENERIC_RULE + "\n"),)
    if target == "qoder":
        return ((project / ".qoder/rules/handoff-memory.md", GENERIC_RULE + "\n"),)
    if target == "opencode":
        adapters = [
            (project / ".opencode/skills/session-handoff/SKILL.md", SKILL_TEMPLATE)
        ]
        if with_agents_rule:
            adapters.append((project / "AGENTS.md", AGENTS_ROUTING_RULE + "\n"))
        return tuple(adapters)
    if target == "skill":
        return ((project / ".agents/skills/session-handoff/SKILL.md", SKILL_TEMPLATE),)
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
    return existing.rstrip() + "\n\n" + payload + "\n"


def _extract_managed_block(content: str) -> str:
    """从带前言的模板中提取唯一受管区块。"""
    start = content.find(_START)
    end = content.find(_END)
    if start < 0 or end < start:
        raise ValueError("接入模板缺少 Handoff Memory 受管标记")
    return content[start : end + len(_END)].strip()
