# Deployment Matrix

This table describes the current end-to-end deployment flow for `skill-tooling`, including the newer local secret-loading and safety controls.

| Deployment Step | Current State |
|---|---|
| Load publish config from `--config`, `SKILL_TOOLING_CONFIG`, or default `publish-config.json` discovery | Real tooling |
| Load local secrets/config from the default `skill-tooling/.env` or explicit `SKILL_TOOLING_ENV_FILE` override | Real tooling |
| Restrict `.env` loading to an allowlist of deployment-related keys | Real tooling |
| Ignore `.env` files in git and fail CI if they are tracked | Real tooling |
| Clone repo for `--repo owner/family` deploys | Real tooling |
| Refuse insecure `http://` git URLs | Real tooling |
| Do not implicitly load `.env` from family repos or the current working directory | Real tooling |
| Validate `family.json` schema | Real tooling |
| Discover skills from `source/*.md` | Real tooling |
| Load target overrides from `overrides/<skill-id>/<target>.md` | Real tooling |
| Generate per-target output folders (`grok/`, `claude/`, `codex/`, etc.) | Real tooling |
| Stage repo changes after deploy (`--git`) | Real tooling |
| Commit repo changes after deploy | Real tooling |
| Push release branch after deploy (`--push`) | Real tooling |
| Open a pull request after deploy (`--open-pr`) | Real tooling |
| Merge a pull request after deploy (`--merge-pr`) | Real tooling |
| Publish `openai-chatgpt` via hosted OpenAI Skills API | Real tooling |
| Publish `codex` via local `$CODEX_HOME/skills` install | Real tooling |
| Publish `claude` via `ant beta:agents` | Real tooling |
| Publish `grok`, `grok-build`, `claude-code` via wrapper command mode | Architecture exists, first-party adapters not built |
| Publish any target via copy mode to install roots | Real tooling |
| Verify copy publishes or run target verify commands | Real tooling |
| Write deployment receipts/state under `.skill-tooling/deployments/` | Real tooling |
| Roll back copy-based publishes | Real tooling |
| Roll back command-based publishes | Guarded tooling; requires `--allow-command-rollback` |
| Roll back API-based publishers (`openai-skills`, `claude-agent`, `codex-skills`) | Not implemented |

## Environment Keys

Currently supported local env keys:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `CODEX_HOME`
- `SKILL_TOOLING_CONFIG`
- `SKILL_TOOLING_ENV_FILE`
- `SKILL_TOOLING_GROK_INSTALL_ROOT`
- `SKILL_TOOLING_GROK_BUILD_INSTALL_ROOT`
- `SKILL_TOOLING_CLAUDE_INSTALL_ROOT`
- `SKILL_TOOLING_CLAUDE_CODE_INSTALL_ROOT`
- `SKILL_TOOLING_OPENAI_CHATGPT_INSTALL_ROOT`
- `SKILL_TOOLING_CODEX_INSTALL_ROOT`

## Notes

- `publish-config.json` should reference env var names like `OPENAI_API_KEY`, not contain inline secrets.
- The default implicit env file is the one in the `skill-tooling` repo.
- Use `SKILL_TOOLING_ENV_FILE` only when you intentionally want to override that default.
