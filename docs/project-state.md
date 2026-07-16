# Project State

The canonical architecture doc set now lives here:

- [CURRENT_STATE.md](CURRENT_STATE.md)
- [TARGET_STATE.md](TARGET_STATE.md)
- [GAPS.md](GAPS.md)
- [ROADMAP.md](ROADMAP.md)
- [DEPLOYMENT_MATRIX.md](DEPLOYMENT_MATRIX.md)

Use those files instead of extending this legacy summary document.

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
