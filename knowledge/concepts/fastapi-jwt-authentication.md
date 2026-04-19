---
title: "FastAPI JWT Authentication"
aliases: [fastapi-auth, jwt-auth]
tags: [python, fastapi, security]
sources:
  - "daily/2026-04-15.md"
created: 2026-04-15
updated: 2026-04-15
---

# FastAPI JWT Authentication

JWT authentication in FastAPI uses python-jose for token encoding/decoding, with tokens passed via the Authorization header using the Bearer scheme. Access tokens default to 30-minute expiration, while refresh tokens are stored server-side.

## Key Points

- Use python-jose over PyJWT for better algorithm support
- Authorization header + Bearer scheme for API-first applications
- HttpOnly cookies are preferred for server-rendered web apps (XSS protection)
- Never hardcode secrets — use environment variables
- Set token expiration: 30 minutes for access tokens

## Details

The recommended pattern creates a FastAPI dependency that extracts and validates the JWT from the Authorization header. This dependency can be injected into any route that requires authentication.

Refresh tokens should never be stored in localStorage due to XSS vulnerability. Instead, store them server-side (e.g., in a database or Redis) and issue new access tokens via a dedicated refresh endpoint.

## Related Concepts

- [[concepts/database-migration-strategy]] - Auth tables require migration management
- [[concepts/cicd-pipeline-design]] - Auth config must be injected via CI/CD secrets

## Sources

- [[daily/2026-04-15.md]] - Initial setup during FastAPI project scaffolding
