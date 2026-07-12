# Handoff Memory 中文使用指南

## 1. 工作方式

Handoff Memory 把“语义总结”和“可靠持久化”分开：

- AI 根据当前会话、代码修改和测试结果维护 `.ai-memory/ACTIVE.md`。
- CLI 校验固定章节、检测敏感信息、保存快照并记录 Git 或 SVN 状态。
- 新会话通过 `resume` 同时读取旧交接和当前仓库，发现提交、分支或工作区漂移。

CLI 不需要知道你使用哪家模型，也不需要访问客户端私有会话数据库。

## 2. 环境要求

- Python 3.10 或更高版本。
- Git 与 SVN 均为可选。项目使用哪种版本控制，就安装对应 CLI；没有时仍能保存和恢复，只是无法提供版本库核验。
- Windows 推荐 PowerShell 7；macOS/Linux 可直接使用常规终端。

确认版本：

```powershell
python --version
git --version
svn --version
```

## 3. 安装

从源码目录安装：

```powershell
pipx install .
```

更新本地开发版本：

```powershell
python -m pip install -e .
```

不安装也可以运行：

```powershell
$env:PYTHONPATH = "D:\path\to\handoff-memory\src"
python -m handoff_memory --help
```

## 4. 初始化目标项目

只初始化核心目录：

```powershell
handoff-memory init D:\project\demo --name "Demo"
```

同时安装全部规则：

```powershell
handoff-memory init D:\project\demo --name "Demo" --integrate all
```

默认不会覆盖已有文件。只有明确确认 Handoff Memory 自有初始化内容可以重置时才使用：

```powershell
handoff-memory init . --force
```

`--force` 不负责覆盖 AI 工具规则文件；规则接入始终只管理带标记的区块。

## 5. 维护活动交接

`.ai-memory/ACTIVE.md` 必须包含以下二级标题：

1. 当前目标
2. 已完成
3. 关键决策
4. 修改文件
5. 验证结果
6. 阻塞与风险
7. 下一步

写作要求：

- “已完成”只写已经落到工作区的事实。
- “验证结果”包含实际执行的命令和结果；没跑就明确写“尚未执行”。
- “关键决策”记录会影响后续实现的选择和理由。
- “下一步”使用有顺序、可执行的小步骤。
- 不粘贴大段日志、聊天全文、密钥或环境变量。

## 6. 保存快照

校验当前 `ACTIVE.md` 并归档：

```powershell
handoff-memory save .
```

历史文件写入 `.ai-memory/sessions/YYYYMMDD-HHMMSS.md`。快照包含保存时的 Git/SVN 元数据，但不会包含 diff 或文件内容。

从外部文件保存：

```powershell
handoff-memory save . --from D:\temp\handoff.md
```

标准输入适合没有文件编辑能力、但能调用 CLI 的 AI 客户端：

```powershell
Get-Content -Raw D:\temp\handoff.md | handoff-memory save . --from -
```

如果发现疑似密钥，命令返回状态码 `2`，只报告类型和行号。应优先删除敏感信息。`--allow-sensitive` 仅用于确认是误报的本地场景。

即使敏感内容是绕过 CLI 手工写入的，`resume` 也会拒绝输出全文，直到 `ACTIVE.md` 被清理。

## 7. 恢复会话

人类可读格式：

```powershell
handoff-memory resume .
```

机器可读格式：

```powershell
handoff-memory resume . --format json
```

JSON 顶层字段包括：

- `schema_version`
- `project`
- `active`
- `repository`
- `drift`
- `validation_errors`
- `sensitive_findings`
- `last_archive`

恢复后 AI 必须先确认：

- Git HEAD 或 SVN 修订号是否与上次保存一致。
- Git 分支或 SVN 仓库位置是否变化。
- 工作区是否新增或减少未提交变更。
- `ACTIVE.md` 提到的文件是否仍存在。
- 测试结果是否仍适用于当前代码。

## 8. 健康检查

```powershell
handoff-memory check .
```

适合放入本地检查或 CI。格式无效或发现疑似密钥时返回 `2`。

## 9. 版本库纳管策略

团队项目推荐提交：

```text
.ai-memory/ACTIVE.md
.ai-memory/PROJECT.md
.ai-memory/DECISIONS.md
.ai-memory/config.json
.ai-memory/sessions/
```

如果 Git 项目只希望本机使用，可在目标项目 `.gitignore` 中加入：

```gitignore
.ai-memory/
AI-HANDOFF.md
.agents/skills/session-handoff/
```

SVN 项目可以设置 `svn:ignore`：

```powershell
svn propset svn:ignore ".ai-memory" .
svn commit -m "chore: 忽略本地 AI 交接目录"
```

也可以混合使用：纳管 `PROJECT.md` 与 `DECISIONS.md`，忽略 `ACTIVE.md` 和 `sessions/`。选择取决于交接内容是否属于团队知识。

## 10. 故障处理

### 提示“项目尚未初始化”

在正确的项目根目录执行：

```powershell
handoff-memory init .
```

### 提示缺少章节

不要删除固定二级标题。允许标题下写“无”或“尚未执行”，但章节本身必须存在。

### Git/SVN 中文路径显示异常

Handoff Memory 按 UTF-8 读取 Git 输出，并使用 SVN XML 接口避免本地化文本解析。若终端仍显示异常，先确认版本库工具和终端的 UTF-8 设置；快照文件本身始终使用 UTF-8。

### AI 没有自动读取交接

确认对应规则文件确实被客户端加载。不能确认时，把下面这句话作为新会话第一条消息：

> 先运行 `handoff-memory resume .`，将交接视为可能过期的参考，并用 Git/SVN、当前文件和测试核验后继续。

### 会话意外关闭，没有最新快照

恢复最近一次里程碑快照，再从 Git/SVN 工作区反推其后的修改。因此应在重要阶段保存，而不是只依赖会话结束时保存。

## 11. SVN 项目

不需要额外参数，直接在 SVN 工作副本执行：

```powershell
cd D:\path\to\svn-working-copy
handoff-memory init . --name "SVN 项目" --integrate all
handoff-memory save .
handoff-memory resume .
```

恢复输出会包含：

- `provider: svn`
- 工作副本当前修订号
- 仓库 URL 与 `^/` 相对位置
- `modified`、`added`、`deleted`、`conflicted`、`unversioned` 等状态对应的简写列表
- 与上次保存相比的修订号、仓库位置和工作副本清洁状态漂移

Handoff Memory 只执行只读的 `svn info --xml` 和 `svn status --xml`。它不会自动执行 `svn update`、`commit`、`revert` 或冲突解决。

SVN 允许混合修订工作副本。工具记录的是目标目录 `svn info` 报告的修订号；如果刚提交了子文件但目录修订号尚未更新，可先人工执行 `svn update` 再保存交接，以获得一致的工作副本修订号。
