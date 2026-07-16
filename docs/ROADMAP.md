# Roadmap

This roadmap is ordered by workflow value and architectural dependency.

## Phase 1: Stabilize The Contract

Goal:
- make the source and target model unambiguous

Tasks:
- finalize the canonical architecture doc set
- keep the family repo contract strict: `family.json`, `source/`, `dist/`, `.skill-tooling/`
- keep source skills tool-neutral
- define target classes: `api`, `local_install`, `manual_ui`, `package_only`
- keep manual targets explicit in CLI output and docs

Exit criteria:
- there is one clear answer to what a family repo is and what each target means

## Phase 2: Normalize Artifact Contracts

Goal:
- make every generated target output clearly vendor-native

Tasks:
- define the exact bundle contract for each target
- emit artifact manifests in `dist/<target>/`
- improve generated install guides for manual targets
- validate target bundle shape in tests

Exit criteria:
- every target output is a documented package, not just an internal representation

## Phase 3: Harden Publish And Rollback

Goal:
- make deploy safe and reversible

Tasks:
- implement full rollback for API-managed publishers
- make preflight mandatory for all requested targets before publish begins
- keep publish ordering deterministic
- roll back automated targets in reverse order on failure

Exit criteria:
- automated deploys do not leave silent partial state behind

## Phase 4: Strengthen Enterprise Governance

Goal:
- make the tool suitable for controlled multi-repo use

Tasks:
- add artifact provenance tied to commit SHA
- improve receipts and state manifests
- expand CI coverage
- add secret scanning and redaction checks
- formalize versioning and deprecation guidance

Exit criteria:
- every deployment is auditable and operationally safe

## Phase 5: Expand OpenAI Enterprise Support

Goal:
- align with OpenAI's real enterprise distribution model

Tasks:
- keep `openai-skills-api` stable
- keep `chatgpt-work` manual unless official automation is documented
- keep `openai-plugin` as the package surface unless official automation is documented
- preserve `codex` as a local developer surface, not the enterprise abstraction

Exit criteria:
- OpenAI targets cleanly separate API, workspace, plugin, and local developer use cases

## Phase 6: Expand Claude Enterprise Support

Goal:
- align with Claude's real skill governance model

Tasks:
- keep `claude-ai` as a manual admin flow unless Anthropic documents automation
- improve native Claude upload package generation
- keep `claude-code` separate as a local developer surface

Exit criteria:
- Claude targets no longer blur org-hosted skills with local file installs

## Phase 7: Expand Grok Enterprise Support

Goal:
- align with xAI's split between Grok skills and Grok Build

Tasks:
- preserve local Grok Build install behavior where valid
- keep `grok-web` separate from the local Grok / Grok Build surfaces
- improve Grok-native packaging where official guidance exists

Exit criteria:
- Grok web/app and Grok Build are modeled as separate product surfaces when required

## Phase 8: Distribution And Reuse

Goal:
- make `skill-tooling` easy to adopt across many family repos

Tasks:
- improve GitHub Actions integration
- publish reusable CI snippets or workflow templates
- document family-repo CI standards

Exit criteria:
- a new family repo can adopt the standard workflow with minimal custom setup

## Immediate Priorities

In strict order:

1. keep the architecture docs canonical and aligned
2. normalize per-target artifact contracts
3. implement API rollback
4. harden security and provenance
5. harden `openai-plugin`, `grok-web`, `chatgpt-work`, and `claude-ai` manual bundle contracts
6. research and implement better enterprise-native Claude and Grok packaging where officially supported
