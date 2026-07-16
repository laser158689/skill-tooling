# Target State

This document defines the intended architecture for `skill-tooling`.

## Product Goal

The end state is:

- one canonical family repo per domain
- one canonical source format per skill
- one deploy command
- vendor-native build outputs
- automated publish only where a real supported publish surface exists
- explicit manual handoff where the vendor requires a UI workflow
- auditability, rollback, and truthful status output

## Core Principle

The system should **not** pretend there is one cross-vendor enterprise skill deploy API.

Instead, it should do this:

1. manage one canonical source model
2. build one native artifact per vendor surface
3. publish into each vendor's real governance or runtime surface
4. report exactly what happened

## Canonical Object Model

The canonical authored object is a **skill family repo** with:

- one `family.json`
- many `source/*.md` source skills
- generated `dist/<target>/` artifacts
- generated deployment state under `.skill-tooling/`

The canonical source skill should remain tool-neutral.

## Target Classes

Every target must belong to exactly one publish class.

### `api`

Definition:
- published through a real supported API

Examples:
- `openai-skills-api`

### `local_install`

Definition:
- published by writing files into a real local runtime surface

Examples:
- `codex`
- `claude-code`
- `grok-build`
- `grok`

### `manual_ui`

Definition:
- the tool generates the exact native handoff artifact and install instructions
- a human admin completes the final step in the vendor UI

Examples:
- `chatgpt-work`
- `claude-ai`
- likely future `grok-web`

### `package_only`

Definition:
- the tool builds a package, but does not yet claim a deploy workflow

This class should only be used for future targets during research or packaging bring-up.

## Target Naming Model

Targets should name real product surfaces, not internal guesses.

Long-term target map:

- `openai-skills-api`
- `chatgpt-work`
- `openai-plugin`
- `codex`
- `claude-ai`
- `claude-code`
- `grok-web`
- `grok-build`

Targets that do not correspond to a real product surface should be removed.

## Canonical Repo Shape

Required family layout:

```text
my-family/
  family.json
  README.md
  source/
    skill-a.md
  dist/
    .gitkeep
```

Generated tool state:

```text
my-family/
  .skill-tooling/
    deployments/
      receipts/
      state/
```

No additional authored directories should be introduced unless they become part of the documented contract.

## Source Skill Contract

Source skills should remain simple Markdown with YAML frontmatter.

Required fields:

- `name`
- `description`

Preferred future additions:

- `slug`
- `tags`
- `audience`
- `triggers`
- `constraints`

The source contract should remain tool-neutral and minimally sufficient for all adapters.

## Build Architecture

The build pipeline should be:

1. load manifest
2. discover source skills
3. validate source files
4. normalize skill metadata
5. build one vendor-native artifact set per target
6. emit an artifact manifest
7. emit human instructions for any manual targets

Build output requirements:

- deterministic
- idempotent
- inspectable
- traceable to source commit

## Publish Architecture

Each target should be implemented through a target adapter with four responsibilities:

- `preflight`
- `publish`
- `verify`
- `rollback`

Rules:

- do not publish anything if preflight fails
- manual targets never say `Deployed`
- unsupported targets fail before publish begins
- local installs must report the install root
- API publishers must persist remote identifiers for reconciliation

## Verification Model

Every target must define what verification means.

Examples:

- `api`: API create/update succeeded and remote IDs reconciled
- `local_install`: files installed into the expected root and discoverable
- `manual_ui`: native bundle and install guide generated successfully
- `package_only`: artifact manifest produced successfully

## Rollback Model

The target state requires rollback across all automated publish targets.

Rules:

- snapshot prior automated state before mutation
- publish automated targets in a deterministic order
- roll back prior automated targets in reverse order on failure
- preserve manual bundles even when automated publish fails

## Security Model

The target state requires:

- default secret loading only from `skill-tooling/.env`
- committed `.env.example`, never committed real `.env`
- no secret echo in logs
- no secret persistence in receipts
- explicit support for service-account credentials where vendors allow them
- secret scanning in CI

## Governance Model

The target state requires:

- PR-based changes
- CI validation in `skill-tooling`
- CI validation in family repos
- commit-to-artifact traceability
- deployment receipts
- versioned releases
- deprecation policy for targets and schema

## Operator Experience

The ideal operator flow is:

```bash
scripts/skill-deploy --source /path/to/family --publish
```

That single command should:

- validate
- build every declared target
- auto-publish real automated targets
- prepare manual bundles for manual targets
- verify results
- roll back automated targets on failure
- print a final summary that distinguishes:
  - deployed
  - prepared
  - manual step required
  - unsupported

## Enterprise Management Model

The enterprise strategy should be:

- central source governance in Git
- vendor-native artifact generation
- vendor-native admin or runtime distribution
- no fake abstraction layer that hides real vendor differences

That is the target state `skill-tooling` should be built toward.
