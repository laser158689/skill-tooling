# Target Folders

`skill-tooling` generates one folder per target under `dist/` inside the family repo by default.

Example:

```text
customer-support/
  source/
    orchestrator.md
    researcher.md
  dist/
    grok/
    grok-web/
    claude-ai/
    claude-code/
    openai-plugin/
    codex/
```

## Folder Shape

Each target folder contains:

```text
dist/<target>/
  README.md
  manifest.json
  family.<ext>
  skill-one.<ext>
  skill-two.<ext>
  INSTALL.md
  uploads/ or plugin/
```

Examples:

- `dist/grok/family.grok`
- `dist/grok/orchestrator.grok`
- `dist/grok-web/uploads/orchestrator.zip`
- `dist/claude-ai/family.skill`
- `dist/claude-ai/uploads/researcher.zip`
- `dist/claude-code/family.skill`
- `dist/claude-code/researcher.skill`
- `dist/openai-plugin/customer-support-plugin.zip`
- `dist/codex/orchestrator.prompt`

## Purpose

These generated folders serve two roles:

- They are the exact target-specific artifacts used for automatic publishing where supported.
- They are the manual deployment artifacts when a human needs to inspect, upload, paste, or import the generated skill/package into a tool.

## Target Extensions

- `grok` uses `.grok`
- `grok-build` uses `.grokbuild`
- `grok-web` uses `.md` plus upload bundles under `uploads/`
- `claude-ai` uses `.skill`
- `claude-code` uses `.skill`
- `openai-skills-api` uses `.prompt`
- `openai-plugin` uses `.md` plus a plugin package under `plugin/` and `<family>-plugin.zip`
- `chatgpt-work` uses `.prompt`
- `codex` uses `.prompt`

## Publishing

Publishers are configured per target in JSON:

```json
{
  "targets": {
    "grok": {
      "mode": "grok-skills"
    },
    "grok-web": {
      "mode": "manual"
    },
    "openai-skills-api": {
      "mode": "openai-skills",
      "api_key_env": "OPENAI_API_KEY"
    },
    "openai-plugin": {
      "mode": "manual"
    },
    "claude-ai": {
      "mode": "manual"
    },
    "claude-code": {
      "mode": "claude-skills"
    },
    "chatgpt-work": {
      "mode": "manual"
    },
    "codex": {
      "mode": "codex-skills"
    }
  }
}
```

`copy` mode copies the generated target folder into `<install-root>/<family-name>/`.

`command` mode invokes a local publish command so you can bridge into vendor-specific CLIs, APIs, or wrapper scripts without changing the canonical family repo layout.

`manual` mode marks the generated folder as the final handoff artifact. This is used for targets like `chatgpt-work`, `grok-web`, `claude-ai`, and `openai-plugin` where `skill-tooling` can prepare the exact bundle/package and install guide, but not complete the vendor UI or admin flow directly.

`openai-skills` publishes each skill in the family as its own hosted OpenAI API skill and stores remote ids under `.skill-tooling/deployments/state/`.

`claude-agent` publishes the generated family bundle as a hosted Claude agent and stores the agent id/version under `.skill-tooling/deployments/state/`.

`grok-skills` installs one local Grok skill directory per source skill under `~/.grok/skills` by default, or into an explicit target install root when configured.

`grok-web` produces upload-oriented Grok Skills bundles for grok.com and supported apps. It does not currently automate web/app publication.

`claude-skills` installs one local Claude Code skill directory per source skill under Claude's documented local skills directory.

`claude-ai` produces the manual Claude Skills handoff bundle for Claude Desktop / claude.ai, including upload-oriented per-skill bundles under `uploads/`. It does not currently automate cloud/UI publication.

`openai-plugin` produces a manual OpenAI plugin package with `plugin/.codex-plugin/plugin.json`, packaged skills, and a zipped plugin artifact for ChatGPT / Codex workspace distribution. It does not currently automate workspace publication.

`codex-skills` installs one local Codex skill directory per source skill. Explicit roots from `--install-path codex=...`, `install_root`, `SKILL_TOOLING_CODEX_INSTALL_ROOT`, or `CODEX_HOME` are honored as single-root installs. Without an explicit root, the publisher installs to `$HOME/.agents/skills` and also updates `$HOME/.codex/skills` when that legacy/current-session directory already exists.

## Receipts And Rollback

Every deploy writes a receipt JSON file under `.skill-tooling/deployments/receipts/` by default for local source deploys, or under the configured `--history-dir`.

For copy-based publishers and built-in local skill publishers, deploy also stores enough information to roll back the previously published destination.

Support command:

```bash
scripts/rollback-deploy --receipt /path/to/receipt.json
```

If a receipt contains command-based rollback steps, you must opt in explicitly:

```bash
scripts/rollback-deploy --receipt /path/to/receipt.json --allow-command-rollback
```
