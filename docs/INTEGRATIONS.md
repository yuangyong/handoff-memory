# 跨 AI 工具接入说明

## 设计

不同 AI 客户端的生命周期钩子、规则文件和 Skill 目录并不统一。Handoff Memory 采用“核心 CLI + 薄适配文件”：

- 核心数据协议不依赖客户端。
- 规则文件只提供轻量提醒，Skill 按需加载完整 `resume` 和 `save` 流程。
- 客户端即使不支持自动规则，也能通过首条提示词使用相同流程。
- 每次只接入实际使用的客户端；`all` 仅用于多客户端项目。
- 每个具名客户端默认只生成原生项目级 Skill；客户端规则必须通过 `--with-rules` 显式开启，`generic` 和 `skill` 是独立辅助目标。
- 所有输出只更新 `handoff-memory:start/end` 受管区块，保留区块外的用户内容。

`--select-tools` 菜单中的 `all` 和 `--integrate all` 都只选择全部具名客户端；`generic` 与 `skill` 必须单独指定。由于 Codex 和 Antigravity 共享 `.agents/skills/session-handoff/SKILL.md`，同一路径只会保留一份幂等文件。

## Codex

```powershell
handoff-memory integrate codex .
```

默认只创建或更新 `.agents/skills/session-handoff/SKILL.md` 项目级技能，不读取或修改 `AGENTS.md`。

需要常驻自动提醒时显式执行：

```powershell
handoff-memory integrate codex . --with-rules
```

此时无论 `AGENTS.md` 是否已存在都会处理：不存在则创建仅含简短路由的文件；已存在则保留原内容，只追加或更新一个受管区块。路由仅要求在用户保存、恢复或继续上次任务时使用 `session-handoff` Skill。

`.agents/skills` 是 Codex 官方约定的仓库级 Skill 目录。新会话仍建议显式说“恢复上次任务”，避免把所有历史无条件注入上下文。参见 [Codex Customization：Skills](https://developers.openai.com/codex/concepts/customization#skills)。

## Claude Code

```powershell
handoff-memory integrate claude .
```

默认根据 [Claude Code Skills](https://code.claude.com/docs/en/slash-commands) 创建 `.claude/skills/session-handoff/SKILL.md`；指定 `--with-rules` 时再更新 `CLAUDE.md`。如果自行配置 SessionStart、PreCompact 或 Stop hooks，可以调用 CLI，但 Handoff Memory 核心不依赖这些 hooks。尤其不要只在 SessionEnd 保存。

## Cursor

```powershell
handoff-memory integrate cursor .
```

默认根据 [Cursor Agent Skills](https://cursor.com/docs/skills) 创建 `.cursor/skills/session-handoff/SKILL.md`；指定 `--with-rules` 时再创建 `.cursor/rules/handoff-memory.mdc`。

## Gemini CLI

```powershell
handoff-memory integrate gemini .
```

默认根据 [Gemini CLI Agent Skills](https://geminicli.com/docs/cli/using-agent-skills/) 创建 `.gemini/skills/session-handoff/SKILL.md`；指定 `--with-rules` 时再更新 `GEMINI.md`。

## Antigravity IDE

```powershell
handoff-memory integrate antigravity .
```

默认根据 [Antigravity IDE Agent Skills](https://antigravity.google/docs/skills?app=antigravity-ide) 创建 `.agents/skills/session-handoff/SKILL.md`；指定 `--with-rules` 时再根据 [Antigravity IDE Rules](https://antigravity.google/docs/ide-rules) 创建轻量规则 `.agents/rules/handoff-memory.md`。Skill 路径与 Codex 共享，因此同时接入两者时只保留一份 Skill 文件。

规则只负责把保存、恢复和继续任务请求路由到 Skill，不复制完整流程。Antigravity 支持 Manual、Always On、Model Decision 和 Glob 等规则激活方式，可在客户端中按项目需要选择；即使不依赖常驻规则，也可以直接要求使用 `session-handoff` Skill。官方规则文件上限为 12,000 字符，当前轻量路由远低于该限制。

## GitHub Copilot

```powershell
handoff-memory integrate copilot .
```

默认根据 [GitHub Copilot Agent Skills](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills) 创建 `.github/skills/session-handoff/SKILL.md`；指定 `--with-rules` 时再更新 `.github/copilot-instructions.md`。

## Windsurf

```powershell
handoff-memory integrate windsurf .
```

默认根据 [Windsurf Skills](https://docs.windsurf.com/windsurf/cascade/skills) 创建 `.windsurf/skills/session-handoff/SKILL.md`；指定 `--with-rules` 时再创建 `.windsurf/rules/handoff-memory.md`。规则使用 `model_decision` 触发方式。

## Cline

```powershell
handoff-memory integrate cline .
```

默认根据 [Cline Skills](https://docs.cline.bot/customization/skills) 创建 `.cline/skills/session-handoff/SKILL.md`；指定 `--with-rules` 时再创建 [Cline 工作区规则](https://docs.cline.bot/customization/cline-rules) `.clinerules/handoff-memory.md`。

## Kiro

```powershell
handoff-memory integrate kiro .
```

默认根据 [Kiro Agent Skills](https://kiro.dev/docs/cli/skills/) 创建 `.kiro/skills/session-handoff/SKILL.md`；指定 `--with-rules` 时再创建 [Kiro Steering](https://kiro.dev/docs/steering/) 文件 `.kiro/steering/handoff-memory.md`。

## TRAE

```powershell
handoff-memory integrate trae .
```

默认根据 [TRAE Agent Skills](https://www.trae.ai/blog/trae_tutorial_0115?v=1) 和[官方社区项目目录说明](https://forum.trae.cn/t/topic/31835)创建 `.trae/skills/session-handoff/SKILL.md`；指定 `--with-rules` 时再更新 [TRAE 项目规则](https://forum.trae.cn/t/topic/52) `.trae/rules/project_rules.md`。

## Qoder

```powershell
handoff-memory integrate qoder .
```

默认根据 [Qoder CLI Skills](https://docs.qoder.com/en/cli/Skills) 创建 `.qoder/skills/session-handoff/SKILL.md`；指定 `--with-rules` 时再创建 [Qoder 项目规则](https://docs.qoder.com/user-guide/rules) `.qoder/rules/handoff-memory.md`。

## OpenCode

```powershell
handoff-memory integrate opencode .
```

创建 `.opencode/skills/session-handoff/SKILL.md`，由 [OpenCode Agent Skills](https://opencode.ai/docs/skills) 的原生 `skill` 工具按需加载，默认不处理 `AGENTS.md`。需要常驻路由时显式执行：

```powershell
handoff-memory integrate opencode . --with-rules
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

生成 `.agents/skills/session-handoff/SKILL.md` 可移植副本。具名客户端已经自动生成各自原生目录，不需要再手工复制；该目标主要用于其他兼容 Agent Skills 开放目录的客户端。

```text
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
