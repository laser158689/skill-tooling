# skill-tooling

`skill-tooling` is the central tooling repository for managing skill families that live in their own Git repositories.

It does two primary things:

- Scaffolds a new family repository.
- Generates and publishes tool-specific views for Grok, Grok Build, Grok web/app manual handoff bundles, Gemini Spark manual handoff bundles, Gemini CLI, Claude Desktop / claude.ai manual handoff bundles, Claude Code, the OpenAI Skills API, OpenAI plugin manual handoff bundles, ChatGPT Work manual handoff bundles, Codex, and future targets.

Validation is part of deployment. You do not need to run a server or keep background infrastructure running.

## Python Tooling

This repo uses Poetry for Python version and dependency governance.

- `pyproject.toml` is the source of truth for the Python runtime and any future libraries.
- `poetry.lock` must be committed whenever dependencies change.
- The current CLI intentionally uses only the Python standard library, so the Poetry setup is minimal today.

If you want a local environment for working on the CLI:

```bash
poetry install
```

## Operating Model

- `skill-tooling` is the shared tooling repo.
- Each skill family lives in its own repo.
- `source/` contains the canonical authored skills.
- `dist/<target>/` contains the generated deployable outputs.
- `docs/SKILLS.md` and `docs/skills/*.md` contain generated skill reference docs.

## Family Repository Contract

Every family repository follows this shape:

```text
my-family/
  family.json
  source/
    orchestrator.md
    researcher.md
  docs/
    SKILLS.md
    skills/
      orchestrator.md
      researcher.md
  dist/
    grok/
    grok-web/
    gemini-spark/
    gemini-cli/
    claude-ai/
    claude-code/
    openai-skills-api/
    openai-plugin/
    chatgpt-work/
    codex/
```

The important ownership rule is simple:

- Humans edit `source/*.md`
- `skill-tooling` rewrites `dist/<target>/`
- `skill-tooling` rewrites `docs/SKILLS.md` and `docs/skills/*.md`

Generated-output rewrite rule:
- Every `skill-deploy` run removes and rebuilds each selected generated target directory.
- Repeated deploys against unchanged source should produce the same target file tree.
- Duplicate-suffixed artifacts like `README 2.md` or `uploads 3/` are treated as invalid generated output.

Manual-target output rule:
- `chatgpt-work`, `grok-web`, and `claude-ai` emit only `INSTALL.md` plus per-skill upload `.zip` files.
- `openai-plugin` emits only `INSTALL.md` plus `<family>-plugin.zip`.
- Manual-target `dist/` folders should not contain extra loose prompt/skill/source files.

Generated-docs rule:
- `docs/SKILLS.md` and `docs/skills/*.md` are derived artifacts.
- Edit `source/*.md`, then rerun `skill-deploy`.

The manifest filename is always `family.json`.
This repo does not use repo-specific manifest filenames like `my-family.yml`.

Source skill note:
- `source/*.md` uses a small standardized YAML frontmatter block.
- Supported frontmatter keys are `name` and `description`.
- Per-skill `targets` are not part of the source contract; targets are defined at the family level in `family.json`.
- `skill-deploy` and `validate-family` measure authored markdown body size after frontmatter removal.
- Source skill bodies warn at 18,000 bytes and fail validation at 20,000 bytes.

Target migration note:
- `openai-chatgpt` has been renamed to `openai-skills-api`.
- `chatgpt-work` is a separate target for the ChatGPT Work UI flow and is not the same thing as the OpenAI Skills API.
- `openai-plugin` is a separate target for packaged ChatGPT / Codex plugin distribution.
- `grok-web` is a separate target for the Grok web/app Skills UI flow and is not the same thing as `grok-build`.
- `gemini-spark` is the manual Gemini Apps / Gemini Mac Skills flow.
- `gemini-cli` is the local Gemini CLI skill install surface.
- `claude` and `claude-local` are deprecated and rejected.
- `claude-ai` is the manual Claude Desktop / claude.ai Skills surface.

See [docs/family-repo-contract.md](docs/family-repo-contract.md) for the full contract.
If an LLM needs the exact authoring rules, start with [docs/llm-authoring-contract.md](docs/llm-authoring-contract.md).
The family manifest schema is documented in [docs/family-schema.md](docs/family-schema.md) and published as [schemas/family.schema.json](schemas/family.schema.json).
A machine-readable schema for source skill frontmatter is published as [schemas/source-skill-frontmatter.schema.json](schemas/source-skill-frontmatter.schema.json).
The canonical architecture doc set lives here:

- [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md)
- [docs/TARGET_STATE.md](docs/TARGET_STATE.md)
- [docs/GAPS.md](docs/GAPS.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/DEPLOYMENT_MATRIX.md](docs/DEPLOYMENT_MATRIX.md)

Older summary docs remain only as pointers:

