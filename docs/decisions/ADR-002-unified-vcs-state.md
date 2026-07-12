# ADR-002：使用统一 VCS 状态模型兼容 Git 与 SVN

## 状态

已接受

## 日期

2026-07-12

## 背景

Handoff Memory 0.1 只采集 Git 状态，但企业和存量项目可能使用 SVN。保存与恢复流程不应要求用户迁移版本控制工具，也不应为每种 VCS 复制完整业务逻辑。

## 决策

引入统一的 `RepositoryState` 数据模型，由自动探测层选择 Git 或 SVN 只读适配器：

- 公共字段保留 `branch`、`head`、`dirty`、`changes` 和 `note`，兼容 0.1 JSON 消费者。
- 新增 `provider`、`revision`、`url` 和 `root`，表达 SVN 及未来 VCS 信息。
- Git 通过固定参数命令采集；SVN 通过 `svn info --xml` 与 `svn status --xml` 采集并使用标准库解析。
- 新配置写入 `last_saved_repository`；读取时回退到 0.1 的 `last_saved_git`。
- 同时检测到多种版本库时，选择离项目目录最近的工作副本标记。

## 备选方案

### 为 SVN 增加独立保存与恢复命令

会让用户和 AI 必须知道项目使用哪种 VCS，并复制漂移逻辑，拒绝。

### 只调用 `svn status` 文本格式

文本输出受本地化和路径格式影响。XML 输出更稳定、可验证，拒绝文本解析。

### 升级配置 schema_version

本次变化是字段增加并提供旧字段回退，不需要破坏性迁移，因此保持 schema 1。

## 后果

- 现有 Git 项目和 JSON 消费者继续工作。
- SVN 工作副本获得修订号、URL、相对仓库位置和本地变更核验。
- 运行环境若需要对应状态，必须安装 `git` 或 `svn` CLI；缺失时工具给出明确说明但仍可保存交接。
