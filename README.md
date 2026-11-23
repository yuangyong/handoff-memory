# Handoff Memory

本地优先、跨 AI 工具的会话交接记忆 CLI。

[中文](README.md) | [English](README.en.md)

> **项目状态：Alpha（0.12.x）**
>
> 正式发行包仅通过 PyPI 提供。公共 CLI 与带版本号的 JSON 输出遵循兼容性扩展原则，但 Alpha 阶段仍可能在明确迁移说明后调整边界。

Handoff Memory 解决的不是“让模型记住一切”，而是一个更可验证的问题：**让下一次 AI 会话准确知道一项持续任务进行到哪里，并用当前产物、依据以及可用的仓库状态核验交接内容**。纯闲聊通常不需要交接。

它不绑定模型、云服务或向量数据库。数据就是项目中的 Markdown，任何 AI、编辑器和人都能读取。

## 特性

- 本地优先：默认不联网、不上传、不调用 LLM。
- 跨工具：内置 12 个主流 AI 编程客户端的项目规则与原生项目级 Skill 适配。
- 可审计：活动交接和历史快照都是 UTF-8 Markdown。
- 可核验：自动识别 Git/SVN，恢复时重新采集分支或仓库位置、HEAD 或修订号以及完整工作区指纹。
- 自动化友好：`save`、`resume`、`check`、`history`、`show` 提供带版本号的 JSON 输出。
- 安全默认：阻止常见 API Key、访问令牌和私钥进入快照。
- 幂等接入：更新规则受管区块和 Skill，不覆盖受管区块外的用户内容。
- 零运行期依赖：仅要求 Python 3.10+。

## 快速开始

### 30 秒体验（推荐：全局安装一次，跨项目即用）

安装 CLI 后，只需把 `handoff-save` 与 `handoff-resume` 双 Skill 安装到用户全局目录（以 Claude Code 或 Codex 为例，支持 `--global` / `-g`）：

```powershell
hmem skills add claude -g
# 或：hmem skills add codex -g
# 也支持通过 Vercel Skills CLI 从仓库安装：npx skills add yuangyong/handoff-memory -g
```

之后在任意项目中完成任务时，直接要求 AI 保存交接（`handoff-save` Skill 会在未初始化时自动运行 `hmem init .` 创建 `.ai-memory/` 并保存快照）；到新会话时要求 AI 恢复交接（`handoff-resume` 只读核验后继续）。

如果你更偏好手动或脚本化执行，也可以在目标项目中显式运行：

```powershell
hmem init . --name "你的项目" --integrate codex
hmem save .
hmem resume .
```

`resume` 只读取和核验交接，不会执行交接中记录的命令。

### 安装

