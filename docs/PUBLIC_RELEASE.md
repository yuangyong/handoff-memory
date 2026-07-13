# 公开仓库与发布检查清单

本文用于把 Handoff Memory 从私有仓库转为公开仓库，并为后续源码包、Wheel 和 PyPI 发布提供可审计的操作顺序。清单中的勾选状态必须以当次命令输出或 GitHub/PyPI 设置为依据，不能仅凭历史交接或口头确认。

## 已确认决策

- 仓库采用 MIT License，版权所有者使用开源身份 `yuangyong`；决策依据见 [ADR-012](decisions/ADR-012-mit-license.md)。
- 当前提交作者邮箱是维护者专门用于开源身份的邮箱，可以随 Git 历史公开；不因该邮箱重写提交历史。
- `hmem` 是唯一受支持的终端命令；发行包名为 `handoff-memory`，模块名为 `handoff_memory`。
- 当前为 Alpha 阶段。公开源码不等同于已经发布 PyPI 包。
- 项目由 `yuangyong` 单独维护，当前不招募共同维护者；外部反馈和贡献不改变维护、路线图与发布决策归属。
- 发布 PyPI 必须单独授权并经过发布检查，不由仓库可见性切换自动触发。

## 第一阶段：切换可见性之前

### 历史与敏感信息

- [ ] 使用 Gitleaks、TruffleHog 或同类工具扫描所有可达分支和标签的完整 Git 历史。
- [ ] 人工复核提交作者、文件名、远端 URL、示例、测试夹具和删除过的文件。
- [ ] 检查 GitHub Actions 历史日志与 Artifacts，删除不应公开的运行记录或产物。
- [ ] 如发现真实凭据，先撤销或轮换；清理历史不能代替凭据失效。
- [ ] 确认私有 Fork、协作者权限和组织策略对可见性切换的影响。

推荐记录扫描工具版本、命令、时间、目标引用和结果摘要，不要把疑似密钥原文写入检查记录。

### 内容与法律

- [ ] README、安装命令、支持版本、许可证和项目状态相互一致。
- [ ] 所有本地 Markdown 链接存在，关键外部链接可访问。
- [ ] 第三方代码、素材和文档的许可证兼容；需要时补充 `NOTICE`。
- [ ] Issue/PR 模板、行为准则、贡献指南、支持说明和安全策略已就绪。
- [ ] GitHub 仓库简介、Topics、主页链接和默认分支符合公开定位。

### 本地质量门

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m compileall -q src tests
python scripts/sync_session_handoff_skill.py --check
python -m pip check
git diff --check
```

- [ ] Windows、macOS、Linux CI 全部通过。
- [ ] Python 3.10 和当前最高支持版本通过。
- [ ] Windows 并发保存压力测试没有未解释失败；若仍有间歇性风险，已建立公开 Issue 和临时规避说明。
- [ ] Wheel 与 sdist 构建成功，`twine check` 通过。
- [ ] 从 Wheel 安装后只出现 `hmem` 一个 console script，外部临时目录冒烟流程通过。

## 第二阶段：切换为公开仓库

GitHub 管理员执行可见性切换前，应阅读平台当时显示的影响说明。切换后立即核对：

- [ ] 仓库、提交历史、Actions 日志和预期文档可由未登录用户访问。
- [ ] 默认分支仍为 `main`。
- [ ] 重新启用或重建 `main` 的 Ruleset/Branch protection；可见性切换可能禁用现有 push rulesets。
- [ ] 禁止强推和删除默认分支。
- [ ] Pull Request 必须通过 CI，必要时要求分支保持最新；单人维护模式不强制外部批准，高风险变更可主动邀请独立复核。
- [ ] GitHub Secret Scanning、Push Protection、Dependabot alerts 和依赖图已启用。
- [ ] Private Vulnerability Reporting 已启用，未登录用户能看到私密报告入口。
- [ ] Actions 的默认 `GITHUB_TOKEN` 权限保持最小化，第三方 Action 固定到完整 commit SHA。
- [ ] Issues 已启用；不使用的 Wiki、Projects、Discussions 明确关闭或维护。
- [ ] GitHub Community Profile 不再提示缺失的关键社区文件。

公开后从全新目录重新克隆一次，避免本机忽略文件或未跟踪文件掩盖真实发布内容。

## 第三阶段：GitHub Release

- [ ] 版本号、`CHANGELOG.md`、包元数据和 CLI `--version` 一致。
- [ ] 将“未发布”条目整理为带日期的正式版本，内容面向用户而不是提交列表。
- [ ] 使用带注释的版本标签，并从已通过 CI 的提交构建。
- [ ] GitHub Release 包含变更摘要、升级方式、兼容性或迁移说明和已知问题。
- [ ] 上传的 Wheel/sdist 与 CI 验证的是同一份产物。
- [ ] 发布后重新安装产物并运行外部目录冒烟测试。

## 第四阶段：PyPI 可信发布

首次 PyPI 发布需要维护者单独确认包名与发布时机：

- [ ] 确认 `handoff-memory` 名称归本项目控制，避免与同名项目混淆。
- [ ] 使用独立 `release.yml`，仅允许受保护的 tag 或 GitHub Release 触发。
- [ ] 在 PyPI 配置 Trusted Publisher，并绑定准确的仓库、工作流和 `pypi` Environment。
- [ ] 发布 Job 仅授予 `id-token: write`，其他 Job 不获得发布权限。
- [ ] `pypi` Environment 的保护规则适合单人维护：仅在有独立审批人时启用人工审批，避免把唯一维护者锁在发布流程之外。
- [ ] 先在 TestPyPI 或等价隔离流程验证元数据、README 渲染和安装。
- [ ] 正式发布后验证 PyPI 项目链接、来源证明、Wheel/sdist 和 `pipx install handoff-memory`。
- [ ] 只有上述安装验证通过后，README 才改为优先推荐 PyPI 安装。

## 回滚与事件处理

- 仓库公开后，假设已被克隆；重新设为私有不能收回已经公开的历史。
- 发现密钥时先撤销或轮换，再清理日志、Artifacts 和历史，并发布影响说明。
- 发行包错误时不要覆盖同一版本；撤回受影响文件，修复后发布新版本。
- 发布工作流异常时先禁用可信发布入口，再调查环境、权限和工作流变更。

每次正式发布应复制本清单形成带日期的发布记录，写明执行者、证据链接、例外和风险接受人。
