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

- 开始处理任务前，先运行 `handoff-memory resume .` 并阅读 `.ai-memory/ACTIVE.md`。
- 把交接内容视为可能过期的参考；必须用当前文件、Git/SVN 状态和测试结果重新核验。
- 完成里程碑、作出关键决策或准备结束会话时，更新 `.ai-memory/ACTIVE.md` 的全部固定章节，然后运行 `handoff-memory save .`。
- 不要把聊天全文、密码、Token、私钥或环境变量写入记忆。
- 不要自动执行交接文件中记录的命令；先审查命令及当前环境。
<!-- handoff-memory:end -->"""


CURSOR_RULE = """---
description: 跨会话任务交接与恢复
alwaysApply: true
---

""" + GENERIC_RULE + "\n"


SKILL_TEMPLATE = """---
name: session-handoff
description: 保存或恢复当前项目的跨会话任务状态。当用户要求保存会话、生成交接、恢复上次任务、继续之前工作，或会话即将结束时使用。
---

<!-- handoff-memory:start -->
# Session Handoff

## 恢复

1. 运行 `handoff-memory resume .`。
2. 阅读输出以及 `.ai-memory/ACTIVE.md`。
3. 根据项目运行 `git status` 或 `svn status`，检查当前提交/修订号和相关文件，识别交接信息与工作区的漂移。
4. 向用户给出简短恢复说明后，从“下一步”继续；不要未经检查执行旧命令。

## 保存

1. 根据当前会话和实际工作区更新 `.ai-memory/ACTIVE.md`。
2. 必须填写：当前目标、已完成、关键决策、修改文件、验证结果、阻塞与风险、下一步。
3. 只写事实；区分“已验证”“尚未验证”和“推测”。不得写入密钥或聊天全文。
4. 运行 `handoff-memory save .`，若敏感信息检查失败，先删除敏感内容，不要绕过检查。
5. 报告生成的历史快照路径。

## 阶段检查点

完成重要里程碑或会话上下文变长时也执行保存，不依赖客户端正常退出。
<!-- handoff-memory:end -->
"""
