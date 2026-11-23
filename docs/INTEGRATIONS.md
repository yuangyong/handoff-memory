# 跨 AI 工具接入说明

## 设计

不同 AI 客户端的生命周期钩子、规则文件和 Skill 目录并不统一。Handoff Memory 采用“核心 CLI + 薄适配文件”：

本文统一使用唯一终端命令 `hmem`。发行包仍命名为 `handoff-memory`，这不是可执行命令。

- 核心数据协议不依赖客户端。
- 规则文件只提供轻量提醒，双 Skill（`handoff-save` 负责写入与按需自动初始化、`handoff-resume` 负责只读恢复与历史排查）按需加载完整流程，实现读写物理隔离。
- 规则与 Skill 只响应用户明确提出的保存、恢复、继续或核验交接请求；普通任务和会话内对话不读写交接。
- 客户端即使不支持自动规则，也能通过首条提示词或 `/handoff-save`、`/handoff-resume` 使用相同流程。
- **命令分工**：
  - `hmem skills add <target> [-g|--global]`：只安装或升级 `handoff-save` 与 `handoff-resume` 双 Skill，不生成客户端规则或 `.ai-memory/`。个人跨项目使用**推荐加 `-g` 安装到用户全局目录**；也支持通过 `npx skills add yuangyong/handoff-memory -g` 从仓库安装。
  - `hmem skills status [PATH]`：只读检查当前项目级和用户全局目录的 Skill 同步状态与旧版 `session-handoff` 残留。
  - `hmem integrate <target> [PATH] [--with-rules]`：面向单个项目的集成入口，除生成项目级双 Skill 外，还负责显式开启 `--with-rules` 时的客户端规则以及纯规则目标 `generic`（`AI-HANDOFF.md`）。
- 每次只接入实际使用的客户端；`all` 仅用于多客户端场景。
- 规则只更新 `handoff-memory:start/end` 受管区块；Skill 还会同步升级触发用 YAML frontmatter。两者均保留受管区块外的用户正文。

`--select-tools` 菜单中的 `all`、`--integrate all` 和 `hmem skills add all` 都只选择全部具名客户端；`generic` 与 `skill` 必须单独指定。项目级接入时 Codex 和 Antigravity 共享 `.agents/skills/`，全局接入时 Antigravity 使用 `~/.gemini/config/skills/`，不再冲突。

### 升级与旧版 `session-handoff` 迁移

- 升级 `hmem` 后，运行 `hmem skills add <target> -g`（或项目级 `hmem skills add <target> .`）即可同步刷新两个新 Skill。
- 若目录中仍存在早期版本的 `session-handoff/SKILL.md`，CLI 不会静默删除，以免误删你在受管区块外补充的内容；请确认无自定义正文后手动删除该旧目录，避免新旧 Skill 同时存在造成触发冲突。

## Codex

```powershell
# 全局安装（推荐）
hmem skills add codex -g
# 或仅当前项目
hmem integrate codex .
```

默认只创建或更新 `~/.agents/skills/`（全局）或 `.agents/skills/`（项目级）下的 `handoff-save/SKILL.md` 与 `handoff-resume/SKILL.md`，不读取或修改 `AGENTS.md`。

需要为单个项目常驻显式请求路由时执行：

```powershell
hmem integrate codex . --with-rules
```

此时无论 `AGENTS.md` 是否已存在都会处理：不存在则创建仅含简短路由的文件；已存在则保留原内容，只追加或更新一个受管区块。路由仅要求在用户保存、恢复或继续上次任务时分别使用 `handoff-save` 与 `handoff-resume` Skill。

