---
name: skill-tooling
description: The skill-tooling family provides the core commands for creating and deploying skill families in the universal skill repository and deployer system. It includes skill-deploy and create-family.
---

# skill-tooling Family

This family contains the operational tooling for the universal skill system.

## Scripts
- `skill-deploy` — Deploy a family from its GitHub master repo into Grok (and generate Codex output)
- `create-family` — Scaffold a brand new skill family with proper structure and local git initialization

## Usage
These scripts are meant to be run from the master repo after it has been deployed, or directly during development.

## Master Location
This family lives in its own GitHub repository: `skill-tooling`

## Deployment
Deploy this family itself using:
```bash
bash skill-deploy --repo YOUR_USERNAME/skill-tooling
```