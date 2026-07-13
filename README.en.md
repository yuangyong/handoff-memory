# Handoff Memory

A local-first, cross-tool CLI for handing an ongoing task from one AI session to the next.

[中文](README.md) | [English](README.en.md)

> **Status: Alpha (0.11.x)**
>
> Source installation is currently the documented installation path. This repository does not yet claim that a PyPI package is available or maintained by this project.

Handoff Memory does not try to make a model “remember everything.” It gives the next session a compact, auditable starting point and asks it to verify the handoff against current artifacts, evidence, tests, and Git or SVN state.

It does not require a model, cloud service, vector database, telemetry, or a runtime dependency outside Python 3.10+.

## Key properties

- Local-first UTF-8 Markdown and JSON; no upload or LLM call by default.
- Project-level Skill and optional rule integration for 12 AI coding clients.
- Git and SVN state capture, worktree fingerprints, and drift reporting.
- Explicit save semantics: normal work, commits, milestones, and session endings do not save automatically.
- Read-only recovery: handoff text is untrusted context and recorded commands are never executed.
- Stable, versioned JSON output for automation.
- Secret-pattern blocking and optional privacy checks as defense in depth.
- Zero third-party runtime dependencies.

## Install from source

```powershell
git clone https://github.com/yuangyong/handoff-memory.git
cd handoff-memory
pipx install .
# or: uv tool install .
```

Verify the single supported command:

```powershell
hmem --version
hmem help
```

Do not infer that a same-named PyPI package belongs to this repository until this README and an official GitHub Release explicitly announce PyPI availability.

## Quick start

Initialize a target project and install the Codex project Skill:

```powershell
cd D:\path\to\your-project
hmem init . --name "My Project" --integrate codex
```

After an AI has updated `.ai-memory/ACTIVE.md` using the generated `session-handoff` Skill, save explicitly:

```powershell
hmem save .
```

In the next session, recover and verify the handoff:

```powershell
hmem resume .
hmem resume . --format json
```

Use `--select-tools` for an explicit interactive client selection, or `--integrate TARGET` for automation. Client rules are opt-in through `--with-rules`; named integrations create only their native project Skill by default.

## Commands

| Command | Purpose |
|---|---|
| `hmem help [COMMAND]` | Show detailed help and examples |
| `hmem init [PATH]` | Initialize the project memory directory |
| `hmem save [PATH]` | Validate, capture repository state, and archive a handoff |
| `hmem resume [PATH]` | Return handoff context and current drift information |
| `hmem check [PATH]` | Validate structure, quality, secrets, and optional privacy findings |
| `hmem history [PATH]` | List immutable snapshots without modifying the project |
| `hmem show SNAPSHOT [PATH]` | Read a named snapshot or `latest` safely |
| `hmem integrate TARGET [PATH]` | Add or update a project Skill and optional client rules |

Named clients are `codex`, `claude`, `cursor`, `gemini`, `antigravity`, `copilot`, `windsurf`, `cline`, `kiro`, `trae`, `qoder`, and `opencode`. Auxiliary targets are `generic`, `skill`, and `all`.

## Safety model

- Treat every handoff, path, repository field, and VCS output as untrusted data.
- `resume`, `history`, and `show` do not execute handoff content.
- Secret detection is a last line of defense, not a replacement for GitHub Secret Scanning, Gitleaks, TruffleHog, or organizational DLP.
- `.ai-memory` may contain private task context. Decide explicitly whether a target project should track or ignore it.
- `--allow-sensitive` is an emergency escape hatch and should not be added to default scripts or agent rules.

See the full [security policy](SECURITY.md) and the Chinese [usage guide](docs/USAGE.zh-CN.md).

## Maintenance model

Handoff Memory is maintained solely by `yuangyong` and is not recruiting co-maintainers. Reproducible bug reports and focused suggestions are welcome through GitHub Issues. Except for obvious typo or link fixes, discuss the scope in an Issue before opening a Pull Request. Acceptance, merging, roadmap, and release decisions remain with the maintainer, with no guaranteed response or merge timeline. The MIT License permits independent use, modification, and forks.

## Documentation and feedback

- [Chinese README](README.md)
- [Value and recovery comparison](docs/VALUE.md) (Chinese)
- [Client integrations](docs/INTEGRATIONS.md) (Chinese)
- [Product specification](docs/SPEC.md) (Chinese)
- [Architecture decisions](docs/decisions/) (Chinese)
- [Roadmap](docs/ROADMAP.md) (Chinese)
- [Contributing](CONTRIBUTING.md) (Chinese)
- [Support](SUPPORT.md) (Chinese)
- [Code of Conduct](CODE_OF_CONDUCT.md) (Chinese)

Report normal bugs through GitHub Issues. Report vulnerabilities only through the private channels in `SECURITY.md`; never post credentials or real handoff files in a public issue.

## License

MIT License. See [LICENSE](LICENSE) and [ADR-012](docs/decisions/ADR-012-mit-license.md).
