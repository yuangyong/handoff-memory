# 跨 AI 工具接入说明

## 设计

不同 AI 客户端的生命周期钩子、规则文件和 Skill 目录并不统一。Handoff Memory 采用“核心 CLI + 薄适配文件”：

- 核心数据协议不依赖客户端。
- 适配文件只告诉 AI 何时执行 `resume` 和 `save`。
- 客户端即使不支持自动规则，也能通过首条提示词使用相同流程。
- 每次只接入实际使用的客户端；`all` 仅用于多客户端项目。
- 所有适配器只更新 `handoff-memory:start/end` 受管区块，保留区块外的用户内容。

## Codex

```powershell
handoff-memory integrate codex .
```

更新项目根目录 `AGENTS.md` 中的受管区块。新会话仍建议显式说“恢复上次任务”，避免把所有历史无条件注入上下文。

这是 Codex 项目规则，不会自动注册名为 `session-handoff` 的个人技能；需要命名技能时，另外使用下文的 Agent Skill 接入方式。

## Claude Code

```powershell
handoff-memory integrate claude .
```

更新 `CLAUDE.md`。如果自行配置 SessionStart、PreCompact 或 Stop hooks，可以调用 CLI，但 Handoff Memory 核心不依赖这些 hooks。尤其不要只在 SessionEnd 保存。

## Cursor

```powershell
handoff-memory integrate cursor .
```

创建 `.cursor/rules/handoff-memory.mdc`，设置为始终应用的项目规则。

## Gemini CLI

```powershell
handoff-memory integrate gemini .
```

更新 `GEMINI.md` 中的受管区块。

## 通用 AI

```powershell
handoff-memory integrate generic .
```

生成 `AI-HANDOFF.md`。对于能读取项目文件但没有专属规则机制的工具，在首条提示中要求读取该文件。

## Agent Skill

```powershell
handoff-memory integrate skill .
```

生成 `.agents/skills/session-handoff/SKILL.md`。这是可移植副本；如果客户端使用不同技能目录，可以把整个 `session-handoff` 目录复制过去，例如：

```text
.claude/skills/session-handoff/     # 某些 Claude Code 配置
~/.codex/skills/session-handoff/    # Codex 个人级技能目录
项目约定的其他 skills 目录
```

仓库还提供 [`skills/session-handoff/SKILL.md`](../skills/session-handoff/SKILL.md)，可以直接复制。

技能恢复时只读取 `resume` 输出，因为输出已经包含 `ACTIVE.md`；保存时会先核对版本库状态、相关 diff 和实际测试结果。若命令不可用或项目没有历史交接，技能必须明确报告，不能模拟成功。

## 没有工具调用能力的聊天 AI

在旧会话结束前：

1. 让 AI 按 `ACTIVE.md` 固定章节生成 Markdown。
2. 人工保存到 `.ai-memory/ACTIVE.md`。
3. 运行 `handoff-memory save .`。

在新会话开始时：

1. 运行 `handoff-memory resume .`。
2. 把输出作为第一条上下文粘贴给 AI。

这也是兼容性最强、最容易审计的基线流程。
