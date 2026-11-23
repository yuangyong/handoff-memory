"""从包内 canonical 资源同步仓库顶层双 Skill 分发副本。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
ASSETS_ROOT = REPOSITORY / "src" / "handoff_memory" / "assets"
DEFAULT_SKILLS_DIR = REPOSITORY / "skills"
SKILL_NAMES = ("handoff-save", "handoff-resume")
_CLI_CHECK_SECTION = re.compile(
    r"(## CLI 可用性检查\n.*?)(?=\n## |\n<!-- handoff-memory:end -->)",
    re.DOTALL,
)


def _configure_utf8_output() -> None:
    """确保 Windows 旧代码页和重定向场景可以输出中文诊断。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def _extract_cli_check_section(content: str, label: str) -> str:
    match = _CLI_CHECK_SECTION.search(content)
    if match is None:
        raise ValueError(f"{label} 缺少 `## CLI 可用性检查` 章节")
    return match.group(1).strip()


def _validate_canonical_consistency(contents: dict[str, str]) -> None:
    """校验双 Skill 的共用 CLI 检查指引完全一致。"""
    sections = {
        name: _extract_cli_check_section(text, name)
        for name, text in contents.items()
    }
    if len(set(sections.values())) != 1:
        raise ValueError("handoff-save 与 handoff-resume 的 `## CLI 可用性检查` 章节不一致")


def _atomic_write_text(target: Path, content: str) -> None:
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
        stream.write(content)
        temporary = Path(stream.name)
    temporary.replace(target)


def main(argv: Sequence[str] | None = None) -> int:
    """同步双 Skill 分发副本，或只读检查副本是否与 canonical 资源一致。"""
    _configure_utf8_output()
    parser = argparse.ArgumentParser(
        description="同步仓库顶层双 Skill（handoff-save / handoff-resume）分发副本。"
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=DEFAULT_SKILLS_DIR,
        help="输出根目录；默认为 skills/",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只检查目标是否同步，不写入文件",
    )
    args = parser.parse_args(argv)

    canonicals = {
        name: (ASSETS_ROOT / name / "SKILL.md").read_text(encoding="utf-8")
        for name in SKILL_NAMES
    }
    try:
        _validate_canonical_consistency(canonicals)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    skills_root = args.skills_dir.expanduser().resolve()
    drifted: list[Path] = []
    updated: list[Path] = []
    for name, canonical in canonicals.items():
        target = skills_root / name / "SKILL.md"
        current = target.read_text(encoding="utf-8") if target.is_file() else None
        if args.check:
            if current != canonical:
                drifted.append(target)
            continue
        if current != canonical:
            _atomic_write_text(target, canonical)
            updated.append(target)

    if args.check:
        if drifted:
            for target in drifted:
                print(f"Skill 分发副本不同步：{target}", file=sys.stderr)
            return 1
        print(f"双 Skill 分发副本已同步：{skills_root}")
        return 0

    if not updated:
        print(f"双 Skill 分发副本无需更新：{skills_root}")
        return 0
    for target in updated:
        print(f"已同步 Skill 分发副本：{target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
