# 变更日志

本项目遵循语义化版本。

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
