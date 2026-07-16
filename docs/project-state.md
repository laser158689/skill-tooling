# Project State

## Purpose

`skill-tooling` is intended to be the central tooling repository for a multi-tool skill ecosystem.

The core product idea is:

- Each skill family lives in its own Git repository.
- Family authors write canonical skill content once.
- `skill-tooling` validates that family repo against a shared contract.
- `skill-tooling` generates target-specific outputs for multiple AI tools.
- `skill-tooling` can optionally publish those generated outputs into each configured tool environment.

The intended user experience is deliberately simple:

- One create command to start a family repo
- One deploy command to validate, build, and publish it
- No always-on service, daemon, or server requirement

The long-term objective is one command that takes a family repo and deploys it everywhere:

```bash
scripts/skill-deploy --repo owner/family --publish --config path/to/publish-config.json
```

## Current State

### Repository Role

This repository is currently the tooling hub, not a family repo.

It contains:

- Shell entrypoints:
  - `scripts/create-family`
  - `scripts/validate-family`
  - `scripts/skill-deploy`
- Python implementation:
  - `scripts/skill_tooling.py`
- Contract docs:
  - [family-repo-contract.md](family-repo-contract.md)
  - [family-schema.md](family-schema.md)
  - [target-bundles.md](target-bundles.md)
  - [deployment-matrix.md](deployment-matrix.md)
- Schema:
  - [schemas/family.schema.json](/Users/brianraney/Documents/GitHub/skill-tooling/schemas/family.schema.json)
- Example publisher config:
  - [publish-config.json](/Users/brianraney/Documents/GitHub/skill-tooling/publish-config.json)
  - [examples/publish-config.json](/Users/brianraney/Documents/GitHub/skill-tooling/examples/publish-config.json)
- Smoke test and CI:
  - [tests/smoke.sh](/Users/brianraney/Documents/GitHub/skill-tooling/tests/smoke.sh)
  - [.github/workflows/validate.yml](/Users/brianraney/Documents/GitHub/skill-tooling/.github/workflows/validate.yml)

### Family Repo Contract

The current family repo model is:

```text
my-family/
  family.json
  source/
    orchestrator.md
    researcher.md
  dist/
    grok/
    grok-build/
    claude-ai/
    claude-code/
    openai-skills-api/
    chatgpt-work/
    codex/
```

Ownership model:

- Humans author `source/*.md`
- `skill-tooling` generates `dist/<target>/`

### Commands

Current commands:

- `scripts/create-family`
  - Scaffolds a family repo with `family.json` using a `skill_family` manifest object, plus `source/`, `README.md`, and `.gitignore`
- `scripts/skill-deploy`
  - Generates target folders
  - Performs validation as part of deployment
  - Can publish generated folders via copy-based, command-based, and selected built-in publishers
  - Can optionally stage, commit, push, open a PR, and merge for local source repos
  - Can operate on a local repo with `--source`
  - Can clone a repo with `--repo`

There is also a `scripts/validate-family` helper, but it should be treated as a support/debugging command rather than the main product surface.

### What Works Today

The current implementation does successfully provide:

- Family scaffolding
- Shared manifest validation via [family.schema.json](/Users/brianraney/Documents/GitHub/skill-tooling/schemas/family.schema.json)
- Source skill loading from `source/*.md`
- Target folder generation under `dist/` for:
  - `grok`
  - `grok-build`
  - `claude-ai`
  - `claude-code`
  - `openai-skills-api`
  - `chatgpt-work`
  - `codex`
- Repo ingestion via `--repo`
- Copy-based publishing into install roots
- Command-based publishing hooks for external wrapper commands
- Built-in local Grok skill publishing for `grok` and `grok-build`
- Built-in OpenAI hosted skill publishing for `openai-skills-api`
- Built-in ChatGPT Work manual-handoff publishing for `chatgpt-work`
- Built-in local Codex skill publishing for `codex`
- Built-in manual Claude Desktop / claude.ai handoff publishing for `claude-ai`
- Built-in local Claude Code skill publishing for `claude-code`
- Deployment receipts and rollback support for copy-based publishers
- Rollback support for built-in local skill publishers (`grok-skills`, `claude-skills`, `codex-skills`)
- Formal source skill frontmatter schema validation for `name` and `description`
- CI smoke coverage for:
  - scaffold
  - validate
  - local generation
  - repo-based publish
  - manifest schema rejection

### Runtime Model

The current implementation is a Python CLI with shell wrappers.

Runtime assumptions:

