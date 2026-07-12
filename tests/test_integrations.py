import subprocess
import sys
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path

from handoff_memory.integrations import (
    AI_TOOL_TARGETS,
    PROJECT_SKILL_PATHS,
    TARGETS,
    integrate,
)
from handoff_memory.templates import GENERIC_RULE, SKILL_TEMPLATE


class IntegrationTemplateTests(unittest.TestCase):
    def test_skill_template_is_loaded_from_canonical_package_resource(self) -> None:
        canonical = files("handoff_memory").joinpath(
            "assets", "session-handoff", "SKILL.md"
        )

        self.assertTrue(canonical.is_file())
        self.assertEqual(canonical.read_text(encoding="utf-8"), SKILL_TEMPLATE)

    def test_sync_script_generates_and_checks_distributable_copy(self) -> None:
        repository = Path(__file__).parents[1]
        script = repository / "scripts/sync_session_handoff_skill.py"

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "SKILL.md"
            synchronized = subprocess.run(
                [sys.executable, str(script), "--target", str(target)],
                cwd=repository,
                capture_output=True,
                text=True,
                check=False,
            )
            checked = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--target",
                    str(target),
                    "--check",
                ],
                cwd=repository,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(synchronized.returncode, 0, synchronized.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), SKILL_TEMPLATE)
            self.assertEqual(checked.returncode, 0, checked.stderr)

            target.write_text("已漂移\n", encoding="utf-8")
            drifted = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--target",
                    str(target),
                    "--check",
                ],
                cwd=repository,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(drifted.returncode, 1)
            self.assertIn("不同步", drifted.stderr)

    def test_mainstream_ai_tools_have_named_targets(self) -> None:
        expected = {
            "codex",
            "claude",
            "cursor",
            "gemini",
            "antigravity",
            "copilot",
            "windsurf",
            "cline",
            "kiro",
            "trae",
            "qoder",
            "opencode",
        }

        self.assertEqual(set(AI_TOOL_TARGETS), expected)
        self.assertTrue(expected.issubset(TARGETS))

    def test_new_mainstream_integrations_use_official_project_rule_paths(self) -> None:
        expected_paths = {
            "copilot": ".github/copilot-instructions.md",
            "windsurf": ".windsurf/rules/handoff-memory.md",
            "cline": ".clinerules/handoff-memory.md",
            "kiro": ".kiro/steering/handoff-memory.md",
            "trae": ".trae/rules/project_rules.md",
            "qoder": ".qoder/rules/handoff-memory.md",
        }

        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            for target, relative_path in expected_paths.items():
                with self.subTest(target=target):
                    changed = integrate(project, target, with_rules=True)
                    destination = project / relative_path
                    self.assertIn(destination, changed)
                    self.assertTrue(destination.is_file())
                    self.assertIn("handoff-memory:start", destination.read_text(encoding="utf-8"))
                    self.assertEqual(integrate(project, target, with_rules=True), [])

    def test_named_integrations_create_only_skills_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            antigravity_changed = integrate(project, "antigravity")
            qoder_changed = integrate(project, "qoder")

            self.assertEqual(
                antigravity_changed,
                [project / ".agents/skills/session-handoff/SKILL.md"],
            )
            self.assertEqual(
                qoder_changed,
                [project / ".qoder/skills/session-handoff/SKILL.md"],
            )
            self.assertFalse((project / ".agents/rules/handoff-memory.md").exists())
            self.assertFalse((project / ".qoder/rules/handoff-memory.md").exists())

    def test_every_named_ai_tool_creates_skill_in_native_project_directory(self) -> None:
        expected_paths = {
            "codex": ".agents/skills/session-handoff/SKILL.md",
            "claude": ".claude/skills/session-handoff/SKILL.md",
            "cursor": ".cursor/skills/session-handoff/SKILL.md",
            "gemini": ".gemini/skills/session-handoff/SKILL.md",
            "antigravity": ".agents/skills/session-handoff/SKILL.md",
            "copilot": ".github/skills/session-handoff/SKILL.md",
            "windsurf": ".windsurf/skills/session-handoff/SKILL.md",
            "cline": ".cline/skills/session-handoff/SKILL.md",
            "kiro": ".kiro/skills/session-handoff/SKILL.md",
            "trae": ".trae/skills/session-handoff/SKILL.md",
            "qoder": ".qoder/skills/session-handoff/SKILL.md",
            "opencode": ".opencode/skills/session-handoff/SKILL.md",
        }

        self.assertEqual(PROJECT_SKILL_PATHS, expected_paths)
        # 每个目标使用独立目录，避免共享路径（如 codex 和 antigravity）导致的幂等干扰
        for target, relative_path in expected_paths.items():
            with self.subTest(target=target):
                with tempfile.TemporaryDirectory() as directory:
                    project = Path(directory)
                    changed = integrate(project, target)
                    skill = project / relative_path
                    self.assertIn(skill, changed)
                    self.assertEqual(skill.read_text(encoding="utf-8"), SKILL_TEMPLATE)
                    self.assertEqual(integrate(project, target), [])

    def test_codex_integration_leaves_existing_agents_untouched_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            agents = project / "AGENTS.md"
            agents.write_text("# 原有规则\n", encoding="utf-8")

            integrate(project, "codex")
            integrate(project, "codex")

            content = agents.read_text(encoding="utf-8")
            self.assertEqual(content, "# 原有规则\n")
            self.assertTrue(
                (project / ".agents/skills/session-handoff/SKILL.md").is_file()
            )

    def test_codex_rules_option_preserves_and_appends_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            agents = project / "AGENTS.md"
            agents.write_text("# 原有规则\n", encoding="utf-8")

            integrate(project, "codex", with_rules=True)
            integrate(project, "codex", with_rules=True)

            content = agents.read_text(encoding="utf-8")
            self.assertIn("# 原有规则", content)
            self.assertIn("使用 `session-handoff` Skill", content)
            self.assertNotIn("开始处理任务前", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)

    def test_codex_rules_option_creates_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "codex", with_rules=True)

            agents = project / "AGENTS.md"
            self.assertTrue(agents.is_file())
            self.assertIn("使用 `session-handoff` Skill", agents.read_text(encoding="utf-8"))
            self.assertEqual(len(changed), 2)

    def test_antigravity_explicit_rules_create_workspace_rule_and_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "antigravity", with_rules=True)

            rule = project / ".agents/rules/handoff-memory.md"
            skill = project / ".agents/skills/session-handoff/SKILL.md"
            self.assertTrue(rule.is_file())
            self.assertTrue(skill.is_file())
            rule_content = rule.read_text(encoding="utf-8")
            self.assertIn("handoff-memory:start", rule_content)
            self.assertIn("使用 `session-handoff` Skill", rule_content)
            self.assertNotIn("handoff-memory resume", rule_content)
            self.assertEqual(skill.read_text(encoding="utf-8"), SKILL_TEMPLATE)
            self.assertEqual(len(changed), 2)
            # 幂等性：再次执行不应产生变更
            self.assertEqual(integrate(project, "antigravity", with_rules=True), [])

    def test_antigravity_preserves_existing_workspace_rule_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            rule = project / ".agents/rules/handoff-memory.md"
            rule.parent.mkdir(parents=True, exist_ok=True)
            rule.write_text("# 用户自定义规则\n", encoding="utf-8")

            integrate(project, "antigravity", with_rules=True)

            content = rule.read_text(encoding="utf-8")
            self.assertIn("用户自定义规则", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)

    def test_antigravity_does_not_touch_agents_md_files(self) -> None:
        """Antigravity 使用 .agents/rules，不应修改 AGENTS.md。"""
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            root_agents = project / "AGENTS.md"
            nested_agents = project / ".agents/AGENTS.md"
            root_agents.write_text("# Codex 规则\n", encoding="utf-8")
            nested_agents.parent.mkdir(parents=True, exist_ok=True)
            nested_agents.write_text("# 其他工具规则\n", encoding="utf-8")

            integrate(project, "antigravity", with_rules=True)

            self.assertEqual(root_agents.read_text(encoding="utf-8"), "# Codex 规则\n")
            self.assertEqual(
                nested_agents.read_text(encoding="utf-8"), "# 其他工具规则\n"
            )
            self.assertTrue((project / ".agents/rules/handoff-memory.md").is_file())

    def test_opencode_creates_project_skill_and_only_adds_agents_rule_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "opencode")

            self.assertEqual(
                changed,
                [project / ".opencode/skills/session-handoff/SKILL.md"],
            )
            self.assertFalse((project / "AGENTS.md").exists())

            changed = integrate(project, "opencode", with_rules=True)

            self.assertEqual(changed, [project / "AGENTS.md"])
            self.assertIn(
                "使用 `session-handoff` Skill",
                (project / "AGENTS.md").read_text(encoding="utf-8"),
            )

    def test_codex_integration_creates_official_project_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "codex")

            skill = project / ".agents/skills/session-handoff/SKILL.md"
            self.assertFalse((project / "AGENTS.md").exists())
            self.assertTrue(skill.is_file())
            self.assertEqual(skill.read_text(encoding="utf-8"), SKILL_TEMPLATE)
            self.assertFalse((project / ".codex/skills/session-handoff/SKILL.md").exists())
            self.assertEqual(len(changed), 1)
            self.assertEqual(integrate(project, "codex"), [])

    def test_codex_integration_shrinks_legacy_managed_rule_to_skill_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            agents = project / "AGENTS.md"
            agents.write_text(GENERIC_RULE + "\n", encoding="utf-8")

            integrate(project, "codex", with_rules=True)

            content = agents.read_text(encoding="utf-8")
            self.assertIn("使用 `session-handoff` Skill", content)
            self.assertNotIn("开始处理任务前", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)

    def test_all_can_explicitly_include_every_native_rule(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "all", with_rules=True)

            self.assertTrue((project / "AGENTS.md").is_file())
            self.assertTrue((project / ".agents/rules/handoff-memory.md").is_file())
            self.assertTrue((project / ".qoder/rules/handoff-memory.md").is_file())
            self.assertEqual(len(changed), 22)

    def test_cursor_integration_preserves_existing_rule_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            cursor_rule = project / ".cursor/rules/handoff-memory.mdc"
            cursor_rule.parent.mkdir(parents=True)
            cursor_rule.write_text("---\nalwaysApply: true\n---\n\n用户自定义规则\n", encoding="utf-8")

            integrate(project, "cursor", with_rules=True)

            content = cursor_rule.read_text(encoding="utf-8")
            self.assertIn("用户自定义规则", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)

    def test_skill_integration_preserves_existing_skill_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            skill = project / ".agents/skills/session-handoff/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("---\nname: session-handoff\n---\n\n用户自定义说明\n", encoding="utf-8")

            integrate(project, "skill")

            content = skill.read_text(encoding="utf-8")
            self.assertIn("用户自定义说明", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)

    def test_all_integration_creates_only_named_project_skills_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "all")

            self.assertFalse((project / "AGENTS.md").exists())
            self.assertFalse((project / "CLAUDE.md").exists())
            self.assertFalse((project / "GEMINI.md").exists())
            self.assertFalse((project / ".cursor/rules/handoff-memory.mdc").exists())
            self.assertFalse((project / "AI-HANDOFF.md").exists())
            self.assertTrue((project / ".agents/skills/session-handoff/SKILL.md").is_file())
            self.assertFalse((project / ".trae/rules/project_rules.md").exists())
            self.assertFalse((project / ".qoder/rules/handoff-memory.md").exists())
            self.assertTrue(
                (project / ".opencode/skills/session-handoff/SKILL.md").is_file()
            )
            for relative_path in PROJECT_SKILL_PATHS.values():
                self.assertTrue((project / relative_path).is_file())
            # Antigravity 与 Codex 共享 .agents/skills，共 11 个唯一 Skill 文件。
            self.assertEqual(len(changed), 11)

            unchanged = integrate(project, "all")
            self.assertEqual(unchanged, [])

    def test_unknown_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                integrate(Path(directory), "unknown")

    def test_rules_option_rejects_auxiliary_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for target in ("generic", "skill"):
                with self.subTest(target=target):
                    with self.assertRaisesRegex(ValueError, "具名客户端.*all"):
                        integrate(Path(directory), target, with_rules=True)

    def test_distributable_skill_matches_generated_skill(self) -> None:
        repository_skill = (
            Path(__file__).parents[1] / "skills/session-handoff/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertEqual(repository_skill, SKILL_TEMPLATE)

    def test_existing_skill_frontmatter_is_upgraded_with_template(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            skill = project / ".agents/skills/session-handoff/SKILL.md"
            skill.parent.mkdir(parents=True)
            outdated = SKILL_TEMPLATE.replace(
                "description: 仅在用户明确要求",
                "description: 保存、恢复或核验跨会话状态。阶段工作完成时使用。",
                1,
            )
            skill.write_text(outdated, encoding="utf-8")

            changed = integrate(project, "codex")

            self.assertEqual(changed, [skill])
            self.assertEqual(skill.read_text(encoding="utf-8"), SKILL_TEMPLATE)

    def test_skill_upgrade_preserves_unknown_frontmatter_and_user_body(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            skill = project / ".agents/skills/session-handoff/SKILL.md"
            skill.parent.mkdir(parents=True)
            customized = SKILL_TEMPLATE.replace(
                "description: 仅在用户明确要求",
                "description: 旧的触发说明。",
                1,
            ).replace(
                "---\n\n<!-- handoff-memory:start -->",
                "allowed-tools: Read, Bash\nmetadata:\n  owner: local\n---\n\n"
                "用户自定义前言\n\n<!-- handoff-memory:start -->",
                1,
            )
            skill.write_text(customized, encoding="utf-8")

            changed = integrate(project, "codex")

            content = skill.read_text(encoding="utf-8")
            self.assertEqual(changed, [skill])
            self.assertIn("description: 仅在用户明确要求", content)
            self.assertIn("allowed-tools: Read, Bash\n", content)
            self.assertIn("metadata:\n  owner: local\n", content)
            self.assertIn("用户自定义前言", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)
            self.assertEqual(integrate(project, "codex"), [])

    def test_skill_upgrade_rejects_malformed_frontmatter_or_managed_markers(self) -> None:
        managed = SKILL_TEMPLATE[SKILL_TEMPLATE.index("<!-- handoff-memory:start -->") :]
        valid_frontmatter = "---\nname: session-handoff\ndescription: 旧说明\n---\n\n"
        malformed_cases = {
            "frontmatter 缺少结束分隔符": (
                "---\nname: session-handoff\ndescription: 旧说明\n\n" + managed
            ),
            "受管区块缺少结束标记": valid_frontmatter
            + "<!-- handoff-memory:start -->\n旧内容\n",
            "受管区块缺少开始标记": valid_frontmatter
            + "旧内容\n<!-- handoff-memory:end -->\n",
            "受管区块重复": valid_frontmatter + managed + "\n" + managed,
            "受管标记顺序交叉": valid_frontmatter
            + "<!-- handoff-memory:end -->\n旧内容\n<!-- handoff-memory:start -->\n",
        }

        for case, original in malformed_cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                skill = project / ".agents/skills/session-handoff/SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text(original, encoding="utf-8")

                with self.assertRaises(ValueError):
                    integrate(project, "codex")

                self.assertEqual(skill.read_text(encoding="utf-8"), original)

    def test_rules_do_not_duplicate_active_context_on_resume(self) -> None:
        self.assertIn("输出已经包含 `ACTIVE.md`", GENERIC_RULE)
        self.assertNotIn("并阅读 `.ai-memory/ACTIVE.md`", GENERIC_RULE)

    def test_rules_only_route_explicit_session_handoff_requests(self) -> None:
        self.assertIn("仅当用户明确要求恢复", GENERIC_RULE)
        self.assertIn("仅当用户明确要求保存", GENERIC_RULE)
        self.assertIn("普通任务不得读取或写入", GENERIC_RULE)
        self.assertNotIn("开始处理任务前", GENERIC_RULE)

    def test_skill_uses_workspace_evidence_and_handles_missing_state(self) -> None:
        self.assertIn("编码任务，检查版本库状态、相关 diff 和实际测试", SKILL_TEMPLATE)
        self.assertIn("写作、研究、规划等任务", SKILL_TEMPLATE)
        self.assertIn("没有可恢复的交接", SKILL_TEMPLATE)
        self.assertIn("不得假装恢复成功", SKILL_TEMPLATE)
        self.assertIn("不要自动使用 `--allow-sensitive`", SKILL_TEMPLATE)

    def test_skill_only_saves_on_explicit_session_handoff_request(self) -> None:
        self.assertIn("只有用户明确要求", SKILL_TEMPLATE)
        self.assertIn("恢复流程是只读操作", SKILL_TEMPLATE)
        self.assertIn("不得更新 `ACTIVE.md` 或创建快照", SKILL_TEMPLATE)
        self.assertNotIn("`handoff-memory ", SKILL_TEMPLATE)
        self.assertNotIn("阶段工作完成时使用", SKILL_TEMPLATE)
        self.assertNotIn("## 阶段检查点", SKILL_TEMPLATE)
        self.assertNotIn("完成重要里程碑", SKILL_TEMPLATE)

    def test_skill_distinguishes_current_evidence_from_handoff_claims(self) -> None:
        self.assertIn("当前已核验", SKILL_TEMPLATE)
        self.assertIn("交接中记录但本次尚未核验", SKILL_TEMPLATE)
        self.assertIn("不要在 `ACTIVE.md` 中记录其自身哈希", SKILL_TEMPLATE)

    def test_skill_requires_actionable_content_in_all_handoff_sections(self) -> None:
        self.assertIn("纯闲聊", SKILL_TEMPLATE)
        self.assertIn("可验证的完成标准", SKILL_TEMPLATE)
        self.assertIn("只写已经落地的结果", SKILL_TEMPLATE)
        self.assertIn("关键上下文与决策", SKILL_TEMPLATE)
        self.assertIn("产物与变更", SKILL_TEMPLATE)
        self.assertIn("测试、来源或人工检查", SKILL_TEMPLATE)
        self.assertIn("分别说明阻塞与风险", SKILL_TEMPLATE)
        self.assertIn("可直接执行的动作和完成条件", SKILL_TEMPLATE)
