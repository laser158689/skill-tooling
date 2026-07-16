# Status And Plan

This document records the current state of `skill-tooling`, the intended target state, the gaps between them, and the current work plan. It is written against the code and family-repo contract in the working tree as of July 16, 2026.

## Current State

### Tooling Repo

`skill-tooling` is a local Python CLI with shell entrypoints.

It currently provides:

- `scripts/create-family`
- `scripts/validate-family`
- `scripts/skill-deploy`
- `scripts/rollback-deploy`

The current family-repo contract is:

```text
family-repo/
  family.json
  source/
    <skill>.md
  dist/
    <target>/
```

Authored source lives only in `source/`.
Generated deployable artifacts live only in `dist/<target>/`.
There is no authored per-target override layer in the contract.

### Supported Targets

Current target ids:

- `grok`
- `grok-build`
- `claude-ai`
- `claude-code`
- `openai-skills-api`
- `chatgpt-work`
- `codex`

Current target behavior:

- `openai-skills-api`: hosted API publisher
- `chatgpt-work`: manual handoff bundle only
- `claude-ai`: manual Claude Desktop / claude.ai handoff bundle
- `claude-code`: local Claude skill install
- `codex`: local Codex skill install
- `grok`: local Grok skill install
- `grok-build`: local Grok skill install

### FH-Coaches

`FH-Coaches` now matches the current family-repo shape:

```text
FH-Coaches/
  family.json
  source/
  dist/
    grok/
    grok-build/
    claude-ai/
    claude-code/
    openai-skills-api/
    chatgpt-work/
    codex/
```

Its ChatGPT Work manual artifact path is:

```text
dist/chatgpt-work/
```

Start with:

```text
dist/chatgpt-work/INSTALL.md
```

## Target State

The intended product state is:

- one create command to start a family repo
- one deploy command to validate, build, and publish
- one canonical source per skill
- one generated deployable form per target
- no server or background control plane
- a truthful target map where every listed target is either:
  - fully supported
  - explicitly manual
  - explicitly stubbed / not yet implemented

The intended deployment outcome is:

- a family author can run `skill-deploy --source . --publish`
- the command publishes every target in `family.json`
- the result is deterministic and auditable

## Gaps Vs Target State

### Product Gaps

1. `chatgpt-work` is manual only.
   `skill-tooling` builds the correct manual deployable bundle, but it does not automatically install into the ChatGPT Work UI.

2. The OpenAI/ChatGPT split is still incomplete.
   `openai-skills-api` is a real documented API surface.
   `chatgpt-work` is a real product surface.
   A documented API bridge between them has not been established.

3. There is no documented ChatGPT Work creation API in this repo yet.
   The documented adjacent OpenAI surfaces currently cover hosted OpenAI Skills and triggering existing workspace agents, not creating ChatGPT Work skills.

### Workflow Gaps

1. Rollback is incomplete for built-in API publishers.
   Copy-mode rollback works.
   Local Grok/Claude/Codex skill installs now roll back.
   API rollback for hosted publishers is still not implemented.

2. Source frontmatter is standardized, but intentionally narrow.
   It now has a formal schema, but only supports the small metadata surface this project currently needs.

3. Generated target artifacts are structurally correct but not yet proven vendor-native for every target.
   For some targets they are still “our deployable representation,” not a vendor-defined package format.

### Documentation Gaps

1. The repo has multiple state docs and they can drift.
   `README.md`, `docs/project-state.md`, `docs/deployment-matrix.md`, and the family contract doc need to stay aligned.

2. The exact meaning of “supported” versus “manual” versus “stub” needs to stay explicit.
   This is especially important for `chatgpt-work`.

### FH-Coaches Gaps

1. `FH-Coaches` still needs an explicit decision on whether Grok targets should publish into your real `~/.grok/skills` environment or remain generated-only for now.

2. `FH-Coaches` has a few incidental local artifacts like `.DS_Store`.
   They are not part of the contract.

## WIP

There is no active in-repo contract migration in progress right now.

The major cleanup items from the last phase are already committed and merged:

- removed the non-required `overrides/` concept from the contract and code
- migrated generated family outputs from root-level target folders to `dist/<target>/`
- added `chatgpt-work` as a standard generated manual deployable target
- added built-in local Grok publishing via `grok-skills`
- added rollback support for built-in local Grok, Claude, and Codex skill publishers
- migrated `FH-Coaches` to the new contract

The remaining work is now product-gap work, not contract-cleanup work.

## Prioritized Work Plan

### P0

1. Keep the OpenAI target map honest.
   `openai-skills-api` is real.
   `chatgpt-work` is manual.
   No undocumented ChatGPT Work publisher should be added.

### P1

1. Implement rollback for built-in API publishers.
   `openai-skills` and `claude-agent` still persist state without rollback handlers.

2. Make target status explicit in CLI output and docs.
   The user should not have to infer whether a target is real, manual, or stubbed.

### P2

1. Evaluate whether `chatgpt-work` can ever be automated through a documented API.
   If not, leave it permanently manual and document that clearly.

2. Add packaging or GitHub Action support for turnkey use from family repos.

## Workflow Status

| Workflow Step | Current Status |
|---|---|
| Create family repo | Real tooling |
| Author canonical source skills in `source/` | Real tooling |
| Validate `family.json` | Real tooling |
| Validate source skill frontmatter (`name`, `description`) | Real tooling |
| Generate deployable artifacts in `dist/<target>/` | Real tooling |
| Generate ChatGPT Work manual upload bundle | Real tooling |
| Publish `openai-skills-api` | Real tooling |
| Publish `chatgpt-work` automatically | Manual only |
| Publish `claude-ai` | Real tooling |
| Publish `claude-code` | Real tooling |
| Publish `codex` | Real tooling |
| Publish `grok` | Real tooling |
| Publish `grok-build` | Real tooling |
| Publish all targets in manifest with one command | Partial |
| Git stage/commit/push/PR/merge from deploy | Real tooling |
| Roll back copy publishes | Real tooling |
| Roll back built-in API publishes | Not implemented |
| Roll back built-in local-skill publishes | Real tooling |

## Recommendation

The highest-value next move is to make the target list truthful in practice, not just in documentation:

1. decide whether `FH-Coaches` should publish Grok targets into your real `~/.grok/skills` environment or stay generated-only for now
2. implement hosted/API rollback for `openai-skills` and `claude-agent`
3. keep `openai-skills-api` and `chatgpt-work` explicitly separated until a documented creation API exists
