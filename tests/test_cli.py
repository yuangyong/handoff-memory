import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from handoff_memory.cli import main
from tests.test_core import valid_handoff


class CliTests(unittest.TestCase):
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
        self.assertIn("跨 AI 工具", result.stdout.decode("utf-8"))

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
