# Current State

This document describes the actual state of `skill-tooling` as of **July 16, 2026**.

## Purpose

`skill-tooling` is the central tooling repo for managing **skill family repositories** that live in their own Git repos.

The intended operating model is:

- one canonical source format per skill
- one family manifest per family repo
- one deploy command to validate, build, and publish
- no server, daemon, or hosted control plane

## Current Product Shape

Today `skill-tooling` is a Python CLI with shell entrypoints:

- `scripts/create-family`
- `scripts/validate-family`
- `scripts/skill-deploy`
- `scripts/rollback-deploy`

The repo is not itself a family repo. It is the shared deploy/build tool for family repos such as `FH-Coaches`.

## Current Family Repo Contract

Current family repos follow this shape:

```text
my-family/
  family.json
  README.md
  source/
    skill-a.md
    skill-b.md
  dist/
    <target>/
  .skill-tooling/
    deployments/
```

Ownership rules:

- humans and LLMs author only `source/*.md`
- `skill-tooling` manages `dist/<target>/`
- `skill-tooling` manages `.skill-tooling/deployments/`

There is no authored per-target override layer in the current contract.

## Current Source Contract

Source skills are Markdown files with a narrow YAML frontmatter contract.

Currently supported frontmatter fields:

- `name`
- `description`

Family-level targets are declared in `family.json`.
Per-skill target declarations are not part of the source contract.

## Current Supported Targets

Current target ids:

- `grok`
- `grok-build`
- `grok-web`
- `claude-ai`
- `claude-code`
- `openai-skills-api`
- `openai-plugin`
- `chatgpt-work`
- `codex`

Current semantics:

- `grok`: local Grok skill install
- `grok-build`: local Grok Build skill install
- `grok-web`: manual Grok web/app Skills handoff bundle
- `claude-ai`: manual Claude Skills handoff bundle
- `claude-code`: local Claude Code skill install
- `openai-skills-api`: hosted OpenAI API publisher
- `openai-plugin`: manual OpenAI plugin package bundle
- `chatgpt-work`: manual ChatGPT Skills handoff bundle
- `codex`: local Codex skill install

## Current Build Behavior

`skill-deploy` currently does the following:

1. load `family.json`
2. validate manifest schema
3. discover `source/*.md`
4. validate source frontmatter
5. generate target-specific output under `dist/<target>/`
6. optionally publish requested targets
7. write receipts and state under `.skill-tooling/deployments/`

## Current Publish Behavior

Publish behavior today is mixed across four classes:

### API-managed

- `openai-skills-api`

### Local install

- `grok`
- `grok-build`
- `claude-code`
- `codex`

### Manual UI handoff

- `grok-web`
- `claude-ai`
- `openai-plugin`
- `chatgpt-work`

### Adapter hooks

- generic `copy`
- generic `command`
- optional `claude-agent`

## What Is Real Today

The following capabilities are implemented and working:

- create a family repo
- validate `family.json`
- validate source frontmatter
- generate `dist/<target>/` bundles
- publish all targets listed in a family manifest in one command
- auto-publish local install targets
- auto-publish `openai-skills-api`
- prepare manual bundles for `claude-ai`
- prepare manual bundles for `grok-web`
- prepare manual plugin packages for `openai-plugin`
- prepare manual bundles for `chatgpt-work`
- load local deployment env vars from `skill-tooling/.env`
- keep deployment state and receipts
- roll back copy-based publishes
- roll back built-in local skill installs
- optionally stage, commit, push, open PRs, and merge during deploy

## What Is Not Real Today

The following things are not implemented or not proven:

- automated ChatGPT workspace skill creation through an official supported API
- automated Claude org skill creation through an official supported API
- automated Grok web/app skill creation through an official supported API
- a single universal enterprise distribution API across vendors
- full rollback for API-managed publishers
- a fully normalized vendor-native packaging model for every target

## Current Security Model

Current secret handling:

- default `.env` is loaded from the `skill-tooling` repo
- family repo `.env` files are not implicitly trusted
- `.env` files are git-ignored
- allowed env keys are restricted
- inline secrets are not intended to live in `publish-config.json`

This is materially better than the earlier state, but not yet the final security model.

## Current Architectural Truth

The key correction is this:

`skill-tooling` does **not** currently deploy one universal skill object everywhere.
It builds one canonical family source into several different target surfaces, some automated and some manual.

That is the correct current description of the system.
