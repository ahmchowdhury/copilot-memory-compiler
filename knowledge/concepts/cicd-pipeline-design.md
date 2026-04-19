---
title: "CI/CD Pipeline Design"
aliases: [github-actions, deployment-pipeline]
tags: [devops, docker, github-actions]
sources:
  - "daily/2026-04-16.md"
created: 2026-04-16
updated: 2026-04-16
---

# CI/CD Pipeline Design

GitHub Actions pipeline for Python FastAPI projects using a multi-stage approach: parallel lint and test jobs, Docker builds with layer caching, and deployment to Azure Container Apps.

## Key Points

- Multi-stage pipeline: lint (ruff), type check (mypy), test (pytest), build, deploy
- Run lint and tests in parallel for speed
- Docker layer caching via `docker/build-push-action` with GitHub Actions cache
- Pin GitHub Actions versions with SHA hashes for supply chain security
- Use `--no-cache-dir` in pip install to reduce Docker image size

## Details

The Dockerfile should order layers so that `requirements.txt` is copied and installed before the application source code. This ensures the dependency layer is cached and only rebuilt when requirements change, significantly speeding up builds.

For production deployments, use multi-stage Docker builds: a builder stage that installs dependencies, and a slim runtime stage that copies only the installed packages and application code.

## Related Concepts

- [[concepts/fastapi-jwt-authentication]] - Auth secrets injected via CI/CD pipeline
- [[concepts/database-migration-strategy]] - Migrations run as pre-deploy step

## Sources

- [[daily/2026-04-16.md]] - Designed the GitHub Actions pipeline architecture
