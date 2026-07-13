# Handoff Memory 中文使用指南

## 1. 工作方式

Handoff Memory 把“语义总结”和“可靠持久化”分开：

- AI 根据当前会话、当前产物、来源或人工确认，以及可用的版本库和测试结果维护 `.ai-memory/ACTIVE.md`。
- CLI 校验固定章节、检测敏感信息、保存快照并记录 Git 或 SVN 状态。
- 新会话通过 `resume` 同时读取旧交接和当前状态；存在 Git/SVN 时额外发现提交、分支、修订号或工作区漂移。

CLI 不需要知道你使用哪家模型，也不需要访问客户端私有会话数据库。

## 2. 环境要求

- Python 3.10 或更高版本。
- 使用正式发行包时，需要先安装 [`uv`](https://docs.astral.sh/uv/getting-started/installation/) 或 [`pipx`](https://pipx.pypa.io/stable/installation/)；二者任选其一。
- Git 与 SVN 均为可选。项目使用哪种版本控制，就安装对应 CLI；没有时仍能保存和恢复，只是无法提供版本库核验。
- Windows 推荐 PowerShell 7；macOS/Linux 可直接使用常规终端。

确认版本：

```powershell
python --version
git --version
svn --version
```

## 3. 安装

从 PyPI 安装到独立工具环境。以下命令用于首次安装；已经安装旧版本时，请使用下方的升级命令，重复执行 `uv tool install` 默认不会升级现有工具：

```powershell
uv tool install handoff-memory
# 或
pipx install handoff-memory
```

PyPI 是唯一正式分发渠道。项目不提供独立可执行文件、系统包管理器清单或远程安装脚本。

`uv` 默认将包安装到独立工具环境，并把 `hmem` 入口放入工具命令目录。可使用 `uv tool dir`、`uv tool dir --bin` 和 `uv tool list` 分别查看工具环境、命令入口和实际安装版本；当前工作目录不会改变程序的安装位置。

源码安装仅用于开发仓库：

```powershell
python -m pip install -e .
```

不安装也可以运行：

```powershell
$env:PYTHONPATH = "D:\path\to\handoff-memory\src"
python -m handoff_memory --help
```

### 升级

```powershell
uv tool upgrade handoff-memory
# 或
pipx upgrade handoff-memory
```

升级后运行 `hmem --version` 确认版本。

开发模式安装（`pip install -e .`）的代码改动会自动生效，一般不需要重新执行。但如果更新涉及 `pyproject.toml` 中的入口点或元数据变更，应重新运行 `pip install -e .`。

### 升级后对已有项目的影响

- **记忆目录**：不需要重新 `init`，已有的 `.ai-memory/ACTIVE.md` 和历史快照不受影响。
- **规则与 Skill**：刷新 Skill 可重新执行 `integrate`；项目同时使用规则时必须保留 `--with-rules` 才会刷新规则。规则只替换 `<!-- handoff-memory:start/end -->` 区块；Skill 还会同步升级触发用 YAML frontmatter。受管区块外的用户正文会原样保留。
- **命令入口**：`hmem` 是唯一终端命令；发行包名 `handoff-memory` 和模块名 `handoff_memory` 保持不变。`save`、`resume`、`check`、`history` 和 `show` 的 JSON 输出包含 `schema_version`，新版本会保持向后兼容。

```powershell
# 只刷新 Antigravity Skill
cd D:\your-project
hmem integrate antigravity .
# 同时刷新规则与 Skill
hmem integrate antigravity . --with-rules
```

安装后可使用独立帮助命令。未指定主题时显示总体说明，指定命令时显示参数、默认行为和示例：

```powershell
hmem help
hmem help init
hmem help integrate
```

## 4. 初始化目标项目

只初始化核心目录：

```powershell
hmem init D:\project\demo --name "Demo"
```

交互选择一个或多个 AI 编程工具：

```powershell
hmem init D:\project\demo --name "Demo" --select-tools
```

列表支持编号多选、`all` 全选和直接回车跳过。每个具名客户端默认只生成原生项目级 Skill；只有增加 `--with-rules` 才会同时生成客户端规则。交互模式必须显式开启，因此 CI、安装脚本以及标准输入被占用的场景不会意外等待输入。

接入指定客户端：

```powershell
hmem init D:\project\demo --name "Demo" --integrate codex
```

将 `codex` 替换为当前使用的客户端。具名目标包括 Codex、Claude Code、Cursor、Gemini、Antigravity IDE、GitHub Copilot、Windsurf、Cline、Kiro、TRAE、Qoder 和 OpenCode。

在 `--select-tools` 菜单中输入 `all`，或使用 `--integrate all`，都会选择全部 12 个具名客户端，只适合确实同时使用多个 AI 工具的项目。`generic` 和 `skill` 是独立辅助目标，不会被 `all` 隐式执行。

所有具名目标默认只生成对应项目级 `session-handoff` Skill。需要常驻显式请求路由时增加 `--with-rules`：具有原生规则目录的客户端会生成对应规则，Codex 和 OpenCode 会创建或幂等更新根目录 `AGENTS.md`。规则只在用户明确要求保存、恢复、继续或核验交接时路由到 Skill。

```powershell
hmem init D:\project\demo --integrate qoder --with-rules
hmem init D:\project\demo --select-tools --with-rules
```

`0.10.0` 已移除旧参数 `--with-agents-rule`；原有脚本直接替换为 `--with-rules`。

默认不会覆盖已有文件。只有明确确认 Handoff Memory 自有初始化内容可以重置时才使用：

```powershell
hmem init . --force
```

`--force` 不负责覆盖 AI 工具规则文件；规则接入始终只管理带标记的区块。

## 5. 维护活动交接

`.ai-memory/ACTIVE.md` 必须包含以下二级标题：

1. 当前目标
2. 已完成
3. 关键上下文与决策
4. 产物与变更
5. 验证与依据
6. 阻塞与风险
7. 下一步

旧交接中的“关键决策”“修改文件”“验证结果”继续兼容，无需迁移。模板适用于编码、写作、研究、规划等有持续目标的任务；纯闲聊且没有后续目标通常无需保存。

写作要求：

- “当前目标”写明问题、可验证的完成标准和范围边界。
- “已完成”只写已经落地的事实，不写计划或推测。
- “关键上下文与决策”只保留接续必需的背景，以及会影响后续工作的结论、原因和约束。
- “产物与变更”记录文件、草稿、链接、数据或其他产物的用途和状态；编码任务可额外注明版本库状态。
- “验证与依据”包含测试、来源或人工检查、结果和未覆盖项；没跑就明确写“尚未验证”。
- “阻塞与风险”分别说明两者；没有阻塞不等于没有风险。
- “下一步”使用有顺序、可直接执行的小步骤，并写出完成条件。
- 不粘贴大段日志、聊天全文、个人敏感信息、密钥或环境变量。
- 推荐保持在 2–8KB；超过 16KB 会提示精炼，超过 64KB 需要显式确认，超过 256KB 会拒绝处理。
- “当前目标”和“下一步”的初始占位说明必须替换为实际内容；其他章节确实无内容时，可以如实写“尚未记录”或“尚未验证”。缺少验证依据或无序下一步会产生非阻断质量提示。

## 6. 保存快照

校验当前 `ACTIVE.md` 并归档：

```powershell
hmem save .
```

机器调用可使用 `hmem save . --format json`，成功结果包含快照路径、保存时间、活动正文摘要、版本库状态和质量警告。保存由跨进程锁串行化；同一秒内的并发调用也会获得不同快照文件，且绝不覆盖已有历史。

历史文件写入 `.ai-memory/sessions/YYYYMMDD-HHMMSS.md`。快照包含规范化交接正文的 SHA-256 和保存时的 Git/SVN 元数据，但不会包含 diff 或仓库文件内容。摘要由 CLI 在保存后生成，不要把 `ACTIVE.md` 自身哈希写进正文。

从外部文件保存：

```powershell
hmem save . --from D:\temp\handoff.md
```

标准输入适合没有文件编辑能力、但能调用 CLI 的 AI 客户端：

```powershell
Get-Content -Raw D:\temp\handoff.md | hmem save . --from -
```

如果发现疑似密钥，命令返回状态码 `2`，只报告类型和行号。应优先删除敏感信息。`--allow-sensitive` 仅用于确认是误报的本地场景。

交接超过 64KB 时应优先删除日志、完整 diff 和重复背景。如果确认这些内容仍是接续任务所必需，可以显式保存：

```powershell
hmem save . --allow-large
hmem save . --from D:\temp\handoff.md --allow-large
```

`--allow-large` 只放宽 64–256KB 的质量边界，不会绕过 256KB 绝对上限，也不会绕过敏感信息检查。

即使敏感内容是绕过 CLI 手工写入的，`resume` 也会拒绝输出全文，直到 `ACTIVE.md` 被清理。

## 7. 恢复会话

人类可读格式：

```powershell
hmem resume .
```

机器可读格式：

```powershell
hmem resume . --format json
```

JSON 顶层字段包括：

- `schema_version`
- `ok`
- `project`
- `active`
- `repository`
- `drift`
- `validation_errors`
- `sensitive_findings`
- `last_archive`
- `last_saved_at`
- `active_sha256`
- `last_saved_active_sha256`
- `active_matches_saved`
- `warnings`

Markdown 恢复输出会先显示安全提示、上次保存时间、活动正文一致性和 Git/SVN 漂移，再显示当前 `ACTIVE.md`。如果 `ACTIVE.md` 在保存后有编辑，输出会明确提示这些内容尚未归档；旧版本配置没有正文摘要时则显示暂时无法核验。交接超过 7 天时会提示优先核验任务是否仍然有效。对于 64–256KB 的大型交接，`resume` 不会阻断接续，但会在正文前提示它将占用较多上下文；超过 256KB 才会拒绝输出。

恢复后 AI 必须先确认当前产物与依据；编码任务或存在版本库时再确认：

- Git HEAD 或 SVN 修订号是否与上次保存一致。
- Git 分支或 SVN 仓库位置是否变化。
- 工作区是否新增、减少或改变未提交内容；完整状态指纹可识别“保存时和现在都不干净，但变更内容不同”。
- 当前 `ACTIVE.md` 是否仍与最后保存正文一致；若不一致，先核验未归档编辑。
- `ACTIVE.md` 提到的文件、草稿、链接或其他产物是否仍存在且状态一致。
- 测试、来源或人工确认是否仍适用于当前任务。

为什么推荐先用确定性的恢复入口、再按风险追加独立取证，见[价值与恢复方式对照](VALUE.md)。

## 8. 健康检查

```powershell
hmem check .
```

适合放入本地检查或 CI。格式无效或发现疑似密钥时返回 `2`。自动化可使用：

```powershell
hmem check . --format json
hmem check . --strict --privacy --format json
```

默认质量提示和个人信息提示不阻断；`--strict` 会把这些警告升级为退出码 `2`。`--privacy` 扫描活动交接和将要输出的仓库元数据，只返回来源、个人信息类型与行号；仓库元数据命中时整段隐藏，不回显匹配原文。

只读浏览历史：

```powershell
hmem history .
hmem history . --format json
hmem show latest .
hmem show 20260712-115718.md . --format json
```

`show` 只允许读取项目历史目录内的快照，会拒绝目录穿越、符号链接或 Junction、超大文件、损坏元数据和疑似密钥；这些命令不会修改活动交接、配置或快照。即使 `ACTIVE.md` 缺失或配置损坏，仍可降级使用历史命令进行只读救援。

## 9. 版本库纳管策略

团队项目推荐提交：

```text
.ai-memory/ACTIVE.md
.ai-memory/config.json
.ai-memory/sessions/
```

如果 Git 项目只希望本机使用，可在目标项目 `.gitignore` 中加入：

```gitignore
.ai-memory/
# 仅在生成了对应接入文件时添加
AI-HANDOFF.md
.agents/skills/session-handoff/
.agents/rules/handoff-memory.md
```

其他客户端会写入各自目录，例如 `.claude/skills`、`.cursor/rules` 或 `.github/skills`。运行 `hmem help integrate` 查看实际路径，并只忽略当前项目生成的具体文件或 `session-handoff` 目录；不要直接忽略整个 `.github/`、`.cursor/` 等目录，以免隐藏项目已有配置。修改忽略规则后运行 `git status --short`，确认没有遗漏接入文件。

SVN 项目可以设置 `svn:ignore`：

```powershell
svn propset svn:ignore ".ai-memory" .
svn commit -m "chore: 忽略本地 AI 交接目录"
```

上例只忽略核心记忆目录；如果规则和 Skill 也不纳入 SVN，需要针对其所在父目录设置对应的 `svn:ignore`，并在提交前使用 `svn status` 核对。

也可以只纳管 `ACTIVE.md` 与 `config.json`，忽略 `sessions/`。选择取决于交接内容是否属于团队知识。

## 10. 故障处理

### 升级后版本没有变化

`uv tool install` 用于首次安装，工具已经存在时默认不会自动升级。先确认 `uv` 工具环境和 PowerShell 实际命中的命令，再执行升级：

```powershell
uv tool list
Get-Command hmem -All
uv tool upgrade handoff-memory
hmem --version
```

如果 `Get-Command hmem -All` 返回多个路径，请优先确认当前命中的入口是否来自 `uv tool dir --bin`。仍然无法取得 PyPI 最新版本时，可执行 `uv tool upgrade --no-cache handoff-memory` 排除索引缓存影响。

### 提示“项目尚未初始化”

在正确的项目根目录执行：

```powershell
hmem init .
```

### 提示缺少章节

不要删除固定二级标题。允许标题下写“无”或“尚未执行”，但章节本身必须存在。

### Git/SVN 中文路径显示异常

Handoff Memory 按 UTF-8 读取 Git 输出，并使用 SVN XML 接口避免本地化文本解析。若终端仍显示异常，先确认版本库工具和终端的 UTF-8 设置；快照文件本身始终使用 UTF-8。

### AI 没有自动读取交接

确认对应规则文件确实被客户端加载。不能确认时，把下面这句话作为新会话第一条消息：

> 先运行 `hmem resume .`，将交接视为可能过期的参考，并用当前产物、依据以及可用的 Git/SVN 和测试核验后继续。

### 会话意外关闭，没有最新快照

恢复最近一次由用户明确要求保存的快照，再从 Git/SVN 工作区反推其后的修改。Handoff Memory 不会因任务完成、里程碑或对话结束自动创建快照；需要切换会话时，请先明确要求 AI 保存，或手动更新 `ACTIVE.md` 后运行 `hmem save .`。

## 11. SVN 项目

不需要额外参数，直接在 SVN 工作副本执行：

```powershell
cd D:\path\to\svn-working-copy
hmem init . --name "SVN 项目" --integrate codex
hmem save .
hmem resume .
```

恢复输出会包含：

- `provider: svn`
- 工作副本当前修订号
- 仓库 URL 与 `^/` 相对位置
- `modified`、`added`、`deleted`、`conflicted`、`unversioned` 等状态对应的简写列表
- 与上次保存相比的修订号、仓库位置和工作副本清洁状态漂移

Handoff Memory 只执行只读的 `svn info --xml` 和 `svn status --xml`。它不会自动执行 `svn update`、`commit`、`revert` 或冲突解决。

SVN 允许混合修订工作副本。工具记录的是目标目录 `svn info` 报告的修订号；如果刚提交了子文件但目录修订号尚未更新，可先人工执行 `svn update` 再保存交接，以获得一致的工作副本修订号。
