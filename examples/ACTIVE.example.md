# 当前任务交接

## 当前目标

为示例项目增加跨会话恢复流程，并保证 Windows 与 Linux 行为一致。

## 已完成

- 定义 CLI 命令契约。
- 完成初始化与快照归档测试。

## 关键决策

- 使用 Markdown 作为事实源。
- 运行期不增加第三方依赖。

## 修改文件

- `src/handoff_memory/core.py`
- `tests/test_core.py`

## 验证结果

- `python -m unittest discover -s tests -v`：通过。
- 尚未执行 macOS 手动验证，交由 CI 覆盖。

## 阻塞与风险

- 某些 AI 客户端不会自动加载项目规则，需要显式恢复提示。

## 下一步

1. 在临时 Git 仓库执行端到端演练。
2. 检查打包产物。
3. 在一个真实目标项目完成首次保存与恢复。
