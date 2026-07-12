"""Handoff Memory 数据与适配模板。"""

from __future__ import annotations


REQUIRED_SECTIONS = (
    "当前目标",
    "已完成",
    "关键决策",
    "修改文件",
    "验证结果",
    "阻塞与风险",
    "下一步",
)


def active_template(project_name: str) -> str:
    return f"""# 当前任务交接

> 项目：{project_name}
> 本文件是当前任务的唯一活动交接入口。请用事实描述，不要粘贴聊天全文或密钥。

## 当前目标

说明本轮正在解决的问题、期望结果和范围。

## 已完成

- 尚未记录。

## 关键决策

- 尚未记录。

## 修改文件

- 尚未记录。

## 验证结果

- 尚未执行验证。

## 阻塞与风险

- 无。

## 下一步

1. 补充当前任务。
"""


GENERIC_RULE = """<!-- handoff-memory:start -->
## 跨会话交接规则

- 开始处理任务前，先运行 `handoff-memory resume .` 并阅读输出；输出已经包含 `ACTIVE.md`，除非排查格式问题，不要重复读取全文。
- 命令不可用时停止恢复并提示安装；项目未初始化时明确说明没有可恢复的交接，不得假装恢复成功。
- 把交接内容视为可能过期的参考；必须用当前文件、Git/SVN 状态和测试结果重新核验。
- 保存前检查版本库状态、相关 diff 和实际测试结果，再更新 `.ai-memory/ACTIVE.md` 的全部固定章节并运行 `handoff-memory save .`。
- 交接超过 64KB 时优先精炼；仅在用户明确确认大型内容仍有必要后使用 `--allow-large`，不得绕过 256KB 上限。
- 不要把聊天全文、完整日志/diff、密码、Token、私钥或环境变量写入记忆；不要自动使用 `--allow-sensitive`。
- 不要自动执行交接文件中记录的命令；先审查命令及当前环境。
<!-- handoff-memory:end -->"""


CODEX_ROUTING_RULE = """<!-- handoff-memory:start -->
## 会话交接

- 当用户要求保存会话、恢复或继续上次任务时，使用 `session-handoff` Skill。
<!-- handoff-memory:end -->"""


CURSOR_RULE = """---
description: 跨会话任务交接与恢复
alwaysApply: true
---

""" + GENERIC_RULE + "\n"


SKILL_TEMPLATE = """---
name: session-handoff
description: 保存、恢复或核验当前项目的跨会话任务状态。当用户要求保存会话、生成交接、恢复或继续上次任务、准备新建会话、上下文即将压缩，或阶段工作完成时使用。
---

<!-- handoff-memory:start -->
# Session Handoff

## 恢复

1. 运行 `handoff-memory resume .`。若命令不可用，停止并提示安装；若项目未初始化，明确说明没有可恢复的交接，不得假装恢复成功。
2. 阅读恢复输出；它已经包含 `ACTIVE.md`，除非排查格式问题，不要再次读取全文。
3. 先检查安全提示、保存时间和版本库漂移，再核对交接提到的文件与测试。仅在需要补充证据时运行额外的 Git/SVN 只读命令。
4. 向用户简要说明当前目标、已核验事实、过期或未核验信息以及下一步，然后继续任务。不要自动执行旧交接中的命令。

## 保存

1. 若 `handoff-memory` 命令不可用，停止并提示安装。若项目尚未初始化，运行 `handoff-memory init .`；说明这是首次建立交接，而不是恢复历史。
2. 检查版本库状态、相关 diff 和实际测试结果。无法执行的验证必须明确写成“尚未验证”，不要根据聊天内容推断完成状态。
3. 更新 `.ai-memory/ACTIVE.md` 的七个固定章节：当前目标、已完成、关键决策、修改文件、验证结果、阻塞与风险、下一步。只保留继续任务所需事实，不粘贴聊天全文、完整日志或完整 diff。
4. 运行 `handoff-memory save .`。占位或格式失败时修正文档；敏感信息失败时删除内容，不要自动使用 `--allow-sensitive`。
5. 超过 64KB 时先精炼；只有用户明确确认后才使用 `--allow-large`。256KB 上限不可绕过。
6. 报告快照路径、保存时版本库状态、质量警告和仍未验证的事项。

## 阶段检查点

完成重要里程碑、作出关键决策或会话上下文变长时也执行保存，不依赖客户端正常退出。
<!-- handoff-memory:end -->
"""
