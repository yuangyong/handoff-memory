# Handoff Memory 产品规范

## 目标

Handoff Memory 是一个本地优先、跨 AI 工具的会话交接 CLI。它把当前任务状态保存为可读、可审计的 Markdown，在新会话中结合真实 Git 或 SVN 状态恢复上下文。

目标用户是使用 Codex、Claude Code、Cursor、Gemini CLI 或其他编码代理的个人与团队。

## 技术栈

- Python 3.10+
- 运行期仅使用 Python 标准库
- Markdown 作为主要数据格式，JSON 保存机器配置
- `unittest` 作为测试框架

## 命令契约

```text
handoff-memory init [PATH] [--name NAME] [--integrate TARGET]
handoff-memory save [PATH] [--from FILE|-] [--allow-sensitive]
handoff-memory resume [PATH] [--format markdown|json]
handoff-memory check [PATH]
handoff-memory integrate TARGET [PATH]
```

支持的 `TARGET`：`generic`、`codex`、`claude`、`cursor`、`gemini`、`skill`、`all`。

所有命令成功返回 `0`；用户输入或状态无效返回 `2`；意外错误返回 `1`。

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
- 文件写入使用“临时文件 + 原子替换”。
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
- 文件系统集成测试：初始化、归档、恢复及幂等接入。
- Git 集成测试：临时仓库中验证分支、提交和脏工作区提示。
- SVN 集成测试：临时仓库与工作副本中验证 URL、修订号、变更和漂移提示。
- 不访问网络，不依赖真实 AI 服务。

## 边界

### 始终执行

- 校验所有 CLI 输入及目标路径。
- 保存前检查常见密钥模式。
- 保存前拒绝模板占位内容；超过 16KB 给出质量警告，超过 64KB 要求显式确认，超过 256KB 绝对拒绝。
- 恢复时重新读取 Git 或 SVN，而不是盲信旧摘要。
- 恢复时先展示安全提示、保存时间和版本库漂移，再展示交接正文。
- 对已有集成文件执行幂等更新，不覆盖用户内容。

### 需要用户明确选择

- 使用 `--allow-sensitive` 保存疑似敏感内容。
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
- 新会话调用 `resume` 可获得交接内容及当前 Git/SVN 漂移信息。
- 六类集成目标均能生成且重复执行不会重复插入内容。
- Windows、macOS、Linux 上均不需要运行期第三方依赖。
- 单元测试以及临时 Git、SVN 仓库端到端测试全部通过。
- README 与中文使用说明覆盖安装、接入、保存、恢复、安全和故障处理。

## 非目标

- 首版不提供向量检索、知识图谱或云同步。
- 不解析任何厂商私有会话数据库。
- 不承诺客户端关闭时一定触发自动保存。

## 未决问题

无。首版优先交付透明、可靠、可移植的文件式流程。
