"""从包内 canonical 资源同步仓库顶层 session-handoff Skill。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
CANONICAL_SKILL = (
    REPOSITORY
    / "src"
    / "handoff_memory"
    / "assets"
    / "session-handoff"
    / "SKILL.md"
)
DEFAULT_TARGET = REPOSITORY / "skills" / "session-handoff" / "SKILL.md"


def _configure_utf8_output() -> None:
    """确保 Windows 旧代码页和重定向场景可以输出中文诊断。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: Sequence[str] | None = None) -> int:
    """同步分发副本，或只读检查副本是否与 canonical 资源一致。"""
    _configure_utf8_output()
    parser = argparse.ArgumentParser(
        description="同步仓库顶层 session-handoff Skill 分发副本。"
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help="输出路径；默认为 skills/session-handoff/SKILL.md",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只检查目标是否同步，不写入文件",
    )
    args = parser.parse_args(argv)

    canonical = CANONICAL_SKILL.read_text(encoding="utf-8")
    target = args.target.expanduser().resolve()
    current = target.read_text(encoding="utf-8") if target.is_file() else None
    if args.check:
        if current != canonical:
            print(f"Skill 分发副本不同步：{target}", file=sys.stderr)
            return 1
        print(f"Skill 分发副本已同步：{target}")
        return 0

    if current == canonical:
        print(f"Skill 分发副本无需更新：{target}")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        stream.write(canonical)
        temporary = Path(stream.name)
    temporary.replace(target)
    print(f"已同步 Skill 分发副本：{target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