`.agents/skills` 是 Codex 官方约定的项目级与用户级 Skill 目录。新会话仍建议显式说“恢复上次任务”，避免把所有历史无条件注入上下文。参见 [Codex Customization：Skills](https://learn.chatgpt.com/docs/customization/overview#skills)。

## Claude Code

```powershell
hmem skills add claude -g
# 或项目级 + 可选规则
hmem integrate claude .
```

根据 [Claude Code Skills](https://code.claude.com/docs/en/skills) 在 `~/.claude/skills/`（全局）或 `.claude/skills/`（项目级）创建双 Skill；通过 `hmem integrate claude . --with-rules` 时再更新 `CLAUDE.md`。如果自行配置 SessionStart、PreCompact 或 Stop hooks，可以调用 CLI，但 Handoff Memory 核心不依赖这些 hooks。尤其不要只在 SessionEnd 保存。

## Cursor

```powershell
hmem skills add cursor -g
# 或项目级
hmem integrate cursor .
```

根据 [Cursor Agent Skills](https://cursor.com/docs/skills) 在 `~/.cursor/skills/`（全局）或 `.cursor/skills/`（项目级）创建双 Skill；通过 `hmem integrate cursor . --with-rules` 时再创建 `.cursor/rules/handoff-memory.mdc`。

## Gemini CLI

```powershell
hmem skills add gemini -g
# 或项目级
hmem integrate gemini .
```

根据 [Gemini CLI Agent Skills](https://geminicli.com/docs/cli/using-agent-skills/) 在 `~/.gemini/skills/`（全局）或 `.gemini/skills/`（项目级）创建双 Skill；通过 `hmem integrate gemini . --with-rules` 时再更新 `GEMINI.md`。

## Antigravity IDE

```powershell
hmem skills add antigravity -g
# 或项目级
hmem integrate antigravity .
```

根据 [Antigravity IDE Agent Skills](https://antigravity.google/docs/skills?app=antigravity-ide) 在 `~/.gemini/config/skills/`（全局）或 `.agents/skills/`（项目级）创建双 Skill；通过 `hmem integrate antigravity . --with-rules` 时再根据 [Antigravity IDE Rules](https://antigravity.google/docs/ide-rules) 创建轻量规则 `.agents/rules/handoff-memory.md`。

规则只负责把保存、恢复和继续任务请求路由到 `handoff-save` 与 `handoff-resume` Skill，不复制完整流程。Antigravity 支持 Manual、Always On、Model Decision 和 Glob 等规则激活方式，可在客户端中按项目需要选择；即使不依赖常驻规则，也可以直接要求使用对应 Skill。官方规则文件上限为 12,000 字符，当前轻量路由远低于该限制。

## GitHub Copilot

```powershell
hmem skills add copilot -g
# 或项目级
hmem integrate copilot .
```

根据 [GitHub Copilot Agent Skills](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills) 在 `~/.copilot/skills/`（全局）或 `.github/skills/`（项目级）创建双 Skill；通过 `hmem integrate copilot . --with-rules` 时再更新 `.github/copilot-instructions.md`。

## Windsurf

```powershell
hmem skills add windsurf -g
# 或项目级
hmem integrate windsurf .
```

根据 [Windsurf Skills](https://docs.devin.ai/desktop/cascade/skills) 在 `~/.codeium/windsurf/skills/`（全局）或 `.windsurf/skills/`（项目级）创建双 Skill；通过 `hmem integrate windsurf . --with-rules` 时再创建 `.windsurf/rules/handoff-memory.md`。规则使用 `model_decision` 触发方式。

## Cline

```powershell
hmem skills add cline -g
# 或项目级
hmem integrate cline .
```

根据 [Cline Skills](https://docs.cline.bot/customization/skills) 在 `~/.cline/skills/`（全局）或 `.cline/skills/`（项目级）创建双 Skill；通过 `hmem integrate cline . --with-rules` 时再创建 [Cline 工作区规则](https://docs.cline.bot/customization/cline-rules) `.clinerules/handoff-memory.md`。

## Kiro

```powershell
hmem skills add kiro -g
# 或项目级
hmem integrate kiro .
```

根据 [Kiro Agent Skills](https://kiro.dev/docs/cli/skills/) 在 `~/.kiro/skills/`（全局）或 `.kiro/skills/`（项目级）创建双 Skill；通过 `hmem integrate kiro . --with-rules` 时再创建 [Kiro Steering](https://kiro.dev/docs/steering/) 文件 `.kiro/steering/handoff-memory.md`。

## TRAE

```powershell
hmem skills add trae -g
# 或项目级
hmem integrate trae .
```

根据 [TRAE Agent Skills](https://www.trae.ai/blog/trae_tutorial_0115?v=1) 和[官方社区项目目录说明](https://forum.trae.cn/t/topic/31835)在 `~/.trae/skills/`（全局）或 `.trae/skills/`（项目级）创建双 Skill；通过 `hmem integrate trae . --with-rules` 时再更新 [TRAE 项目规则](https://forum.trae.cn/t/topic/52) `.trae/rules/project_rules.md`。

## Qoder

```powershell
hmem skills add qoder -g
# 或项目级
hmem integrate qoder .
```

根据 [Qoder CLI Skills](https://docs.qoder.com/en/cli/Skills) 在 `~/.qoder/skills/`（全局）或 `.qoder/skills/`（项目级）创建双 Skill；通过 `hmem integrate qoder . --with-rules` 时再创建 [Qoder 项目规则](https://docs.qoder.com/user-guide/rules) `.qoder/rules/handoff-memory.md`。

## OpenCode

```powershell
hmem skills add opencode -g
# 或项目级
hmem integrate opencode .
```

在 `~/.config/opencode/skills/`（全局）或 `.opencode/skills/`（项目级）创建双 Skill，由 [OpenCode Agent Skills](https://opencode.ai/docs/skills) 的原生 `skill` 工具按需加载，默认不处理 `AGENTS.md`。需要为单个项目常驻路由时显式执行：

```powershell
hmem integrate opencode . --with-rules
```

OpenCode 也支持 `.agents/skills`，但使用独立的 `.opencode/skills`（与 `~/.config/opencode/skills/`）可以清楚表达所选客户端，并避免与 Codex 接入状态混淆。

## 通用 AI

```powershell
hmem integrate generic .
```

生成项目根 `AI-HANDOFF.md`（仅规则，不支持 `hmem skills` 与 `-g`）。对于能读取项目文件但没有专属规则机制的工具，在首条提示中要求读取该文件。

## Agent Skill

```powershell
hmem skills add skill -g
# 或项目级：hmem skills add skill . / hmem integrate skill .
```

在 `~/.agents/skills/`（全局）或 `.agents/skills/`（项目级）生成 `handoff-save` 与 `handoff-resume` 可移植副本。具名客户端已经自动生成各自原生目录，不需要再手工复制；该目标主要用于其他兼容 Agent Skills 开放目录的客户端，也可直接通过 Vercel Skills CLI 从 GitHub 仓库全局安装：

```powershell
npx skills add yuangyong/handoff-memory -g
```

仓库顶层还直接提供 [`skills/handoff-save/SKILL.md`](../skills/handoff-save/SKILL.md) 与 [`skills/handoff-resume/SKILL.md`](../skills/handoff-resume/SKILL.md)。

`handoff-resume` 恢复时只读取 `resume` 输出，因为输出已经包含 `ACTIVE.md`；先检查活动正文是否与最后保存一致，再区分当前已核验事实和仅由交接记录的事实。`handoff-save` 保存时按任务类型核验：编码任务检查版本库、diff 和测试，写作、研究或规划任务检查产物、来源或人工确认，未初始化的项目会自动运行 `hmem init .`（半损坏目录禁止强制覆盖）；CLI 在快照元数据中生成正文摘要，不能把 `ACTIVE.md` 自身哈希写回正文。纯闲聊且没有持续目标通常无需交接。若 `hmem` 命令不可用（缺少 CLI 且存在 `uv`/`pipx` 时先展示标准命令并征得用户同意后再安装）或项目没有历史交接，技能必须明确报告，不能模拟成功。

## 没有工具调用能力的聊天 AI

在旧会话结束前：

1. 让 AI 按 `ACTIVE.md` 固定章节生成 Markdown。
2. 人工保存到 `.ai-memory/ACTIVE.md`。
3. 运行 `hmem save .`。

在新会话开始时：

1. 运行 `hmem resume .`。
2. 把输出作为第一条上下文粘贴给 AI。

这也是兼容性最强、最容易审计的基线流程。
