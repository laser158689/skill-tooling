---
name: skill-tooling
description: Tooling for scaffolding, validating, generating, and publishing external skill family repositories into multiple AI target ecosystems.
---

# skill-tooling

## Role

`skill-tooling` is the operational layer for a multi-target skill ecosystem.

It is not the canonical home of all skills. Instead, each family lives in its own repo, authors canonical skill files in `source/`, and uses this tooling to generate top-level target folders like `grok/`, `claude/`, and `codex/`.

## Commands

- `create-family` scaffolds a family repo with `source/`, `overrides/`, and generated target folder slots.
- `validate-family` validates family metadata, source files, and optional overrides.
- `skill-deploy` can read a local family repo or clone one from Git, generate target folders, and publish them through configured adapters.

## Publishing Model

Deployment is adapter-based.

- Copy publishers install generated target folders into configured filesystem roots.
- Command publishers hand those target folders to local wrapper commands for tool-specific integration.

## Ownership Model

- `source/` is canonical authored content.
- `overrides/` is optional authored target-specific content.
- Top-level target folders are generated artifacts and manual deployment views.
