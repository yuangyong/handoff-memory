import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from handoff_memory.core import archive_active, initialize_project, inspect_project, render_resume
from handoff_memory.repository_state import read_repository_state
from tests.test_core import valid_handoff


SVN_AVAILABLE = bool(shutil.which("svn") and shutil.which("svnadmin"))


class RepositoryStateTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_git_state_keeps_legacy_fields_and_adds_provider(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run(project, "git", "init")

            state = read_repository_state(project)
            payload = state.to_dict()

            self.assertEqual(payload["provider"], "git")
            self.assertIn("branch", payload)
            self.assertIn("head", payload)
            self.assertIn("dirty", payload)
            self.assertIn("changes", payload)

    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_repository_url_does_not_expose_embedded_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run(project, "git", "init")
            run(
                project,
                "git",
                "remote",
                "add",
                "origin",
                "https://user:super-secret-token@example.com/team/repo.git",
            )

            state = read_repository_state(project)

            self.assertEqual(state.url, "https://example.com/team/repo.git")
            self.assertNotIn("super-secret-token", state.url or "")

    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_inspection_reads_legacy_last_saved_git_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run(project, "git", "init")
            run(project, "git", "config", "user.name", "Handoff Test")
            run(project, "git", "config", "user.email", "handoff@example.invalid")
            (project / "tracked.txt").write_text("第一版\n", encoding="utf-8")
            run(project, "git", "add", "tracked.txt")
            run(project, "git", "commit", "-m", "初始提交")
            initialize_project(project, name="旧配置示例")
            (project / ".ai-memory/ACTIVE.md").write_text(valid_handoff(), encoding="utf-8")
            archive_active(project)

            config_path = project / ".ai-memory/config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config.pop("last_saved_repository")
            config_path.write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (project / "tracked.txt").write_text("第二版\n", encoding="utf-8")
            run(project, "git", "add", "tracked.txt")
            run(project, "git", "commit", "-m", "更新内容")

            report = inspect_project(project)

            self.assertTrue(any("HEAD 已变化" in item for item in report.drift))

    @unittest.skipUnless(SVN_AVAILABLE, "当前环境未安装 svn 与 svnadmin")
    def test_svn_working_copy_reports_revision_url_and_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            working_copy = create_svn_working_copy(root)

            clean = read_repository_state(working_copy)
            self.assertEqual(clean.provider, "svn")
            self.assertTrue(clean.is_repository)
            self.assertEqual(clean.revision, "1")
            self.assertEqual(clean.head, "1")
            self.assertTrue(clean.url and clean.url.startswith("file:"))
            self.assertFalse(clean.dirty)

            (working_copy / "tracked.txt").write_text("第二版\n", encoding="utf-8")
            dirty = read_repository_state(working_copy)

            self.assertTrue(dirty.dirty)
            self.assertTrue(any("tracked.txt" in item and "M" in item for item in dirty.changes))

    @unittest.skipUnless(SVN_AVAILABLE, "当前环境未安装 svn 与 svnadmin")
    def test_save_and_resume_detect_svn_revision_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            working_copy = create_svn_working_copy(root)
            initialize_project(working_copy, name="SVN 示例")
            (working_copy / ".ai-memory/ACTIVE.md").write_text(
                valid_handoff(), encoding="utf-8"
            )

            archive_active(working_copy)
            config = json.loads(
                (working_copy / ".ai-memory/config.json").read_text(encoding="utf-8")
            )
            self.assertEqual(config["last_saved_repository"]["provider"], "svn")

            (working_copy / "tracked.txt").write_text("第二版\n", encoding="utf-8")
            run(working_copy, "svn", "commit", "tracked.txt", "-m", "第二次提交")
            run(working_copy, "svn", "update")

            report = inspect_project(working_copy)
            output = render_resume(report, output_format="markdown")

            self.assertEqual(report.repository.provider, "svn")
            self.assertTrue(any("修订号已变化" in item for item in report.drift))
            self.assertIn("版本库：SVN", output)
            self.assertIn("修订号：2", output)


def create_svn_working_copy(root: Path) -> Path:
    repository = root / "repository"
    working_copy = root / "working-copy"
    run(root, "svnadmin", "create", str(repository))
    run(root, "svn", "checkout", repository.as_uri(), str(working_copy))
    (working_copy / "tracked.txt").write_text("第一版\n", encoding="utf-8")
    run(working_copy, "svn", "add", "tracked.txt")
    run(working_copy, "svn", "commit", "-m", "初始提交")
    run(working_copy, "svn", "update")
    return working_copy


def run(cwd: Path, *command: str) -> None:
    subprocess.run(
        list(command),
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
