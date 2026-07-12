"""向不同 AI 客户端写入幂等的项目规则与原生项目级 Skill。"""

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
    "antigravity",
    "copilot",
    "windsurf",
    "cline",
    "kiro",
    "trae",
    "qoder",
    "opencode",
)
PROJECT_SKILL_PATHS = {
    "codex": ".agents/skills/session-handoff/SKILL.md",
    "claude": ".claude/skills/session-handoff/SKILL.md",
    "cursor": ".cursor/skills/session-handoff/SKILL.md",
    "gemini": ".gemini/skills/session-handoff/SKILL.md",
    "antigravity": ".agents/skills/session-handoff/SKILL.md",
    "copilot": ".github/skills/session-handoff/SKILL.md",
    "windsurf": ".windsurf/skills/session-handoff/SKILL.md",
    "cline": ".cline/skills/session-handoff/SKILL.md",
    "kiro": ".kiro/skills/session-handoff/SKILL.md",
    "trae": ".trae/skills/session-handoff/SKILL.md",
    "qoder": ".qoder/skills/session-handoff/SKILL.md",
    "opencode": ".opencode/skills/session-handoff/SKILL.md",
}
TARGETS = ("generic", *AI_TOOL_TARGETS, "skill", "all")
_START = "<!-- handoff-memory:start -->"
_END = "<!-- handoff-memory:end -->"


def integrate(
    path: Path | str,
    target: str,
    *,
    with_rules: bool = False,
) -> list[Path]:
    """生成指定 AI 工具 Skill，并按显式选项生成规则。"""
    project = resolve_project(path)
    if target not in TARGETS:
        raise ValueError(f"未知接入目标：{target}")
    if with_rules and target not in {*AI_TOOL_TARGETS, "all"}:
        raise ValueError("--with-rules 仅适用于具名客户端或 all 接入目标")
    targets = AI_TOOL_TARGETS if target == "all" else (target,)
    changed: list[Path] = []
    for item in targets:
        adapters = _adapters(
            project,
            item,
            with_rules=with_rules,
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
    with_rules: bool = False,
) -> tuple[tuple[Path, str], ...]:
    if target == "generic":
        return ((project / "AI-HANDOFF.md", "# AI 会话交接\n\n" + GENERIC_RULE + "\n"),)
    if target == "codex":
        adapters = list(_with_project_skill(project, target))
        if with_rules:
            adapters.append((project / "AGENTS.md", AGENTS_ROUTING_RULE + "\n"))
        return tuple(adapters)
    if target == "claude":
        return _with_optional_rule(
            project,
            target,
            (project / "CLAUDE.md", GENERIC_RULE + "\n"),
            with_rules=with_rules,
        )
    if target == "gemini":
        return _with_optional_rule(
            project,
            target,
            (project / "GEMINI.md", GENERIC_RULE + "\n"),
            with_rules=with_rules,
        )
    if target == "cursor":
        return _with_optional_rule(
            project,
            target,
            (project / ".cursor/rules/handoff-memory.mdc", CURSOR_RULE),
            with_rules=with_rules,
        )
    if target == "copilot":
        return _with_optional_rule(
            project,
            target,
            (project / ".github/copilot-instructions.md", GENERIC_RULE + "\n"),
            with_rules=with_rules,
        )
    if target == "windsurf":
        return _with_optional_rule(
            project,
            target,
            (project / ".windsurf/rules/handoff-memory.md", WINDSURF_RULE),
            with_rules=with_rules,
        )
    if target == "cline":
        return _with_optional_rule(
            project,
            target,
            (project / ".clinerules/handoff-memory.md", GENERIC_RULE + "\n"),
            with_rules=with_rules,
        )
    if target == "kiro":
        return _with_optional_rule(
            project,
            target,
            (project / ".kiro/steering/handoff-memory.md", KIRO_RULE),
            with_rules=with_rules,
        )
    if target == "trae":
        return _with_optional_rule(
            project,
            target,
            (project / ".trae/rules/project_rules.md", GENERIC_RULE + "\n"),
            with_rules=with_rules,
        )
    if target == "qoder":
        return _with_optional_rule(
            project,
            target,
            (project / ".qoder/rules/handoff-memory.md", GENERIC_RULE + "\n"),
            with_rules=with_rules,
        )
    if target == "antigravity":
        return _with_optional_rule(
            project,
            target,
            (
                project / ".agents/rules/handoff-memory.md",
                AGENTS_ROUTING_RULE + "\n",
            ),
            with_rules=with_rules,
        )
    if target == "opencode":
        adapters = list(_with_project_skill(project, target))
        if with_rules:
            adapters.append((project / "AGENTS.md", AGENTS_ROUTING_RULE + "\n"))
        return tuple(adapters)
    if target == "skill":
        return ((project / ".agents/skills/session-handoff/SKILL.md", SKILL_TEMPLATE),)
    raise ValueError(f"未知接入目标：{target}")


def _with_project_skill(
    project: Path,
    target: str,
    *adapters: tuple[Path, str],
) -> tuple[tuple[Path, str], ...]:
    """在客户端规则之后追加其原生项目级 session-handoff Skill。"""
    skill = (project / PROJECT_SKILL_PATHS[target], SKILL_TEMPLATE)
    return (*adapters, skill)


def _with_optional_rule(
    project: Path,
    target: str,
    rule: tuple[Path, str],
    *,
    with_rules: bool,
) -> tuple[tuple[Path, str], ...]:
    """默认只生成 Skill；显式开启后在 Skill 前追加客户端规则。"""
    adapters = (rule,) if with_rules else ()
    return _with_project_skill(project, target, *adapters)


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
