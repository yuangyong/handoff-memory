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
_MANAGED_SKILL_FIELDS = ("name", "description")


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
            # Skill 的触发条件位于 frontmatter，升级时必须同步；受管区块外的
            # 用户正文仍需保留。规则文件则只替换受管区块。
            after = (
                _merge_skill(before, content)
                if content == SKILL_TEMPLATE
                else _merge_managed_block(before, content)
            )
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
    bounds = _managed_block_bounds(existing, required=False, source="现有文件")
    if bounds is not None:
        start, end = bounds
        merged = existing[:start].rstrip() + "\n\n" + payload + existing[end:]
        return merged.strip() + "\n"
    if not existing.strip():
        return content.strip() + "\n"
    return existing.rstrip() + "\n\n" + payload + "\n"


def _merge_skill(existing: str, content: str) -> str:
    """升级 Skill 元数据和受管正文，同时保留用户自定义正文。"""
    if not existing.strip():
        return content.strip() + "\n"

    template_fields, template_body = _split_skill_frontmatter(content, "Skill 模板")
    existing_fields, existing_body = _split_skill_frontmatter(existing, "现有 Skill")
    merged_fields = _merge_skill_frontmatter(existing_fields, template_fields)

    # Skill frontmatter 与正文分别合并，避免替换元数据时吞掉用户正文。
    # 这里只传递模板的受管正文，不能把模板 frontmatter 重复附加到正文中。
    managed_body = _extract_managed_block(template_body) + "\n"
    merged_body = _merge_managed_block(existing_body, managed_body).lstrip("\n")
    frontmatter = "---\n" + "\n".join(merged_fields) + "\n---"
    return frontmatter + ("\n\n" + merged_body if merged_body else "\n")


def _split_skill_frontmatter(content: str, source: str) -> tuple[list[str], str]:
    """拆分 Skill frontmatter；格式不完整时拒绝猜测或修复。"""
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ValueError(f"{source} 缺少 YAML frontmatter 开始分隔符")

    end_index = next(
        (
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.rstrip("\r\n") == "---"
        ),
        None,
    )
    if end_index is None:
        raise ValueError(f"{source} 缺少 YAML frontmatter 结束分隔符")

    fields = [line.rstrip("\r\n") for line in lines[1:end_index]]
    body = "".join(lines[end_index + 1 :]).lstrip("\r\n")
    return fields, body


def _merge_skill_frontmatter(
    existing: list[str], template: list[str]
) -> list[str]:
    """只升级项目管理的字段，保留客户端或用户添加的其他字段。"""
    template_values = _managed_frontmatter_values(template, "Skill 模板")
    _managed_frontmatter_values(existing, "现有 Skill")

    merged: list[str] = []
    seen: set[str] = set()
    last_managed_index = -1
    for line in existing:
        key = _managed_frontmatter_key(line)
        if key is None:
            merged.append(line)
            continue
        merged.append(template_values[key])
        seen.add(key)
        last_managed_index = len(merged) - 1

    missing = [key for key in _MANAGED_SKILL_FIELDS if key not in seen]
    insertion = last_managed_index + 1
    for key in missing:
        merged.insert(insertion, template_values[key])
        insertion += 1
    return merged


def _managed_frontmatter_values(lines: list[str], source: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        key = _managed_frontmatter_key(line)
        if key is None:
            continue
        if key in values:
            raise ValueError(f"{source} 的 frontmatter 包含重复字段：{key}")
        value = line.partition(":")[2].strip()
        if not value or value in {"|", ">", "|-", ">-", "|+", ">+"}:
            raise ValueError(f"{source} 的 frontmatter 字段必须是单行值：{key}")
        values[key] = line

    missing = [key for key in _MANAGED_SKILL_FIELDS if key not in values]
    if source == "Skill 模板" and missing:
        raise ValueError(f"Skill 模板缺少受管 frontmatter 字段：{', '.join(missing)}")
    return values


def _managed_frontmatter_key(line: str) -> str | None:
    if not line or line[0].isspace() or line.startswith("#"):
        return None
    key, separator, _ = line.partition(":")
    return key if separator and key in _MANAGED_SKILL_FIELDS else None


def _extract_managed_block(content: str) -> str:
    """从带前言的模板中提取唯一受管区块。"""
    bounds = _managed_block_bounds(content, required=True, source="接入模板")
    assert bounds is not None
    start, end = bounds
    return content[start:end].strip()


def _managed_block_bounds(
    content: str,
    *,
    required: bool,
    source: str,
) -> tuple[int, int] | None:
    """返回唯一受管区块范围；单边、重复或乱序标记均视为损坏。"""
    starts = _marker_positions(content, _START)
    ends = _marker_positions(content, _END)
    if not starts and not ends:
        if required:
            raise ValueError(f"{source} 缺少 Handoff Memory 受管标记")
        return None
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        raise ValueError(f"{source} 的 Handoff Memory 受管标记不完整、重复或顺序错误")
    return starts[0], ends[0] + len(_END)


def _marker_positions(content: str, marker: str) -> list[int]:
    positions: list[int] = []
    start = 0
    while (position := content.find(marker, start)) >= 0:
        positions.append(position)
        start = position + len(marker)
    return positions
