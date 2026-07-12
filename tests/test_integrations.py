import tempfile
import unittest
from pathlib import Path

from handoff_memory.integrations import AI_TOOL_TARGETS, TARGETS, integrate
from handoff_memory.templates import GENERIC_RULE, SKILL_TEMPLATE


class IntegrationTemplateTests(unittest.TestCase):
    def test_mainstream_ai_tools_have_named_targets(self) -> None:
        expected = {
            "codex",
            "claude",
            "cursor",
            "gemini",
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
            "opencode": ".opencode/skills/session-handoff/SKILL.md",
        }

        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            for target, relative_path in expected_paths.items():
                with self.subTest(target=target):
                    changed = integrate(project, target)
                    destination = project / relative_path
                    self.assertEqual(changed, [destination])
                    self.assertTrue(destination.is_file())
                    self.assertIn("handoff-memory:start", destination.read_text(encoding="utf-8"))
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

    def test_codex_agents_rule_option_preserves_and_appends_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            agents = project / "AGENTS.md"
            agents.write_text("# 原有规则\n", encoding="utf-8")

            integrate(project, "codex", with_agents_rule=True)
            integrate(project, "codex", with_agents_rule=True)

            content = agents.read_text(encoding="utf-8")
            self.assertIn("# 原有规则", content)
            self.assertIn("使用 `session-handoff` Skill", content)
            self.assertNotIn("开始处理任务前", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)

    def test_codex_agents_rule_option_creates_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "codex", with_agents_rule=True)

            agents = project / "AGENTS.md"
            self.assertTrue(agents.is_file())
            self.assertIn("使用 `session-handoff` Skill", agents.read_text(encoding="utf-8"))
            self.assertEqual(len(changed), 2)

    def test_opencode_creates_project_skill_and_only_adds_agents_rule_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "opencode")

            self.assertEqual(
                changed,
                [project / ".opencode/skills/session-handoff/SKILL.md"],
            )
            self.assertFalse((project / "AGENTS.md").exists())

            changed = integrate(project, "opencode", with_agents_rule=True)

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

            integrate(project, "codex", with_agents_rule=True)

            content = agents.read_text(encoding="utf-8")
            self.assertIn("使用 `session-handoff` Skill", content)
            self.assertNotIn("开始处理任务前", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)

    def test_all_can_explicitly_include_agents_rule(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "all", with_agents_rule=True)

            self.assertTrue((project / "AGENTS.md").is_file())
            self.assertEqual(len(changed), 13)

    def test_cursor_integration_preserves_existing_rule_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            cursor_rule = project / ".cursor/rules/handoff-memory.mdc"
            cursor_rule.parent.mkdir(parents=True)
            cursor_rule.write_text("---\nalwaysApply: true\n---\n\n用户自定义规则\n", encoding="utf-8")

            integrate(project, "cursor")

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

    def test_all_integration_creates_all_standalone_adapter_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "all")

            self.assertFalse((project / "AGENTS.md").exists())
            self.assertTrue((project / "CLAUDE.md").is_file())
            self.assertTrue((project / "GEMINI.md").is_file())
            self.assertTrue((project / ".cursor/rules/handoff-memory.mdc").is_file())
            self.assertTrue((project / "AI-HANDOFF.md").is_file())
            self.assertTrue((project / ".agents/skills/session-handoff/SKILL.md").is_file())
            self.assertTrue((project / ".trae/rules/project_rules.md").is_file())
            self.assertTrue((project / ".qoder/rules/handoff-memory.md").is_file())
            self.assertTrue(
                (project / ".opencode/skills/session-handoff/SKILL.md").is_file()
            )
            self.assertEqual(len(changed), 12)

            unchanged = integrate(project, "all")
            self.assertEqual(unchanged, [])

    def test_unknown_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                integrate(Path(directory), "unknown")

    def test_agents_rule_option_is_limited_to_codex_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "codex.*all"):
                integrate(Path(directory), "claude", with_agents_rule=True)

    def test_distributable_skill_matches_generated_skill(self) -> None:
        repository_skill = (
            Path(__file__).parents[1] / "skills/session-handoff/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertEqual(repository_skill, SKILL_TEMPLATE)

    def test_rules_do_not_duplicate_active_context_on_resume(self) -> None:
        self.assertIn("输出已经包含 `ACTIVE.md`", GENERIC_RULE)
        self.assertNotIn("并阅读 `.ai-memory/ACTIVE.md`", GENERIC_RULE)

    def test_skill_uses_workspace_evidence_and_handles_missing_state(self) -> None:
        self.assertIn("版本库状态、相关 diff 和实际测试结果", SKILL_TEMPLATE)
        self.assertIn("没有可恢复的交接", SKILL_TEMPLATE)
        self.assertIn("不得假装恢复成功", SKILL_TEMPLATE)
        self.assertIn("不要自动使用 `--allow-sensitive`", SKILL_TEMPLATE)
