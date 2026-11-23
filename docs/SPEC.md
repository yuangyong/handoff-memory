# Handoff Memory 产品规范

## 目标

Handoff Memory 是一个本地优先、跨 AI 工具的会话交接 CLI。它把当前任务状态保存为可读、可审计的 Markdown，在新会话中结合真实 Git 或 SVN 状态恢复上下文。

目标用户是使用主流 AI 编程客户端或其他编码代理，并需要在这些工具中接续编码、写作、研究或规划任务的个人与团队。纯闲聊记录不是产品目标。

## 技术栈

- Python 3.10+
- 运行期仅使用 Python 标准库
- Markdown 作为主要数据格式，JSON 保存机器配置
- `unittest` 作为测试框架

## 命令契约

```text
hmem help [COMMAND]
hmem init [PATH] [--name NAME] [--integrate TARGET | --select-tools] [--with-rules]
hmem save [PATH] [--from FILE|-] [--allow-sensitive] [--allow-large] [--format text|json]
hmem resume [PATH] [--format markdown|json]
hmem check [PATH] [--strict] [--privacy] [--format text|json]
hmem history [PATH] [--format markdown|json]
hmem show SNAPSHOT [PATH] [--format markdown|json]
hmem integrate TARGET [PATH] [--with-rules]
hmem skills add TARGET [PATH] [-g|--global]
hmem skills status [PATH] [--format text|json]
```

`hmem` 是唯一终端命令。帮助、版本、错误提示和示例始终使用 `hmem`；直接调用 Python `main([...])`、通过 `python -m handoff_memory` 启动或重命名启动器时也不得改变该名称。发行包名 `handoff-memory` 与模块名 `handoff_memory` 不属于 CLI 入口。

具名 AI 工具 `TARGET`：`codex`、`claude`、`cursor`、`gemini`、`antigravity`、`copilot`、`windsurf`、`cline`、`kiro`、`trae`、`qoder`、`opencode`。另有 `generic`、`skill`、`all`。

`help` 与每个命令的 `-h/--help` 都必须可用，并包含中文用途、参数说明和示例。`--select-tools` 显式开启零依赖交互多选；直接回车跳过工具接入，菜单中的 `all` 选择全部具名客户端。它与 `--integrate` 互斥，非交互脚本继续使用 `--integrate TARGET`。`--integrate all` 同样只选择全部具名客户端；`generic` 和 `skill` 必须单独指定。

每个具名目标默认只生成原生项目级双 Skill（`handoff-save/SKILL.md` 与 `handoff-resume/SKILL.md`）。项目级 Skill 目录由 `PROJECT_SKILL_ROOTS` 统一声明，用户级全局 Skill 目录由 `GLOBAL_SKILL_ROOTS` 统一声明，新增具名目标时必须同时提供路径与测试。显式指定 `--with-rules` 后，具有原生规则目录的客户端生成对应规则，`codex` 和 `opencode` 创建或幂等更新根目录 `AGENTS.md`；所有规则均保留受管区块外内容。`generic` 保留为只生成 `AI-HANDOFF.md` 的通用规则入口，`skill` 保留为只生成 `.agents/skills`（或全局 `~/.agents/skills`）可移植副本的独立入口。

`hmem skills` 仅管理 Skill（不创建客户端规则或 `.ai-memory/`）：`hmem skills add` 支持项目级与 `-g/--global` 全局安装，目标不包含 `generic`；`hmem skills status` 保持只读，检查项目与全局 Skill 同步状态及旧版 `session-handoff` 残留。

Skill 与规则只能在用户明确要求保存、恢复、继续或核验跨会话交接时触发。`handoff-save` 在目标项目完全未初始化（且非用户主目录或系统根目录）时显式先运行 `hmem init .` 再更新并保存；`handoff-resume` 与 `resume` 对交接文件保持严格只读，未初始化时绝不自动 `init`，仅在损坏、缺失或用户明确查询时只读调用 `history` / `show`。普通任务执行、阶段完成、代码提交、里程碑、关键决策、单轮对话结束或上下文变长均不得更新 `ACTIVE.md` 或创建快照。

Skill 检测到缺少 `hmem` CLI 时不得自动静默运行远程安装脚本；应先探测本机 `uv`/`pipx`，向用户展示标准 PyPI 安装命令并获得确认后再安装，或停止并给出手动安装指引。

所有命令成功返回 `0`；用户输入或状态无效返回 `2`；意外错误返回 `1`。

`history` 与 `show` 必须保持只读，并在 `ACTIVE.md` 缺失或配置损坏时仍允许历史救援。`show` 只接受 `.ai-memory/sessions` 中的快照文件名或 `latest`，拒绝路径穿越、符号链接越界、损坏元数据、超大文件和疑似密钥；`latest` 优先指向配置记录的最后完整保存。所有业务命令的 JSON 成功输出都包含 `schema_version` 与 `ok: true`；增加字段属于向后兼容变更。参数尚未成功解析时仍使用标准 CLI 文本错误。

## 项目结构

