"""Handoff Memory 命令行接口。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from . import __version__
from .core import (
    HARD_ACTIVE_LIMIT,
    HandoffError,
    archive_active,
    initialize_project,
    inspect_project,
    list_history,
    render_history,
    render_resume,
    render_snapshot,
    show_snapshot,
)
from .integrations import AI_TOOL_TARGETS, TARGETS, integrate
from .security import find_personal_information, find_secrets


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

_COMMANDS = ("init", "save", "resume", "check", "history", "show", "integrate")
_FORMATTER = argparse.RawDescriptionHelpFormatter
_CANONICAL_PROGRAM = "hmem"


def build_parser() -> argparse.ArgumentParser:
    program_name = _CANONICAL_PROGRAM
    parser = argparse.ArgumentParser(
        prog=program_name,
        description="本地优先、跨 AI 工具的会话交接记忆 CLI",
        formatter_class=_FORMATTER,
        epilog=f"""常用示例：
  {program_name} init . --select-tools
  {program_name} save .
  {program_name} resume .
  {program_name} help init

使用 `{program_name} help [COMMAND]` 查看某个命令的详细说明。""",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{program_name} {__version__}",
        help="显示版本并退出",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser(
        "init",
        help="初始化记忆目录并可选接入 AI 工具",
        description="初始化项目的会话交接目录，并可通过参数或交互选择列表接入 AI 编程工具。",
        formatter_class=_FORMATTER,
        epilog=f"""示例：
  {program_name} init . --select-tools
  {program_name} init . --name "示例项目" --integrate codex
  {program_name} init . --integrate codex --with-rules

`--select-tools` 是显式交互模式，支持多选；脚本和 CI 请使用 `--integrate`。""",
    )
    init.add_argument("path", nargs="?", default=".", help="项目目录，默认为当前目录")
    init.add_argument("--name", help="项目显示名称")
    init.add_argument("--force", action="store_true", help="覆盖 Handoff Memory 自有初始化文件")
    integration_mode = init.add_mutually_exclusive_group()
    integration_mode.add_argument(
        "--integrate",
        choices=TARGETS,
        help="非交互接入一个 AI 工具；all 表示全部具名客户端",
    )
    integration_mode.add_argument(
        "--select-tools",
        action="store_true",
        help="显示 AI 工具列表并交互多选，直接回车可跳过",
    )
    init.add_argument(
        "--with-rules",
        action="store_true",
        help="显式生成所选客户端规则；默认只生成项目级 Skill",
    )

    save = subparsers.add_parser(
        "save",
        help="校验并归档当前交接",
        description="校验 ACTIVE.md，采集 Git/SVN 状态并创建只增不改的会话快照。",
        formatter_class=_FORMATTER,
        epilog=f"""示例：
  {program_name} save .
  {program_name} save . --from handoff.md
  Get-Content -Raw handoff.md | {program_name} save . --from -""",
    )
    save.add_argument("path", nargs="?", default=".", help="项目目录，默认为当前目录")
    save.add_argument("--from", dest="source", help="先从 UTF-8 文件读取交接；使用 - 表示标准输入")
    save.add_argument("--allow-sensitive", action="store_true", help="明确允许保存疑似敏感内容（不推荐）")
    save.add_argument(
        "--allow-large",
        action="store_true",
        help="明确允许保存 64KB 到 256KB 的大型交接",
    )
    save.add_argument("--format", choices=("text", "json"), default="text")

    resume = subparsers.add_parser(
        "resume",
        help="输出供新会话读取的恢复上下文",
        description="读取活动交接并核对当前 Git/SVN 状态，输出可直接提供给新会话的上下文。",
        formatter_class=_FORMATTER,
        epilog=f"""示例：
  {program_name} resume .
  {program_name} resume . --format json""",
    )
    resume.add_argument("path", nargs="?", default=".", help="项目目录，默认为当前目录")
    resume.add_argument("--format", choices=("markdown", "json"), default="markdown")

    check = subparsers.add_parser(
        "check",
        help="检查记忆目录、格式与安全状态",
        description="只读检查交接格式、大小、质量提示和高置信度敏感信息。",
        formatter_class=_FORMATTER,
        epilog=f"示例：\n  {program_name} check .",
    )
    check.add_argument("path", nargs="?", default=".", help="项目目录，默认为当前目录")
    check.add_argument("--format", choices=("text", "json"), default="text")
    check.add_argument(
        "--strict", action="store_true", help="把质量或隐私提示视为检查失败"
    )
    check.add_argument(
        "--privacy", action="store_true", help="额外扫描基础个人信息类型（可能误报）"
    )

    history_parser = subparsers.add_parser(
        "history",
        help="只读列出历史快照及诊断",
        description="按保存时间列出历史快照，并识别损坏或疑似未完成的快照。",
        formatter_class=_FORMATTER,
        epilog=f"示例：\n  {program_name} history .\n  {program_name} history . --format json",
    )
    history_parser.add_argument(
        "path", nargs="?", default=".", help="项目目录，默认为当前目录"
    )
    history_parser.add_argument(
        "--format", choices=("markdown", "json"), default="markdown"
    )

    show_parser = subparsers.add_parser(
        "show",
        help="只读查看一个历史快照",
        description="按安全快照名称或 latest 查看归档正文与元数据。",
        formatter_class=_FORMATTER,
        epilog=f"示例：\n  {program_name} show latest .\n  {program_name} show 20260712-120000.md . --format json",
    )
    show_parser.add_argument("snapshot", metavar="SNAPSHOT", help="安全快照 basename 或 latest")
    show_parser.add_argument(
        "path", nargs="?", default=".", help="项目目录，默认为当前目录"
    )
    show_parser.add_argument(
        "--format", choices=("markdown", "json"), default="markdown"
    )

    adapter = subparsers.add_parser(
        "integrate",
        help="生成项目级 Skill，并可显式生成客户端规则",
        description="默认只生成原生项目级 Skill；指定 --with-rules 后生成幂等客户端规则。",
        formatter_class=_FORMATTER,
        epilog=f"""主要目标与项目级 Skill：
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

