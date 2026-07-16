# LLM Authoring Contract

This document is the shortest authoritative contract for any LLM that needs to create or update a skill family repository managed by `skill-tooling`.

If you are an LLM writing into a family repo, follow this file exactly and do not invent extra layers such as `overrides/`, per-skill target declarations, alternate manifest filenames, or target-specific authored source folders.

## Required Family Repo Shape

```text
family-repo/
  family.json
  source/
    skill-one.md
    skill-two.md
  dist/
    <target>/
```

Rules:

- Write human-authored skill source files only into `source/`.
- Treat `dist/` as generated output owned by `skill-tooling`.
- Do not hand-edit generated files under `dist/` unless the user explicitly asks for generated output surgery.
- Do not create `overrides/`.
- Do not create `grok/`, `claude-ai/`, `codex/`, or other root-level generated target folders.

## Required Manifest File

The manifest filename must be:

```text
family.json
```

Do not use:

- `FH-Coaches.yml`
- `family.yaml`
- `family.yml`
- any repo-specific manifest name

Minimum valid shape:

```json
{
  "skill_family": {
    "name": "customer-support",
    "description": "Reusable support skills for support teams",
    "version": "0.1.0"
  },
  "targets": [
    "grok",
    "grok-build",
    "grok-web",
    "claude-ai",
    "claude-code",
    "openai-skills-api",
    "openai-plugin",
    "chatgpt-work",
    "codex"
  ]
}
```

Manifest rules:

- `skill_family.name` must be a lowercase slug using letters, numbers, and hyphens.
- `skill_family.description` must be non-empty.
- `skill_family.version` must be non-empty.
- `targets` is defined only at the family level.

## Required Source Skill Format

Each skill must live at:

```text
source/<skill-id>.md
```

Minimum valid source file:

```md
---
name: Researcher
description: Investigate and synthesize relevant information
---

# Researcher

Skill instructions go here.
```

Source rules:

- `<skill-id>` comes from the filename stem.
- Skill ids may use letters, numbers, dots, underscores, or hyphens.
- Frontmatter keys allowed:
  - `name`
  - `description`
- Do not add `targets` to source frontmatter.
- Do not add nested YAML structures unless the contract is explicitly expanded in this repo.
- Keep the body as normal Markdown after the frontmatter.

## What An LLM Should Do

When asked to add a new skill to a family repo:

1. Do not edit `dist/` directly.
2. Create one new file under `source/`.
3. Use valid frontmatter with only `name` and `description`.
4. Keep `family.json` as the canonical manifest.
5. Update `family.json` only if family-level metadata or the family target list actually needs to change.
6. Let `skill-tooling` regenerate `dist/` by running deploy later.

## What An LLM Must Not Invent

Do not invent:

- `overrides/`
- per-skill target lists
- alternate manifest filenames
- target-specific source subdirectories
- server processes
- background control planes
- undocumented publish APIs

## Canonical References

For more detail, use these files:

- [family-repo-contract.md](./family-repo-contract.md)
- [family-schema.md](./family-schema.md)
- [../schemas/family.schema.json](../schemas/family.schema.json)
- [../schemas/source-skill-frontmatter.schema.json](../schemas/source-skill-frontmatter.schema.json)
