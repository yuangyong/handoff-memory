import tempfile
import unittest
from pathlib import Path

from handoff_memory.integrations import integrate
from handoff_memory.templates import SKILL_TEMPLATE


class IntegrationTemplateTests(unittest.TestCase):
    def test_codex_integration_preserves_existing_agents_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            agents = project / "AGENTS.md"
            agents.write_text("# 原有规则\n", encoding="utf-8")

            integrate(project, "codex")
            integrate(project, "codex")

            content = agents.read_text(encoding="utf-8")
            self.assertIn("# 原有规则", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)

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

    def test_all_integration_creates_every_supported_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "all")

            self.assertTrue((project / "AGENTS.md").is_file())
            self.assertTrue((project / "CLAUDE.md").is_file())
            self.assertTrue((project / "GEMINI.md").is_file())
            self.assertTrue((project / ".cursor/rules/handoff-memory.mdc").is_file())
            self.assertTrue((project / "AI-HANDOFF.md").is_file())
            self.assertTrue((project / ".agents/skills/session-handoff/SKILL.md").is_file())
            self.assertEqual(len(changed), 6)

            unchanged = integrate(project, "all")
            self.assertEqual(unchanged, [])

    def test_unknown_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                integrate(Path(directory), "unknown")

    def test_distributable_skill_matches_generated_skill(self) -> None:
        repository_skill = (
            Path(__file__).parents[1] / "skills/session-handoff/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertEqual(repository_skill, SKILL_TEMPLATE)
