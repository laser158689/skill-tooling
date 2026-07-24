# Security Policy

## Reporting A Vulnerability

Do not open a public issue for a suspected vulnerability, exposed credential, or privacy concern.

Use GitHub's private vulnerability reporting flow:

1. Open the repository's **Security** tab.
2. Choose **Advisories**.
3. Choose **Report a vulnerability**.

Include the affected version or commit, reproduction steps, impact, and any suggested mitigation. Avoid including real credentials or personal data; use redacted examples.

## Supported Version

Security fixes are applied to the current `main` branch. This project has not yet published versioned security-support releases.

## Security Boundaries

- Local `.env` and deployment-history files must never be committed.
- API publishing only sends the primary OpenAI key to the official OpenAI API host.
- Custom API hosts require a separate `SKILL_TOOLING_CUSTOM_API_KEY` credential.
- Authenticated API calls reject redirects and non-HTTPS endpoints.
- `command`, verification-command, and command-rollback publishers execute local programs from trusted configuration. Treat publisher configuration and rollback receipts as executable input.
- Filesystem rollback requires explicit `--allow-file-rollback` confirmation and should only use receipts generated locally.
- Generated Git commits stage only the family manifest, canonical source, generated docs, and generated distribution folders.

## Maintainer Release Checks

Before a public release:

1. Run the smoke and security regression tests.
2. Run a full-history secret scan.
3. Review tracked files for private paths, personal data, local databases, archives, and credentials.
4. Confirm GitHub secret scanning, push protection, dependency alerts, code scanning, and branch protection remain enabled.
