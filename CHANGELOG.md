# 变更日志

本项目遵循语义化版本。

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
