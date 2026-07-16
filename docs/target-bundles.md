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
    claude-local/
    claude-ai/
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
```

Examples:

- `dist/grok/family.grok`
- `dist/grok/orchestrator.grok`
- `dist/claude-local/family.skill`
- `dist/claude-local/researcher.skill`
- `dist/claude-ai/family.skill`
- `dist/claude-ai/researcher.skill`
- `dist/codex/orchestrator.prompt`

## Purpose

These generated folders serve two roles:

- They are the exact target-specific text used for automatic publishing.
- They are the manual deployment artifacts when a human needs to inspect, paste, or import the generated skill text into a tool.

## Target Extensions

- `grok` uses `.grok`
- `grok-build` uses `.grokbuild`
- `claude-local` uses `.skill`
- `claude-ai` uses `.skill`
- `claude-code` uses `.skill`
- `openai-skills-api` uses `.prompt`
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
    "openai-skills-api": {
      "mode": "openai-skills",
      "api_key_env": "OPENAI_API_KEY"
    },
    "claude-local": {
      "mode": "claude-skills"
    },
    "claude-ai": {
      "mode": "manual"
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

`manual` mode marks the generated folder as the final handoff artifact. This is used for targets like `chatgpt-work` where `skill-tooling` can prepare the exact text bundle and install guide, but not complete the vendor UI flow directly.

`openai-skills` publishes each skill in the family as its own hosted OpenAI API skill and stores remote ids under `.skill-tooling/deployments/state/`.

`claude-agent` publishes the generated family bundle as a hosted Claude agent and stores the agent id/version under `.skill-tooling/deployments/state/`.

`grok-skills` installs one local Grok skill directory per source skill under `~/.grok/skills` by default, or into an explicit target install root when configured.

`claude-skills` installs one local Claude skill directory per source skill under Claude's documented local skills directory.

`claude-ai` produces the manual `.skill` handoff bundle for Claude Desktop / claude.ai. It does not currently automate cloud/UI publication.

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