- [docs/project-state.md](docs/project-state.md)
- [docs/status-and-plan.md](docs/status-and-plan.md)
- [docs/deployment-matrix.md](docs/deployment-matrix.md)

## Primary Commands

- `scripts/create-family` scaffolds a new family repository.
- `scripts/skill-deploy` validates, generates tool folders, and optionally publishes them.

There is also `scripts/validate-family`, but it is a support command. The intended day-to-day workflow is just `create-family` and `skill-deploy`.

`skill-deploy` can also handle git staging, commit, push, pull-request creation, and merge for local source repos when you pass the explicit git workflow flags. That workflow stages generated docs and `dist/` artifacts together.

## Quick Start

Create a new family repo:

```bash
scripts/create-family customer-support "Reusable support skills for customer support teams" --path /tmp
```

Generate tool-specific deployable folders directly inside the family repo:

```bash
scripts/skill-deploy --source /tmp/customer-support
```

Publish every configured tool from a repo in one command:

```bash
scripts/skill-deploy \
  --repo your-org/customer-support \
  --publish
```

If you omit `--target`, `--publish` publishes every target listed in `family.json`.
By default, the CLI looks for `publish-config.json` in the `skill-tooling` repo.
Anything else should be an explicit override through `--config` or `SKILL_TOOLING_CONFIG`.

That is the intended operating model:

1. Run `create-family` once to start a family.
2. Edit the skill files in `source/`.
3. Run `skill-deploy` whenever you want validation, target generation, generated-doc refresh, and publish.

Every deploy also writes a receipt under `.skill-tooling/deployments/` by default so publish results are auditable and copy-based publishes can be rolled back.

If you want one-command deploy plus git workflow on a local family repo:

```bash
scripts/skill-deploy \
  --source /tmp/customer-support \
  --publish \
  --git \
  --branch codex/customer-support-release \
  --commit-message "Deploy customer-support"
```

If you want the generated deployable folders somewhere else, override the output root:

```bash
scripts/skill-deploy --source /tmp/customer-support --output /tmp/customer-support-build
```

## Publishing

Publishing is adapter-based.

- `copy` publishers copy a generated tool folder into a configured install root.
- `command` publishers run a target-specific local command with bundle metadata.
- `openai-skills` creates or updates hosted OpenAI API skills, one per `source/*.md` skill.
- `claude-agent` creates or updates a hosted Claude agent from the generated family bundle.
- `grok-skills` installs one local Grok skill directory per `source/*.md` skill under `~/.grok/skills` by default.
- `claude-skills` installs one local Claude Code skill directory per `source/*.md` skill under Claude's documented local skills root.
- `codex-skills` installs one local Codex skill directory per `source/*.md` skill.

The canonical publish config is [publish-config.json](publish-config.json).
The sample in [examples/publish-config.json](examples/publish-config.json) remains as a reference copy.

Supported template variables for `command` publishers:

- `{bundle_dir}`
- `{family_name}`
- `{target}`
- `{source}`
- `{source_descriptor}`
- `{output_root}`
- `{destination}` for verify commands when a publish destination exists

Optional publisher fields:

- `verify_command`
- `rollback_command`
- `api_key_env` for API-based publishers
- `base_url` for HTTPS API publishers when you need a non-default endpoint; custom hosts require the dedicated `SKILL_TOOLING_CUSTOM_API_KEY`
- `cli_path`, `model`, and `tool` for Claude agent publishing

Current adapter status:

- `openai-skills-api` has a built-in hosted publisher via `openai-skills`.
- `openai-plugin` has a built-in manual package publisher that writes a plugin bundle and install guide for ChatGPT / Codex workspace distribution.
- `chatgpt-work` has a built-in manual-handoff publisher that writes the exact bundle and install guide for the ChatGPT Work UI flow.
- `grok` and `grok-build` have built-in local publishers via `grok-skills`.
- `grok-web` has a built-in manual-handoff publisher that writes upload-oriented Grok Skills bundles and an install guide.
- `gemini-spark` has a built-in manual-handoff publisher that writes upload-oriented Gemini Spark skill bundles and an install guide.
- `gemini-cli` has a built-in local publisher via `gemini-skills`.
- `codex` has a built-in local publisher via `codex-skills`.
- `claude-ai` has a built-in manual-handoff publisher for the Claude Desktop / claude.ai Skills UI.
- `claude-code` has a built-in local publisher via `claude-skills`.
- `gemini-spark` verifies its current artifact contract and the currently documented Gemini Spark upload constraints that affect generated skills: slug-safe `name`, root `SKILL.md`, and description length.
- `gemini-cli` has a built-in local publisher via `gemini-skills`.
- Generated target folders under `dist/` remain the manual fallback artifacts for every target.

Manual stub review status:

