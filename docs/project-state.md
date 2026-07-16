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
  overrides/
    orchestrator/
      claude.md
  grok/
  grok-build/
  claude/
  claude-code/
  openai-chatgpt/
  codex/
```

Ownership model:

- Humans author `source/*.md`
- Humans optionally author `overrides/<skill-id>/<target>.md`
- `skill-tooling` generates the top-level target folders

### Commands

Current commands:

- `scripts/create-family`
  - Scaffolds a family repo with `family.json` using a `skill_family` manifest object, plus `source/`, `overrides/`, `README.md`, and `.gitignore`
- `scripts/skill-deploy`
  - Generates target folders
  - Performs validation as part of deployment
  - Can publish generated folders via copy-based, command-based, and selected built-in publishers
  - Can operate on a local repo with `--source`
  - Can clone a repo with `--repo`

There is also a `scripts/validate-family` helper, but it should be treated as a support/debugging command rather than the main product surface.

### What Works Today

The current implementation does successfully provide:

- Family scaffolding
- Shared manifest validation via [family.schema.json](/Users/brianraney/Documents/GitHub/skill-tooling/schemas/family.schema.json)
- Source skill loading from `source/*.md`
- Optional target-specific skill overrides from `overrides/<skill-id>/<target>.md`
- Target folder generation for:
  - `grok`
  - `grok-build`
  - `claude`
  - `claude-code`
  - `openai-chatgpt`
  - `codex`
- Repo ingestion via `--repo`
- Copy-based publishing into install roots
- Command-based publishing hooks for external wrapper commands
- Built-in OpenAI hosted skill publishing for `openai-chatgpt`
- Built-in local Codex skill publishing for `codex`
- Built-in Claude hosted agent publishing for `claude`
- Deployment receipts and rollback support for copy-based publishers
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
- `git` is available
- The local machine or CI runner has filesystem access to any copy-publish roots
- Any `command` publishers refer to locally installed wrapper commands or scripts
- OpenAI hosted publishing requires an API key
- Codex local publishing defaults to `$CODEX_HOME/skills`
- Claude hosted publishing requires the Anthropic CLI on the runner
- Deploy auto-loads `.env` / `.skill-tooling.env` files from the working directory and source repo
- Repo-based deploys intentionally do not trust `.env` files from cloned family repos

Today this can reasonably run:

- Locally on a developer machine
- In GitHub Actions
- In any CI or automation runner with Python 3 and git

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
4. Apply any target-specific overrides.
5. Generate target-native output for each enabled tool.
6. Publish each target output into the corresponding tool.
7. Return clear success/failure status per target.

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

- `openai-chatgpt` can publish hosted skills through the OpenAI API
- `codex` can publish local Codex skills into a Codex skills root
- `claude` can publish a hosted agent through the Anthropic CLI
- `grok`, `grok-build`, and `claude-code` still rely on `command` wrappers or copy/manual flows

Issue:

- The project now has real integrations, but not yet for every listed tool
- The current Claude publisher is family-level, not individual-skill level
- The current Codex publisher is local-install based, not remote/hosted

Fix:

- Keep expanding first-party publishers target by target
- Add individual-skill Anthropic publishing if Anthropic exposes the right surface for this use case
- Keep `command` mode as the escape hatch for everything else

### 3. Source skill frontmatter still lacks a formal schema

Current state:

- `family.json` has a schema with a canonical `skill_family` object
- Publish config now has a formal schema
- Source skill files still do not have a formal machine-readable schema

Issue:

- Governance is still partial
- Validation logic for source skill frontmatter still lives primarily in imperative code

Fix:

- Add `schemas/source-skill.schema.json`
- Validate it at load time

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

- `skill-deploy --source .` rewrites top-level target folders inside the family repo

Issue:

- That is the intended model, but it can overwrite manual edits in generated folders without warning

Fix:

- Document this as a hard rule
- Add optional `--dry-run`
- Add optional `--clean` / `--no-clean` behavior or diff preview

### 8. Deployment history exists, but API/CLI rollback is still incomplete

Current state:

- Deploy now writes receipts and supports rollback for copy-based publishers
- API/CLI publishers persist state, but they do not yet have rollback handlers
- `codex-skills` currently overwrites matching installed skill directories and records state, but does not yet provide target-aware rollback
- There is still no full release lifecycle or target-aware version ledger

Issue:

- The project now has basic deployment history, but not a complete release-management model

Fix:

- Keep deployment receipts
- Add target-aware version tracking
- Add rollback mechanics for command/API publishers
- Add release metadata and promotion workflows later

### 9. Secret handling must stay local-only

Current state:

- Local `.env` loading is supported for trusted local use
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

- Build the next real vendor publishers for Grok, Grok Build, and Claude Code
- Define target-native output contracts for those targets
- Add `--dry-run`
- Improve error reporting per target during publish

### Medium Term

- Package this as a reusable GitHub Action
- Add schema versioning
- Add deployment history and release metadata
- Add richer test fixtures with multiple skills and multiple overrides

## Current Summary

This project is no longer just an idea. It now has:

- A coherent family repo contract
- A shared family manifest schema
- A working scaffold/validate/deploy/publish CLI
- A repo-ingestion path
- A generated top-level target-folder model

What it does not yet have is the final layer that makes it production-grade:

- real vendor-native adapters for every listed target
- real built-in publishers for Grok, Grok Build, Claude Code, and Codex
- full schema coverage
- release and deployment governance

That is the gap between the current state and the intended universal deployer.