推荐使用 `uv` 或 `pipx` 从 PyPI 安装到独立工具环境，避免污染目标项目。尚未安装工具管理器时，先参考 [`uv` 安装文档](https://docs.astral.sh/uv/getting-started/installation/)或 [`pipx` 安装文档](https://pipx.pypa.io/stable/installation/)完成准备。

以下命令用于首次安装；如果已经安装旧版本，请使用下方的升级命令。重复执行 `uv tool install` 默认不会升级现有工具：

```powershell
uv tool install handoff-memory
# 或
pipx install handoff-memory
```

Handoff Memory 不提供独立可执行文件、系统包管理器清单或远程安装脚本；PyPI 是唯一正式分发渠道。

安装后先确认命令已经进入 `PATH`：

```powershell
hmem --version
hmem help
```

`hmem` 是唯一 CLI 命令。发行包仍命名为 `handoff-memory`，Python 模块仍命名为 `handoff_memory`；安装名、模块名与终端命令名无需相同。

升级到新版本：

```powershell
uv tool upgrade handoff-memory
# 或
pipx upgrade handoff-memory
```

升级后运行 `hmem --version` 确认版本。使用 `uv` 时，也可以通过 `uv tool list` 查看工具环境中实际安装的版本。

升级后已初始化的项目不需要重新 `init`。刷新项目级或全局双 Skill 可执行 `hmem skills add <target> [-g]`（或通过 `hmem skills status .` 检查同步状态与旧版 `session-handoff` 残留）；项目同时使用规则时，通过 `hmem integrate <target> . --with-rules` 刷新规则。规则只更新受管正文并保留区块外内容；Skill 会同步升级触发用 YAML frontmatter 和受管正文，同时保留区块外的用户正文。

开发模式：

```powershell
python -m pip install -e .
```

发行包通过 GitHub Actions 和 PyPI Trusted Publishing 自动上传，不使用长期 PyPI Token。版本标签、包版本和变更日志必须一致，完整流程见[发布手册](docs/RELEASING.md)。

### 将流程引入一个项目

```powershell
cd D:\path\to\your-project
hmem init . --name "你的项目" --select-tools
```

命令会显示编号列表；输入一个或多个编号（逗号分隔），也可以输入 `all`。直接回车只初始化核心记忆目录，不接入客户端规则和 Skill。该交互仅在显式指定 `--select-tools` 时出现，不会阻塞脚本或 CI。

非交互环境继续使用稳定的参数形式：

```powershell
hmem init . --name "你的项目" --integrate codex
```

如果希望客户端常驻一条显式请求路由，可以生成 `AGENTS.md`：

```powershell
hmem init . --name "你的项目" --integrate codex --with-rules
```

这会创建：

```text
.ai-memory/
├── ACTIVE.md       # 当前任务唯一活动交接入口
├── config.json     # 机器可读配置与上次保存信息
└── sessions/       # 只增不改的历史快照
```

每个具名目标默认只生成原生项目级双 Skill（`handoff-save` 与 `handoff-resume`），不创建客户端规则。需要常驻提醒时显式增加 `--with-rules`；`hmem integrate` 会创建或幂等更新所选客户端的原生规则（Codex 和 OpenCode 使用根目录 `AGENTS.md`）以及项目级双 Skill。如果只想跨项目使用、不向仓库写入客户端配置，改用纯 Skill 管理命令 `hmem skills add <target> -g`。具名客户端包括：

```text
codex | claude | cursor | gemini | antigravity | copilot | windsurf
cline | kiro | trae | qoder | opencode
```

另有 `generic`、`skill` 和 `all`。菜单中的 `all`、`--integrate all` 与 `hmem skills add all` 都表示全部具名客户端；`generic` 仅为项目级通用规则，`skill` 为开放可移植 Skill 目录（项目 `.agents/skills/` 或全局 `~/.agents/skills/`）。完整路径可运行 `hmem help integrate` 与 `hmem help skills` 查看。

### 保存当前会话

让当前 AI 执行：

> 请使用 `handoff-save` 技能保存当前会话（或：请按照项目中的跨会话交接规则保存当前会话，核对实际修改和测试结果后更新交接文件）。

如果当前项目尚未初始化 `.ai-memory/`，`handoff-save` 会自动执行 `hmem init .` 创建核心记忆目录并完成首次交接（不会往项目写入客户端规则或 Skill）。独立的 `--integrate skill` 和 `hmem skills add skill [-g]` 仍用于只生成 `.agents/skills` 可移植副本。

只有用户明确提出保存、恢复、继续或核验跨会话任务时才会触发 Skill。普通对话、任务完成、代码提交、里程碑、关键决策、单轮对话结束和上下文变长都不会更新 `ACTIVE.md` 或创建快照。

或者手动编辑 `.ai-memory/ACTIVE.md`，然后运行：

```powershell
hmem save .
```

也可以让任何工具把完整交接写到文件或标准输入：

```powershell
hmem save . --from handoff.md
Get-Content -Raw handoff.md | hmem save . --from -
```

### 在新会话中恢复

新会话第一句话可以是：

> 请先运行 `hmem resume .`，核对当前产物、依据以及可用的版本库状态后继续上一次任务。

也可以直接复制命令输出作为首条上下文：

```powershell
hmem resume .
hmem resume . --format json
```

## 命令

| 命令 | 用途 |
|---|---|
| `hmem help [COMMAND]` | 查看总体或分命令详细帮助与示例 |
| `hmem init [PATH]` | 初始化记忆目录 |
| `hmem save [PATH]` | 校验、采集 Git/SVN 状态并归档 |
| `hmem resume [PATH]` | 输出恢复上下文和状态漂移 |
| `hmem check [PATH]` | 检查结构、必需章节和敏感信息 |
| `hmem history [PATH]` | 只读列举历史快照 |
| `hmem show SNAPSHOT [PATH]` | 只读查看指定快照或 `latest` |
| `hmem integrate TARGET [PATH]` | 为项目生成双 Skill，并可配合 `--with-rules` 更新客户端规则 |
| `hmem skills add TARGET [PATH] [-g]` | 仅安装或更新 `handoff-save` / `handoff-resume` 双 Skill（`-g` 装到全局） |
| `hmem skills status [PATH]` | 只读检查项目级与全局级双 Skill 状态及旧版 `session-handoff` 残留 |

执行 `hmem init --help` 可查看初始化参数，或用 `hmem init . --select-tools` 交互选择客户端。

完整说明见[中文使用指南](docs/USAGE.zh-CN.md)、[价值与恢复方式对照](docs/VALUE.md)和[跨工具接入说明](docs/INTEGRATIONS.md)。

## 推荐工作流

```text
用户明确要求恢复或继续上次任务
  └─ resume：只读 ACTIVE + 核对保存摘要、当前产物与可用版本库
       └─ 正常执行任务，不自动写入交接
            └─ 用户明确要求保存或准备切换会话
                 └─ 更新 ACTIVE + save
```

Handoff Memory 不监听每轮对话，也不依赖退出钩子自动总结。需要跨会话接续时，由用户在切换会话前明确要求保存；意外关闭后只能恢复最近一次显式保存的快照，并结合当前产物、依据以及可用的版本库状态核验后续改动。

普通聊天不应默认逐轮归档。只有当对话形成了需要未来继续的目标、决定、开放问题或约束时，才使用同一套七章节模板提炼交接；“产物与变更”可以是结论、草稿或链接，“验证与依据”可以是来源、人工确认或“尚未验证”，无需伪造代码、文件或测试。

`save` 会拒绝未填写的模板。推荐把 `ACTIVE.md` 控制在 2–8KB，只记录目标与完成标准、已落地结果、关键上下文与决策、产物状态、验证依据、风险和可执行下一步。模板适用于编码、写作、研究和规划；旧版编程标题继续兼容。缺少验证依据或无序下一步会产生非阻断质量提示。大小采用分级策略：

- 超过 16KB：提示继续精炼。
- 超过 64KB：默认拒绝保存；确认确有必要时可显式使用 `--allow-large`。
- 64–256KB 的交接仍可 `resume`，但会在正文前显示强警告。
- 超过 256KB：保存和恢复均拒绝，通常表示误粘贴了日志、diff 或聊天全文。

不建议把 `--allow-large` 变成固定配置或自动参数；它是避免紧急交接被完全阻断的显式逃生口。

## Git 与 SVN

工具会自动识别目标项目使用的版本控制系统：

- Git：采集分支、HEAD、远端 URL 和工作区变更。
- SVN：采集仓库相对位置、工作副本修订号、URL 和本地变更。
- 嵌套环境中同时存在两者时，选择离目标目录最近的 `.git` 或 `.svn` 标记。
- 对应 CLI 不可用时仍可保存交接，但恢复输出会说明无法核验版本库。

SVN 环境需要安装 Subversion CLI，并确保 `svn --version` 可执行。完整示例见[中文使用指南](docs/USAGE.zh-CN.md#11-svn-项目)。

## 安全模型

- 交接文件是**不可信参考信息**，不是可执行脚本。
- `resume` 永远不会执行其中记录的命令。
- `save` 会在快照元数据中记录规范化正文的 SHA-256；`resume` 会提示 `ACTIVE.md` 是否包含保存后的未归档编辑。
- `save` 默认阻止高置信度密钥模式，且错误只显示类型和行号。
- `check --privacy` 可额外检查常见个人信息；`check --strict` 可把质量与隐私警告作为 CI 失败处理。
- `resume` 检测到疑似密钥时会拒绝输出全文，避免把内容传播到新会话。
- `--allow-sensitive` 是显式逃生口；团队环境不建议使用。
- `.ai-memory` 是否提交 Git/SVN 由项目决定。项目事实可以提交，个人信息和私有路径建议忽略或拆分保存。

敏感信息检测不能替代专业 Secret Scanner。是否使用 GitHub Secret Scanning、Gitleaks、TruffleHog 或其他外部扫描器由维护者按项目策略决定，不属于当前发布门槛。

## 设计原则

- 当前产物、来源或人工确认，以及可用的版本库状态和测试是事实源；交接文件只是恢复索引。
- `ACTIVE.md` 只保留当前任务事实，避免把长期资料和聊天历史塞进上下文。
- 首版不提供向量检索；历史量真正变大后再增加可选索引层。
- 公共 CLI 采用向后兼容扩展，稳定 JSON 输出包含 `schema_version`。

设计依据见 [ADR-001](docs/decisions/ADR-001-local-markdown.md)、[ADR-002](docs/decisions/ADR-002-unified-vcs-state.md)、[ADR-003](docs/decisions/ADR-003-explicit-interactive-tool-selection.md)、[ADR-004](docs/decisions/ADR-004-native-project-skills.md)、[ADR-005](docs/decisions/ADR-005-explicit-rule-generation.md)、[ADR-006](docs/decisions/ADR-006-active-integrity.md)、[ADR-007](docs/decisions/ADR-007-task-oriented-template.md)、[ADR-008](docs/decisions/ADR-008-hmem-command.md)、[ADR-009](docs/decisions/ADR-009-reliable-save-and-drift.md)、[ADR-010](docs/decisions/ADR-010-machine-readable-operations-and-history.md)、[ADR-011](docs/decisions/ADR-011-single-hmem-entry.md) 与 [ADR-013](docs/decisions/ADR-013-dual-skills-and-global-install.md)。

## 开发

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m compileall -q src tests
python -m pip check
```

完整贡献政策、测试要求和 Pull Request 规范见[贡献指南](CONTRIBUTING.md)。

## 维护模式

Handoff Memory 由 `yuangyong` 单独维护，当前不招募共同维护者。欢迎通过 Issue 报告可复现缺陷或提出建议；除明显的拼写、链接等小型修正外，提交 Pull Request 前请先通过 Issue 确认范围。是否采纳建议、合并贡献、安排路线图和发布版本由维护者决定，不承诺响应或合并时限。MIT License 允许任何人依法使用、修改和 Fork 项目。

## 维护与反馈

- 使用问题与故障排查：[支持说明](SUPPORT.md)
- 功能建议与缺陷报告：[GitHub Issues](https://github.com/yuangyong/handoff-memory/issues)
- 贡献政策：[贡献指南](CONTRIBUTING.md)
- 公开协作行为规范：[行为准则](CODE_OF_CONDUCT.md)
- 安全漏洞：[安全策略](SECURITY.md)，请勿在公开 Issue 中粘贴密钥、真实交接内容或可利用细节
- 版本、PyPI 可信发布、Yank 与事件处理流程：[发布手册](docs/RELEASING.md)
- 后续优先级与非目标：[路线图](docs/ROADMAP.md)

当前提交作者邮箱是维护者专门用于开源身份的公开邮箱，无需重写 Git 历史。普通支持优先使用公开 Issue；安全问题遵循 `SECURITY.md` 的私密渠道。

## Star History

如果 handoff-memory 帮到了你，欢迎留下一个 ⭐ Star，让更多开发者发现它。

社区：[LINUX DO —— 中文开发者社区](https://linux.do/)

## 开源许可

MIT License。参见 [LICENSE](LICENSE)；采用该许可证的原因与影响见 [ADR-012](docs/decisions/ADR-012-mit-license.md)。