- `chatgpt-work` now verifies its generated upload bundles against the currently known ChatGPT uploader contract, including slug-safe frontmatter `name` values.
- `claude-ai` verifies its current artifact contract only: emitted files, ZIP shape, frontmatter presence, and markdown body shape.
- `gemini-spark` verifies exact emitted files, ZIP shape, slug-safe frontmatter `name`, and the current documented Gemini Apps description cap of 1024 characters.
- `grok-web` verifies its current artifact contract only: emitted files, ZIP shape, markdown heading, and description line.
- `openai-plugin` verifies its current artifact contract only: emitted files, plugin ZIP contents, and plugin manifest basics.
- These checks are intentionally isolated per target so future tool-specific discoveries only change that target's stub.

## Credentials And Environment

Deploy auto-loads environment variables from:

- `.env` in the `skill-tooling` repo
- `.skill-tooling.env` in the `skill-tooling` repo
- `SKILL_TOOLING_ENV_FILE` if you explicitly want to override the default env file

Existing shell environment variables win over `.env` values.

Security rules:

- `.env` files are for local secrets only and are git-ignored.
- Secrets should not be stored in `publish-config.json`.
- Family repo or current-directory `.env` files are not trusted implicitly.
- Any non-default env file must be explicitly selected with `SKILL_TOOLING_ENV_FILE`.
- `.env` loading only accepts a small allowlist of deployment-related keys.
- Authenticated API publishing rejects non-HTTPS endpoints and redirects.
- The primary OpenAI key is only sent to the official OpenAI API host.
- Custom API hosts must use a separate `SKILL_TOOLING_CUSTOM_API_KEY`.

Typical variables:

- `OPENAI_API_KEY` for `openai-skills`
- `SKILL_TOOLING_CUSTOM_API_KEY` only for an explicitly configured custom API host
- `ANTHROPIC_API_KEY` only if you explicitly enable `claude-agent`
- `CLAUDE_CONFIG_DIR` if you want Claude local skills installed somewhere other than `~/.claude`
- `SKILL_TOOLING_GEMINI_CLI_INSTALL_ROOT` if you want Gemini CLI skills installed somewhere other than `~/.gemini/skills`
- `CODEX_HOME` for isolated or legacy `codex-skills` installs
- `SKILL_TOOLING_CONFIG` to override the default publish config path

Starter values are shown in [examples/.env.example](examples/.env.example).

Typical local setup:

```bash
cp examples/.env.example .env
```

## Installation Roots

Copy-based publishing installs each generated tool folder to `<install-root>/<family-name>/`.

You can provide install roots with repeated `--install-path` flags:

```bash
scripts/skill-deploy \
  --source /tmp/customer-support \
  --publish \
  --install-path grok=/srv/grok/skills \
  --install-path codex=/srv/codex/skills
```

You can also use environment variables for copy-based publishers:

- `SKILL_TOOLING_GROK_INSTALL_ROOT`
- `SKILL_TOOLING_GROK_BUILD_INSTALL_ROOT`
- `SKILL_TOOLING_CLAUDE_AI_INSTALL_ROOT`
- `SKILL_TOOLING_CLAUDE_CODE_INSTALL_ROOT`
- `SKILL_TOOLING_OPENAI_SKILLS_API_INSTALL_ROOT`
- `SKILL_TOOLING_CODEX_INSTALL_ROOT`

For `grok-skills`, an explicit `--install-path grok=...` or `--install-path grok-build=...` wins. Otherwise the publisher installs to `~/.grok/skills`.

For `claude-skills`, an explicit `--install-path claude-code=...` wins. Otherwise the publisher installs to Claude's documented local skills root at `~/.claude/skills`, or `CLAUDE_CONFIG_DIR/skills` when `CLAUDE_CONFIG_DIR` is set.

For `codex-skills`, an explicit `--install-path codex=...`, `install_root`, `SKILL_TOOLING_CODEX_INSTALL_ROOT`, or `CODEX_HOME` installs to one configured root. Without one of those explicit roots, the publisher installs to the documented user skills location at `$HOME/.agents/skills`; if `$HOME/.codex/skills` already exists, it also updates that legacy/current-session location so older Codex installs can still discover the skill.

## Targets

Current targets:

- `grok`
- `grok-build`
- `grok-web`
- `claude-ai`
- `claude-code`
- `openai-skills-api`
- `openai-plugin`
- `chatgpt-work`
- `codex`

Current gaps:

- `chatgpt-work` automatic publishing
- `openai-plugin` automatic publishing
- `claude-ai` automatic publishing
- `grok-web` automatic publishing
- hosted/API rollback for `openai-skills` and `claude-agent`

The generated folder shapes are documented in [docs/target-bundles.md](docs/target-bundles.md).
The publish config schema is published as [schemas/publish-config.schema.json](schemas/publish-config.schema.json).
