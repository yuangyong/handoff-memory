import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from handoff_memory import core
from handoff_memory.cli import build_parser, main


class HistoryTests(unittest.TestCase):
    def test_history_lists_newest_first_and_accepts_legacy_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            core.initialize_project(project, name="历史示例")
            sessions = project / ".ai-memory/sessions"
            write_snapshot(sessions / "20260712-120000.md", "2026-07-12T12:00:00Z", "旧正文")
            digest = active_digest("新正文")
            write_snapshot(
                sessions / "20260712-130000.md",
                "2026-07-12T13:00:00Z",
                "新正文",
                active_sha256=digest,
            )

            result = core.list_history(project)
            payload = json.loads(core.render_history(result, output_format="json"))

            self.assertEqual(
                [item["name"] for item in payload["snapshots"]],
                ["20260712-130000.md", "20260712-120000.md"],
            )
            self.assertEqual(payload["snapshots"][0]["active_sha256"], digest)
            self.assertIsNone(payload["snapshots"][1]["active_sha256"])
            self.assertEqual(payload["snapshots"][1]["status"], "ok")

    def test_history_reports_corrupt_and_newer_orphan_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            core.initialize_project(project, name="诊断示例")
            memory = project / ".ai-memory"
            config_path = memory / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["last_saved_at"] = "2026-07-12T12:00:00Z"
            config["last_archive"] = ".ai-memory/sessions/20260712-120000.md"
            config_path.write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            sessions = memory / "sessions"
            write_snapshot(sessions / "20260712-120000.md", "2026-07-12T12:00:00Z", "正常")
            write_snapshot(sessions / "20260712-130000.md", "2026-07-12T13:00:00Z", "孤立")
            write_snapshot(
                sessions / "20260712-140000.md",
                "2026-07-12T14:00:00Z",
                "损坏内容",
                active_sha256="0" * 64,
            )

            payload = json.loads(
                core.render_history(core.list_history(project), output_format="json")
            )
            by_name = {item["name"]: item for item in payload["snapshots"]}

            self.assertEqual(by_name["20260712-130000.md"]["status"], "orphan")
            self.assertTrue(
                any("更新" in item or "孤立" in item for item in by_name["20260712-130000.md"]["diagnostics"])
            )
            self.assertEqual(by_name["20260712-140000.md"]["status"], "corrupt")
            self.assertTrue(
                any("摘要" in item for item in by_name["20260712-140000.md"]["diagnostics"])
            )
            self.assertTrue(
                any("孤立" in item for item in by_name["20260712-140000.md"]["diagnostics"])
            )

    def test_show_latest_returns_metadata_and_active_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            core.initialize_project(project, name="查看示例")
            sessions = project / ".ai-memory/sessions"
            write_snapshot(sessions / "20260712-120000.md", "2026-07-12T12:00:00Z", "第一份")
            write_snapshot(sessions / "20260712-130000.md", "2026-07-12T13:00:00Z", "第二份")
            before = project_files(project)

            snapshot = core.show_snapshot(project, "latest")
            payload = json.loads(core.render_snapshot(snapshot, output_format="json"))
            markdown = core.render_snapshot(snapshot, output_format="markdown")

            self.assertEqual(payload["snapshot"], "20260712-130000.md")
            self.assertEqual(payload["metadata"]["saved_at"], "2026-07-12T13:00:00Z")
            self.assertEqual(payload["active"], "第二份\n")
            self.assertIn("第二份", markdown)
            self.assertEqual(before, project_files(project))

    def test_show_latest_prefers_last_committed_archive_in_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            core.initialize_project(project, name="最后完整保存")
            sessions = project / ".ai-memory/sessions"
            write_snapshot(sessions / "20260712-120000.md", "2026-07-12T12:00:00Z", "第一份")
            write_snapshot(sessions / "20260712-120000-2.md", "2026-07-12T12:00:00Z", "第二份")
            config_path = project / ".ai-memory/config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["last_archive"] = ".ai-memory/sessions/20260712-120000-2.md"
            config["last_saved_at"] = "2026-07-12T12:00:00Z"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            self.assertEqual(core.show_snapshot(project, "latest").active, "第二份\n")

    def test_same_second_history_uses_numeric_sequence_and_marks_orphan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            core.initialize_project(project, name="同秒顺序")
            sessions = project / ".ai-memory/sessions"
            write_snapshot(sessions / "20260712-120000.md", "2026-07-12T12:00:00Z", "第一份")
            write_snapshot(sessions / "20260712-120000-2.md", "2026-07-12T12:00:00Z", "第二份")
            config_path = project / ".ai-memory/config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["last_archive"] = ".ai-memory/sessions/20260712-120000.md"
            config["last_saved_at"] = "2026-07-12T12:00:00Z"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            records = core.list_history(project).snapshots
            self.assertEqual([item.name for item in records], ["20260712-120000-2.md", "20260712-120000.md"])
            self.assertEqual(records[0].status, "orphan")

            config_path.write_text("损坏", encoding="utf-8")
            self.assertEqual(core.show_snapshot(project, "latest").active, "第二份\n")

    def test_history_remains_available_when_active_or_config_is_broken(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            core.initialize_project(project, name="只读救援")
            write_snapshot(
                project / ".ai-memory/sessions/20260712-120000.md",
                "2026-07-12T12:00:00Z",
                "可恢复正文",
            )
            (project / ".ai-memory/ACTIVE.md").unlink()
            (project / ".ai-memory/config.json").write_text("损坏", encoding="utf-8")

            self.assertEqual(len(core.list_history(project).snapshots), 1)
            self.assertEqual(core.show_snapshot(project, "latest").active, "可恢复正文\n")

    def test_snapshot_round_trip_preserves_whitespace_and_marker_literal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            core.initialize_project(project, name="正文往返")
            active = "\n前置空行\n<!-- handoff-memory:repository-state:start -->\n正文尾部\n\n"
            state = core.RepositoryState(available=False, is_repository=False)
            rendered = core._render_archive(
                active,
                state,
                saved_at="2026-07-12T12:00:00Z",
                active_sha256=core._active_sha256(active),
            )
            path = project / ".ai-memory/sessions/20260712-120000.md"
            path.write_text(rendered, encoding="utf-8")

            snapshot = core.show_snapshot(project, path.name)
            self.assertEqual(snapshot.active, core._normalize_text(active))

    def test_show_rejects_path_traversal_and_non_markdown_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            core.initialize_project(project, name="安全路径示例")

            for name in ("../config.json", "..\\config.json", "config.json", ".md"):
                with self.subTest(name=name), self.assertRaises(core.HandoffError):
                    core.show_snapshot(project, name)

    def test_history_and_show_never_echo_secret_like_snapshot_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            core.initialize_project(project, name="敏感名称示例")
            secret_name = "ghp_" + "A" * 32 + ".md"
            write_snapshot(
                project / ".ai-memory/sessions" / secret_name,
                "2026-07-12T12:00:00Z",
                "正文",
            )

            rendered = core.render_history(core.list_history(project), output_format="json")
            self.assertNotIn(secret_name, rendered)
            self.assertIn("敏感快照名称已隐藏", rendered)
            with self.assertRaisesRegex(core.HandoffError, "敏感信息") as error:
                core.show_snapshot(project, secret_name)
            self.assertNotIn(secret_name, str(error.exception))

    def test_history_and_show_reject_snapshot_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            core.initialize_project(project, name="符号链接示例")
            sessions = project / ".ai-memory/sessions"
            outside = project / "outside.md"
            write_snapshot(outside, "2026-07-12T12:00:00Z", "外部正文")
            link = sessions / "20260712-120000.md"
            try:
                link.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"当前环境不能创建符号链接：{exc}")

            history = core.list_history(project)
            self.assertEqual(history.snapshots[0].status, "corrupt")
            self.assertTrue(
                any("符号链接" in item for item in history.snapshots[0].diagnostics)
            )
            with self.assertRaisesRegex(core.HandoffError, "符号链接"):
                core.show_snapshot(project, link.name)

    def test_history_rejects_symlinked_sessions_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            outside = Path(directory) / "outside"
            project.mkdir()
            outside.mkdir()
            core.initialize_project(project, name="目录链接示例")
            sessions = project / ".ai-memory/sessions"
            (sessions / ".gitkeep").unlink()
            sessions.rmdir()
            try:
                sessions.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"当前环境不能创建符号链接：{exc}")

            with self.assertRaisesRegex(core.HandoffError, "符号链接"):
                core.list_history(project)

    def test_show_rejects_secret_and_snapshot_larger_than_one_megabyte(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            core.initialize_project(project, name="安全内容示例")
            sessions = project / ".ai-memory/sessions"
            write_snapshot(
                sessions / "20260712-120000.md",
                "2026-07-12T12:00:00Z",
                "api_key=abcdefghijklmnopqrstuvwxyz123456",
            )
            (sessions / "20260712-130000.md").write_bytes(b"x" * (1_000_001))

            with self.assertRaises(core.HandoffError) as secret_error:
                core.show_snapshot(project, "20260712-120000.md")
            with self.assertRaises(core.HandoffError) as large_error:
                core.show_snapshot(project, "20260712-130000.md")

            self.assertIn("敏感", str(secret_error.exception))
            self.assertIn("1 MB", str(large_error.exception))

    def test_show_rejects_invalid_metadata_and_digest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            core.initialize_project(project, name="损坏元数据示例")
            sessions = project / ".ai-memory/sessions"
            write_snapshot(
                sessions / "20260712-120000.md",
                "不是时间",
                "正文",
            )
            write_snapshot(
                sessions / "20260712-130000.md",
                "2026-07-12T13:00:00Z",
                "正文",
                active_sha256="0" * 64,
            )

            with self.assertRaisesRegex(core.HandoffError, "已损坏"):
                core.show_snapshot(project, "20260712-120000.md")
            with self.assertRaisesRegex(core.HandoffError, "已损坏"):
                core.show_snapshot(project, "20260712-130000.md")

    def test_history_and_show_reject_truncated_repository_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            core.initialize_project(project, name="截断快照示例")
            sessions = project / ".ai-memory/sessions"
            state = core.RepositoryState(available=False, is_repository=False)
            complete = core._render_archive(
                "正文\n",
                state,
                saved_at="2026-07-12T12:00:00Z",
                active_sha256=core._active_sha256("正文\n"),
            )
            marker = "<!-- handoff-memory:repository-state:start -->"
            missing_block = complete.split(marker, 1)[0]
            missing_end = complete.replace(
                "<!-- handoff-memory:repository-state:end -->", ""
            )
            first = sessions / "20260712-120000.md"
            second = sessions / "20260712-130000.md"
            first.write_text(missing_block, encoding="utf-8")
            second.write_text(missing_end, encoding="utf-8")

            history = core.list_history(project)
            self.assertTrue(all(item.status == "corrupt" for item in history.snapshots))
            for path in (first, second):
                with self.assertRaisesRegex(core.HandoffError, "已损坏"):
                    core.show_snapshot(project, path.name)

    def test_cli_history_and_show_support_json_and_hmem_help(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            core.initialize_project(project, name="CLI 历史示例")
            write_snapshot(
                project / ".ai-memory/sessions/20260712-120000.md",
                "2026-07-12T12:00:00Z",
                "CLI 正文",
            )
            history_stdout = io.StringIO()
            show_stdout = io.StringIO()

            with contextlib.redirect_stdout(history_stdout):
                history_code = main(["history", str(project), "--format", "json"])
            with contextlib.redirect_stdout(show_stdout):
                show_code = main(
                    ["show", "latest", str(project), "--format", "json"]
                )

            self.assertEqual(history_code, 0)
            self.assertEqual(show_code, 0)
            self.assertEqual(
                json.loads(show_stdout.getvalue())["snapshot"],
                "20260712-120000.md",
            )
            self.assertIn("snapshots", json.loads(history_stdout.getvalue()))
            parser = build_parser()
            history_parser = next(
                action.choices["history"]
                for action in parser._actions
                if isinstance(getattr(action, "choices", None), dict)
                and "history" in action.choices
            )
            self.assertIn("usage: hmem history", history_parser.format_help())


def write_snapshot(
    path: Path,
    saved_at: str,
    active: str,
    *,
    active_sha256: str | None = None,
) -> None:
    digest_line = f"active_sha256: {active_sha256}\n" if active_sha256 else ""
    path.write_text(
        "---\n"
        f"saved_at: {saved_at}\n"
        "schema_version: 1\n"
        f"{digest_line}"
        "---\n\n"
        f"{active.rstrip()}\n"
        "<!-- handoff-memory:repository-state:start -->\n"
        "## 保存时仓库状态\n\n"
        "```json\n{}\n```\n"
        "<!-- handoff-memory:repository-state:end -->\n",
        encoding="utf-8",
    )


def active_digest(active: str) -> str:
    return hashlib.sha256((active.rstrip() + "\n").encode("utf-8")).hexdigest()


def project_files(project: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(project): path.read_bytes()
        for path in project.rglob("*")
        if path.is_file()
    }