- Python 3 is available
- Poetry metadata is the source of truth for Python version and future library changes
- `git` is available
- The local machine or CI runner has filesystem access to any copy-publish roots
- Any `command` publishers refer to locally installed wrapper commands or scripts
- Grok local skill publishing defaults to `~/.grok/skills`
- OpenAI hosted publishing requires an API key
- Claude Code local skill publishing defaults to `~/.claude/skills` and honors `CLAUDE_CONFIG_DIR`
- Claude Desktop / claude.ai Skills UI is a separate product surface and remains manual-only here
- Codex local publishing uses explicit roots when configured; otherwise it defaults to `$HOME/.agents/skills` and updates an existing `$HOME/.codex/skills` legacy/current-session root
- Claude hosted agent publishing requires the Anthropic CLI only if you explicitly opt into `claude-agent`
- Deploy auto-loads `.env` / `.skill-tooling.env` from the `skill-tooling` repo by default
- Any non-default env file must be explicitly selected with `SKILL_TOOLING_ENV_FILE`

Today this can reasonably run:

- Locally on a developer machine
- In GitHub Actions
- In any CI or automation runner with Python 3 and git

Dependency management expectations:

- Runtime and library declarations belong in [pyproject.toml](/Users/brianraney/Documents/GitHub/skill-tooling/pyproject.toml)
- Dependency resolution output belongs in `poetry.lock`
- Any new third-party Python library should be added through Poetry so the lock file stays authoritative

It is not intended to require:

- a web server
- a background service
- a database
- a long-running control plane

## Future Target State

### Product Goal

The target product state is:

- A stable canonical contract that every family repo follows
- One command to validate, build, and publish a family everywhere
- Vendor-specific target adapters that emit real platform-native formats
- Vendor-specific publishers that integrate with actual CLIs or APIs
- Clear manual fallback artifacts when automatic publishing is unavailable
- Consistent governance across all families via shared schemas and validation

### Target User Experience

For a family author:

```bash
scripts/create-family my-family "Description" --path /somewhere
```

Then:

```bash
scripts/skill-deploy --source . --publish --config path/to/publish-config.json
```

For centralized automation:

```bash
scripts/skill-deploy --repo owner/family --ref main --publish --config path/to/publish-config.json
```

The intended behavior:

1. Load the family definition.
2. Validate it against shared schemas.
3. Load canonical source skills.
4. Generate target-native output for each enabled tool.
5. Publish each target output into the corresponding tool.
6. Return clear success/failure status per target.

The intent is that this remains a CLI workflow, not a hosted system.

### Desired Technical State

The future target state should include:

- Manifest schema versioning
- Source skill schema and/or frontmatter schema
- Publish config schema
- Real vendor adapters instead of placeholder file extensions alone
- Explicit target capability metadata
- Better release/version management across families
- Deployment logs and auditability
- Optional dry-run mode with diff output
- Stronger CI coverage
- GitHub Action packaging for turnkey use in family repos

## Current Defects, Gaps, And Risks

### 1. Target outputs are still synthetic for most targets

Current state:

- Generated files use tool-specific extensions such as `.grok`, `.skill`, and `.prompt`
- The emitted content is a generic transformed text format
- The built-in OpenAI and Claude publishers still start from that generated text rather than a fully vendor-specific authoring model

Issue:

- This is enough for structure and manual review, but it is not yet proof that each generated folder matches the final ingestion contract for Grok, Grok Build, Claude Code, or Codex

Fix:

- Define a concrete output contract per target
- Implement target adapters that emit actual vendor-ready payloads
- Add fixture-based tests for each target adapter

### 2. Built-in publishers exist, but coverage is incomplete

Current state:

- `openai-skills-api` publishes hosted skills through the OpenAI API
- `chatgpt-work` prepares manual handoff bundles rather than completing a vendor UI flow
- `codex` can publish local Codex skills into a Codex skills root
- `claude-ai` can generate the manual `.skill` handoff bundle for Claude Desktop / claude.ai
- `claude-code` can publish local Claude Code skills into Claude's documented skills root
- `grok` and `grok-build` can publish local Grok skills into `~/.grok/skills` or an explicit install root

Issue:

- The project now has real integrations, but not yet for every listed tool
- The current Claude local-skills publisher is individual-skill local install, not a hosted remote publisher
- The current Codex publisher is local-install based, not remote/hosted

Fix:

- Keep expanding first-party publishers target by target
- Add individual-skill Anthropic publishing if Anthropic exposes the right surface for this use case
- Keep `command` mode as the escape hatch for everything else

### 3. Source skill frontmatter is standardized, but intentionally narrow

Current state:

- `family.json` has a schema with a canonical `skill_family` object
- Publish config now has a formal schema
- Source skill frontmatter now has a formal machine-readable schema
- Supported source frontmatter keys are `name` and `description`

Issue:

- The source format is still intentionally narrow
- It does not support rich YAML structures or per-skill target declarations

Fix:

- Keep the narrow contract and document it explicitly
- Expand only if a real source-authoring need appears

