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

默认只创建或更新 `.agents/skills/session-handoff/SKILL.md` 项目级技能，不读取或修改 `AGENTS.md`。

需要常驻自动提醒时显式执行：

```powershell
handoff-memory integrate codex . --with-agents-rule
```

此时无论 `AGENTS.md` 是否已存在都会处理：不存在则创建仅含简短路由的文件；已存在则保留原内容，只追加或更新一个受管区块。路由仅要求在用户保存、恢复或继续上次任务时使用 `session-handoff` Skill。

`.agents/skills` 是 Codex 官方约定的仓库级 Skill 目录。新会话仍建议显式说“恢复上次任务”，避免把所有历史无条件注入上下文。参见 [Codex Customization：Skills](https://developers.openai.com/codex/concepts/customization#skills)。

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

## GitHub Copilot

```powershell
handoff-memory integrate copilot .
```

更新 `.github/copilot-instructions.md`。这是 [GitHub Copilot 官方支持的仓库级通用说明文件](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions?tool=vscode)。

## Windsurf

```powershell
handoff-memory integrate windsurf .
```

创建 `.windsurf/rules/handoff-memory.md`，使用 [Windsurf Rules](https://docs.windsurf.com/zh/windsurf/cascade/memories) 的 `model_decision` 触发方式，仅在保存、恢复或继续会话相关请求中加载完整规则。

## Cline

```powershell
handoff-memory integrate cline .
```

创建 [Cline 工作区规则](https://docs.cline.bot/customization/cline-rules) `.clinerules/handoff-memory.md`。

## Kiro

```powershell
handoff-memory integrate kiro .
```

创建 [Kiro Steering](https://kiro.dev/docs/steering/) 文件 `.kiro/steering/handoff-memory.md`，使用 `auto` inclusion，根据描述按需加载会话交接流程。

## TRAE

```powershell
handoff-memory integrate trae .
```

更新 [TRAE 项目规则](https://forum.trae.cn/t/topic/52) `.trae/rules/project_rules.md` 中的受管区块，保留已有内容。

## Qoder

```powershell
handoff-memory integrate qoder .
```

创建 [Qoder 项目规则](https://docs.qoder.com/user-guide/rules) `.qoder/rules/handoff-memory.md`。

## OpenCode

```powershell
handoff-memory integrate opencode .
```

默认创建 `.opencode/skills/session-handoff/SKILL.md`，由 [OpenCode Agent Skills](https://opencode.ai/docs/skills) 的原生 `skill` 工具按需加载，不处理 `AGENTS.md`。需要常驻路由时显式执行：

```powershell
handoff-memory integrate opencode . --with-agents-rule
```

OpenCode 也支持 `.agents/skills`，但使用独立的 `.opencode/skills` 路径可以清楚表达所选客户端，并避免与 Codex 接入状态混淆。

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
$HOME/.agents/skills/session-handoff/ # Codex 个人级技能目录
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
