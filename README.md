# Handoff Memory

本地优先、跨 AI 工具的会话交接记忆 CLI。

Handoff Memory 解决的不是“让模型记住一切”，而是一个更可验证的问题：**让下一次 AI 会话准确知道当前任务做到哪里，并用真实仓库状态核验旧摘要。**

它不绑定模型、云服务或向量数据库。数据就是项目中的 Markdown，任何 AI、编辑器和人都能读取。

## 特性

- 本地优先：默认不联网、不上传、不调用 LLM。
- 跨工具：内置 Codex、Claude Code、Cursor、Gemini 和通用 AI 规则。
- 可审计：活动交接和历史快照都是 UTF-8 Markdown。
- 可核验：自动识别 Git/SVN，恢复时重新采集分支或仓库位置、HEAD 或修订号以及工作区状态。
- 安全默认：阻止常见 API Key、访问令牌和私钥进入快照。
- 幂等接入：更新规则文件中的受管区块，不覆盖已有用户规则。
- 零运行期依赖：仅要求 Python 3.10+。

## 快速开始

### 安装

推荐使用 `pipx` 或 `uv`，避免污染项目环境：

```powershell
pipx install .
# 或
uv tool install .
```

开发模式：

```powershell
python -m pip install -e .
```

### 将流程引入一个项目

```powershell
cd D:\path\to\your-project
handoff-memory init . --name "你的项目" --integrate codex
```

把 `codex` 换成正在使用的 `claude`、`cursor`、`gemini`、`generic` 或 `skill`。只有确实同时使用多个客户端时才选择 `all`。

这会创建：

```text
.ai-memory/
├── ACTIVE.md       # 当前任务唯一活动交接入口
├── config.json     # 机器可读配置与上次保存信息
└── sessions/       # 只增不改的历史快照
```

同时只生成所选 AI 工具的接入规则，例如 Codex 使用 `AGENTS.md`。支持的目标包括：

```text
codex | claude | cursor | gemini | generic | skill | all
```

### 保存当前会话

让当前 AI 执行：

> 请使用 session-handoff 技能保存当前会话，核对实际修改和测试结果后更新交接文件。

或者手动编辑 `.ai-memory/ACTIVE.md`，然后运行：

```powershell
handoff-memory save .
```

也可以让任何工具把完整交接写到文件或标准输入：

```powershell
handoff-memory save . --from handoff.md
Get-Content -Raw handoff.md | handoff-memory save . --from -
```

### 在新会话中恢复

新会话第一句话可以是：

> 请先运行 `handoff-memory resume .`，核对 Git/SVN 和当前文件后继续上一次任务。

也可以直接复制命令输出作为首条上下文：

```powershell
handoff-memory resume .
handoff-memory resume . --format json
```

## 命令

| 命令 | 用途 |
|---|---|
| `handoff-memory init [PATH]` | 初始化记忆目录 |
| `handoff-memory save [PATH]` | 校验、采集 Git/SVN 状态并归档 |
| `handoff-memory resume [PATH]` | 输出恢复上下文和状态漂移 |
| `handoff-memory check [PATH]` | 检查结构、必需章节和敏感信息 |
| `handoff-memory integrate TARGET [PATH]` | 添加或更新 AI 工具规则 |

接入目标：`generic`、`codex`、`claude`、`cursor`、`gemini`、`skill`、`all`。

完整说明见[中文使用指南](docs/USAGE.zh-CN.md)和[跨工具接入说明](docs/INTEGRATIONS.md)。

## 推荐工作流

```text
新会话开始
  └─ resume：读取 ACTIVE + 核对当前 Git/SVN
       └─ 执行任务
            ├─ 里程碑：更新 ACTIVE + save
            ├─ 关键决策：更新 ACTIVE + save
            └─ 会话结束：更新 ACTIVE + save
```

不要只依赖客户端正常退出。窗口关闭、网络错误或上下文压缩都可能导致结束钩子没有机会运行，因此里程碑快照比“退出时自动总结”更可靠。

`save` 会拒绝未填写的模板。推荐把 `ACTIVE.md` 控制在 2–8KB，只记录当前目标、已完成、关键决策、验证、风险和下一步。大小采用分级策略：

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
- `save` 默认阻止高置信度密钥模式，且错误只显示类型和行号。
- `resume` 检测到疑似密钥时会拒绝输出全文，避免把内容传播到新会话。
- `--allow-sensitive` 是显式逃生口；团队环境不建议使用。
- `.ai-memory` 是否提交 Git/SVN 由项目决定。项目事实可以提交，个人信息和私有路径建议忽略或拆分保存。

敏感信息检测不能替代专业 Secret Scanner。公开仓库仍建议启用 GitHub Secret Scanning、Gitleaks 或 TruffleHog。

## 设计原则

- 当前代码、版本库状态和测试是事实源，交接文件只是恢复索引。
- `ACTIVE.md` 只保留当前任务事实，避免把长期资料和聊天历史塞进上下文。
- 首版不提供向量检索；历史量真正变大后再增加可选索引层。
- 公共 CLI 采用向后兼容扩展，稳定 JSON 输出包含 `schema_version`。

设计依据见 [ADR-001](docs/decisions/ADR-001-local-markdown.md) 与 [ADR-002](docs/decisions/ADR-002-unified-vcs-state.md)。

## 开发

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m compileall -q src tests
python -m pip check
```

## 开源许可

Apache License 2.0。参见 [LICENSE](LICENSE)。
