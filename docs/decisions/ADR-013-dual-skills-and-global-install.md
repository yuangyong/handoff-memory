# ADR-013：双 Skill 读写分离、全局安装与按需自动初始化

## 状态

已接受；扩展 ADR-004 与 ADR-005

## 日期

2026-11-23

## 背景

此前项目仅提供单一 `session-handoff` 项目级 Skill，每次在新项目中启用交接都需要先执行 `hmem init` 并选择客户端。实际跨项目使用中存在三类痛点：

- 在临时或他人仓库中使用时，不希望为了启用交接而往仓库写入客户端配置目录。
- 将“写入交接（保存）”与“只读核验（恢复、历史排查）”混在同一个 Skill 中，容易产生规则串扰，也不便于通过 `/handoff-save`、`/handoff-resume` 直接点名触发。
- 在全局直接调用交接 Skill 时，用户希望未初始化的常规项目能自动初始化 `.ai-memory/`，并在缺少 `hmem` CLI 时获得安全的安装引导。

## 决策

- **双 Skill 读写分离**：将原单一 `session-handoff` 拆分为 `handoff-save`（写入端）与 `handoff-resume`（只读端）；历史排查（`history`、`show`）作为 `handoff-resume` 的异常处理分支，不单独拆出常驻 Skill。
- **新增纯 Skill 管理命令 `hmem skills`**：
  - `hmem skills add TARGET [PATH] [-g|--global]`：仅安装或幂等升级 `handoff-save` 与 `handoff-resume`，不创建客户端规则或 `.ai-memory/`。默认写入 `[PATH]`（默认 `.`）项目级目录，显式 `-g`/`--global` 写入当前用户全局目录（基于官方核实的 `GLOBAL_SKILL_ROOTS`）。`TARGET` 支持 12 个具名客户端、`skill` 与 `all`，不包含 `generic`。
  - `hmem skills status [PATH]`：只读检查当前项目与用户全局目录的 Skill 同步状态，以及旧版 `session-handoff` 残留。
- **保留并明确 `hmem integrate` 职责**：`hmem init --integrate` 与 `hmem integrate TARGET [PATH] [--with-rules]` 保持项目级兼容，同步写入双 Skill，并继续负责 `--with-rules` 客户端规则与 `generic`（`AI-HANDOFF.md`）。
- **兼容外部 Skill 分发生态**：仓库顶层 `skills/handoff-save/SKILL.md` 与 `skills/handoff-resume/SKILL.md` 保持与包内资源同步，天然兼容 `npx skills add yuangyong/handoff-memory -g`。
- **保存时按需自动初始化**：仅 `handoff-save` 在目标目录完全未初始化且非用户主目录/根目录时显式执行 `hmem init .`，随后写入 `ACTIVE.md` 并执行 `hmem save`；`hmem save` CLI 本身不新增 `--init` 参数。`handoff-resume` 保持严格只读，未初始化绝不自动 `init`；半损坏目录禁止 `init --force` 覆盖。
- **CLI 缺失安全确认**：Skill 不静默执行远程安装脚本；检测到缺少 `hmem` 时，先探测 `uv`/`pipx`，向用户展示标准 PyPI 安装命令并获明确同意后再安装；无包管理器或离线时停止并给出手动指引。
- **旧版迁移不静默删除**：保留用户可能修改过的旧版 `session-handoff/SKILL.md`，在 `skills status`、`skills add` 与 `integrate` 中检测并提示用户确认后清理。

## 备选方案

### 维持单一 Skill 或拆出 3 个以上常驻 Skill

拒绝。单一 Skill 难以实现读写隔离和独立斜杠触发；拆出单独的 `handoff-history` 会增加全局常驻上下文占用并与 `resume` 语义重叠。

### 把全局安装直接挂在 `hmem integrate --global`

拒绝。`integrate` 语义偏向项目级完整接入（Skill + 可选规则）；独立 `hmem skills` 命令组更能清晰表达“仅管理 Skill”的边界，也方便承接 `status` 检查。

### 缺少 CLI 时由 Skill 自动静默执行安装脚本

拒绝。与 PyPI 唯一正式分发渠道及最小权限原则冲突，容易在多 Python 环境或沙箱中产生不可控副作用。

## 后果

- 个人跨项目只需安装一次全局 Skill，即可在任意项目中触发保存（自动初始化）与恢复。
- 项目级接入与团队共享规则工作流保持向后兼容。
- 升级工具后，新旧并存的 `session-handoff` 需要提示用户清理以避免多 Skill 冲突。