```text
src/handoff_memory/   CLI 与领域逻辑
tests/                单元与集成测试
docs/                 规范、设计决策及使用说明
examples/             示例交接文件
```

被初始化的目标项目包含：

```text
.ai-memory/
├── ACTIVE.md
├── config.json
└── sessions/
```

## 代码风格

- 公共函数使用类型注解和中文文档字符串。
- 路径参数统一解析为绝对路径，但输出尽量使用相对路径。
- 文件写入使用“临时文件 + 原子替换”；快照保存还必须使用跨进程锁和独占路径，不能覆盖已有历史。
- 外部进程仅允许固定参数的 Git/SVN 只读命令，不执行交接内容中的命令。

```python
def resolve_project(path: Path) -> Path:
    """解析并验证目标项目目录。"""
    project = path.expanduser().resolve()
    if not project.is_dir():
        raise UserError(f"项目目录不存在：{project}")
    return project
```

## 测试策略

- 单元测试：格式校验、敏感信息识别、模板渲染。
- CLI 契约测试：Wheel 只暴露 `hmem`，帮助与版本始终使用唯一品牌，旧 console script 不得出现。
- 文件系统集成测试：初始化、归档、恢复及幂等接入。
- Git 集成测试：临时仓库中验证分支、提交和脏工作区提示。
- SVN 集成测试：临时仓库与工作副本中验证 URL、修订号、变更和漂移提示。
- 不访问网络，不依赖真实 AI 服务。

## 边界

### 始终执行

- 校验所有 CLI 输入及目标路径。
- 保存前检查常见密钥模式。
- 保存前拒绝关键章节的模板占位内容；对缺少验证依据或无序下一步给出非阻断质量提示；超过 16KB 给出容量警告，超过 64KB 要求显式确认，超过 256KB 绝对拒绝。
- 恢复时重新读取 Git 或 SVN，而不是盲信旧摘要。
- 使用规范化的完整 Git/SVN 状态指纹识别脏工作区内部变化；状态采集失败必须报告未知，不能伪装为干净。
- 保存时由 CLI 在配置和快照元数据中记录规范化交接正文的 SHA-256，不在 `ACTIVE.md` 正文中记录其自身哈希。
- 恢复时先展示安全提示、保存时间、活动正文一致性和版本库漂移，再展示交接正文。
- 对已有集成文件执行幂等更新，不覆盖用户内容。
- 为每个具名 AI 工具生成其原生项目级（或显式 `-g/--global` 用户级）`handoff-save` 与 `handoff-resume` 双 Skill。
- 仅在用户指定 `--select-tools` 时读取交互输入。
- `history`、`show` 和 `skills status` 不修改 `ACTIVE.md`、配置、快照或任何 Skill 文件。

### 需要用户明确选择

- 使用 `-g/--global` 将双 Skill 安装到用户级全局目录。
- 在缺少 `hmem` CLI 时，由用户明确确认后再执行标准包管理器安装（`uv`/`pipx`）。

- 使用 `--allow-sensitive` 保存疑似敏感内容。
- 使用 `--allow-large` 保存 64–256KB 的大型交接。
- 使用 `--with-rules` 为所选客户端创建或更新原生规则。
- 使用 `--select-tools` 交互选择一个或多个 AI 编程客户端。
- 使用 `--force` 替换已有初始化文件。

### 永不执行

- 不上传交接内容。
- 不自动执行 `ACTIVE.md` 中记录的命令。
- 不保存聊天全文或环境变量。
- 不静默覆盖用户规则文件。

## 成功标准

- 可在空目录一条命令初始化完整记忆目录。
- AI 可通过编辑 `ACTIVE.md` 后调用 `save` 生成不可变历史快照。
- 未填写的初始模板不能被保存为有效交接。
- 正常交接保持紧凑：16KB 以上提示，64KB 以上默认拒绝保存但允许显式确认，256KB 以上保存和恢复均拒绝。
- 新会话调用 `resume` 可获得交接内容、当前正文相对最后保存的变化及 Git/SVN 漂移信息。
- 普通任务和会话内对话不会触发交接读写；只有用户明确请求保存时才创建快照。
- 12 个具名客户端均能默认生成原生项目级双 Skill（`handoff-save` 与 `handoff-resume`），并在显式指定 `--with-rules` 时生成适用规则；也支持通过 `hmem skills add <target> -g` 安装到用户全局 Skill 目录；重复执行不会重复插入内容。
- Windows、macOS、Linux 上均不需要运行期第三方依赖。
- Wheel 必须只安装 `hmem` 一个控制台入口。
- 单元测试以及临时 Git、SVN 仓库端到端测试全部通过。
- README 与中文使用说明覆盖安装、接入、保存、恢复、安全和故障处理。

## 非目标

- 首版不提供向量检索、知识图谱或云同步。
- 不解析任何厂商私有会话数据库。
- 不提供客户端关闭、任务完成或对话轮次结束时的自动保存；保存必须由用户明确请求。
- 不把没有持续目标的纯闲聊保存为逐轮聊天记录。

## 未决问题

无。首版优先交付透明、可靠、可移植的文件式流程。
