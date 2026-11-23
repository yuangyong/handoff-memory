import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from handoff_memory import __version__
from handoff_memory.cli import main
from tests.test_core import valid_handoff


class CliTests(unittest.TestCase):
    def test_pyproject_exposes_only_hmem_cli_entry(self) -> None:
        pyproject = (Path(__file__).parents[1] / "pyproject.toml").read_text(
            encoding="utf-8"
        )
        scripts = pyproject.split("[project.scripts]", 1)[1].split("[", 1)[0]

        self.assertEqual(scripts.strip(), 'hmem = "handoff_memory.cli:main"')

    def test_direct_main_call_uses_hmem_as_canonical_name(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                main(["--help"])

        content = output.getvalue()
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("usage: hmem", content)
        self.assertIn("hmem init . --select-tools", content)
        self.assertNotIn("handoff-memory init . --select-tools", content)

    def test_help_and_version_always_use_hmem_brand(self) -> None:
        help_output = io.StringIO()
        with patch.object(sys, "argv", ["handoff-memory", "help", "save"]):
            with redirect_stdout(help_output):
                self.assertEqual(main(), 0)

        help_content = help_output.getvalue()
        self.assertIn("usage: hmem save", help_content)
        self.assertIn("hmem save . --from handoff.md", help_content)
        self.assertNotIn("usage: handoff-memory", help_content)

        version_output = io.StringIO()
        with patch.object(sys, "argv", ["handoff-memory", "--version"]):
            with redirect_stdout(version_output):
                with self.assertRaises(SystemExit) as raised:
                    main()

        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(version_output.getvalue().strip(), f"hmem {__version__}")

    def test_help_command_prints_detailed_overview(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            code = main(["help"])

        content = output.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("常用示例", content)
        self.assertIn("help [COMMAND]", content)
        self.assertIn("--select-tools", content)
        self.assertIn("显示版本并退出", content)

    def test_help_command_prints_detailed_init_help(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            code = main(["help", "init"])

        content = output.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("交互选择", content)
        self.assertIn("--integrate", content)
        self.assertIn("--with-rules", content)
        self.assertNotIn("--with-agents-rule", content)
        self.assertIn("示例", content)

    def test_integrate_help_lists_supported_targets_and_output_paths(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            code = main(["help", "integrate"])

        content = output.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("OpenCode", content)
        self.assertIn(".opencode/skills/", content)
        self.assertIn(".cursor/skills/", content)
        self.assertIn(".agents/rules/handoff-memory.md", content)
        self.assertIn("Antigravity IDE", content)
        self.assertIn(".trae/skills/", content)
        self.assertIn("TRAE", content)
        self.assertIn(".trae/rules/project_rules.md", content)
        self.assertIn("规则默认不生成", content)
        self.assertIn("hmem skills add", content)
        self.assertNotIn("Roo Code", content)

    def test_package_version_matches_pyproject(self) -> None:
        pyproject = (Path(__file__).parents[1] / "pyproject.toml").read_text(
            encoding="utf-8"
        )
        match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)

        self.assertIsNotNone(match)
        self.assertEqual(__version__, match.group(1))

    def test_package_metadata_uses_mit_and_public_maintainer(self) -> None:
        pyproject = (Path(__file__).parents[1] / "pyproject.toml").read_text(
            encoding="utf-8"
        )
        license_text = (Path(__file__).parents[1] / "LICENSE").read_text(
            encoding="utf-8"
        )

        self.assertRegex(pyproject, r'(?m)^license = "MIT"$')
        self.assertIn(
            'authors = [{ name = "yuangyong", email = "2314042921@qq.com" }]',
            pyproject,
        )
        self.assertIn(
            'maintainers = [{ name = "yuangyong", email = "2314042921@qq.com" }]',
            pyproject,
        )
        self.assertTrue(license_text.startswith("MIT License\n"))
        self.assertIn("Copyright (c) 2026 yuangyong", license_text)

    def test_help_output_is_utf8_in_subprocess(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")

        result = subprocess.run(
            [sys.executable, "-m", "handoff_memory", "--help"],
            cwd=Path(__file__).parents[1],
            env=environment,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        output = result.stdout.decode("utf-8")
        self.assertIn("跨 AI 工具", output)
        self.assertIn("usage: hmem", output)
        self.assertIn("hmem resume .", output)
        self.assertNotIn("handoff-memory resume .", output)

    def test_utf8_standard_input_works_in_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.assertEqual(main(["init", str(project)]), 0)
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "handoff_memory",
                    "save",
                    str(project),
                    "--from",
                    "-",
                ],
                cwd=Path(__file__).parents[1],
                env=environment,
                input=valid_handoff().encode("utf-8"),
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))

    def test_end_to_end_cli_flow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            output = io.StringIO()

            with redirect_stdout(output):
                self.assertEqual(main(["init", str(project), "--name", "CLI 示例"]), 0)

            source = project / "handoff.md"
            source.write_text(valid_handoff(), encoding="utf-8")
            with redirect_stdout(output):
                self.assertEqual(main(["save", str(project), "--from", str(source)]), 0)
                self.assertEqual(main(["resume", str(project)]), 0)
                self.assertEqual(main(["check", str(project)]), 0)

            self.assertIn("实现恢复流程", output.getvalue())

    def test_resume_commands_do_not_modify_memory_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            output = io.StringIO()
            self.assertEqual(main(["init", str(project), "--name", "只读示例"]), 0)
            source = project / "handoff.md"
            source.write_text(valid_handoff(), encoding="utf-8")
            self.assertEqual(main(["save", str(project), "--from", str(source)]), 0)
            memory = project / ".ai-memory"
            before = {
                path.relative_to(memory): path.read_bytes()
                for path in memory.rglob("*")
                if path.is_file()
            }

            with redirect_stdout(output):
                self.assertEqual(main(["resume", str(project)]), 0)
                self.assertEqual(
                    main(["resume", str(project), "--format", "json"]), 0
                )

            after = {
                path.relative_to(memory): path.read_bytes()
                for path in memory.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

    def test_init_with_codex_creates_skill_without_new_agents_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            code = main(["init", str(project), "--integrate", "codex"])

            self.assertEqual(code, 0)
            self.assertFalse((project / "AGENTS.md").exists())
            self.assertTrue((project / ".agents/skills/handoff-save/SKILL.md").is_file())
            self.assertTrue((project / ".agents/skills/handoff-resume/SKILL.md").is_file())

    def test_init_can_interactively_select_multiple_ai_tools(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            output = io.StringIO()

            with patch("builtins.input", return_value="1,3,6"), redirect_stdout(output):
                code = main(["init", str(project), "--select-tools"])

            self.assertEqual(code, 0)
            self.assertTrue((project / ".agents/skills/handoff-save/SKILL.md").is_file())
            self.assertTrue((project / ".agents/skills/handoff-resume/SKILL.md").is_file())
            self.assertFalse((project / ".cursor/rules/handoff-memory.mdc").exists())
            self.assertTrue((project / ".cursor/skills/handoff-save/SKILL.md").is_file())
            self.assertTrue((project / ".cursor/skills/handoff-resume/SKILL.md").is_file())
            self.assertFalse((project / ".github/copilot-instructions.md").exists())
            self.assertTrue((project / ".github/skills/handoff-save/SKILL.md").is_file())
            self.assertTrue((project / ".github/skills/handoff-resume/SKILL.md").is_file())
            self.assertFalse((project / "CLAUDE.md").exists())
            self.assertIn("Codex", output.getvalue())
            self.assertIn("GitHub Copilot", output.getvalue())

    def test_interactive_tool_selection_can_be_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            with patch("builtins.input", return_value=""):
                code = main(["init", str(project), "--select-tools"])

            self.assertEqual(code, 0)
            self.assertTrue((project / ".ai-memory/ACTIVE.md").is_file())
            self.assertFalse((project / ".agents").exists())

    def test_interactive_selection_retries_invalid_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            output = io.StringIO()

            with patch("builtins.input", side_effect=["99", "2"]), redirect_stdout(output):
                code = main(["init", str(project), "--select-tools"])

            self.assertEqual(code, 0)
            self.assertTrue((project / ".claude/skills/handoff-save/SKILL.md").is_file())
            self.assertTrue((project / ".claude/skills/handoff-resume/SKILL.md").is_file())
            self.assertFalse((project / "CLAUDE.md").exists())
            self.assertIn("无效选择", output.getvalue())

    def test_interactive_codex_antigravity_qoder_default_to_skills_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            output = io.StringIO()

            with patch("builtins.input", return_value="1,5,11"), redirect_stdout(output):
                code = main(["init", str(project), "--select-tools"])

            self.assertEqual(code, 0)
            self.assertTrue((project / ".agents/skills/handoff-save/SKILL.md").is_file())
            self.assertTrue((project / ".agents/skills/handoff-resume/SKILL.md").is_file())
            self.assertTrue((project / ".qoder/skills/handoff-save/SKILL.md").is_file())
            self.assertTrue((project / ".qoder/skills/handoff-resume/SKILL.md").is_file())
            self.assertFalse((project / ".agents/rules/handoff-memory.md").exists())
            self.assertFalse((project / ".qoder/rules/handoff-memory.md").exists())
            self.assertIn("已更新 4 个 AI 接入文件", output.getvalue())

    def test_interactive_rules_option_creates_selected_native_rules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            with patch("builtins.input", return_value="1,5,11"):
                code = main(
                    ["init", str(project), "--select-tools", "--with-rules"]
                )

            self.assertEqual(code, 0)
            self.assertTrue((project / "AGENTS.md").is_file())
            self.assertTrue((project / ".agents/rules/handoff-memory.md").is_file())
            self.assertTrue((project / ".qoder/rules/handoff-memory.md").is_file())

    def test_init_with_codex_rules_appends_route_to_existing_agents_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            project.mkdir(exist_ok=True)
            agents = project / "AGENTS.md"
            agents.write_text("# 团队原有规则\n", encoding="utf-8")

            code = main(
                [
                    "init",
                    str(project),
                    "--integrate",
                    "codex",
                    "--with-rules",
                ]
            )

            self.assertEqual(code, 0)
            content = agents.read_text(encoding="utf-8")
            self.assertIn("# 团队原有规则", content)
            self.assertIn("使用 `handoff-save` Skill", content)
            self.assertIn("使用 `handoff-resume` Skill", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)

    def test_integrate_codex_can_create_root_rule_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            code = main(
                ["integrate", "codex", str(project), "--with-rules"]
            )

            self.assertEqual(code, 0)
            self.assertTrue((project / "AGENTS.md").is_file())
            self.assertTrue((project / ".agents/skills/handoff-save/SKILL.md").is_file())
            self.assertTrue((project / ".agents/skills/handoff-resume/SKILL.md").is_file())

    def test_init_rules_option_supports_non_codex_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code = main(
                ["init", directory, "--integrate", "claude", "--with-rules"]
            )

            self.assertEqual(code, 0)
            self.assertTrue((Path(directory) / "CLAUDE.md").is_file())

    def test_rules_option_rejects_auxiliary_target_before_initialization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            error = io.StringIO()

            with redirect_stderr(error):
                code = main(
                    ["init", str(project), "--integrate", "generic", "--with-rules"]
                )

            self.assertEqual(code, 2)
            self.assertFalse((project / ".ai-memory").exists())
            self.assertIn("具名客户端", error.getvalue())

    def test_removed_agents_rule_option_is_rejected(self) -> None:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "handoff_memory",
                "integrate",
                "codex",
                ".",
                "--with-agents-rule",
            ],
            cwd=Path(__file__).parents[1],
            env=environment,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn(b"--with-agents-rule", result.stderr)

    def test_user_error_returns_exit_code_two_without_traceback(self) -> None:
        error = io.StringIO()

        with redirect_stderr(error):
            code = main(["resume", "Z:/definitely-not-existing/handoff-memory"])

        self.assertEqual(code, 2)
        self.assertIn("错误", error.getvalue())
        self.assertNotIn("Traceback", error.getvalue())

    def test_save_allow_large_is_required_for_64_to_256kb_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.assertEqual(main(["init", str(project)]), 0)
            source = project / "large-handoff.md"
            source.write_text(
                valid_handoff().replace("实现恢复流程。", "A" * 66_000),
                encoding="utf-8",
            )
            error = io.StringIO()

            with redirect_stderr(error):
                rejected = main(["save", str(project), "--from", str(source)])
            accepted = main(
                ["save", str(project), "--from", str(source), "--allow-large"]
            )

            self.assertEqual(rejected, 2)
            self.assertIn("--allow-large", error.getvalue())
            self.assertEqual(accepted, 0)

    def test_save_rejects_source_above_256kb_even_when_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.assertEqual(main(["init", str(project)]), 0)
            source = project / "oversized-handoff.md"
            source.write_text(
                valid_handoff().replace("实现恢复流程。", "A" * 263_000),
                encoding="utf-8",
            )
            error = io.StringIO()

            with redirect_stderr(error):
                code = main(
                    ["save", str(project), "--from", str(source), "--allow-large"]
                )

            self.assertEqual(code, 2)
            self.assertIn("256KB", error.getvalue())

    def test_help_skills_prints_global_and_status_usage(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            code = main(["help", "skills"])

        content = output.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("skills add claude -g", content)
        self.assertIn("skills status .", content)
        self.assertIn("~/.gemini/config/skills/", content)
        self.assertIn("~/.codeium/windsurf/skills/", content)
        self.assertIn("~/.config/opencode/skills/", content)

    def test_skills_add_global_installs_only_skills_to_mocked_home(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as project_dir:
            fake_home = Path(home_dir).resolve()
            project = Path(project_dir).resolve()
            output = io.StringIO()

            with patch("handoff_memory.integrations.Path.home", return_value=fake_home), redirect_stdout(output):
                code = main(["skills", "add", "claude", "-g"])

            self.assertEqual(code, 0)
            self.assertIn("已更新 2 个用户全局 Skill 文件", output.getvalue())
            self.assertTrue((fake_home / ".claude/skills/handoff-save/SKILL.md").is_file())
            self.assertTrue((fake_home / ".claude/skills/handoff-resume/SKILL.md").is_file())
            self.assertFalse((fake_home / "CLAUDE.md").exists())
            self.assertFalse((project / ".claude").exists())

    def test_skills_add_rejects_path_with_global_and_rejects_generic(self) -> None:
        error = io.StringIO()
        with redirect_stderr(error):
            conflict_code = main(["skills", "add", "codex", ".", "-g"])
        self.assertEqual(conflict_code, 2)
        self.assertIn("不能同时指定项目路径", error.getvalue())

        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(["skills", "add", "generic"])
        self.assertEqual(raised.exception.code, 2)

    def test_skills_status_json_and_legacy_warning_are_readonly(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as project_dir:
            fake_home = Path(home_dir).resolve()
            project = Path(project_dir).resolve()
            legacy = project / ".agents/skills/session-handoff/SKILL.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("legacy\n", encoding="utf-8")

            add_output = io.StringIO()
            with patch("handoff_memory.integrations.Path.home", return_value=fake_home), redirect_stdout(add_output):
                self.assertEqual(main(["skills", "add", "codex", str(project)]), 0)
            self.assertIn("旧版 session-handoff Skill", add_output.getvalue())
            self.assertTrue(legacy.exists())

            status_output = io.StringIO()
            with patch("handoff_memory.integrations.Path.home", return_value=fake_home), redirect_stdout(status_output):
                self.assertEqual(main(["skills", "status", str(project), "--format", "json"]), 0)
            payload = json.loads(status_output.getvalue())
            self.assertEqual(payload["schema_version"], 1)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["legacy_skills"], [str(legacy)])
            self.assertTrue(legacy.exists())
