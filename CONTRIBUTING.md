# 贡献指南

Handoff Memory 由 `yuangyong` 单独维护，当前不招募共同维护者。本指南说明外部反馈和贡献的接受边界，不构成共同维护、路线图参与或持续评审邀请。

参与公开协作即表示你同意遵守[行为准则](CODE_OF_CONDUCT.md)。安全漏洞不要通过公开 Issue 或 Pull Request 报告，请改用[安全策略](SECURITY.md)中的私密渠道。

## 开始之前

- 使用问题先查阅 [README](README.md)、[中文使用指南](docs/USAGE.zh-CN.md)和[支持说明](SUPPORT.md)。
- 缺陷报告和功能建议可以直接创建 Issue；请提供可复现信息并先搜索现有条目。
- 除明显的拼写、链接等小型修正外，代码或较大文档 Pull Request 必须先创建 Issue，说明动机、用户场景和兼容性影响，并等待维护者确认范围。
- 未经确认的大型 Pull Request 可能直接关闭；维护者也可能采纳思路后独立实现，不保证采用提交中的具体方案。
- 不要在 Issue、测试夹具或提交中加入真实密钥、Token、个人交接文件或未脱敏的私人路径。

## 本地开发

要求 Python 3.10+。核心运行期保持零第三方依赖；开发检查可以使用 Ruff、mypy、build 和 twine。

```powershell
git clone https://github.com/yuangyong/handoff-memory.git
cd handoff-memory
python -m pip install -e .
$env:PYTHONPATH = "src"
```

运行与 CI 对齐的基础检查：

```powershell
python -m unittest discover -s tests -v
python -m compileall -q src tests
python scripts/sync_session_handoff_skill.py --check
python -m pip check
```

如果本地安装了质量工具，再运行：

```powershell
ruff check src tests scripts
mypy --no-incremental src/handoff_memory
```

构建发行包时运行：

```powershell
python -m build
python -m twine check dist/*
```

生成的 `build/`、`dist/`、缓存和虚拟环境不得提交。

## 设计约束

- 保持核心运行期零第三方依赖；新增依赖前说明必要性、维护状态、许可证、包体积和无依赖替代方案。
- 公共 CLI 与 JSON 输出只做兼容性扩展；破坏性变化必须提供新 schema、迁移说明和变更日志。
- 改变行为时先增加会失败的测试，再实现最小修复。
- 不增加默认联网、遥测、云账户或特定 AI 厂商依赖。
- 用户输入、Git/SVN 输出、路径和交接内容都视为不可信数据。
- 保存仅由用户明确触发；恢复、历史和查看命令保持只读。
- 中文是当前主要文档语言。面向国际用户的入口和关键操作应同步维护英文概览。

涉及长期兼容性、数据格式、安全边界或跨客户端约定的决策，应更新 `docs/SPEC.md`，并在必要时新增 ADR；不要删除旧 ADR，应通过新 ADR 标记取代关系。

## 变更与测试

Pull Request 应保持单一目的并尽量小。请根据变更类型提供相称的验证：

| 变更类型 | 最低验证 |
|---|---|
| 文档 | 本地链接、外链可达性、`git diff --check` |
| CLI 行为 | 单元测试、CLI 契约测试、编译检查 |
| 文件系统或安全 | 正常路径、拒绝路径、Windows/Unix 差异测试 |
| Git/SVN | 临时仓库集成测试；不能访问网络或真实仓库 |
| 分发与入口 | Wheel/sdist 构建、twine 检查、外部目录安装冒烟 |
| Skill/规则模板 | 同步脚本、幂等更新和用户内容保留测试 |

测试应验证可观察行为，不要依赖执行顺序、真实用户目录、网络服务或本机已有 AI 配置。

## 提交规范

推荐 Conventional Commits，冒号后的说明使用中文：

```text
feat: 增加新的 AI 工具适配
fix: 修复 Windows 路径归档问题
docs: 完善公开发布说明
test: 增加并发保存回归测试
```

一个提交只处理一个逻辑问题。不要把大范围格式化、重构和行为变更混在同一提交中。

## Pull Request 要求

提交前确认：

- 已说明问题、方案、用户可见影响和不在范围内的内容。
- 新行为有测试，文档与实际命令一致。
- 完整测试通过，或明确列出无法执行的检查和原因。
- `git diff --check` 通过，Skill 分发副本保持同步。
- diff 和提交历史中没有密钥、Token、私钥或非预期个人信息。
- 没有提交 `.ai-memory/`、构建产物、缓存或本机 AI 客户端配置。
- 公共 CLI、JSON schema、快照格式或安全边界变化已更新规范、ADR 和变更日志。

维护者会优先判断正确性、安全、兼容性、范围和长期维护成本，再讨论风格偏好。提交者仍需根据反馈更新变更；创建或接受 Pull Request 不授予维护权限、发布权限或路线图决策权，也不保证评审、响应或合并时限。

## 许可证与归属

贡献内容按本仓库的 [MIT License](LICENSE) 许可。提交代码表示你有权提供该贡献，并同意项目按该许可证分发。复制或改编第三方代码时必须说明来源和许可证，不得加入许可证不兼容或来源不明的内容。
