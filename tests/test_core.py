import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from handoff_memory.core import (
    HandoffError,
    archive_active,
    initialize_project,
    inspect_project,
    render_resume,
)
from handoff_memory.git_state import read_git_state


class CoreFlowTests(unittest.TestCase):
    def test_init_creates_complete_memory_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            result = initialize_project(project, name="示例项目")

            self.assertTrue(result.created)
            self.assertTrue((project / ".ai-memory/ACTIVE.md").is_file())
            self.assertTrue((project / ".ai-memory/PROJECT.md").is_file())
            self.assertTrue((project / ".ai-memory/DECISIONS.md").is_file())
            config = json.loads((project / ".ai-memory/config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["project_name"], "示例项目")
            self.assertEqual(config["schema_version"], 1)

    def test_init_is_idempotent_and_preserves_active_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="示例项目")
            active = project / ".ai-memory/ACTIVE.md"
            active.write_text("用户内容", encoding="utf-8")

            result = initialize_project(project, name="示例项目")

            self.assertFalse(result.created)
            self.assertEqual(active.read_text(encoding="utf-8"), "用户内容")

    def test_save_archives_valid_active_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="示例项目")
            active = project / ".ai-memory/ACTIVE.md"
            active.write_text(valid_handoff(), encoding="utf-8")

            result = archive_active(project)

            self.assertTrue(result.archive_path.is_file())
            self.assertIn("实现恢复流程", result.archive_path.read_text(encoding="utf-8"))

    def test_save_rejects_missing_required_sections(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="示例项目")
            (project / ".ai-memory/ACTIVE.md").write_text("# 只有标题", encoding="utf-8")

            with self.assertRaises(HandoffError):
                archive_active(project)

    def test_save_rejects_likely_secret_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="示例项目")
            content = valid_handoff() + "\nAPI_KEY=sk-" + "a" * 32
            (project / ".ai-memory/ACTIVE.md").write_text(content, encoding="utf-8")

            with self.assertRaises(HandoffError):
                archive_active(project)

    def test_resume_contains_active_content_and_current_repository_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="示例项目")
            (project / ".ai-memory/ACTIVE.md").write_text(valid_handoff(), encoding="utf-8")

            report = inspect_project(project)
            output = render_resume(report, output_format="markdown")

            self.assertIn("实现恢复流程", output)
            self.assertIn("当前仓库核验", output)
            self.assertIn("未识别 Git 或 SVN", output)

    def test_json_resume_has_stable_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="示例项目")
            (project / ".ai-memory/ACTIVE.md").write_text(valid_handoff(), encoding="utf-8")

            payload = json.loads(render_resume(inspect_project(project), output_format="json"))

            self.assertEqual(payload["schema_version"], 1)
            self.assertIn("active", payload)
            self.assertIn("repository", payload)

    def test_resume_refuses_to_echo_detected_secret(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="安全示例")
            content = valid_handoff() + "\naccess_token=" + "x" * 32
            (project / ".ai-memory/ACTIVE.md").write_text(content, encoding="utf-8")

            report = inspect_project(project)
            with self.assertRaises(HandoffError) as raised:
                render_resume(report, output_format="markdown")

            self.assertNotIn("x" * 32, str(raised.exception))

    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_resume_detects_commit_drift_in_real_git_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_git(project, "init")
            run_git(project, "config", "user.name", "Handoff Test")
            run_git(project, "config", "user.email", "handoff@example.invalid")
            (project / "tracked.txt").write_text("第一版\n", encoding="utf-8")
            run_git(project, "add", "tracked.txt")
            run_git(project, "commit", "-m", "初始提交")
            initialize_project(project, name="Git 示例")
            (project / ".ai-memory/ACTIVE.md").write_text(valid_handoff(), encoding="utf-8")
            archive_active(project)

            (project / "tracked.txt").write_text("第二版\n", encoding="utf-8")
            run_git(project, "add", "tracked.txt")
            run_git(project, "commit", "-m", "更新内容")
            report = inspect_project(project)

            self.assertTrue(report.repository.is_repository)
            self.assertEqual(report.repository.provider, "git")
            self.assertTrue(any("HEAD 已变化" in item for item in report.drift))

    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_git_state_bounds_large_change_lists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run_git(project, "init")
            for index in range(205):
                (project / f"file-{index:03}.txt").write_text("内容\n", encoding="utf-8")

            state = read_git_state(project)

            self.assertEqual(len(state.changes), 200)
            self.assertIn("205", state.note or "")


def valid_handoff() -> str:
    return """# 当前任务交接

## 当前目标

实现恢复流程。

## 已完成

- 初始化设计。

## 关键决策

- 使用 Markdown。

## 修改文件

- `src/example.py`

## 验证结果

- 单元测试待执行。

## 阻塞与风险

- 无。

## 下一步

1. 编写实现。
"""


def run_git(project: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(project), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
