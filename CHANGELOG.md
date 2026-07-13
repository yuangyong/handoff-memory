# 变更日志

本项目遵循语义化版本。

## [未发布]

## [0.11.1] - 2026-07-13

### 文档

- 完善公开仓库首页、源码安装边界、支持渠道、贡献流程和路线图。
- 将一次性的公开仓库检查清单转换为可重复执行的版本、GitHub Release、PyPI 和回滚手册。
- 增加英文项目概览、行为准则以及 Issue/Pull Request 仓库协作模板。
- 明确项目采用单一维护者模式，不招募共同维护者，并收紧贡献、支持和发布审批承诺。
- 修复 Claude Code Skills 官方文档链接。

### 修复

- 修复 Windows 并发保存争用空锁文件时，锁前初始化写入可能触发 `PermissionError` 的问题。
- 修复 macOS `/var` 别名和 Windows 8.3 短路径导致接入测试误判返回路径的问题。
- 修复 Skill 同步脚本在 Windows 非 UTF-8 代码页输出中文时触发 `UnicodeEncodeError` 的问题。

### 元数据

- 补充公开维护者、变更日志和安全策略项目链接。
- 首次公开发布前将项目许可证从 Apache-2.0 调整为 MIT，并记录许可决策。
- 固定 GitHub Actions 到完整提交 SHA，增加并发取消、超时和 Actions 依赖更新配置。
- 升级 GitHub Actions 至 Node.js 24 运行时版本，并将后续 Actions 依赖更新合并为单一 Pull Request。
- 新增仅由正式版本标签触发的 PyPI Trusted Publishing 工作流，发行包只构建一次并通过 OIDC 上传。
- 将唯一正式分发渠道收敛为 PyPI，不提供 GitHub Release 附件、独立可执行文件或系统包管理器安装。
- 将仓库级 Secret Scanning、Push Protection、Private Vulnerability Reporting、Action SHA 强制和 Immutable Releases 记录为已接受的发布例外。

## [0.11.0] - 2026-07-13

### 新增

- `save` 和 `check` 新增稳定 JSON 输出；`check --strict` 可将质量警告升级为失败，`check --privacy` 可按类型和行号提示邮箱、手机号与中国居民身份证号，而不回显原文。
- 新增只读的 `history` 与 `show` 命令，可用 Markdown 或 JSON 列举、查看历史快照，并支持 `latest`。
- Git/SVN 状态新增包含变更内容的完整工作区指纹和变更数量，使“同一路径仍为修改状态，但内容已经变化”也能被恢复流程识别。
- 保存流程新增由操作系统自动释放的跨进程文件锁与原子独占快照发布，避免并发保存互相覆盖，并在进程崩溃后自动恢复可用。
- 快照结果新增保存时间与活动正文摘要，供自动化可靠关联本次归档。

### 变更

- 首次公开发布只安装 `hmem` 一个终端命令；移除开发阶段的旧 console script，发行包名与 Python 模块名保持不变。

### 改进

- 将 `session-handoff` Skill 设为单一源文件并提供同步校验脚本，避免发布包与仓库副本漂移。
- 发布元数据改用 SPDX 许可证表达式，并在 CI 同时构建、校验和留存 Wheel 与源码包。
- YAML frontmatter 更新会保留未知字段，并在受管标记损坏、重复或乱序时拒绝写入。
- 恢复措辞从“仓库核验”泛化为“当前状态核验”，适用于写作、研究、规划及有持续目标的对话。
- 仓库 URL 元数据统一移除 userinfo、查询参数和片段。

### 修复

- Git/SVN 状态采集失败时不再被误判为干净工作区。
- 工作区指纹排除 CLI 自身生成的配置、快照、临时文件与锁，同时保留 `ACTIVE.md` 的真实变化。
- 历史快照读取拒绝目录穿越、超大文件、损坏元数据和疑似密钥传播。
- 受管路径拒绝符号链接重定向；历史命令在 `ACTIVE.md` 缺失或配置损坏时仍可只读救援。
- 仓库元数据纳入密钥检测，避免令牌风格的分支、路径或文件名进入快照和恢复输出。

## [0.10.1] - 2026-07-12

### 新增

- 新增短命令 `hmem`，作为后续公开发布使用的终端入口。

### 修复

- 将 `session-handoff` Skill 严格限制为用户明确要求保存、恢复或核验跨会话交接时触发。
- 移除任务完成、代码提交、里程碑、关键决策、对话结束或上下文变长时的自动保存指引。
- 修正规则模板，不再要求每个任务开始前自动恢复；普通任务不会读取或写入 `.ai-memory/`。
- 升级现有项目级 Skill 时同步刷新触发用 YAML frontmatter，并保留受管区块外的用户正文。
- 保存规范化交接正文摘要，并在恢复时提示 `ACTIVE.md` 是否包含保存后的未归档编辑。
- 要求恢复报告区分当前已核验事实和仅由交接记录的事实，避免在正文中记录自指哈希。
- 将新建交接模板泛化为任务导向结构，支持编码、写作、研究和规划；旧版编程标题保持兼容，纯闲聊默认不保存。
- 强化七章节内容提示，并对缺少验证依据或无序下一步给出非阻断质量警告。

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

- 新增 Antigravity IDE 接入目标。
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

- 新增独立 `help [COMMAND]` 子命令，提供总体说明、分命令参数、默认行为和常用示例。
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
