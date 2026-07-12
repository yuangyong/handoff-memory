import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from handoff_memory.core import (
    _detect_drift,
    archive_active,
    initialize_project,
    inspect_project,
    render_resume,
)
from handoff_memory.repository_state import (
    RepositoryState,
    _sanitize_repository_url,
    read_repository_state,
)
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
            self.assertIn("worktree_sha256", payload)
            self.assertIn("worktree_change_count", payload)
            self.assertIn("status_available", payload)

    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_git_fingerprint_uses_complete_changes_before_display_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run(project, "git", "init")
            for index in range(205):
                (project / f"file-{index:03}.txt").write_text("内容\n", encoding="utf-8")

            first = read_repository_state(project)
            (project / "file-204.txt").unlink()
            (project / "replacement.txt").write_text("替换\n", encoding="utf-8")
            second = read_repository_state(project)

            self.assertEqual(len(first.changes), 200)
            self.assertEqual(first.worktree_change_count, 205)
            self.assertEqual(second.worktree_change_count, 205)
            self.assertNotEqual(first.worktree_sha256, second.worktree_sha256)

    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_resume_detects_git_dirty_to_dirty_worktree_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run(project, "git", "init")
            run(project, "git", "config", "user.name", "Handoff Test")
            run(project, "git", "config", "user.email", "handoff@example.invalid")
            tracked = project / "tracked.txt"
            tracked.write_text("第一版\n", encoding="utf-8")
            run(project, "git", "add", "tracked.txt")
            run(project, "git", "commit", "-m", "初始提交")
            initialize_project(project, name="Git dirty 漂移")
            (project / ".ai-memory/ACTIVE.md").write_text(valid_handoff(), encoding="utf-8")
            tracked.write_text("保存时修改\n", encoding="utf-8")
            archive_active(project)

            tracked.write_text("第一版\n", encoding="utf-8")
            (project / "new.txt").write_text("当前新增\n", encoding="utf-8")
            report = inspect_project(project)

            self.assertTrue(report.repository.dirty)
            self.assertTrue(any("工作区具体变更已变化" in item for item in report.drift))

    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_git_fingerprint_detects_content_change_with_same_status_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run(project, "git", "init")
            tracked = project / "tracked.txt"
            tracked.write_text("初始\n", encoding="utf-8")
            run(project, "git", "add", "tracked.txt")
            run(project, "git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "初始")
            tracked.write_text("脏内容 A\n", encoding="utf-8")
            first = read_repository_state(project)
            tracked.write_text("脏内容 B\n", encoding="utf-8")
            second = read_repository_state(project)

            self.assertEqual(first.changes, second.changes)
            self.assertNotEqual(first.worktree_sha256, second.worktree_sha256)

    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_git_fingerprint_reads_paths_from_repository_root_for_nested_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            run(repository, "git", "init")
            project = repository / "nested"
            project.mkdir()
            changed = project / "changed.txt"
            changed.write_text("脏内容 A\n", encoding="utf-8")
            first = read_repository_state(project)
            changed.write_text("脏内容 B\n", encoding="utf-8")
            second = read_repository_state(project)

            self.assertEqual(first.changes, second.changes)
            self.assertNotEqual(first.worktree_sha256, second.worktree_sha256)

    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_git_fingerprint_detects_dirty_submodule_content_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "submodule-source"
            source.mkdir()
            run(source, "git", "init")
            run(source, "git", "config", "user.name", "Test")
            run(source, "git", "config", "user.email", "test@example.invalid")
            (source / "a.txt").write_text("初始\n", encoding="utf-8")
            run(source, "git", "add", "a.txt")
            run(source, "git", "commit", "-m", "初始")

            project = root / "project"
            project.mkdir()
            run(project, "git", "init")
            run(project, "git", "config", "user.name", "Test")
            run(project, "git", "config", "user.email", "test@example.invalid")
            run(
                project,
                "git",
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                str(source),
                "sub",
            )
            run(project, "git", "commit", "-m", "添加子模块")
            nested = project / "sub/a.txt"
            nested.write_text("脏内容 A\n", encoding="utf-8")
            first = read_repository_state(project)
            nested.write_text("脏内容 B\n", encoding="utf-8")
            second = read_repository_state(project)

            self.assertEqual(first.changes, second.changes)
            self.assertNotEqual(first.worktree_sha256, second.worktree_sha256)

    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_git_save_bookkeeping_does_not_create_worktree_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run(project, "git", "init")
            initialize_project(project, name="内部记账过滤")
            active = project / ".ai-memory/ACTIVE.md"
            active.write_text(valid_handoff(), encoding="utf-8")

            saved = archive_active(project).repository_state
            current = inspect_project(project).repository

            self.assertEqual(saved.worktree_sha256, current.worktree_sha256)
            self.assertEqual(saved.worktree_change_count, current.worktree_change_count)
            self.assertTrue(any(".ai-memory/ACTIVE.md" in item for item in current.changes))
            self.assertFalse(any("config.json" in item for item in current.changes))
            self.assertFalse(any("sessions/" in item for item in current.changes))

    @unittest.skipUnless(shutil.which("git"), "当前环境未安装 Git")
    def test_git_ignores_handoff_temporary_and_lock_files_but_keeps_active(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            run(project, "git", "init")
            initialize_project(project, name="临时文件过滤")
            memory = project / ".ai-memory"
            (memory / "ACTIVE.md").write_text(valid_handoff(), encoding="utf-8")
            baseline = read_repository_state(project)

            (memory / ".config.json.pending.tmp").write_text("临时\n", encoding="utf-8")
            (memory / "handoff-memory.lock").write_text("lock\n", encoding="utf-8")
            (memory / "sessions/session.pending.tmp").write_text(
                "临时快照\n", encoding="utf-8"
            )
            after = read_repository_state(project)

            self.assertEqual(baseline.worktree_sha256, after.worktree_sha256)
            self.assertTrue(any(".ai-memory/ACTIVE.md" in item for item in after.changes))

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

    def test_repository_url_removes_query_and_fragment(self) -> None:
        cases = {
            "查询参数": (
                "https://example.com/team/repo.git?access_token=secret-value",
                "https://example.com/team/repo.git",
            ),
            "片段": (
                "https://example.com/team/repo.git#token=secret-value",
                "https://example.com/team/repo.git",
            ),
            "userinfo、查询参数与片段组合": (
                "https://user:password@example.com/team/repo.git"
                "?token=secret-value#credential",
                "https://example.com/team/repo.git",
            ),
            "普通路径": (
                "https://example.com/team/nested/repo.git",
                "https://example.com/team/nested/repo.git",
            ),
            "scp-like SSH": (
                "git@example.com:team/repo.git",
                "git@example.com:team/repo.git",
            ),
            "scp-like 非标准身份": (
                "secret-deploy-token@example.com:team/repo.git",
                "redacted@example.com:team/repo.git",
            ),
            "scp-like 查询参数": (
                "git@example.com:team/repo.git?access_token=secret-value",
                "git@example.com:team/repo.git",
            ),
            "scp-like 片段": (
                "git@example.com:team/repo.git#token=secret-value",
                "git@example.com:team/repo.git",
            ),
        }

        for case, (repository_url, expected) in cases.items():
            with self.subTest(case=case):
                self.assertEqual(_sanitize_repository_url(repository_url), expected)

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
    def test_svn_unversioned_memory_keeps_active_without_internal_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            working_copy = create_svn_working_copy(root)
            initialize_project(working_copy, name="SVN 未纳管交接")

            state = read_repository_state(working_copy)

            self.assertTrue(any(".ai-memory/ACTIVE.md" in item for item in state.changes))
            self.assertFalse(any("config.json" in item for item in state.changes))
            self.assertFalse(any("sessions/" in item for item in state.changes))

    @unittest.skipUnless(SVN_AVAILABLE, "当前环境未安装 svn 与 svnadmin")
    def test_resume_detects_svn_dirty_to_dirty_worktree_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            working_copy = create_svn_working_copy(root)
            initialize_project(working_copy, name="SVN dirty 漂移")
            (working_copy / ".ai-memory/ACTIVE.md").write_text(
                valid_handoff(), encoding="utf-8"
            )
            tracked = working_copy / "tracked.txt"
            tracked.write_text("保存时修改\n", encoding="utf-8")
            archive_active(working_copy)

            run(working_copy, "svn", "revert", "tracked.txt")
            (working_copy / "new.txt").write_text("当前新增\n", encoding="utf-8")
            report = inspect_project(working_copy)

            self.assertTrue(report.repository.dirty)
            self.assertTrue(any("工作区具体变更已变化" in item for item in report.drift))

    @unittest.skipUnless(SVN_AVAILABLE, "当前环境未安装 svn 与 svnadmin")
    def test_svn_fingerprint_detects_content_change_with_same_status_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            working_copy = create_svn_working_copy(Path(directory))
            tracked = working_copy / "tracked.txt"
            tracked.write_text("脏内容 A\n", encoding="utf-8")
            first = read_repository_state(working_copy)
            tracked.write_text("脏内容 B\n", encoding="utf-8")
            second = read_repository_state(working_copy)

            self.assertEqual(first.changes, second.changes)
            self.assertNotEqual(first.worktree_sha256, second.worktree_sha256)

    @unittest.skipUnless(SVN_AVAILABLE, "当前环境未安装 svn 与 svnadmin")
    def test_svn_fingerprint_detects_property_value_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            working_copy = create_svn_working_copy(Path(directory))
            run(working_copy, "svn", "propset", "review-prop", "A", "tracked.txt")
            first = read_repository_state(working_copy)
            run(working_copy, "svn", "propset", "review-prop", "B", "tracked.txt")
            second = read_repository_state(working_copy)

            self.assertEqual(first.changes, second.changes)
            self.assertNotEqual(first.worktree_sha256, second.worktree_sha256)

    @unittest.skipUnless(SVN_AVAILABLE, "当前环境未安装 svn 与 svnadmin")
    def test_svn_fingerprint_detects_unversioned_directory_content_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            working_copy = create_svn_working_copy(Path(directory))
            untracked = working_copy / "untracked"
            untracked.mkdir()
            payload = untracked / "note.txt"
            payload.write_text("脏内容 A\n", encoding="utf-8")
            first = read_repository_state(working_copy)
            payload.write_text("脏内容 B\n", encoding="utf-8")
            second = read_repository_state(working_copy)

            self.assertEqual(first.changes, second.changes)
            self.assertNotEqual(first.worktree_sha256, second.worktree_sha256)

    @unittest.skipUnless(SVN_AVAILABLE, "当前环境未安装 svn 与 svnadmin")
    def test_svn_save_bookkeeping_does_not_create_worktree_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            working_copy = create_svn_working_copy(root)
            initialize_project(working_copy, name="SVN 内部记账过滤")
            active = working_copy / ".ai-memory/ACTIVE.md"
            active.write_text(valid_handoff(), encoding="utf-8")
            run(working_copy, "svn", "add", ".ai-memory")
            run(working_copy, "svn", "commit", ".ai-memory", "-m", "加入交接文件")
            active.write_text(
                valid_handoff().replace("实现恢复流程。", "实现 SVN 恢复流程。"),
                encoding="utf-8",
            )

            saved = archive_active(working_copy).repository_state
            current = inspect_project(working_copy).repository

            self.assertEqual(saved.worktree_sha256, current.worktree_sha256)
            self.assertEqual(saved.worktree_change_count, current.worktree_change_count)
            self.assertTrue(any(".ai-memory/ACTIVE.md" in item for item in current.changes))
            self.assertFalse(any("config.json" in item for item in current.changes))
            self.assertFalse(any("sessions/" in item for item in current.changes))

            memory = working_copy / ".ai-memory"
            (memory / "handoff-memory.lock").write_text("lock\n", encoding="utf-8")
            (memory / ".config.json.pending.tmp").write_text("临时\n", encoding="utf-8")
            after_internal_files = read_repository_state(working_copy)
            self.assertEqual(
                current.worktree_sha256, after_internal_files.worktree_sha256
            )

    def test_drift_does_not_claim_stable_when_current_status_collection_failed(self) -> None:
        saved = RepositoryState(
            available=True,
            is_repository=True,
            provider="git",
            branch="main",
            head="abc123",
            dirty=True,
            changes=(" M tracked.txt",),
        ).to_dict()
        current = RepositoryState(
            available=True,
            is_repository=True,
            provider="git",
            branch="main",
            head="abc123",
            note="无法读取 Git 工作区状态",
            status_available=False,
        )

        drift = _detect_drift(saved, current)

        self.assertTrue(any("无法核验工作区具体变更" in item for item in drift))
        self.assertFalse(any("清洁状态已变化" in item for item in drift))
        self.assertFalse(any("未发现" in item for item in drift))

    def test_drift_accepts_legacy_snapshot_without_worktree_fingerprint(self) -> None:
        saved = {
            "available": True,
            "is_repository": True,
            "provider": "git",
            "branch": "main",
            "head": "abc123",
            "dirty": True,
            "changes": [" M tracked.txt"],
        }
        current = RepositoryState(
            available=True,
            is_repository=True,
            provider="git",
            branch="main",
            head="abc123",
            dirty=True,
            changes=(" M tracked.txt",),
            worktree_sha256="0" * 64,
            worktree_change_count=1,
        )

        drift = _detect_drift(saved, current)

        self.assertTrue(any("上次保存未记录工作区指纹" in item for item in drift))

    def test_non_repository_state_does_not_require_worktree_fingerprint(self) -> None:
        saved = RepositoryState(available=True, is_repository=False).to_dict()
        current = RepositoryState(available=True, is_repository=False)

        drift = _detect_drift(saved, current)

        self.assertFalse(any("工作区指纹" in item for item in drift))
        self.assertTrue(any("未发现" in item for item in drift))

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
