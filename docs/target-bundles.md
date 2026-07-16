# Target Folders

`skill-tooling` generates one top-level folder per target. By default these folders are written directly into the family repo.

Example:

```text
customer-support/
  source/
    orchestrator.md
    researcher.md
  grok/
  claude/
  codex/
```

## Folder Shape

Each target folder contains:

```text
<target>/
  README.md
  manifest.json
  family.<ext>
  skill-one.<ext>
  skill-two.<ext>
```

Examples:

- `grok/family.grok`
- `grok/orchestrator.grok`
- `claude/family.skill`
- `claude/researcher.skill`
- `codex/orchestrator.prompt`

## Purpose

These generated folders serve two roles:

- They are the exact target-specific text used for automatic publishing.
- They are the manual deployment artifacts when a human needs to inspect, paste, or import the generated skill text into a tool.

## Target Extensions

- `grok` uses `.grok`
- `grok-build` uses `.grokbuild`
- `claude` uses `.skill`
- `claude-code` uses `.skill`
- `openai-skills-api` uses `.prompt`
- `chatgpt-work` uses `.prompt`
- `codex` uses `.prompt`

## Publishing

Publishers are configured per target in JSON:

```json
{
  "targets": {
    "openai-skills-api": {
      "mode": "openai-skills",
      "api_key_env": "OPENAI_API_KEY"
    },
    "claude": {
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

`manual` mode marks the generated folder as the final handoff artifact. This is used for targets like `chatgpt-work` where `skill-tooling` can prepare the exact text bundle and install guide, but not complete the vendor UI flow directly.

`openai-skills` publishes each skill in the family as its own hosted OpenAI API skill and stores remote ids under `.skill-tooling/deployments/state/`.

`claude-agent` publishes the generated family bundle as a hosted Claude agent and stores the agent id/version under `.skill-tooling/deployments/state/`.

`claude-skills` installs one local Claude skill directory per source skill under Claude's documented skills directory.

`codex-skills` installs one local Codex skill directory per source skill. Explicit roots from `--install-path codex=...`, `install_root`, `SKILL_TOOLING_CODEX_INSTALL_ROOT`, or `CODEX_HOME` are honored as single-root installs. Without an explicit root, the publisher installs to `$HOME/.agents/skills` and also updates `$HOME/.codex/skills` when that legacy/current-session directory already exists.

## Receipts And Rollback

Every deploy writes a receipt JSON file under `.skill-tooling/deployments/receipts/` by default for local source deploys, or under the configured `--history-dir`.

For copy-based publishers, deploy also stores enough information to roll back the previously published destination.

Support command:

```bash
scripts/rollback-deploy --receipt /path/to/receipt.json
```

If a receipt contains command-based rollback steps, you must opt in explicitly:

```bash
scripts/rollback-deploy --receipt /path/to/receipt.json --allow-command-rollback
```
