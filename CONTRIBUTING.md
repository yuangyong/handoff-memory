# 贡献指南

感谢参与 Handoff Memory。

## 本地开发

```powershell
python -m pip install -e .
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

## 设计约束

- 保持核心运行期零第三方依赖，新增依赖前必须说明必要性、许可证和替代方案。
- 公共 CLI 与 JSON 输出只做兼容性扩展；破坏性变化需要新 schema 或迁移说明。
- 新行为先写失败测试。
- 不增加默认联网、遥测或云账户要求。
- 用户输入、Git 输出和交接内容都视为不可信数据。

## 提交规范

推荐 Conventional Commits，例如：

```text
feat: 增加新的 AI 工具适配
fix: 修复 Windows 路径归档问题
docs: 补充标准输入使用示例
```

提交前运行完整测试，并确认 diff 中不存在密钥、Token、私钥或真实个人信息。
