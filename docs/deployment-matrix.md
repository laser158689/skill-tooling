# Deployment Matrix

This table describes the current end-to-end deployment flow for `skill-tooling`, including the newer local secret-loading and safety controls.

| Deployment Step | Current State |
|---|---|
| Load publish config from `--config`, `SKILL_TOOLING_CONFIG`, or default `skill-tooling/publish-config.json` | Real tooling |
| Load local secrets/config from the default `skill-tooling/.env` or explicit `SKILL_TOOLING_ENV_FILE` override | Real tooling |
| Restrict `.env` loading to an allowlist of deployment-related keys | Real tooling |
| Ignore `.env` files in git and fail CI if they are tracked | Real tooling |
| Clone repo for `--repo owner/family` deploys | Real tooling |
| Refuse insecure `http://` git URLs | Real tooling |
| Do not implicitly load `.env` from family repos or the current working directory | Real tooling |
| Validate `family.json` schema | Real tooling |
| Discover skills from `source/*.md` | Real tooling |
| Generate per-target output folders under `dist/` (`dist/grok/`, `dist/claude-local/`, `dist/claude-ai/`, `dist/codex/`, etc.) | Real tooling |
| Stage repo changes after deploy (`--git`) | Real tooling |
| Commit repo changes after deploy | Real tooling |
| Push release branch after deploy (`--push`) | Real tooling |
| Open a pull request after deploy (`--open-pr`) | Real tooling |
| Merge a pull request after deploy (`--merge-pr`) | Real tooling |
| Publish `openai-skills-api` via hosted OpenAI Skills API | Real tooling |
| Publish `chatgpt-work` as a manual handoff bundle with generated prompts and `INSTALL.md` | Real tooling |
| Publish `codex` via local filesystem skill install | Real tooling |
| Publish `claude-local` and `claude-code` via Claude local skills install (`~/.claude/skills` or `CLAUDE_CONFIG_DIR/skills`) | Real tooling |
| Publish `claude-ai` via generated manual handoff bundle for Claude Desktop / claude.ai Skills UI | Real tooling |
| Publish `grok` and `grok-build` via local Grok skills install (`~/.grok/skills` by default) | Real tooling |
| Publish any target via copy mode to install roots | Real tooling |
| Verify copy publishes or run target verify commands | Real tooling |
| Write deployment receipts/state under `.skill-tooling/deployments/` | Real tooling |
| Roll back copy-based publishes | Real tooling |
| Roll back command-based publishes | Guarded tooling; requires `--allow-command-rollback` |
| Roll back local skill publishers (`grok-skills`, `claude-skills`, `codex-skills`) | Real tooling |
| Roll back API-based publishers (`openai-skills`, `claude-agent`) | Not implemented |

## Environment Keys

Currently supported local env keys:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `CLAUDE_CONFIG_DIR`
- `CODEX_HOME`
- `SKILL_TOOLING_CONFIG`
- `SKILL_TOOLING_ENV_FILE`
- `SKILL_TOOLING_GROK_INSTALL_ROOT`
- `SKILL_TOOLING_GROK_BUILD_INSTALL_ROOT`
- `SKILL_TOOLING_CLAUDE_LOCAL_INSTALL_ROOT`
- `SKILL_TOOLING_CLAUDE_AI_INSTALL_ROOT`
- `SKILL_TOOLING_CLAUDE_CODE_INSTALL_ROOT`
- `SKILL_TOOLING_OPENAI_SKILLS_API_INSTALL_ROOT`
- `SKILL_TOOLING_CODEX_INSTALL_ROOT`

## Notes

- `publish-config.json` should reference env var names like `OPENAI_API_KEY`, not contain inline secrets.
- The default implicit env file is the one in the `skill-tooling` repo.
- Use `SKILL_TOOLING_ENV_FILE` only when you intentionally want to override that default.
