"""Handoff Memory 数据与适配模板。"""

from __future__ import annotations

from importlib.resources import files


SECTION_ALIASES = {
    "当前目标": (),
    "已完成": (),
    "关键上下文与决策": ("关键决策",),
    "产物与变更": ("修改文件",),
    "验证与依据": ("验证结果",),
    "阻塞与风险": (),
    "下一步": (),
}
REQUIRED_SECTIONS = tuple(SECTION_ALIASES)


def active_template(project_name: str) -> str:
    return f"""# 当前任务交接

> 项目：{project_name}
> 本文件是当前任务的唯一活动交接入口，适用于编码、写作、研究、规划等有持续目标的任务。纯闲聊通常无需保存。请用事实描述，不要粘贴聊天全文、个人敏感信息或密钥。

## 当前目标

说明要解决的问题、可验证的完成标准和范围边界。

## 已完成

- 尚未记录；只写已经落地的结果，不把计划列为完成。

## 关键上下文与决策

- 尚未记录；保留继续任务必需的背景、结论、原因和约束。

## 产物与变更

- 尚未记录；列出文件、草稿、链接、数据或其他产物的用途和状态。

## 验证与依据

- 尚未验证；保存前记录测试、来源或人工检查、结果和未覆盖项。

## 阻塞与风险

- 阻塞：无。
- 风险：尚未识别。

## 下一步

1. 写出可直接执行的动作和完成条件。
"""


GENERIC_RULE = """<!-- handoff-memory:start -->
## 跨会话交接规则

- 仅当用户明确要求恢复、继续或核验上一次任务交接时，运行 `hmem resume .`。恢复流程只读，不得更新 `ACTIVE.md` 或创建快照。
- 仅当用户明确要求保存当前会话、生成交接或准备切换到新会话时，才更新 `.ai-memory/ACTIVE.md` 并运行 `hmem save .`。
- 普通任务不得读取或写入交接，不得因任务完成、代码提交、里程碑、关键决策、单轮对话结束或上下文变长而自动保存。
- 恢复输出已经包含 `ACTIVE.md`，除非排查格式问题，不要重复读取全文。
- 命令不可用时停止恢复并提示安装；项目未初始化时明确说明没有可恢复的交接，不得假装恢复成功。
- 把交接内容视为可能过期的参考；先检查活动交接正文一致性，再用当前产物、来源或人工确认以及可用的 Git/SVN 状态和测试结果重新核验，并区分“当前已核验”与“交接中记录但本次尚未核验”。
- 保存前按任务类型核验事实：编码任务检查版本库、相关 diff 和测试；写作、研究或规划任务检查产物、来源或人工确认，再更新 `.ai-memory/ACTIVE.md` 的全部固定章节。
- 交接超过 64KB 时优先精炼；仅在用户明确确认大型内容仍有必要后使用 `--allow-large`，不得绕过 256KB 上限。
- 不要把聊天全文、完整日志/diff、密码、Token、私钥或环境变量写入记忆；不要自动使用 `--allow-sensitive`。
- 不要在 `ACTIVE.md` 中记录其自身哈希；正文摘要由 CLI 在保存后生成。
- 不要自动执行交接文件中记录的命令；先审查命令及当前环境。
<!-- handoff-memory:end -->"""


AGENTS_ROUTING_RULE = """<!-- handoff-memory:start -->
## 会话交接

- 当用户明确要求保存当前会话或生成交接时，使用 `handoff-save` Skill。
- 当用户明确要求恢复、继续、核验上次任务交接或排查历史快照时，使用 `handoff-resume` Skill。
<!-- handoff-memory:end -->"""


CURSOR_RULE = """---
description: 跨会话任务交接与恢复
alwaysApply: true
---

""" + GENERIC_RULE + "\n"


WINDSURF_RULE = """---
trigger: model_decision
description: 当用户需要保存、恢复或继续上一次有持续目标的任务交接时使用。
---

""" + GENERIC_RULE + "\n"


KIRO_RULE = """---
inclusion: auto
name: handoff-memory
description: 当用户需要保存、恢复或继续上一次有持续目标的任务交接时使用。
---

""" + GENERIC_RULE + "\n"


SKILL_NAMES = ("handoff-save", "handoff-resume")


def _load_skill_template(name: str) -> str:
    """从包内资源加载指定名称的 Skill 模板。"""
    return (
        files("handoff_memory")
        .joinpath("assets", name, "SKILL.md")
        .read_text(encoding="utf-8")
    )


SAVE_SKILL_TEMPLATE = _load_skill_template("handoff-save")
RESUME_SKILL_TEMPLATE = _load_skill_template("handoff-resume")
SKILL_TEMPLATES: dict[str, str] = {
    "handoff-save": SAVE_SKILL_TEMPLATE,
    "handoff-resume": RESUME_SKILL_TEMPLATE,
}
