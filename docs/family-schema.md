# Family Manifest Schema

The family manifest has an explicit schema at [schemas/family.schema.json](../schemas/family.schema.json).

That schema defines the data model for the family definition regardless of whether you think about it as JSON or YAML.

The canonical manifest filename is `family.json`.

The tooling does not currently support repo-named manifests such as `FH-Coaches.yml`.
Using one fixed filename keeps family repos consistent and makes validation and deployment simpler.

## Current Shape

```json
{
  "skill_family": {
    "name": "customer-support",
    "description": "Reusable support skills for support teams",
    "version": "0.1.0"
  },
  "targets": [
    "grok",
    "claude-ai",
    "codex"
  ]
}
```

## Rules

- `skill_family.name` is a lowercase slug.
- `skill_family.description` is required.
- `skill_family.version` is required.
- `targets` must be a non-empty list of supported target ids.
- Unknown top-level fields are rejected.
- Unknown fields inside `skill_family` are rejected.

## YAML Note

If you choose to represent the same data as YAML in surrounding documentation or external tooling, the field names and value types should remain identical to the JSON schema.

## Contract

The manifest key is `skill_family`.

Older manifests that use `family` are not supported by the current contract.
