import os
import subprocess
import sys
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path

from handoff_memory.integrations import (
    AI_TOOL_TARGETS,
    GLOBAL_SKILL_ROOTS,
    PROJECT_SKILL_ROOTS,
    SKILL_TARGETS,
    TARGETS,
    inspect_skills_status,
    install_skills,
    integrate,
)
from handoff_memory.templates import (
    GENERIC_RULE,
    RESUME_SKILL_TEMPLATE,
    SAVE_SKILL_TEMPLATE,
    SKILL_TEMPLATES,
)


class IntegrationTemplateTests(unittest.TestCase):
    def test_skill_template_is_loaded_from_canonical_package_resource(self) -> None:
        for name, template in SKILL_TEMPLATES.items():
            with self.subTest(skill=name):
                canonical = files("handoff_memory").joinpath("assets", name, "SKILL.md")
                self.assertTrue(canonical.is_file())
                self.assertEqual(canonical.read_text(encoding="utf-8"), template)

    def test_sync_script_generates_and_checks_distributable_copy(self) -> None:
        repository = Path(__file__).parents[1]
        script = repository / "scripts/sync_skills.py"
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp1252"

        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory)
            synchronized = subprocess.run(
                [sys.executable, str(script), "--skills-dir", str(skills_dir)],
                cwd=repository,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
                check=False,
            )
            checked = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--skills-dir",
                    str(skills_dir),
                    "--check",
                ],
                cwd=repository,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
                check=False,
            )

            self.assertEqual(synchronized.returncode, 0, synchronized.stderr)
            for name, template in SKILL_TEMPLATES.items():
                self.assertEqual(
                    (skills_dir / name / "SKILL.md").read_text(encoding="utf-8"),
                    template,
                )
            self.assertEqual(checked.returncode, 0, checked.stderr)

            drifted_file = skills_dir / "handoff-save" / "SKILL.md"
            drifted_file.write_text("已漂移\n", encoding="utf-8")
            drifted = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--skills-dir",
                    str(skills_dir),
                    "--check",
                ],
                cwd=repository,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
                check=False,
            )

            self.assertEqual(drifted.returncode, 1)
            self.assertIn("不同步", drifted.stderr)

    def test_mainstream_ai_tools_have_named_targets(self) -> None:
        expected = {
            "codex",
            "claude",
            "cursor",
            "gemini",
            "antigravity",
            "copilot",
            "windsurf",
            "cline",
            "kiro",
            "trae",
            "qoder",
            "opencode",
        }

        self.assertEqual(set(AI_TOOL_TARGETS), expected)
        self.assertTrue(expected.issubset(TARGETS))

    def test_new_mainstream_integrations_use_official_project_rule_paths(self) -> None:
        expected_paths = {
            "copilot": ".github/copilot-instructions.md",
            "windsurf": ".windsurf/rules/handoff-memory.md",
            "cline": ".clinerules/handoff-memory.md",
            "kiro": ".kiro/steering/handoff-memory.md",
            "trae": ".trae/rules/project_rules.md",
            "qoder": ".qoder/rules/handoff-memory.md",
        }

        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory).resolve()
            for target, relative_path in expected_paths.items():
                with self.subTest(target=target):
                    changed = integrate(project, target, with_rules=True)
                    destination = project / relative_path
                    self.assertIn(destination, changed)
                    self.assertTrue(destination.is_file())
                    self.assertIn("handoff-memory:start", destination.read_text(encoding="utf-8"))
                    self.assertEqual(integrate(project, target, with_rules=True), [])

    def test_named_integrations_create_only_skills_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory).resolve()

            antigravity_changed = integrate(project, "antigravity")
            qoder_changed = integrate(project, "qoder")

            self.assertEqual(
                antigravity_changed,
                [
                    project / ".agents/skills/handoff-save/SKILL.md",
                    project / ".agents/skills/handoff-resume/SKILL.md",
                ],
            )
            self.assertEqual(
                qoder_changed,
                [
                    project / ".qoder/skills/handoff-save/SKILL.md",
                    project / ".qoder/skills/handoff-resume/SKILL.md",
                ],
            )
            self.assertFalse((project / ".agents/rules/handoff-memory.md").exists())
            self.assertFalse((project / ".qoder/rules/handoff-memory.md").exists())

    def test_every_named_ai_tool_creates_skills_in_native_project_directory(self) -> None:
        expected_roots = {
            "codex": ".agents/skills",
            "claude": ".claude/skills",
            "cursor": ".cursor/skills",
            "gemini": ".gemini/skills",
            "antigravity": ".agents/skills",
            "copilot": ".github/skills",
            "windsurf": ".windsurf/skills",
            "cline": ".cline/skills",
            "kiro": ".kiro/skills",
            "trae": ".trae/skills",
            "qoder": ".qoder/skills",
            "opencode": ".opencode/skills",
        }

        self.assertEqual(PROJECT_SKILL_ROOTS, expected_roots)
        # 每个目标使用独立目录，避免共享路径（如 codex 和 antigravity）导致的幂等干扰
        for target, relative_root in expected_roots.items():
            with self.subTest(target=target):
                with tempfile.TemporaryDirectory() as directory:
                    project = Path(directory).resolve()
                    changed = integrate(project, target)
                    for name, template in SKILL_TEMPLATES.items():
                        skill = project / relative_root / name / "SKILL.md"
                        self.assertIn(skill, changed)
                        self.assertEqual(skill.read_text(encoding="utf-8"), template)
                    self.assertEqual(integrate(project, target), [])

    def test_codex_integration_leaves_existing_agents_untouched_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            agents = project / "AGENTS.md"
            agents.write_text("# 原有规则\n", encoding="utf-8")

            integrate(project, "codex")
            integrate(project, "codex")

            content = agents.read_text(encoding="utf-8")
            self.assertEqual(content, "# 原有规则\n")
            self.assertTrue((project / ".agents/skills/handoff-save/SKILL.md").is_file())
            self.assertTrue((project / ".agents/skills/handoff-resume/SKILL.md").is_file())

    def test_codex_rules_option_preserves_and_appends_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            agents = project / "AGENTS.md"
            agents.write_text("# 原有规则\n", encoding="utf-8")

            integrate(project, "codex", with_rules=True)
            integrate(project, "codex", with_rules=True)

            content = agents.read_text(encoding="utf-8")
            self.assertIn("# 原有规则", content)
            self.assertIn("使用 `handoff-save` Skill", content)
            self.assertIn("使用 `handoff-resume` Skill", content)
            self.assertNotIn("开始处理任务前", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)

    def test_codex_rules_option_creates_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "codex", with_rules=True)

            agents = project / "AGENTS.md"
            self.assertTrue(agents.is_file())
            agents_text = agents.read_text(encoding="utf-8")
            self.assertIn("使用 `handoff-save` Skill", agents_text)
            self.assertIn("使用 `handoff-resume` Skill", agents_text)
            self.assertEqual(len(changed), 3)

    def test_antigravity_explicit_rules_create_workspace_rule_and_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "antigravity", with_rules=True)

            rule = project / ".agents/rules/handoff-memory.md"
            save_skill = project / ".agents/skills/handoff-save/SKILL.md"
            resume_skill = project / ".agents/skills/handoff-resume/SKILL.md"
            self.assertTrue(rule.is_file())
            self.assertTrue(save_skill.is_file())
            self.assertTrue(resume_skill.is_file())
            rule_content = rule.read_text(encoding="utf-8")
            self.assertIn("handoff-memory:start", rule_content)
            self.assertIn("使用 `handoff-save` Skill", rule_content)
            self.assertIn("使用 `handoff-resume` Skill", rule_content)
            self.assertNotIn("handoff-memory resume", rule_content)
            self.assertEqual(save_skill.read_text(encoding="utf-8"), SAVE_SKILL_TEMPLATE)
            self.assertEqual(resume_skill.read_text(encoding="utf-8"), RESUME_SKILL_TEMPLATE)
            self.assertEqual(len(changed), 3)
            # 幂等性：再次执行不应产生变更
            self.assertEqual(integrate(project, "antigravity", with_rules=True), [])

    def test_antigravity_preserves_existing_workspace_rule_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            rule = project / ".agents/rules/handoff-memory.md"
            rule.parent.mkdir(parents=True, exist_ok=True)
            rule.write_text("# 用户自定义规则\n", encoding="utf-8")

            integrate(project, "antigravity", with_rules=True)

            content = rule.read_text(encoding="utf-8")
            self.assertIn("用户自定义规则", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)

    def test_antigravity_does_not_touch_agents_md_files(self) -> None:
        """Antigravity 使用 .agents/rules，不应修改 AGENTS.md。"""
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            root_agents = project / "AGENTS.md"
            nested_agents = project / ".agents/AGENTS.md"
            root_agents.write_text("# Codex 规则\n", encoding="utf-8")
            nested_agents.parent.mkdir(parents=True, exist_ok=True)
            nested_agents.write_text("# 其他工具规则\n", encoding="utf-8")

            integrate(project, "antigravity", with_rules=True)

            self.assertEqual(root_agents.read_text(encoding="utf-8"), "# Codex 规则\n")
            self.assertEqual(
                nested_agents.read_text(encoding="utf-8"), "# 其他工具规则\n"
            )
            self.assertTrue((project / ".agents/rules/handoff-memory.md").is_file())

    def test_opencode_creates_project_skill_and_only_adds_agents_rule_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory).resolve()

            changed = integrate(project, "opencode")

            self.assertEqual(
                changed,
                [
                    project / ".opencode/skills/handoff-save/SKILL.md",
                    project / ".opencode/skills/handoff-resume/SKILL.md",
                ],
            )
            self.assertFalse((project / "AGENTS.md").exists())

            changed = integrate(project, "opencode", with_rules=True)

            self.assertEqual(changed, [project / "AGENTS.md"])
            agents_text = (project / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("使用 `handoff-save` Skill", agents_text)
            self.assertIn("使用 `handoff-resume` Skill", agents_text)

    def test_codex_integration_creates_official_project_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "codex")

            save_skill = project / ".agents/skills/handoff-save/SKILL.md"
            resume_skill = project / ".agents/skills/handoff-resume/SKILL.md"
            self.assertFalse((project / "AGENTS.md").exists())
            self.assertTrue(save_skill.is_file())
            self.assertTrue(resume_skill.is_file())
            self.assertEqual(save_skill.read_text(encoding="utf-8"), SAVE_SKILL_TEMPLATE)
            self.assertEqual(resume_skill.read_text(encoding="utf-8"), RESUME_SKILL_TEMPLATE)
            self.assertFalse((project / ".codex/skills/handoff-save/SKILL.md").exists())
            self.assertEqual(len(changed), 2)
            self.assertEqual(integrate(project, "codex"), [])

    def test_codex_integration_shrinks_legacy_managed_rule_to_skill_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            agents = project / "AGENTS.md"
            agents.write_text(GENERIC_RULE + "\n", encoding="utf-8")

            integrate(project, "codex", with_rules=True)

            content = agents.read_text(encoding="utf-8")
            self.assertIn("使用 `handoff-save` Skill", content)
            self.assertIn("使用 `handoff-resume` Skill", content)
            self.assertNotIn("开始处理任务前", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)

    def test_all_can_explicitly_include_every_native_rule(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "all", with_rules=True)

            self.assertTrue((project / "AGENTS.md").is_file())
            self.assertTrue((project / ".agents/rules/handoff-memory.md").is_file())
            self.assertTrue((project / ".qoder/rules/handoff-memory.md").is_file())
            # 11 个唯一项目级 Skill 目录 * 2 个 Skill + 11 个唯一规则文件 = 33
            self.assertEqual(len(changed), 33)

    def test_cursor_integration_preserves_existing_rule_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            cursor_rule = project / ".cursor/rules/handoff-memory.mdc"
            cursor_rule.parent.mkdir(parents=True)
            cursor_rule.write_text("---\nalwaysApply: true\n---\n\n用户自定义规则\n", encoding="utf-8")

            integrate(project, "cursor", with_rules=True)

            content = cursor_rule.read_text(encoding="utf-8")
            self.assertIn("用户自定义规则", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)

    def test_skill_integration_preserves_existing_skill_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            skill = project / ".agents/skills/handoff-save/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("---\nname: handoff-save\n---\n\n用户自定义说明\n", encoding="utf-8")

            integrate(project, "skill")

            content = skill.read_text(encoding="utf-8")
            self.assertIn("用户自定义说明", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)
            self.assertTrue((project / ".agents/skills/handoff-resume/SKILL.md").is_file())

    def test_all_integration_creates_only_named_project_skills_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)

            changed = integrate(project, "all")

            self.assertFalse((project / "AGENTS.md").exists())
            self.assertFalse((project / "CLAUDE.md").exists())
            self.assertFalse((project / "GEMINI.md").exists())
            self.assertFalse((project / ".cursor/rules/handoff-memory.mdc").exists())
            self.assertFalse((project / "AI-HANDOFF.md").exists())
            self.assertTrue((project / ".agents/skills/handoff-save/SKILL.md").is_file())
            self.assertTrue((project / ".agents/skills/handoff-resume/SKILL.md").is_file())
            self.assertFalse((project / ".trae/rules/project_rules.md").exists())
            self.assertFalse((project / ".qoder/rules/handoff-memory.md").exists())
            self.assertTrue((project / ".opencode/skills/handoff-save/SKILL.md").is_file())
            self.assertTrue((project / ".opencode/skills/handoff-resume/SKILL.md").is_file())
            for relative_root in PROJECT_SKILL_ROOTS.values():
                for name in SKILL_TEMPLATES:
                    self.assertTrue((project / relative_root / name / "SKILL.md").is_file())
            # Antigravity 与 Codex 共享 .agents/skills，共 11 个唯一目录 * 2 = 22 个 Skill 文件。
            self.assertEqual(len(changed), 22)

            unchanged = integrate(project, "all")
            self.assertEqual(unchanged, [])

    def test_unknown_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                integrate(Path(directory), "unknown")

    def test_rules_option_rejects_auxiliary_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for target in ("generic", "skill"):
                with self.subTest(target=target):
                    with self.assertRaisesRegex(ValueError, "具名客户端.*all"):
                        integrate(Path(directory), target, with_rules=True)

    def test_distributable_skills_match_generated_skills(self) -> None:
        for name, template in SKILL_TEMPLATES.items():
            with self.subTest(skill=name):
                repository_skill = (
                    Path(__file__).parents[1] / "skills" / name / "SKILL.md"
                ).read_text(encoding="utf-8")
                self.assertEqual(repository_skill, template)

    def test_existing_skill_frontmatter_is_upgraded_with_template(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory).resolve()
            skill = project / ".agents/skills/handoff-save/SKILL.md"
            skill.parent.mkdir(parents=True)
            outdated = SAVE_SKILL_TEMPLATE.replace(
                "description: 仅在用户明确要求",
                "description: 保存、恢复或核验跨会话状态。阶段工作完成时使用。",
                1,
            )
            skill.write_text(outdated, encoding="utf-8")

            changed = integrate(project, "codex")

            self.assertIn(skill, changed)
            self.assertEqual(skill.read_text(encoding="utf-8"), SAVE_SKILL_TEMPLATE)

    def test_skill_upgrade_preserves_unknown_frontmatter_and_user_body(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory).resolve()
            skill = project / ".agents/skills/handoff-save/SKILL.md"
            skill.parent.mkdir(parents=True)
            customized = SAVE_SKILL_TEMPLATE.replace(
                "description: 仅在用户明确要求",
                "description: 旧的触发说明。",
                1,
            ).replace(
                "---\n\n<!-- handoff-memory:start -->",
                "allowed-tools: Read, Bash\nmetadata:\n  owner: local\n---\n\n"
                "用户自定义前言\n\n<!-- handoff-memory:start -->",
                1,
            )
            skill.write_text(customized, encoding="utf-8")

            changed = integrate(project, "codex")

            content = skill.read_text(encoding="utf-8")
            self.assertIn(skill, changed)
            self.assertIn("description: 仅在用户明确要求", content)
            self.assertIn("allowed-tools: Read, Bash\n", content)
            self.assertIn("metadata:\n  owner: local\n", content)
            self.assertIn("用户自定义前言", content)
            self.assertEqual(content.count("handoff-memory:start"), 1)
            self.assertEqual(integrate(project, "codex"), [])

    def test_skill_upgrade_rejects_malformed_frontmatter_or_managed_markers(self) -> None:
        managed = SAVE_SKILL_TEMPLATE[SAVE_SKILL_TEMPLATE.index("<!-- handoff-memory:start -->") :]
        valid_frontmatter = "---\nname: handoff-save\ndescription: 旧说明\n---\n\n"
        malformed_cases = {
            "frontmatter 缺少结束分隔符": (
                "---\nname: handoff-save\ndescription: 旧说明\n\n" + managed
            ),
            "受管区块缺少结束标记": valid_frontmatter
            + "<!-- handoff-memory:start -->\n旧内容\n",
            "受管区块缺少开始标记": valid_frontmatter
            + "旧内容\n<!-- handoff-memory:end -->\n",
            "受管区块重复": valid_frontmatter + managed + "\n" + managed,
            "受管标记顺序交叉": valid_frontmatter
            + "<!-- handoff-memory:end -->\n旧内容\n<!-- handoff-memory:start -->\n",
        }

        for case, original in malformed_cases.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                skill = project / ".agents/skills/handoff-save/SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text(original, encoding="utf-8")

                with self.assertRaises(ValueError):
                    integrate(project, "codex")

                self.assertEqual(skill.read_text(encoding="utf-8"), original)

    def test_rules_do_not_duplicate_active_context_on_resume(self) -> None:
        self.assertIn("输出已经包含 `ACTIVE.md`", GENERIC_RULE)
        self.assertNotIn("并阅读 `.ai-memory/ACTIVE.md`", GENERIC_RULE)

    def test_rules_only_route_explicit_session_handoff_requests(self) -> None:
        self.assertIn("仅当用户明确要求恢复", GENERIC_RULE)
        self.assertIn("仅当用户明确要求保存", GENERIC_RULE)
        self.assertIn("普通任务不得读取或写入", GENERIC_RULE)
        self.assertNotIn("开始处理任务前", GENERIC_RULE)

    def test_skills_separate_write_and_readonly_responsibilities(self) -> None:
        self.assertIn("编码任务检查版本库状态、相关 diff 和实际测试", SAVE_SKILL_TEMPLATE)
        self.assertIn("写作、研究或规划任务", SAVE_SKILL_TEMPLATE)
        self.assertIn("不要自动使用 `--allow-sensitive`", SAVE_SKILL_TEMPLATE)
        self.assertIn("自动执行 `hmem init .`", SAVE_SKILL_TEMPLATE)
        self.assertIn("禁止**运行 `hmem init --force`", SAVE_SKILL_TEMPLATE)
        self.assertNotIn("hmem resume", SAVE_SKILL_TEMPLATE)

        self.assertIn("全流程严格只读", RESUME_SKILL_TEMPLATE)
        self.assertIn("没有可恢复的交接", RESUME_SKILL_TEMPLATE)
        self.assertIn("不得假装恢复成功或自动执行 `hmem init`", RESUME_SKILL_TEMPLATE)
        self.assertIn("当前已核验", RESUME_SKILL_TEMPLATE)
        self.assertIn("交接中记录但本次尚未核验", RESUME_SKILL_TEMPLATE)
        self.assertIn("hmem history . --format json", RESUME_SKILL_TEMPLATE)
        self.assertIn("hmem show latest . --format json", RESUME_SKILL_TEMPLATE)
        self.assertNotIn("hmem save", RESUME_SKILL_TEMPLATE)

    def test_both_skills_share_identical_cli_check_and_strict_triggers(self) -> None:
        for template in SKILL_TEMPLATES.values():
            self.assertIn("只有用户明确要求", template)
            self.assertIn("征得用户明确同意后再执行安装", template)
            self.assertIn("不得静默运行远程安装脚本", template)
            self.assertNotIn("`handoff-memory ", template)
            self.assertNotIn("阶段工作完成时使用", template)
            self.assertNotIn("## 阶段检查点", template)
            self.assertNotIn("完成重要里程碑", template)

    def test_save_skill_requires_actionable_content_in_all_handoff_sections(self) -> None:
        self.assertIn("纯闲聊", SAVE_SKILL_TEMPLATE)
        self.assertIn("可验证的完成标准", SAVE_SKILL_TEMPLATE)
        self.assertIn("只写已经落地的结果", SAVE_SKILL_TEMPLATE)
        self.assertIn("关键上下文与决策", SAVE_SKILL_TEMPLATE)
        self.assertIn("产物与变更", SAVE_SKILL_TEMPLATE)
        self.assertIn("测试、来源或人工检查", SAVE_SKILL_TEMPLATE)
        self.assertIn("分别说明阻塞与风险", SAVE_SKILL_TEMPLATE)
        self.assertIn("可直接执行的动作和完成条件", SAVE_SKILL_TEMPLATE)
        self.assertIn("不要在正文中记录其自身哈希", SAVE_SKILL_TEMPLATE)

    def test_skill_targets_exclude_generic_and_map_all_global_roots(self) -> None:
        self.assertNotIn("generic", SKILL_TARGETS)
        self.assertIn("skill", SKILL_TARGETS)
        self.assertIn("all", SKILL_TARGETS)
        expected_global = {
            "codex": ".agents/skills",
            "claude": ".claude/skills",
            "cursor": ".cursor/skills",
            "gemini": ".gemini/skills",
            "antigravity": ".gemini/config/skills",
            "copilot": ".copilot/skills",
            "windsurf": ".codeium/windsurf/skills",
            "cline": ".cline/skills",
            "kiro": ".kiro/skills",
            "trae": ".trae/skills",
            "qoder": ".qoder/skills",
            "opencode": ".config/opencode/skills",
            "skill": ".agents/skills",
        }
        self.assertEqual(GLOBAL_SKILL_ROOTS, expected_global)

    def test_install_skills_globally_writes_only_skills_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as project_dir:
            home = Path(home_dir).resolve()
            project = Path(project_dir).resolve()

            result = install_skills("all", path=project, global_install=True, home=home)

            # 12 个具名客户端在全局各自对应独立路径，共 12 * 2 = 24 个 Skill 文件
            self.assertEqual(len(result.changed), 24)
            self.assertFalse((project / ".ai-memory").exists())
            self.assertFalse((home / "AGENTS.md").exists())
            self.assertFalse((home / "CLAUDE.md").exists())
            for target in AI_TOOL_TARGETS:
                root = home / GLOBAL_SKILL_ROOTS[target]
                for name, template in SKILL_TEMPLATES.items():
                    self.assertEqual((root / name / "SKILL.md").read_text(encoding="utf-8"), template)

            rerun = install_skills("all", path=project, global_install=True, home=home)
            self.assertEqual(rerun.changed, ())

    def test_install_skills_rejects_generic_and_warns_legacy_without_deleting(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir:
            home = Path(home_dir).resolve()
            legacy = home / ".claude/skills/session-handoff/SKILL.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("旧版自定义内容\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                install_skills("generic", global_install=True, home=home)

            result = install_skills("claude", global_install=True, home=home)
            self.assertEqual(len(result.changed), 2)
            self.assertEqual(result.legacy_skills, (legacy,))
            self.assertEqual(legacy.read_text(encoding="utf-8"), "旧版自定义内容\n")

    def test_inspect_skills_status_is_readonly_and_detects_synced_outdated_and_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as project_dir:
            home = Path(home_dir).resolve()
            project = Path(project_dir).resolve()

            install_skills("claude", global_install=True, home=home)
            save_global = home / ".claude/skills/handoff-save/SKILL.md"
            # 受管区块外保留自定义内容仍视为 synced
            save_global.write_text(
                save_global.read_text(encoding="utf-8") + "\n个人补充说明\n",
                encoding="utf-8",
            )
            # 项目级写入过时版 + 旧版残留
            proj_save = project / ".agents/skills/handoff-save/SKILL.md"
            proj_save.parent.mkdir(parents=True)
            proj_save.write_text(
                SAVE_SKILL_TEMPLATE.replace("description: 仅在用户明确要求", "description: 旧说明", 1),
                encoding="utf-8",
            )
            proj_legacy = project / ".agents/skills/session-handoff/SKILL.md"
            proj_legacy.parent.mkdir(parents=True)
            proj_legacy.write_text("legacy\n", encoding="utf-8")

            report = inspect_skills_status(project, home=home)

            global_claude = next(e for e in report.entries if e.scope == "global" and e.target == "claude")
            self.assertEqual(global_claude.skills, {"handoff-save": "synced", "handoff-resume": "synced"})
            proj_codex = next(e for e in report.entries if e.scope == "project" and e.target == "codex")
            self.assertEqual(proj_codex.skills, {"handoff-save": "outdated", "handoff-resume": "missing"})
            self.assertEqual(report.legacy_skills, (proj_legacy,))
            self.assertTrue(proj_legacy.exists())
