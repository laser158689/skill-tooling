# Deployment Matrix

This matrix describes the intended deployment workflow in workflow order and the current implementation status.

| Workflow Step | Current Status |
|---|---|
| Load family manifest from `family.json` | Real tooling |
| Validate `family.json` against the shared schema | Real tooling |
| Discover source skills from `source/*.md` | Real tooling |
| Validate source skill frontmatter | Real tooling |
| Normalize family and skill metadata | Partial |
| Build deterministic target bundles under `dist/<target>/` | Real tooling |
| Emit clearly vendor-native target package contracts for every target | Partial |
| Emit artifact manifests and checksums per target | Not implemented |
| Load default env from `skill-tooling/.env` only | Real tooling |
| Restrict implicit env loading to an allowlist of deployment-related keys | Real tooling |
| Run target preflight before publish | Real tooling |
| Fail the whole publish before mutation if any requested target preflight fails | Real tooling |
| Publish `openai-skills-api` through the hosted API path | Real tooling |
| Prepare `chatgpt-work` native manual bundle and install guide | Real tooling |
| Publish `chatgpt-work` automatically through an official API | Not implemented |
| Prepare `claude-ai` native manual bundle and install guide | Real tooling |
| Publish `claude-ai` automatically through an official API | Not implemented |
| Publish `claude-code` through local skill install | Real tooling |
| Publish `codex` through local skill install | Real tooling |
| Publish `grok` through local skill install | Real tooling |
| Publish `grok-build` through local skill install | Real tooling |
| Publish future OpenAI plugin packaging target | Not implemented |
| Publish future Grok web/app skill target | Not implemented |
| Verify API-managed publishes | Real tooling |
| Verify local-install publishes | Real tooling |
| Verify manual targets by artifact generation and install guide output | Real tooling |
| Write receipts and state under `.skill-tooling/deployments/` | Real tooling |
| Roll back copy-mode publishes | Real tooling |
| Roll back built-in local-install publishers | Real tooling |
| Roll back API-managed publishers | Not implemented |
| Stage, commit, push, open PR, and merge from deploy flags | Real tooling |

## Current Target Summary

| Target | Publish Class |
|---|---|
| `openai-skills-api` | `api` |
| `chatgpt-work` | `manual_ui` |
| `claude-ai` | `manual_ui` |
| `claude-code` | `local_install` |
| `codex` | `local_install` |
| `grok` | `local_install` |
| `grok-build` | `local_install` |

## Status Language Rules

CLI output should use these meanings consistently:

- `Deployed to ...`: automated publish actually completed
- `Prepared for ...`: artifact bundle was generated for a manual or package-only target
- `Manual next step required`: human admin action is still needed
- `Unsupported`: target exists conceptually but does not yet have a supported build/publish path