### 4. YAML is discussed conceptually but not supported operationally

Current state:

- Documentation says the schema represents the contract whether serialized as JSON or YAML
- Tooling only reads `family.json`

Issue:

- This can create confusion about whether `.yml` is actually supported today

Fix:

- Either explicitly support `family.yaml` / `family.yml`
- Or narrow the docs and state clearly that only JSON is supported right now

### 5. Frontmatter parsing is intentionally narrow

Current state:

- Source skills use a simple custom frontmatter parser
- It expects line-oriented `key: value` pairs
- The allowed keys are `name` and `description`

Issue:

- This is not full YAML frontmatter support
- Multiline values, nested structures, and richer YAML constructs are not handled

Fix:

- Keep the narrow contract and document it explicitly
- Or adopt a real YAML parser if richer frontmatter is required

### 6. GitHub Actions checks executable bits, but tracked file modes are not yet normalized in git history

Current state:

- CI requires executable scripts
- The working tree uses executable permissions locally
- The tracked git metadata shown in the current repository state still reflects older non-executable script entries for some files

Issue:

- A future commit needs to persist the intended file modes, or CI may fail in a clean checkout depending on what is actually committed

Fix:

- Stage and commit the wrapper scripts and smoke test with executable bits
- Verify in git index before merging

### 7. Output-in-source-root behavior is powerful but potentially destructive

Current state:

- `skill-deploy --source .` rewrites `dist/<target>/` inside the family repo

Issue:

- That is the intended model, but it can overwrite manual edits in generated folders without warning

Fix:

- Document this as a hard rule
- Add optional `--dry-run`
- Add optional `--clean` / `--no-clean` behavior or diff preview

### 8. Deployment history exists, but hosted/API rollback is still incomplete

Current state:

- Deploy now writes receipts and supports rollback for copy-based publishers
- Built-in local skill publishers for Grok, Claude, and Codex now restore prior local installs during rollback
- Hosted/API publishers still persist state without rollback handlers
- There is still no full release lifecycle or target-aware version ledger

Issue:

- The project now has basic deployment history, but not a complete release-management model

Fix:

- Keep deployment receipts
- Add target-aware version tracking
- Add rollback mechanics for hosted/API publishers
- Add release metadata and promotion workflows later

### 9. Secret handling must stay local-only

Current state:

- Local `.env` loading is supported only from the `skill-tooling` repo by default
- `.env` files are meant to stay out of git
- Inline API keys in publish config are not supported

Issue:

- Secrets remain a serious operational risk if users commit local env files or bypass the intended env-only pattern

Fix:

- Keep `.env` and `.skill-tooling.env` ignored in every repo this scaffolds
- Keep secrets out of JSON config
- Prefer local shell env or ignored env files over committed config

### 10. The project is still a local CLI, not yet a turnkey GitHub Action product

Current state:

- The tooling can run in GitHub Actions, but it is not packaged as a reusable action yet

Issue:

- Adoption across many family repos will be slower until there is a standard action wrapper

Fix:

- Package the core workflow as a reusable GitHub Action or composite action

### 11. No explicit architecture doc tying all pieces together

Current state:

- The repo now has focused docs, but the architecture narrative has been spread across multiple files

Issue:

- Someone new to the project can understand the pieces, but not yet the whole system quickly

Fix:

- This document should be kept as the project-level overview and updated alongside major contract changes

### 12. The public workflow is still documented a little too broadly

Current state:

- The repo exposes `create-family`, `validate-family`, and `skill-deploy`
- Some docs still read like validation is a separate normal user step

Issue:

- The product vision is simpler than that
- The main user story should be "create once, deploy whenever"

Fix:

- Keep `validate-family` as a support command
- Present `create-family` and `skill-deploy` as the only primary commands
- Make deploy the obvious home for validation, generation, and publish

## Recommended Next Steps

### Immediate

- Commit the current repo contract and executable script modes cleanly
- Clarify JSON-only vs JSON-and-YAML support
- Add source skill schema

### Near Term

- Define target-native output contracts for Grok, Grok Build, Claude Code, and Codex
- Add `--dry-run`
- Improve error reporting per target during publish

### Medium Term

- Package this as a reusable GitHub Action
- Add schema versioning
- Add deployment history and release metadata
- Add richer test fixtures with multiple skills

## Current Summary

This project is no longer just an idea. It now has:

- A coherent family repo contract
- A shared family manifest schema
- A working scaffold/validate/deploy/publish CLI
- A repo-ingestion path
- A generated `dist/<target>/` deployable model

What it does not yet have is the final layer that makes it production-grade:

- real vendor-native adapters for every listed target
- automatic ChatGPT Work publishing
- hosted/API rollback for OpenAI Skills and Claude agents
- release and deployment governance

That is the gap between the current state and the intended universal deployer.
