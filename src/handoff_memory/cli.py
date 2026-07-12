"""Handoff Memory 命令行接口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .core import (
    HARD_ACTIVE_LIMIT,
    HandoffError,
    archive_active,
    initialize_project,
    inspect_project,
    render_resume,
)
from .integrations import TARGETS, integrate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="handoff-memory",
        description="本地优先、跨 AI 工具的会话交接记忆 CLI",
    )
    parser.add_argument("--version", action="version", version=f"handoff-memory {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="初始化项目记忆目录")
    init.add_argument("path", nargs="?", default=".")
    init.add_argument("--name", help="项目显示名称")
    init.add_argument("--force", action="store_true", help="覆盖 Handoff Memory 自有初始化文件")
    init.add_argument("--integrate", choices=TARGETS, help="同时生成指定 AI 工具接入规则")

    save = subparsers.add_parser("save", help="校验并归档当前交接")
    save.add_argument("path", nargs="?", default=".")
    save.add_argument("--from", dest="source", help="先从 UTF-8 文件读取交接；使用 - 表示标准输入")
    save.add_argument("--allow-sensitive", action="store_true", help="明确允许保存疑似敏感内容（不推荐）")

    resume = subparsers.add_parser("resume", help="输出供新会话读取的恢复上下文")
    resume.add_argument("path", nargs="?", default=".")
    resume.add_argument("--format", choices=("markdown", "json"), default="markdown")

    check = subparsers.add_parser("check", help="检查记忆目录、格式与安全状态")
    check.add_argument("path", nargs="?", default=".")

    adapter = subparsers.add_parser("integrate", help="生成 AI 工具接入规则")
    adapter.add_argument("target", choices=TARGETS)
    adapter.add_argument("path", nargs="?", default=".")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """运行 CLI；预期的用户错误不输出堆栈。"""
    _configure_utf8_stdio()
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.command == "init":
            result = initialize_project(args.path, name=args.name, force=args.force)
            print(f"已{'创建' if result.created else '检查'}记忆目录：{Path(args.path).resolve() / '.ai-memory'}")
            if args.integrate:
                changed = integrate(args.path, args.integrate)
                print(f"已更新 {len(changed)} 个 AI 接入文件")
            return 0
        if args.command == "save":
            content = _read_source(args.source) if args.source else None
            result = archive_active(args.path, content=content, allow_sensitive=args.allow_sensitive)
            print(f"已保存交接快照：{result.archive_path}")
            for warning in result.warnings:
                print(f"提示：{warning}")
            return 0
        if args.command == "resume":
            print(render_resume(inspect_project(args.path), output_format=args.format), end="")
            return 0
        if args.command == "check":
            report = inspect_project(args.path)
            problems = list(report.validation_errors)
            problems.extend(f"疑似 {item.kind}（第 {item.line} 行）" for item in report.secret_findings)
            if problems:
                print("检查失败：", file=sys.stderr)
                for problem in problems:
                    print(f"- {problem}", file=sys.stderr)
                return 2
            for warning in report.quality_warnings:
                print(f"提示：{warning}")
            print("检查通过：记忆格式有效，未发现高置信度敏感信息。")
            return 0
        if args.command == "integrate":
            changed = integrate(args.path, args.target)
            print(f"已更新 {len(changed)} 个 AI 接入文件")
            return 0
        parser.error("缺少命令")
        return 2
    except (HandoffError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("错误：操作已取消", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"内部错误：{type(exc).__name__}：{exc}", file=sys.stderr)
        return 1


def _read_source(source: str) -> str:
    if source == "-":
        content = sys.stdin.read(HARD_ACTIVE_LIMIT + 1)
        if len(content.encode("utf-8")) > HARD_ACTIVE_LIMIT:
            raise HandoffError("标准输入超过 64KB 限制")
        return content
    path = Path(source).expanduser().resolve()
    if not path.is_file() or path.stat().st_size > HARD_ACTIVE_LIMIT:
        raise HandoffError(f"交接来源不存在或超过 64KB：{path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise HandoffError(f"交接来源必须是 UTF-8 文本：{path}") from exc


def _configure_utf8_stdio() -> None:
    """统一 Windows 旧代码页与管道场景下的 CLI 输出编码。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
