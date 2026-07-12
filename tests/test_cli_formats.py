import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from handoff_memory.cli import main
from handoff_memory.core import archive_active, initialize_project
from tests.test_core import valid_handoff


class CliFormatTests(unittest.TestCase):
    def test_save_json_has_stable_machine_readable_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="JSON 保存示例")
            (project / ".ai-memory/ACTIVE.md").write_text(
                valid_handoff(), encoding="utf-8"
            )
            output = io.StringIO()

            with redirect_stdout(output):
                code = main(["save", str(project), "--format", "json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(payload["schema_version"], 1)
            self.assertTrue(payload["ok"])
            self.assertTrue(Path(payload["archive"]).is_file())
            self.assertEqual(len(payload["active_sha256"]), 64)
            self.assertIn("repository", payload)
            self.assertIn("warnings", payload)

    def test_json_error_is_machine_readable_without_traceback(self) -> None:
        output = io.StringIO()
        error = io.StringIO()

        with redirect_stdout(output), redirect_stderr(error):
            code = main(
                ["check", "Z:/definitely-not-existing/handoff-memory", "--format", "json"]
            )

        payload = json.loads(output.getvalue())
        self.assertEqual(code, 2)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "HANDOFF_ERROR")
        self.assertFalse(error.getvalue())

    def test_check_strict_fails_on_quality_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="严格检查示例")
            content = valid_handoff().replace(
                "- 单元测试待执行。", "- 测试已经通过。"
            ).replace("1. 编写实现。", "继续处理剩余工作。")
            (project / ".ai-memory/ACTIVE.md").write_text(content, encoding="utf-8")
            output = io.StringIO()

            with redirect_stdout(output):
                code = main(
                    ["check", str(project), "--strict", "--format", "json"]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(code, 2)
            self.assertFalse(payload["ok"])
            self.assertTrue(payload["strict"])
            self.assertGreaterEqual(len(payload["warnings"]), 2)

    def test_privacy_check_is_optional_and_strict_can_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="隐私检查示例")
            content = valid_handoff().replace(
                "实现恢复流程。", "联系 user@example.com 后实现恢复流程。"
            )
            (project / ".ai-memory/ACTIVE.md").write_text(content, encoding="utf-8")

            without_privacy = io.StringIO()
            with redirect_stdout(without_privacy):
                normal_code = main(
                    ["check", str(project), "--format", "json"]
                )
            privacy_output = io.StringIO()
            with redirect_stdout(privacy_output):
                privacy_code = main(
                    [
                        "check",
                        str(project),
                        "--privacy",
                        "--strict",
                        "--format",
                        "json",
                    ]
                )

            normal = json.loads(without_privacy.getvalue())
            privacy = json.loads(privacy_output.getvalue())
            self.assertEqual(normal_code, 0)
            self.assertEqual(normal["privacy_findings"], [])
            self.assertEqual(privacy_code, 2)
            self.assertEqual(privacy["privacy_findings"][0]["kind"], "邮箱地址")
            self.assertNotIn("user@example.com", privacy_output.getvalue())

    def test_check_json_success_contains_integrity_and_repository_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="检查输出示例")
            (project / ".ai-memory/ACTIVE.md").write_text(
                valid_handoff(), encoding="utf-8"
            )
            output = io.StringIO()

            with redirect_stdout(output):
                code = main(["check", str(project), "--format", "json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(code, 0)
            self.assertTrue(payload["ok"])
            self.assertIn("repository", payload)
            self.assertIn("active_sha256", payload)
            self.assertIn("active_matches_saved", payload)

    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_privacy_check_redacts_personal_information_in_repository_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            subprocess.run(["git", "init", str(project)], check=True, capture_output=True)
            initialize_project(project, name="仓库隐私检查")
            (project / ".ai-memory/ACTIVE.md").write_text(valid_handoff(), encoding="utf-8")
            personal_name = "user@example.com.txt"
            (project / personal_name).write_text("内容\n", encoding="utf-8")
            output = io.StringIO()

            with redirect_stdout(output):
                code = main(
                    ["check", str(project), "--privacy", "--strict", "--format", "json"]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(code, 2)
            self.assertTrue(payload["repository"]["redacted"])
            self.assertTrue(
                any(item["source"] == "repository" for item in payload["privacy_findings"])
            )
            self.assertNotIn(personal_name, output.getvalue())

    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_check_redacts_secret_in_repository_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            subprocess.run(["git", "init", str(project)], check=True, capture_output=True)
            initialize_project(project, name="仓库密钥检查")
            (project / ".ai-memory/ACTIVE.md").write_text(valid_handoff(), encoding="utf-8")
            secret_name = "sk-" + "A" * 24 + ".txt"
            (project / secret_name).write_text("内容\n", encoding="utf-8")
            output = io.StringIO()

            with redirect_stdout(output):
                code = main(["check", str(project), "--format", "json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(code, 2)
            self.assertTrue(payload["repository"]["redacted"])
            self.assertNotIn(secret_name, output.getvalue())

    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_privacy_check_redacts_personal_information_in_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            subprocess.run(["git", "init", str(project)], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(project), "config", "user.name", "Test"], check=True
            )
            subprocess.run(
                ["git", "-C", str(project), "config", "user.email", "test@example.invalid"], check=True
            )
            subprocess.run(
                ["git", "-C", str(project), "config", "core.autocrlf", "false"], check=True
            )
            initialize_project(project, name="漂移隐私检查")
            (project / ".ai-memory/ACTIVE.md").write_text(valid_handoff(), encoding="utf-8")
            subprocess.run(["git", "-C", str(project), "add", "."], check=True)
            subprocess.run(["git", "-C", str(project), "commit", "-m", "初始"], check=True, capture_output=True)
            archive_active(project)
            personal_branch = "alice@example.com"
            subprocess.run(
                ["git", "-C", str(project), "checkout", "-b", personal_branch],
                check=True,
                capture_output=True,
            )
            output = io.StringIO()

            with redirect_stdout(output):
                code = main(
                    ["check", str(project), "--privacy", "--strict", "--format", "json"]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(code, 2)
            self.assertTrue(payload["repository"]["redacted"])
            self.assertEqual(payload["drift"], ["仓库漂移包含个人信息，已隐藏具体值"])
            self.assertNotIn(personal_branch, output.getvalue())
