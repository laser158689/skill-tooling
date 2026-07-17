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

Automatic-install targets contain:

```text
dist/<target>/
  README.md
  manifest.json
  family.<ext>
  skill-one.<ext>
  skill-two.<ext>
```

Manual-upload targets contain only the upload/import artifact plus `INSTALL.md`:

```text
dist/<manual-target>/
  INSTALL.md
  uploads/*.zip
```

or:

```text
dist/openai-plugin/
  INSTALL.md
  <family>-plugin.zip
```

Examples:

- `dist/grok/family.grok`
- `dist/grok/orchestrator.grok`
- `dist/grok-web/uploads/orchestrator.zip`
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
- `grok-web` uses upload bundles under `uploads/`
- `claude-ai` uses upload bundles under `uploads/`
- `claude-code` uses `.skill`
- `openai-skills-api` uses `.prompt`
- `openai-plugin` uses `<family>-plugin.zip`
- `chatgpt-work` uses upload bundles under `uploads/`
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

`manual` mode marks the generated folder as the final handoff artifact. For manual targets, `skill-tooling` now emits only the exact upload/import artifact plus explicit tool-specific instructions in `INSTALL.md`.

## Manual Target Contract Review

Current manual-target verification is intentionally per-target.

`chatgpt-work`
- verifies exact emitted files: `INSTALL.md` plus `uploads/*.zip`
- verifies ZIP shape: `<skill-id>/SKILL.md`
- verifies frontmatter `name` is the slug-safe `skill_id`
- this is the strongest reviewed manual stub because the ChatGPT uploader rejected non-slug names and that rule is now enforced

`claude-ai`
- verifies exact emitted files: `INSTALL.md` plus `uploads/*.zip`
- verifies ZIP shape: `<skill-id>/skill.md`
- verifies frontmatter parses and carries the skill description
- verifies the markdown body starts with a heading
- this is artifact-contract verification only, not proof of Anthropic UI acceptance

`grok-web`
- verifies exact emitted files: `INSTALL.md` plus `uploads/*.zip`
- verifies ZIP shape: `<skill-id>/SKILL.md`
- verifies the markdown starts with a heading and includes the description line
- this is artifact-contract verification only, not proof of Grok web UI acceptance

`openai-plugin`
- verifies exact emitted files: `INSTALL.md` plus `<family>-plugin.zip`
- verifies the plugin ZIP contains `.codex-plugin/plugin.json` and one `skills/<skill-id>/SKILL.md` per skill
- verifies basic plugin manifest fields
- this is artifact-contract verification only, not proof of workspace admin-surface acceptance

`openai-skills` publishes each skill in the family as its own hosted OpenAI API skill and stores remote ids under `.skill-tooling/deployments/state/`.

`claude-agent` publishes the generated family bundle as a hosted Claude agent and stores the agent id/version under `.skill-tooling/deployments/state/`.

`grok-skills` installs one local Grok skill directory per source skill under `~/.grok/skills` by default, or into an explicit target install root when configured.

`grok-web` produces one `.zip` upload bundle per skill plus a Grok-specific install guide. It does not currently automate web publication.

`claude-skills` installs one local Claude Code skill directory per source skill under Claude's documented local skills directory.

`claude-ai` produces one `.zip` upload bundle per skill plus a Claude-specific install guide. It does not currently automate cloud/UI publication.

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
