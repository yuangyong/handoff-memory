import os
import subprocess
import sys
import threading
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from handoff_memory import core
from handoff_memory.core import HandoffError, archive_active, initialize_project
from tests.test_core import valid_handoff


class SaveReliabilityTests(unittest.TestCase):
    def test_same_project_save_lock_serializes_writers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="锁示例")
            first_entered = threading.Event()
            release_first = threading.Event()
            second_entered = threading.Event()

            def first() -> None:
                with core._save_lock(project):
                    first_entered.set()
                    release_first.wait(timeout=2)

            def second() -> None:
                first_entered.wait(timeout=2)
                with core._save_lock(project):
                    second_entered.set()

            first_thread = threading.Thread(target=first)
            second_thread = threading.Thread(target=second)
            first_thread.start()
            second_thread.start()
            self.assertTrue(first_entered.wait(timeout=2))
            self.assertFalse(second_entered.wait(timeout=0.15))
            release_first.set()
            self.assertTrue(second_entered.wait(timeout=2))
            first_thread.join(timeout=2)
            second_thread.join(timeout=2)

    @unittest.skipUnless(os.name == "nt", "仅验证 Windows 空文件字节锁")
    def test_contended_empty_lock_file_waits_without_initialization_write(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            lock_path = core._save_lock_path(project)
            lock_path.touch()
            holder = lock_path.open("a+b")
            self.assertTrue(core._try_lock_stream(holder))
            entered = threading.Event()
            errors: list[Exception] = []

            def contend() -> None:
                try:
                    with core._save_lock(project):
                        entered.set()
                except Exception as exc:  # pragma: no cover - 失败时保留原异常
                    errors.append(exc)

            thread = threading.Thread(target=contend)
            thread.start()
            self.assertFalse(entered.wait(timeout=0.15))
            core._unlock_stream(holder)
            holder.close()
            thread.join(timeout=2)

            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            self.assertTrue(entered.is_set())

    def test_exclusive_snapshot_creation_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "snapshot.md"
            core._atomic_create(destination, "第一份\n")

            with self.assertRaisesRegex(HandoffError, "已存在"):
                core._atomic_create(destination, "第二份\n")

            self.assertEqual(destination.read_text(encoding="utf-8"), "第一份\n")

    def test_exclusive_snapshot_creation_publishes_complete_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "snapshot.md"

            core._atomic_create(destination, "完整内容")

            self.assertEqual(destination.read_text(encoding="utf-8"), "完整内容\n")
            self.assertFalse(any(destination.parent.glob("*.tmp")))

    def test_parallel_saves_create_distinct_complete_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="并发示例")
            active = project / ".ai-memory/ACTIVE.md"
            active.write_text(valid_handoff(), encoding="utf-8")

            with ThreadPoolExecutor(max_workers=6) as executor:
                results = list(executor.map(lambda _: archive_active(project), range(6)))

            paths = {result.archive_path for result in results}
            self.assertEqual(len(paths), 6)
            self.assertTrue(all(path.is_file() for path in paths))
            self.assertTrue(
                all("实现恢复流程" in path.read_text(encoding="utf-8") for path in paths)
            )

    def test_unlocked_residual_lock_file_does_not_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="残留锁文件示例")
            lock_path = core._save_lock_path(project)
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_bytes(b"\0")

            with core._save_lock(project):
                self.assertTrue(lock_path.is_file())

            self.assertTrue(lock_path.is_file())

    def test_process_exit_automatically_releases_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="崩溃恢复示例")
            code = (
                "import os,sys; from pathlib import Path; "
                "from handoff_memory.core import _save_lock; "
                "ctx=_save_lock(Path(sys.argv[1])); ctx.__enter__(); "
                "print('locked', flush=True); os._exit(0)"
            )
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
            child = subprocess.run(
                [sys.executable, "-c", code, str(project)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
                timeout=5,
            )
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertIn("locked", child.stdout)
            with core._save_lock(project):
                self.assertTrue(core._save_lock_path(project).is_file())

    def test_save_lock_serializes_separate_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="跨进程锁示例")
            release = project / "release.lock-test"
            code = (
                "import sys,time; from pathlib import Path; "
                "from handoff_memory.core import _save_lock; "
                "p=Path(sys.argv[1]); release=Path(sys.argv[2]); "
                "ctx=_save_lock(p); ctx.__enter__(); print('locked', flush=True); "
                "deadline=time.time()+10; "
                "\nwhile not release.exists() and time.time()<deadline: time.sleep(0.02)\n"
                "ctx.__exit__(None,None,None)"
            )
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
            child = subprocess.Popen(
                [sys.executable, "-c", code, str(project), str(release)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                env=environment,
            )
            try:
                self.assertEqual(child.stdout.readline().strip(), "locked")
                with patch.object(core, "_SAVE_LOCK_TIMEOUT_SECONDS", 0.1):
                    with self.assertRaisesRegex(HandoffError, "保存操作仍在进行"):
                        with core._save_lock(project):
                            self.fail("不应越过子进程持有的锁")
            finally:
                release.write_text("释放\n", encoding="utf-8")
                stdout, stderr = child.communicate(timeout=5)
                self.assertEqual(child.returncode, 0, stdout + stderr)

    def test_active_save_lock_times_out_with_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            initialize_project(project, name="锁超时示例")
            with core._save_lock(project):
                with patch.object(core, "_SAVE_LOCK_TIMEOUT_SECONDS", 0.05):
                    with self.assertRaisesRegex(HandoffError, "保存操作仍在进行"):
                        with core._save_lock(project):
                            self.fail("不应进入已被占用的锁")
