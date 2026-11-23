# 发布手册

本文定义 Handoff Memory 的长期 PyPI 发布流程，覆盖版本决策、发布 Pull Request、Trusted Publishing、发布后验证、Yank 和事件处理。PyPI 是唯一正式分发渠道；仓库源码公开不等同于已经发布发行包。

当前发布基线已经由 `0.11.1` 完成验证：GitHub Environment、Trusted Publisher、Actions allow-list、标签工作流和安装后冒烟测试均已打通。证据见 [`0.11.1` 发布记录](releases/0.11.1.md)。后续常规发布应复用并核验这套基线，不重复创建 Pending Publisher。

## 发布职责与稳定约束

- 项目由 `yuangyong` 单独维护，版本范围、发布时间和发布批准均由维护者决定。
- `hmem` 是唯一受支持的终端命令；PyPI 发行包名为 `handoff-memory`，Python 模块名为 `handoff_memory`。
- 版本遵循[语义化版本](https://semver.org/lang/zh-CN/)。在 `1.0.0` 之前，可能破坏兼容性的变更必须提高次版本号并在变更日志中明确说明。
- 正式版本使用 `vX.Y.Z` 标签；预发布版本使用符合 Python 版本规范的形式，例如 `v0.12.0rc1`。
- 发布只允许来自 `main`，且目标提交必须通过全部必需 CI。
- Wheel 与源码包在标签工作流中只构建一次；PyPI Job 只能下载并上传该内部 Artifact，不得重新构建或替换文件。
- 已上传 PyPI 的版本号和文件视为不可变；修复问题时发布新版本，不覆盖旧版本。
- PyPI 只使用 Trusted Publishing，不在仓库、Environment 或本机保存长期发布 Token。
- 不提供 GitHub Release 发行附件、独立可执行文件、系统包管理器清单或远程安装脚本。

## 已接受的发布例外

维护者已明确决定，以下仓库级设置不处理，也不作为 PyPI 发布阻塞条件：

- GitHub Secret Scanning。
- Secret Scanning Push Protection。
- Private Vulnerability Reporting。
- 仓库级 GitHub Actions 完整 SHA 强制。
- GitHub Immutable Releases。

不启用仓库级 SHA 强制，不代表工作流可以使用浮动标签；仓库内所有外部 Action 仍必须人工固定到经过核验的完整提交 SHA。上述例外只移除对应仓库设置门槛，不放宽发布工作流的 OIDC、最小权限、版本一致性和产物不可替换要求。

## 发布类型

| 类型 | 示例 | 适用范围 |
| --- | --- | --- |
| 修订版本 | `0.11.1` | 向后兼容的缺陷、安全、文档或分发修复 |
| 次版本 | `0.12.0` | 新功能；`1.0.0` 前也用于明确记录的兼容性调整 |
| 主版本 | `1.0.0` | 稳定公共契约后的重大不兼容变更 |
| 预发布版本 | `0.12.0rc1` | 需要公开验证但尚未承诺为正式版本的候选版本 |

纯文档或仓库配置变更不必单独发版，除非它们直接影响安装、分发元数据、安全边界或用户可见契约。

## 发布前置条件

开始发布前必须确认：

- [ ] 发布范围已经冻结，不混入无关重构或依赖升级。
- [ ] 没有尚未处理的严重安全问题、失败检查或会影响发布的已知缺陷。
- [ ] `main` 的 Ruleset 处于启用状态，禁止强推和删除，并要求 Pull Request 与必需 CI。
- [ ] GitHub Actions 默认权限为只读；外部 Action 固定到完整提交 SHA。
- [ ] `CHANGELOG.md`、用户文档、包元数据和公共行为描述相互一致。
- [ ] 本地分支与 `origin/main` 同步，工作区没有未提交文件。

首次发布到 PyPI 时，还必须一次性确认：

- [ ] `handoff-memory` 名称尚未被无关项目占用。
- [ ] GitHub 已创建名为 `pypi` 的 Environment，且没有会锁住单一维护者的必需审批规则。
- [ ] PyPI Pending Trusted Publisher 精确绑定用户 `yuangyong`、仓库 `handoff-memory`、工作流 `release.yml` 和 Environment `pypi`。
- [ ] 仓库 Actions allow-list 已放行工作流中固定 SHA 的 `pypa/gh-action-pypi-publish`，没有扩大为允许全部第三方或全部 verified creator。
- [ ] `.github/workflows/release.yml` 已在 `main` 上通过审查，发布 Job 是唯一拥有 `id-token: write` 的 Job。

Pending Trusted Publisher 在第一次成功上传前不会保留 PyPI 项目名。工作流、Environment 和 allow-list 未准备完成时，不要先推送正式版本标签。

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

发布 Pull Request 的说明至少包含版本号、用户可见变更、兼容性影响、验证命令、PyPI 发布方式和 Yank 条件。

## 2. 执行本地质量门

在仓库根目录执行：

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m compileall -q src tests
python scripts/sync_skills.py --check
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

`python -m build` 应同时生成 Wheel 和源码包。检查文件名、版本号、许可证、README 渲染、项目链接以及源码包包含的文档和 Skill 分发文件。

本地产物只用于预检。最终发布必须使用标签触发的发布工作流构建并留存的 Artifact，不能用本机文件替代。

## 3. 合并并锁定发布提交

1. 等待发布 Pull Request 的全部必需检查通过：六个跨平台测试矩阵、`package` 和 `svn-integration`。
2. 确认 PR 分支基于最新 `main`，所有评审对话已经解决。
3. 使用 Squash Merge 合并，并让 GitHub 自动删除分支。
4. 记录合并提交 SHA、Pull Request URL 和成功的 CI 运行 URL。
5. 确认合并后的 `main` CI 仍然成功。

如果合并后的 `main` CI 失败，停止发布；修复并重新走发布 Pull Request，不得对失败提交创建正式标签。

## 4. 首次配置 PyPI 可信发布

本节只用于首次创建 PyPI 项目。`handoff-memory` 已在 `0.11.1` 发布时完成配置；常规发布只需在推送标签前确认现有 Trusted Publisher、GitHub Environment 和 Actions allow-list 没有漂移。

在 GitHub 仓库创建 Environment：

```text
名称：pypi
部署分支和标签：只允许受保护分支或与正式版本规则匹配的标签
必需审批：单一维护者模式下不要配置会造成自我审批锁死的规则
```

在 PyPI 账户的 Publishing 页面创建 Pending Publisher：

```text
PyPI 项目名：handoff-memory
GitHub Owner：yuangyong
GitHub Repository：handoff-memory
Workflow：release.yml
Environment：pypi
```

仓库 Actions allow-list 只增加 `.github/workflows/release.yml` 中实际使用的固定 SHA PyPA Action。GitHub 官方的 checkout、setup-python、upload-artifact 和 download-artifact 继续由 `github_owned_allowed` 覆盖。

PyPI 会在第一次成功 OIDC 上传时创建项目，并把 Pending Publisher 转换为普通 Trusted Publisher。配置方式以 [PyPI Trusted Publishers 文档](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)为准。

## 5. 创建标签并发布到 PyPI

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

推送 `v*` 标签会触发 `.github/workflows/release.yml`。工作流按顺序执行：

1. 确认标签提交属于远端 `main`。
2. 确认标签、`pyproject.toml`、`handoff_memory.__version__` 和变更日志一致。
3. 重新运行发行质量门。
4. 构建并校验 Wheel 与源码包。
5. 从 Wheel 安装并执行核心流程冒烟测试。
6. 将发行文件保存为内部 Actions Artifact。
7. PyPI Job 下载同一 Artifact，通过 `pypi` Environment 和 OIDC 上传。

工作流失败后不得改用本机 Token 或手工 `twine upload` 绕过可信发布。

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
- [ ] `uv tool install handoff-memory` 和 `pipx install handoff-memory` 至少各完成一次全新环境验证。
- [ ] 在外部临时目录完成 `init`、`check --strict`、`save`、`resume`、`history` 和 `show latest` 冒烟流程。

将版本号、提交 SHA、PR、CI、标签、PyPI URL、文件哈希、验证结果和任何例外写入 `docs/releases/X.Y.Z.md`。仓库不使用 GitHub Release，因此该文件是每个正式版本的长期发布记录。

## 7. 失败、撤回与安全事件

### 发布工作流失败

- 在任何文件上传前失败：修复工作流后删除未发布标签，重新走发布 PR，并创建新标签。
- 已有文件上传成功：先查询 PyPI 真实状态，不进行盲目重跑或手工补传。
- 构建内容发生变化：必须使用新版本号，不能覆盖已经上传的文件。

### 发行包存在缺陷

- 不覆盖或重新上传同一版本。
- 对不可安装、违反兼容性承诺或存在安全漏洞的版本优先使用 Yank，并写明原因；操作依据见 [PyPI Yanking 文档](https://docs.pypi.org/project-management/yanking/)。
- 修复后发布新的修订版本，并在变更日志中说明受影响版本。

### 凭据或供应链事件

1. 暂停或禁用发布工作流和 Trusted Publisher。
2. 检查 Git 历史、Actions 日志、Artifacts 和 PyPI 文件的影响范围。
3. 真实凭据如有泄露，立即撤销或轮换；删除文件或改写历史不能替代凭据失效。
4. 通过 `SECURITY.md` 中的私密邮箱协调调查和披露。
5. 发布修复版本与必要的安全说明，并记录时间线和后续措施。

## 发布记录模板

每次正式发布复制以下字段到 `docs/releases/X.Y.Z.md`；如果发布过程另有 Issue，可从记录中链接该 Issue：

```text
版本：
发布日期：
维护者：yuangyong
发布 PR：
目标提交 SHA：
CI 运行：
标签：
PyPI：
Wheel SHA-256：
源码包 SHA-256：
发布后验证：
已知问题与例外：
Yank 决策：
```