使用 --with-rules 时的规则输出：
  claude CLAUDE.md；cursor .cursor/rules/handoff-memory.mdc；gemini GEMINI.md
  antigravity .agents/rules/handoff-memory.md
  copilot .github/copilot-instructions.md；windsurf .windsurf/rules/handoff-memory.md
  cline .clinerules/handoff-memory.md；kiro .kiro/steering/handoff-memory.md
  trae .trae/rules/project_rules.md；qoder .qoder/rules/handoff-memory.md
  codex/opencode AGENTS.md

规则默认不生成；generic 是只生成通用规则的独立辅助目标。

其他目标：generic 生成通用规则，skill 生成可移植 Skill，all 生成全部具名客户端 Skill。

示例：
  {program_name} integrate copilot .
  {program_name} integrate qoder . --with-rules
  {program_name} integrate all . --with-rules""",
    )
    adapter.add_argument("target", choices=TARGETS, help="客户端短名称或辅助目标")
    adapter.add_argument("path", nargs="?", default=".", help="项目目录，默认为当前目录")
    adapter.add_argument(
        "--with-rules",
        action="store_true",
        help="显式生成所选客户端规则；默认只生成项目级 Skill",
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
        history_parser,
        show_parser,
        adapter,
        help_command,
    ):
        _localize_help(command_parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """运行 CLI；预期的用户错误不输出堆栈。"""
    _configure_utf8_stdio()
    parser = build_parser()
    args = None
    try:
        args = parser.parse_args(argv)
        if args.command == "help":
            _print_help(parser, args.topic)
            return 0
        if args.command == "init":
            selected_targets = (
                _select_ai_tools() if args.select_tools else ((args.integrate,) if args.integrate else ())
            )
            if args.with_rules and (
                not selected_targets
                or any(target in {"generic", "skill"} for target in selected_targets)
            ):
                raise HandoffError(
                    "--with-rules 必须与具名客户端、--select-tools 或 --integrate all 一起使用"
                )
            init_result = initialize_project(args.path, name=args.name, force=args.force)
            print(f"已{'创建' if init_result.created else '检查'}记忆目录：{Path(args.path).resolve() / '.ai-memory'}")
            if selected_targets:
                changed = []
                for target in selected_targets:
                    changed.extend(
                        integrate(
                            args.path,
                            target,
                            with_rules=args.with_rules,
                        )
                    )
                print(f"已更新 {len(changed)} 个 AI 接入文件")
            elif args.select_tools:
                print("已跳过 AI 工具接入")
            return 0
        if args.command == "save":
            content = _read_source(args.source) if args.source else None
            archive_result = archive_active(
                args.path,
                content=content,
                allow_sensitive=args.allow_sensitive,
                allow_large=args.allow_large,
            )
            if args.format == "json":
                _print_json(
                    {
                        "schema_version": 1,
                        "ok": True,
                        "archive": str(archive_result.archive_path),
                        "saved_at": archive_result.saved_at,
                        "active_sha256": archive_result.active_sha256,
                        "repository": archive_result.repository_state.to_dict(),
                        "warnings": list(archive_result.warnings),
                    }
                )
            else:
                print(f"已保存交接快照：{archive_result.archive_path}")
                for warning in archive_result.warnings:
                    print(f"提示：{warning}")
            return 0
        if args.command == "resume":
            print(render_resume(inspect_project(args.path), output_format=args.format), end="")
            return 0
        if args.command == "check":
            report = inspect_project(args.path)
            problems = list(report.validation_errors)
            problems.extend(f"疑似 {item.kind}（第 {item.line} 行）" for item in report.secret_findings)
            active_privacy_findings = (
                find_personal_information(report.active) if args.privacy else []
            )
            repository_payload = report.repository.to_dict()
            serialized_repository = json.dumps(
                repository_payload, ensure_ascii=False, sort_keys=True, indent=2
            )
            repository_secret_findings = find_secrets(serialized_repository)
            saved_repository = report.config.get("last_saved_repository")
            if not isinstance(saved_repository, dict):
                saved_repository = report.config.get("last_saved_git")
            serialized_saved_repository = json.dumps(
                saved_repository if isinstance(saved_repository, dict) else {},
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            serialized_drift = json.dumps(
                list(report.drift), ensure_ascii=False, indent=2
            )
            repository_privacy_findings = (
                find_personal_information(serialized_repository)
                if args.privacy
                else []
            )
            saved_repository_privacy_findings = (
                find_personal_information(serialized_saved_repository)
                if args.privacy
                else []
            )
            drift_privacy_findings = (
                find_personal_information(serialized_drift) if args.privacy else []
            )
            privacy_findings = [
                {**asdict(item), "source": "active"}
                for item in active_privacy_findings
            ] + [
                {**asdict(item), "source": "repository"}
                for item in repository_privacy_findings
            ] + [
                {**asdict(item), "source": "saved_repository"}
                for item in saved_repository_privacy_findings
            ] + [
                {**asdict(item), "source": "drift"}
                for item in drift_privacy_findings
            ]
            if (
                repository_secret_findings
                or repository_privacy_findings
                or saved_repository_privacy_findings
            ):
                repository_payload = {
                    "provider": report.repository.provider,
                    "redacted": True,
                    "note": "仓库元数据包含敏感或个人信息，已在检查输出中隐藏",
                }
            drift_payload = list(report.drift)
            if drift_privacy_findings:
                drift_payload = ["仓库漂移包含个人信息，已隐藏具体值"]
            warnings = list(report.quality_warnings)
            warnings.extend(
                f"疑似 {item['kind']}（{item['source']} 第 {item['line']} 行）"
                for item in privacy_findings
            )
            ok = not problems and (not args.strict or not warnings)
            if args.format == "json":
                _print_json(
                    {
                        "schema_version": 1,
                        "ok": ok,
                        "strict": args.strict,
                        "privacy": args.privacy,
                        "problems": problems,
                        "warnings": warnings,
                        "privacy_findings": privacy_findings,
                        "repository": repository_payload,
                        "drift": drift_payload,
                        "active_sha256": report.active_sha256,
                        "last_saved_active_sha256": report.saved_active_sha256,
                        "active_matches_saved": report.active_matches_saved,
                    }
                )
                return 0 if ok else 2
            if problems:
                print("检查失败：", file=sys.stderr)
                for problem in problems:
                    print(f"- {problem}", file=sys.stderr)
                return 2
            if args.strict and warnings:
                print("严格检查失败：", file=sys.stderr)
                for warning in warnings:
                    print(f"- {warning}", file=sys.stderr)
                return 2
            for warning in warnings:
                print(f"提示：{warning}")
            print("检查通过：记忆格式有效，未发现高置信度敏感信息。")
            return 0
        if args.command == "history":
            print(
                render_history(list_history(args.path), output_format=args.format),
                end="",
            )
            return 0
        if args.command == "show":
            print(
                render_snapshot(
                    show_snapshot(args.path, args.snapshot),
                    output_format=args.format,
                ),
                end="",
            )
            return 0
        if args.command == "integrate":
            changed = integrate(
                args.path,
                args.target,
                with_rules=args.with_rules,
            )
            print(f"已更新 {len(changed)} 个 AI 接入文件")
            return 0
        parser.error("缺少命令")
        return 2
    except (HandoffError, ValueError) as exc:
        if _json_requested(args):
            _print_json(
                {
                    "schema_version": 1,
                    "ok": False,
                    "error": {"code": "HANDOFF_ERROR", "message": str(exc)},
                }
            )
        else:
            print(f"错误：{exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("错误：操作已取消", file=sys.stderr)
        return 130
    except Exception as exc:
        if _json_requested(args):
            _print_json(
                {
                    "schema_version": 1,
                    "ok": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"{type(exc).__name__}：{exc}",
                    },
                }
            )
        else:
            print(f"内部错误：{type(exc).__name__}：{exc}", file=sys.stderr)
        return 1


def _json_requested(args: argparse.Namespace | None) -> bool:
    return args is not None and getattr(args, "format", None) == "json"


def _print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


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
