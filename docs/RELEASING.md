# 发布手册

本文定义 Handoff Memory 的长期发布流程，覆盖版本决策、发布 Pull Request、GitHub Release、PyPI Trusted Publishing、发布后验证和事件处理。仓库源码公开不等同于已经发布发行包；任何 GitHub Release 或 PyPI 发布都必须由维护者显式启动并留下可核验记录。

## 发布职责与稳定约束

- 项目由 `yuangyong` 单独维护，版本范围、发布时间和发布批准均由维护者决定。
- `hmem` 是唯一受支持的终端命令；PyPI 发行包名为 `handoff-memory`，Python 模块名为 `handoff_memory`。
- 版本遵循[语义化版本](https://semver.org/lang/zh-CN/)。在 `1.0.0` 之前，可能破坏兼容性的变更必须提高次版本号并在变更日志中明确说明。
- 正式版本使用 `vX.Y.Z` 标签；预发布版本使用符合 Python 版本规范的形式，例如 `v0.12.0rc1`。
- 发布只允许来自受保护的 `main`，且目标提交必须通过全部必需 CI。
- GitHub Release 和 PyPI 必须使用同一目标提交产生的同一组 Wheel 与源码包，不得在发布阶段临时重建或替换文件。
- 已公开的版本号、标签和发行文件视为不可变；修复问题时发布新版本，不覆盖旧版本。
- PyPI 只使用 Trusted Publishing，不在仓库、Environment 或本机保存长期发布 Token。

## 发布类型

| 类型 | 示例 | 适用范围 |
| --- | --- | --- |
| 修订版本 | `0.11.1` | 向后兼容的缺陷、安全或文档修复 |
| 次版本 | `0.12.0` | 新功能；`1.0.0` 前也用于明确记录的兼容性调整 |
| 主版本 | `1.0.0` | 稳定公共契约后的重大不兼容变更 |
| 预发布版本 | `0.12.0rc1` | 需要公开验证但尚未承诺为正式版本的候选版本 |

纯文档或仓库配置变更不必单独发版，除非它们直接影响安装、分发元数据、安全边界或用户可见契约。

## 发布前置条件

开始发布前必须确认：

- [ ] 发布范围已经冻结，不混入无关重构或依赖升级。
- [ ] 没有尚未处理的严重安全问题、失败检查或会影响发布的已知缺陷。
- [ ] `main` 的 Ruleset 处于启用状态，禁止强推和删除，并要求 Pull Request 与必需 CI。
- [ ] GitHub Actions 默认权限为只读；所有外部 Action 固定到完整提交 SHA。
- [ ] Dependabot alerts、Secret Scanning、Push Protection 和 Private Vulnerability Reporting 已按公开仓库策略启用。
- [ ] `CHANGELOG.md`、用户文档、包元数据和公共行为描述相互一致。
- [ ] 本地分支与 `origin/main` 同步，工作区没有未提交文件。

首次发布到 PyPI 时，还必须一次性确认：

- [ ] `handoff-memory` 包名由本项目控制，不与无关项目混淆。
- [ ] PyPI 中的 Trusted Publisher 精确绑定本仓库、发布工作流和 `pypi` Environment。
- [ ] 发布工作流仅在发布 Job 上授予 `id-token: write`，其他 Job 保持只读。
- [ ] Actions allow-list 只额外放行固定到完整 SHA 的 PyPA 发布 Action，不扩大到全部第三方或全部 verified creator。
- [ ] 单一维护者不会被 Environment 的必需审批规则锁在发布流程之外。

在上述 PyPI 条件全部满足且专用发布工作流通过审查之前，禁止上传正式 PyPI 包。

## 1. 准备发布 Pull Request

从最新 `main` 创建短期发布分支，并只提交与本次版本有关的变更：

1. 同时更新 `pyproject.toml` 与 `src/handoff_memory/__init__.py` 中的版本号。
2. 将 `CHANGELOG.md` 的“未发布”内容整理为 `## [X.Y.Z] - YYYY-MM-DD`，并保留新的空“未发布”区段。
3. 更新受影响的 README、使用文档、迁移说明和兼容性说明。
4. 明确已知问题；不能接受的发布风险必须在合并前修复，而不是留到发布后处理。

提交信息建议使用：

```text
chore: 准备 X.Y.Z 版本发布
```

发布 Pull Request 的说明至少包含版本号、用户可见变更、兼容性影响、验证命令和回滚方式。

## 2. 执行本地质量门

在仓库根目录执行：

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m compileall -q src tests
python scripts/sync_session_handoff_skill.py --check
python -m pip check
python -m ruff check .
python -m mypy src
git diff --check
```

在干净检出中构建并检查发行文件，避免旧 `dist` 内容混入：

```powershell
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

`python -m build` 应同时生成 Wheel 和源码包。检查文件名、版本号、许可证、README 渲染、项目链接以及源码包包含的文档和 Skill 分发文件。构建方式以 [Python Packaging User Guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/) 为准。

本地产物只用于预检。最终发布必须使用 CI 留存的产物，不能用本机重新构建的文件替代。

## 3. 合并并锁定发布提交

1. 等待发布 Pull Request 的全部必需检查通过：六个跨平台测试矩阵、`package` 和 `svn-integration`。
2. 确认 PR 分支基于最新 `main`，所有评审对话已经解决。
3. 使用 Squash Merge 合并，并让 GitHub 自动删除分支。
4. 记录合并提交 SHA、Pull Request URL 和成功的 CI 运行 URL。
5. 从该提交的 `package` Job 下载 `handoff-memory-dist`，核对 Wheel 与源码包版本，并记录 SHA-256。

```powershell
Get-FileHash -Algorithm SHA256 dist/*
```

如果合并后的 `main` CI 失败，停止发布；修复并重新走发布 Pull Request，不得对失败提交创建正式标签。

## 4. 创建标签和 GitHub Release

同步并核验本地 `main`：

```powershell
git switch main
git pull --ff-only origin main
git status --short --branch
git log -1 --oneline
```

为已通过 CI 的确切提交创建带注释标签：

```powershell
$version = "X.Y.Z"
git tag -a "v$version" -m "发布 $version"
git show "v$version" --no-patch
git push origin "v$version"
```

如果维护者已配置可靠的 Git 签名，可使用签名标签；未配置时不要在发布过程中临时引入未经验证的签名方案。

在 GitHub 的 Releases 页面先创建 Draft Release：

- 标签和标题使用 `vX.Y.Z`。
- 正文包含变更摘要、安装或升级方式、兼容性说明、已知问题和完整变更日志链接。
- 预发布版本必须勾选 `Set as a pre-release`。
- 上传 CI 生成的原始 Wheel 与源码包，不重新压缩、不重命名。
- 发布前核对文件 SHA-256 与记录一致。

GitHub Release 基于 Git 标签；创建与管理方式以 [GitHub Releases 文档](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)为准。

## 5. 发布到 PyPI

PyPI 发布应由独立的 `.github/workflows/release.yml` 完成，并满足以下约束：

- 仅由受保护标签或 GitHub Release 发布事件触发。
- 构建 Job 只构建一次并上传内部 Artifact；GitHub Release 与 PyPI Job 下载同一 Artifact。
- PyPI Job 绑定 `pypi` Environment，并只在该 Job 设置 `permissions: id-token: write`。
- `pypa/gh-action-pypi-publish` 固定到经过核验的完整提交 SHA，并以相同精度加入仓库 Actions allow-list。
- 不使用 `PYPI_TOKEN`、用户名密码或 `pull_request_target`。
- 失败后不得改用本机手工上传绕过工作流。

PyPI 推荐通过 OIDC Trusted Publishing 获取短期身份，不保存长期凭据；配置方式以 [PyPI Trusted Publishers 文档](https://docs.pypi.org/trusted-publishers/using-a-publisher/)为准。

## 6. 发布后验证

发布完成后立即从全新临时环境验证，不使用当前工作区或本地缓存中的可编辑安装：

```powershell
$version = "X.Y.Z"
$smoke = Join-Path $env:TEMP "hmem-release-$version"
python -m venv $smoke
& "$smoke\Scripts\python.exe" -m pip install --upgrade pip
& "$smoke\Scripts\python.exe" -m pip install "handoff-memory==$version"
& "$smoke\Scripts\hmem.exe" --version
& "$smoke\Scripts\hmem.exe" help
```

继续核对：

- [ ] `hmem --version` 与发布版本一致，且没有安装旧的 `handoff-memory` 命令。
- [ ] PyPI 页面正确渲染 README、MIT License、Python 版本和项目链接。
- [ ] Wheel 与源码包均可下载，文件哈希和来源证明符合预期。
- [ ] GitHub Release 标签指向记录的 `main` 提交，附件与 PyPI 文件来自同一构建。
- [ ] 在外部临时目录完成 `init`、`check --strict`、`save`、`resume`、`history` 和 `show latest` 冒烟流程。
- [ ] README 只有在正式 PyPI 安装验证通过后，才把 PyPI 作为首选安装方式。

将版本号、提交 SHA、PR、CI、GitHub Release、PyPI URL、文件哈希、验证结果和任何例外写入发布记录。

## 7. 失败、撤回与安全事件

### 发布工作流失败

- 在任何文件上传前失败：修复工作流后重试同一目标提交。
- 已有文件上传成功：先确认 PyPI 和 GitHub 的真实状态，不进行盲目重跑或手工补传。
- 构建内容发生变化：必须重新走发布 PR，并使用新版本号。

### 发行包存在缺陷

- 不覆盖或重新上传同一版本。
- 对不可安装、违反兼容性承诺或存在安全漏洞的 PyPI 版本优先使用 Yank，并写明原因；操作依据见 [PyPI Yanking 文档](https://docs.pypi.org/project-management/yanking/)。
- 修复后发布新的修订版本，并在变更日志和 GitHub Release 中说明受影响版本。

### 凭据或供应链事件

1. 立即撤销或轮换真实凭据；删除文件或改写历史不能替代凭据失效。
2. 暂停或禁用发布工作流和 Trusted Publisher。
3. 使用 Private Vulnerability Reporting 或仓库 Security Advisory 进行私密调查。
4. 评估 Git 历史、Actions 日志、Artifacts、GitHub Release 和 PyPI 文件的影响范围。
5. 发布修复版本与必要的安全公告，并记录时间线和后续措施。

## 发布记录模板

每次正式发布复制以下字段到发布 Issue、Release 草稿或其他可审计记录中：

```text
版本：
发布日期：
维护者：yuangyong
发布 PR：
目标提交 SHA：
CI 运行：
标签：
GitHub Release：
PyPI：
Wheel SHA-256：
源码包 SHA-256：
发布后验证：
已知问题与例外：
回滚或 Yank 决策：
```
