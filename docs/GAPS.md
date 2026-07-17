# Gaps

This document lists the gaps between the current state and the target state.

## P0 Gaps

### 1. No unified vendor-native packaging model

Current state:
- some targets are represented by project-specific transformed text bundles

Needed state:
- each target should produce a clearly vendor-native package or artifact contract

Fix:
- document one artifact contract per target
- make the build step emit those contracts explicitly

### 2. Incomplete enterprise target taxonomy

Current state:
- the target list is mostly truthful now, but still incomplete at the enterprise level

Needed state:
- explicit product-surface mapping for:
  - ChatGPT workspace skills
  - OpenAI plugin packaging
  - Claude Skills
  - Grok web/app skills
  - local developer surfaces

Fix:
- promote target taxonomy into a first-class documented model
- add missing enterprise-facing targets only when the product surface is confirmed

### 3. Incomplete rollback for API publishers

Current state:
- local installs and copy-mode rollback exist
- API rollback is not fully implemented

Needed state:
- all automated publishers roll back cleanly

Fix:
- add state snapshots and reverse mutation logic for API-managed targets

## P1 Gaps

### 4. Manual enterprise surfaces are not fully normalized

Current state:
- `chatgpt-work` and `claude-ai` are manual handoff bundles
- `grok-web` and `openai-plugin` now also have manual handoff/package bundles

Needed state:
- manual surfaces should still emit polished native artifacts, consistent install guides, and artifact manifests

Fix:
- formalize manual target bundle contracts
- add validation for generated manual packages

Status update:
- this is now partly addressed
- manual targets now have isolated target-specific artifact-contract verification
- the remaining gap is proving real vendor UI/admin acceptance beyond the generated artifact shape

### 5. OpenAI enterprise packaging strategy is incomplete

Current state:
- `openai-skills-api` exists
- `openai-plugin` now exists as a manual package surface
- `chatgpt-work` exists as a manual surface

Needed state:
- a complete OpenAI model that distinguishes:
  - hosted Skills API
  - ChatGPT workspace skills
  - plugin packaging as the likely enterprise distribution unit

Fix:
- keep `openai-plugin` as the package surface until a real supported workspace publish path is documented
- keep `chatgpt-work` manual until a real supported publish path is documented

Status update:
- `chatgpt-work` now enforces the currently known uploader rule that skill `name` must be a slug-safe identifier
- `openai-plugin` remains artifact-verified only

### 6. Claude enterprise automation strategy is incomplete

Current state:
- `claude-ai` is manual
- `claude-code` is local install

Needed state:
- confirmed packaging and governance model for org-provisioned Claude Skills

Fix:
- keep `claude-ai` manual until Anthropic exposes a real documented automation path
- improve native package generation for Claude uploads

Status update:
- `claude-ai` now has its own artifact-contract verifier
- Anthropic UI acceptance is still not proven by automation in this repo

### 7. Grok enterprise automation strategy is incomplete

Current state:
- `grok` and `grok-build` publish locally
- `grok-web` now exists as a manual web/app surface

Needed state:
- separate Grok web/app admin distribution from Grok Build developer-local distribution

Fix:
- keep `grok-web` separate from local Grok / Grok Build installs
- keep local Grok Build installs explicit and separate

## P2 Gaps

### 8. Source skill metadata is intentionally minimal

Current state:
- only `name` and `description` are standardized

Needed state:
- enough portable metadata to support better package generation, discovery, and governance

Fix:
- extend the source frontmatter schema carefully and only where multiple targets benefit

### 9. Artifact provenance is not first-class enough

Current state:
- receipts and state exist

Needed state:
- deterministic artifact manifests tied to commit SHA and family version

Fix:
- emit build manifests and checksums per target

### 10. Documentation still has multiple layers

Current state:
- several historical docs can drift

Needed state:
- one canonical architecture doc set

Fix:
- make this doc set canonical
- reduce older docs to summaries or references

## Non-Goals

These are not current goals unless requirements change:

- launching a server
- building a database-backed control plane
- inventing undocumented vendor APIs
- hiding manual vendor admin steps behind misleading success messages
