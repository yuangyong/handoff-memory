"""向不同 AI 客户端写入幂等的项目规则与原生项目级 Skill。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .core import atomic_write, resolve_project
from .templates import (
    AGENTS_ROUTING_RULE,
    CURSOR_RULE,
    GENERIC_RULE,
    KIRO_RULE,
    SKILL_TEMPLATES,
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
PROJECT_SKILL_ROOTS: dict[str, str] = {
    "codex": ".agents/skills",
    "claude": ".claude/skills",
    "cursor": ".cursor/skills",
    "gemini": ".gemini/skills",
    "antigravity": ".agents/skills",
    "copilot": ".github/skills",
    "windsurf": ".windsurf/skills",
    "cline": ".cline/skills",
    "kiro": ".kiro/skills",
    "trae": ".trae/skills",
    "qoder": ".qoder/skills",
    "opencode": ".opencode/skills",
}
GLOBAL_SKILL_ROOTS: dict[str, str] = {
    "codex": ".agents/skills",
    "claude": ".claude/skills",
    "cursor": ".cursor/skills",
    "gemini": ".gemini/skills",
    "antigravity": ".gemini/config/skills",
    "copilot": ".copilot/skills",
    "windsurf": ".codeium/windsurf/skills",
    "cline": ".cline/skills",
    "kiro": ".kiro/skills",
    "trae": ".trae/skills",
    "qoder": ".qoder/skills",
    "opencode": ".config/opencode/skills",
    "skill": ".agents/skills",
}
_PORTABLE_SKILL_ROOT = ".agents/skills"
_LEGACY_SKILL_NAME = "session-handoff"
SKILL_TARGETS = (*AI_TOOL_TARGETS, "skill", "all")
TARGETS = ("generic", *SKILL_TARGETS)
_START = "<!-- handoff-memory:start -->"
_END = "<!-- handoff-memory:end -->"
_MANAGED_SKILL_FIELDS = ("name", "description")

_PROJECT_RULE_ADAPTERS: dict[str, tuple[str, str]] = {
    "codex": ("AGENTS.md", AGENTS_ROUTING_RULE + "\n"),
    "claude": ("CLAUDE.md", GENERIC_RULE + "\n"),
    "gemini": ("GEMINI.md", GENERIC_RULE + "\n"),
    "cursor": (".cursor/rules/handoff-memory.mdc", CURSOR_RULE),
    "copilot": (".github/copilot-instructions.md", GENERIC_RULE + "\n"),
    "windsurf": (".windsurf/rules/handoff-memory.md", WINDSURF_RULE),
    "cline": (".clinerules/handoff-memory.md", GENERIC_RULE + "\n"),
    "kiro": (".kiro/steering/handoff-memory.md", KIRO_RULE),
    "trae": (".trae/rules/project_rules.md", GENERIC_RULE + "\n"),
    "qoder": (".qoder/rules/handoff-memory.md", GENERIC_RULE + "\n"),
    "antigravity": (".agents/rules/handoff-memory.md", AGENTS_ROUTING_RULE + "\n"),
    "opencode": ("AGENTS.md", AGENTS_ROUTING_RULE + "\n"),
}


@dataclass(frozen=True)
class SkillInstallResult:
    """双 Skill 安装或升级的结果。"""

    changed: tuple[Path, ...]
    skill_roots: tuple[Path, ...]
    legacy_skills: tuple[Path, ...]


@dataclass(frozen=True)
class SkillScopeStatus:
    """单个客户端在项目级或全局级的 Skill 状态。"""

    scope: str
    target: str
    root: Path
    skills: dict[str, str]
    legacy_path: Path | None = None


@dataclass(frozen=True)
class SkillsStatusReport:
    """项目级与用户全局级 Skill 只读状态汇总。"""

    project: Path
    home: Path
    entries: tuple[SkillScopeStatus, ...]
    legacy_skills: tuple[Path, ...]


def integrate(
    path: Path | str,
    target: str,
    *,
    with_rules: bool = False,
) -> list[Path]:
    """生成指定 AI 工具的项目级双 Skill，并按显式选项生成规则。"""
    project = resolve_project(path)
    if target not in TARGETS:
        raise ValueError(f"未知接入目标：{target}")
    if with_rules and target not in {*AI_TOOL_TARGETS, "all"}:
        raise ValueError("--with-rules 仅适用于具名客户端或 all 接入目标")
    targets = AI_TOOL_TARGETS if target == "all" else (target,)
    adapters = [
        adapter
        for item in targets
        for adapter in _adapters(project, item, with_rules=with_rules)
    ]
    return _write_adapters(adapters)


def install_skills(
    target: str,
    *,
    path: Path | str = ".",
    global_install: bool = False,
    home: Path | None = None,
) -> SkillInstallResult:
    """只安装或幂等升级双 Skill（项目级或用户全局级），不触碰规则文件。"""
    if target not in SKILL_TARGETS:
        raise ValueError(f"未知 Skill 安装目标：{target}")
    base = (
        (home or Path.home()).expanduser().resolve()
        if global_install
        else resolve_project(path)
    )
    roots = _resolve_skill_roots(base, target, global_install=global_install)
    adapters = [
        adapter
        for root in roots
        for adapter in _skill_adapters(root)
    ]
    changed = tuple(_write_adapters(adapters))
    legacy = tuple(find_legacy_skills_in_roots(roots))
    return SkillInstallResult(
        changed=changed,
        skill_roots=roots,
        legacy_skills=legacy,
    )


def find_legacy_skills(path: Path | str, target: str) -> list[Path]:
    """检查指定接入目标在项目级 Skill 目录下是否存在旧版 session-handoff 残留。"""
    if target == "generic":
        return []
    project = resolve_project(path)
    roots = _resolve_skill_roots(project, target, global_install=False)
    return find_legacy_skills_in_roots(roots)


def find_legacy_skills_in_roots(roots: tuple[Path, ...] | list[Path]) -> list[Path]:
    """从给定 Skill 根目录列表中收集存在的旧版 session-handoff/SKILL.md。"""
    found: list[Path] = []
    for root in roots:
        legacy = root / _LEGACY_SKILL_NAME / "SKILL.md"
        if legacy.exists() and legacy not in found:
            found.append(legacy)
    return found


def inspect_skills_status(
    path: Path | str = ".",
    *,
    home: Path | None = None,
) -> SkillsStatusReport:
    """只读检查当前项目与用户全局的 Skill 安装状态及旧版残留。"""
    project = resolve_project(path)
    resolved_home = (home or Path.home()).expanduser().resolve()
    entries: list[SkillScopeStatus] = []
    entries.extend(_inspect_scope("project", project, PROJECT_SKILL_ROOTS))
    entries.extend(_inspect_scope("global", resolved_home, GLOBAL_SKILL_ROOTS))
    legacy = tuple(
        dict.fromkeys(
            entry.legacy_path for entry in entries if entry.legacy_path is not None
        )
    )
    return SkillsStatusReport(
        project=project,
        home=resolved_home,
        entries=tuple(entries),
        legacy_skills=legacy,
    )


def _resolve_skill_roots(
    base: Path,
    target: str,
    *,
    global_install: bool,
) -> tuple[Path, ...]:
    """解析目标客户端对应的唯一 Skill 根目录列表（保留顺序并去重）。"""
    mapping = GLOBAL_SKILL_ROOTS if global_install else PROJECT_SKILL_ROOTS
    items = AI_TOOL_TARGETS if target == "all" else (target,)
    roots: list[Path] = []
    for item in items:
        relative = _PORTABLE_SKILL_ROOT if item == "skill" else mapping[item]
        root = base / relative
        if root not in roots:
            roots.append(root)
    return tuple(roots)


def _skill_adapters(skill_root: Path) -> tuple[tuple[Path, str, bool], ...]:
    """为指定 Skill 根目录生成双 Skill 写入描述符。"""
    return tuple(
        (skill_root / name / "SKILL.md", template, True)
        for name, template in SKILL_TEMPLATES.items()
    )


def _adapters(
    project: Path,
    target: str,
    *,
    with_rules: bool = False,
) -> tuple[tuple[Path, str, bool], ...]:
    if target == "generic":
        return ((project / "AI-HANDOFF.md", "# AI 会话交接\n\n" + GENERIC_RULE + "\n", False),)
    if target == "skill":
        return _skill_adapters(project / _PORTABLE_SKILL_ROOT)
    skills = _skill_adapters(project / PROJECT_SKILL_ROOTS[target])
    if not with_rules:
        return skills
    rule_relative, rule_content = _PROJECT_RULE_ADAPTERS[target]
    rule = (project / rule_relative, rule_content, False)
    if target in {"codex", "opencode"}:
        return (*skills, rule)
    return (rule, *skills)


def _write_adapters(
    adapters: list[tuple[Path, str, bool]],
) -> list[Path]:
    """幂等写入适配器文件，返回实际发生内容变化的文件路径列表。"""
    changed: list[Path] = []
    for destination, content, is_skill in adapters:
        before = destination.read_text(encoding="utf-8") if destination.exists() else ""
        # Skill 同步更新 frontmatter 与受管正文，规则文件仅替换受管区块，
        # 均保留受管区块外的用户自定义正文。
        after = (
            _merge_skill(before, content)
            if is_skill
            else _merge_managed_block(before, content)
        )
        if before != after:
            atomic_write(destination, after)
            changed.append(destination)
    return changed


def _inspect_scope(
    scope: str,
    base: Path,
    mapping: dict[str, str],
) -> list[SkillScopeStatus]:
    """只读检查单个作用域内各目标目录的双 Skill 与旧版残留状态。"""
    results: list[SkillScopeStatus] = []
    targets = (*AI_TOOL_TARGETS, "skill")
    for target in targets:
        relative = _PORTABLE_SKILL_ROOT if (scope == "project" and target == "skill") else mapping[target]
        root = base / relative
        statuses = {
            name: _skill_file_status(root / name / "SKILL.md", template)
            for name, template in SKILL_TEMPLATES.items()
        }
        legacy = root / _LEGACY_SKILL_NAME / "SKILL.md"
        legacy_path = legacy if legacy.exists() else None
        if any(state != "missing" for state in statuses.values()) or legacy_path is not None:
            results.append(
                SkillScopeStatus(
                    scope=scope,
                    target=target,
                    root=root,
                    skills=statuses,
                    legacy_path=legacy_path,
                )
            )
    return results


def _skill_file_status(destination: Path, template: str) -> str:
    if not destination.is_file():
        return "missing"
    current = destination.read_text(encoding="utf-8")
    try:
        merged = _merge_skill(current, template)
    except ValueError:
        return "malformed"
    return "synced" if merged == current else "outdated"


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
