# 变更日志

本项目遵循语义化版本。

## [0.10.0] - 2026-07-12

### 变更

- 具名 AI 工具接入默认只生成项目级 `session-handoff` Skill，不再隐式创建客户端规则。
- 新增统一的 `--with-rules` 显式选项，为所选客户端生成原生规则；Codex 和 OpenCode 的根 `AGENTS.md` 也由该选项控制。
- 移除 `--with-agents-rule`；原有命令请直接替换为 `--with-rules`。
- `all` 统一表示全部具名客户端，`generic` 和 `skill` 保持为需要单独指定的辅助目标。

### 修复

- 修复交互初始化未指定规则参数时仍生成 Antigravity、Qoder 等客户端规则的问题。

## [0.9.0] - 2026-07-12

### 新增

- 新增 Antigravity IDE 适配（`handoff-memory integrate antigravity .`）。
- Antigravity IDE 的轻量规则写入 `.agents/rules/handoff-memory.md`，Skill 写入 `.agents/skills/session-handoff/SKILL.md`。
- Skill 路径与 Codex 共享 `.agents/skills/`，同时接入时只保留一份 Skill 文件，互不冲突。
- 具名 AI 编程客户端数量从 11 个增至 12 个。

## [0.8.0] - 2026-07-12

### 改进

- 11 个具名 AI 工具接入现在都会把 `session-handoff` Skill 写入各自官方项目目录，不再只有 Codex 和 OpenCode 生成技能。
- Claude、Cursor、Gemini CLI、GitHub Copilot、Windsurf、Cline、Kiro、TRAE 和 Qoder 接入由“仅规则”升级为“规则 + Skill”。
- `all` 同步生成全部原生项目 Skill；帮助、规格、集成文档和 Wheel 冒烟验证展示并检查对应目录。

## [0.7.0] - 2026-07-12

### 新增

- 新增 `handoff-memory help [COMMAND]`，提供总体说明、分命令参数、默认行为和常用示例。
- `init --select-tools` 提供零依赖的交互式多选列表，可一次接入多个 AI 编程工具。
- 新增 GitHub Copilot、Windsurf、Cline、Kiro、TRAE、Qoder 和 OpenCode 项目规则适配。

### 改进

- `all` 现在覆盖当前版本支持的 11 个具名 AI 编程客户端，并继续保持规则文件幂等更新。
- Codex 与 OpenCode 默认使用项目级 Skill；`--with-agents-rule` 才会创建或更新共享的 `AGENTS.md` 路由。
- 帮助标题和内置提示统一为中文；原有 `--integrate TARGET` 非交互接口保持兼容。

## [0.6.0] - 2026-07-12

### 改进

- `--integrate codex` 默认只创建项目级 Skill，不再为项目新建 `AGENTS.md`。
- 新增 `--with-agents-rule` 显式选项；启用后不存在则创建 `AGENTS.md`，已存在则保留原内容并追加简短、幂等的 Skill 路由。

## [0.5.0] - 2026-07-12

### 新增

- `--integrate codex` 现在同时初始化 `AGENTS.md` 和官方仓库级目录 `.agents/skills/session-handoff/SKILL.md`。

### 改进

- 修正 Codex 个人级 Skill 路径说明，并保留 `--integrate skill` 作为独立的可移植技能入口。

## [0.4.1] - 2026-07-12

### 改进

- `session-handoff` 技能改为证据驱动保存，避免恢复时重复读取 `ACTIVE.md`，并补充命令缺失与未初始化处理。
- 明确 Codex 项目规则与命名技能的区别，修正安全策略、CLI 契约和示例中的过期说明。
- Wheel CI 增加安装后在外部项目执行 `init`、`check`、`save`、`resume` 的冒烟验证。

## [0.4.0] - 2026-07-12

### 新增

- `save --allow-large`：显式允许保存 64–256KB 的大型交接。

### 改进

- 交接大小改为分级策略：16KB 软提示、64KB 显式确认、256KB 绝对上限。
- `resume` 不再拒绝 64–256KB 的交接，而是在正文前显示强警告，避免关键时刻无法接续任务。
- Windows 中文环境下，标准输入现在固定按 UTF-8 解码，PowerShell 管道不再被系统代码页破坏。

## [0.3.0] - 2026-07-12

### 改进

- 默认初始化只创建 `ACTIVE.md`、`config.json` 和 `sessions/`。
- 拒绝未填写的模板占位交接和超过 64KB 的内容；超过 16KB 给出精炼提示。
- 恢复输出先展示安全声明、保存时间和版本库漂移，7 天以上提示过期。
- Cursor 与 Agent Skill 接入改为受管区块更新，不再覆盖用户自定义内容。
- 快速开始默认只接入一个 AI 客户端，`all` 降为多客户端高级选项。

### 删除

- 新项目不再自动创建超出当前任务交接范围的 `PROJECT.md` 和 `DECISIONS.md`。

## [0.2.0] - 2026-07-12

### 新增

- 自动识别 Git 与 SVN 工作副本。
- SVN URL、仓库相对位置、修订号和本地变更采集。
- SVN 快照保存、修订漂移检测和专用恢复输出。
- `RepositoryState` 统一版本库状态模型及 SVN CI 集成测试。
- Git/SVN 仓库 URL 凭据脱敏。

### 兼容性

- 保留 `repository` JSON 中原有 Git 字段，并增加 `provider`、`revision`、`url` 和 `root`。
- 继续读取 0.1 配置的 `last_saved_git`，新配置统一使用 `last_saved_repository`。

## [0.1.0] - 2026-07-12

### 新增

- 本地 Markdown 记忆目录初始化。
- 活动交接格式校验、敏感信息检测和历史归档。
- 恢复时 Git 分支、HEAD、工作区及漂移核验。
- Markdown 与 JSON 两种恢复输出。
- Codex、Claude Code、Cursor、Gemini、通用 AI 和 Agent Skill 接入。
- Windows、macOS、Linux CI 测试矩阵。
