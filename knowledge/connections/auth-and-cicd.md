---
title: "Connection: Auth and CI/CD"
connects:
  - "concepts/fastapi-jwt-authentication"
  - "concepts/cicd-pipeline-design"
sources:
  - "daily/2026-04-15.md"
  - "daily/2026-04-16.md"
created: 2026-04-16
updated: 2026-04-16
---

# Connection: Auth and CI/CD

## The Connection

JWT authentication configuration and CI/CD pipeline design intersect at secret management — the same environment variables that store JWT secrets locally must be injected securely during deployment.

## Key Insight

The decision to use environment variables for JWT secrets (rather than config files) directly simplified the CI/CD pipeline. GitHub Actions secrets map 1:1 to the env vars the app expects, with no file-mounting or volume management needed in Container Apps.

## Evidence

- In the auth session (2026-04-15), the decision was made to use environment variables for all secrets
- In the CI/CD session (2026-04-16), this enabled a straightforward secret injection via GitHub Actions + Container Apps environment config

## Related Concepts

- [[concepts/fastapi-jwt-authentication]]
- [[concepts/cicd-pipeline-design]]
