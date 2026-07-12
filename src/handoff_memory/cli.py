"""Handoff Memory 命令行接口。"""

from __future__ import annotations

import argparse
import re
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
from .integrations import AI_TOOL_TARGETS, TARGETS, integrate


AI_TOOL_LABELS = {
    "codex": "OpenAI Codex",
    "claude": "Claude Code",
    "cursor": "Cursor",
    "gemini": "Gemini CLI",
    "antigravity": "Antigravity IDE",
    "copilot": "GitHub Copilot",
    "windsurf": "Windsurf",
    "cline": "Cline",
    "kiro": "Kiro",
    "trae": "TRAE",
    "qoder": "Qoder",
    "opencode": "OpenCode",
}

_COMMANDS = ("init", "save", "resume", "check", "integrate")
_FORMATTER = argparse.RawDescriptionHelpFormatter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="handoff-memory",
        description="本地优先、跨 AI 工具的会话交接记忆 CLI",
        formatter_class=_FORMATTER,
        epilog="""常用示例：
  handoff-memory init . --select-tools
  handoff-memory save .
  handoff-memory resume .
  handoff-memory help init

使用 `handoff-memory help [COMMAND]` 查看某个命令的详细说明。""",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"handoff-memory {__version__}",
        help="显示版本并退出",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser(
        "init",
        help="初始化记忆目录并可选接入 AI 工具",
        description="初始化项目的会话交接目录，并可通过参数或交互选择列表接入 AI 编程工具。",
        formatter_class=_FORMATTER,
        epilog="""示例：
  handoff-memory init . --select-tools
  handoff-memory init . --name "示例项目" --integrate codex
  handoff-memory init . --integrate codex --with-agents-rule

`--select-tools` 是显式交互模式，支持多选；脚本和 CI 请使用 `--integrate`。""",
    )
    init.add_argument("path", nargs="?", default=".", help="项目目录，默认为当前目录")
    init.add_argument("--name", help="项目显示名称")
    init.add_argument("--force", action="store_true", help="覆盖 Handoff Memory 自有初始化文件")
    integration_mode = init.add_mutually_exclusive_group()
    integration_mode.add_argument(
        "--integrate",
        choices=TARGETS,
        help="非交互接入一个 AI 工具；all 表示全部已支持目标",
    )
    integration_mode.add_argument(
        "--select-tools",
        action="store_true",
        help="显示 AI 工具列表并交互多选，直接回车可跳过",
    )
    init.add_argument(
        "--with-agents-rule",
        action="store_true",
        help="为 codex/opencode/all 创建或更新 AGENTS.md Skill 路由",
    )

    save = subparsers.add_parser(
        "save",
        help="校验并归档当前交接",
        description="校验 ACTIVE.md，采集 Git/SVN 状态并创建只增不改的会话快照。",
        formatter_class=_FORMATTER,
        epilog="""示例：
  handoff-memory save .
  handoff-memory save . --from handoff.md
  Get-Content -Raw handoff.md | handoff-memory save . --from -""",
    )
    save.add_argument("path", nargs="?", default=".", help="项目目录，默认为当前目录")
    save.add_argument("--from", dest="source", help="先从 UTF-8 文件读取交接；使用 - 表示标准输入")
    save.add_argument("--allow-sensitive", action="store_true", help="明确允许保存疑似敏感内容（不推荐）")
    save.add_argument(
        "--allow-large",
        action="store_true",
        help="明确允许保存 64KB 到 256KB 的大型交接",
    )

    resume = subparsers.add_parser(
        "resume",
        help="输出供新会话读取的恢复上下文",
        description="读取活动交接并核对当前 Git/SVN 状态，输出可直接提供给新会话的上下文。",
        formatter_class=_FORMATTER,
        epilog="""示例：
  handoff-memory resume .
  handoff-memory resume . --format json""",
    )
    resume.add_argument("path", nargs="?", default=".", help="项目目录，默认为当前目录")
    resume.add_argument("--format", choices=("markdown", "json"), default="markdown")

    check = subparsers.add_parser(
        "check",
        help="检查记忆目录、格式与安全状态",
        description="只读检查交接格式、大小、质量提示和高置信度敏感信息。",
        formatter_class=_FORMATTER,
        epilog="示例：\n  handoff-memory check .",
    )
    check.add_argument("path", nargs="?", default=".", help="项目目录，默认为当前目录")

    adapter = subparsers.add_parser(
        "integrate",
        help="生成或更新 AI 工具规则与项目级 Skill",
        description="为指定客户端生成幂等规则和原生项目级 Skill；保留受管区块外的原有内容。",
        formatter_class=_FORMATTER,
        epilog="""主要目标与项目级 Skill：
  codex        OpenAI Codex      .agents/skills/session-handoff/SKILL.md
  opencode     OpenCode          .opencode/skills/session-handoff/SKILL.md
  claude       Claude Code       .claude/skills/session-handoff/SKILL.md
  cursor       Cursor            .cursor/skills/session-handoff/SKILL.md
  gemini       Gemini CLI        .gemini/skills/session-handoff/SKILL.md
  antigravity  Antigravity IDE   .agents/skills/session-handoff/SKILL.md
  copilot      GitHub Copilot    .github/skills/session-handoff/SKILL.md
  windsurf     Windsurf          .windsurf/skills/session-handoff/SKILL.md
  cline        Cline             .cline/skills/session-handoff/SKILL.md
  kiro         Kiro              .kiro/skills/session-handoff/SKILL.md
  trae         TRAE              .trae/skills/session-handoff/SKILL.md
  qoder        Qoder             .qoder/skills/session-handoff/SKILL.md

规则输出：
  claude CLAUDE.md；cursor .cursor/rules/handoff-memory.mdc；gemini GEMINI.md
  antigravity .agents/rules/handoff-memory.md
  copilot .github/copilot-instructions.md；windsurf .windsurf/rules/handoff-memory.md
  cline .clinerules/handoff-memory.md；kiro .kiro/steering/handoff-memory.md
  trae .trae/rules/project_rules.md；qoder .qoder/rules/handoff-memory.md
  Codex/OpenCode 的 AGENTS.md 路由需显式开启。

其他目标：generic 生成通用规则，skill 生成可移植 Skill，all 生成全部适配。

示例：
  handoff-memory integrate copilot .
  handoff-memory integrate codex . --with-agents-rule
  handoff-memory integrate all .""",
    )
    adapter.add_argument("target", choices=TARGETS, help="客户端短名称或辅助目标")
    adapter.add_argument("path", nargs="?", default=".", help="项目目录，默认为当前目录")
    adapter.add_argument(
        "--with-agents-rule",
        action="store_true",
        help="为 codex/opencode/all 创建或更新 AGENTS.md Skill 路由",
    )

    help_command = subparsers.add_parser(
        "help",
        help="显示总体帮助或指定命令的详细帮助",
        description="显示总体帮助，或查看某个命令的参数、默认行为与示例。",
        formatter_class=_FORMATTER,
    )
    help_command.add_argument("topic", nargs="?", choices=_COMMANDS, metavar="COMMAND")
    for command_parser in (
        parser,
        init,
        save,
        resume,
        check,
        adapter,
        help_command,
    ):
        _localize_help(command_parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """运行 CLI；预期的用户错误不输出堆栈。"""
    _configure_utf8_stdio()
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.command == "help":
            _print_help(parser, args.topic)
            return 0
        if args.command == "init":
            selected_targets = (
                _select_ai_tools() if args.select_tools else ((args.integrate,) if args.integrate else ())
            )
            if args.with_agents_rule and not any(
                target in {"codex", "opencode", "all"} for target in selected_targets
            ):
                raise HandoffError(
                    "--with-agents-rule 必须选择 codex/opencode，或与 --integrate all 一起使用"
                )
            result = initialize_project(args.path, name=args.name, force=args.force)
            print(f"已{'创建' if result.created else '检查'}记忆目录：{Path(args.path).resolve() / '.ai-memory'}")
            if selected_targets:
                changed = []
                for target in selected_targets:
                    changed.extend(
                        integrate(
                            args.path,
                            target,
                            with_agents_rule=(
                                args.with_agents_rule
                                and target in {"codex", "opencode", "all"}
                            ),
                        )
                    )
                print(f"已更新 {len(changed)} 个 AI 接入文件")
            elif args.select_tools:
                print("已跳过 AI 工具接入")
            return 0
        if args.command == "save":
            content = _read_source(args.source) if args.source else None
            result = archive_active(
                args.path,
                content=content,
                allow_sensitive=args.allow_sensitive,
                allow_large=args.allow_large,
            )
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
            changed = integrate(
                args.path,
                args.target,
                with_agents_rule=args.with_agents_rule,
            )
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
        try:
            content = sys.stdin.read(HARD_ACTIVE_LIMIT + 1)
        except UnicodeError as exc:
            raise HandoffError("标准输入必须是 UTF-8 文本") from exc
        if len(content.encode("utf-8")) > HARD_ACTIVE_LIMIT:
            raise HandoffError("标准输入超过 256KB 限制")
        return content
    path = Path(source).expanduser().resolve()
    if not path.is_file() or path.stat().st_size > HARD_ACTIVE_LIMIT:
        raise HandoffError(f"交接来源不存在或超过 256KB：{path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise HandoffError(f"交接来源必须是 UTF-8 文本：{path}") from exc


def _select_ai_tools() -> tuple[str, ...]:
    """显示零依赖多选列表；返回按菜单顺序去重后的接入目标。"""
    print("请选择需要接入的 AI 编程工具（可多选）：")
    for index, target in enumerate(AI_TOOL_TARGETS, start=1):
        print(f"  {index:>2}. {AI_TOOL_LABELS[target]} ({target})")
    print("输入编号并用逗号分隔；输入 all 选择全部；直接回车跳过。")
    while True:
        try:
            answer = input("请选择：").strip().lower()
        except EOFError as exc:
            raise HandoffError("无法读取交互输入；非交互环境请使用 --integrate") from exc
        if not answer:
            return ()
        if answer in {"all", "a"}:
            return AI_TOOL_TARGETS
        parts = [part for part in re.split(r"[,，\s]+", answer) if part]
        if parts and all(part.isdigit() for part in parts):
            indexes = [int(part) for part in parts]
            if all(1 <= index <= len(AI_TOOL_TARGETS) for index in indexes):
                selected = set(indexes)
                return tuple(
                    target
                    for index, target in enumerate(AI_TOOL_TARGETS, start=1)
                    if index in selected
                )
        print(f"无效选择：请输入 1–{len(AI_TOOL_TARGETS)} 的编号、all，或直接回车。")


def _print_help(parser: argparse.ArgumentParser, topic: str | None) -> None:
    if topic is None:
        parser.print_help()
        return
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            action.choices[topic].print_help()
            return
    raise RuntimeError("CLI 子命令帮助不可用")


def _localize_help(parser: argparse.ArgumentParser) -> None:
    """让 argparse 的固定帮助标签与项目中文 CLI 保持一致。"""
    parser._positionals.title = "位置参数"
    parser._optionals.title = "选项"
    for action in parser._actions:
        if action.dest == "help":
            action.help = "显示帮助并退出"


def _configure_utf8_stdio() -> None:
    """统一 Windows 旧代码页与管道场景下的 CLI 输出编码。"""
    reconfigure_stdin = getattr(sys.stdin, "reconfigure", None)
    if callable(reconfigure_stdin):
        reconfigure_stdin(encoding="utf-8", errors="strict")
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
