# Zettel

A shared shopping list for households. Everyone in the household edits the same lists, and changes show up instantly on every device.

Zettel is a learning project: a Go backend split into gRPC microservices, a SwiftUI iOS app, and a deployment to Kubernetes (local k3d first, then a homelab K3s cluster).

## Architecture at a glance

| Service | Responsibility |
| --- | --- |
| `user-service` | Sign in with Apple, JWTs, households, invites |
| `list-service` | Lists and items, optimistic locking |
| `sync-service` | Live updates to devices via gRPC server streaming |

All three run behind a Traefik ingress and share one PostgreSQL instance, with one schema per service.

## Documentation

- [Project plan & architecture](docs/PLAN.md) – scope, modules, API, data model, deployment, sprints
- [Architecture decision records](docs/adr/)
- Work is tracked as GitHub issues and in the **Zettel** GitHub Project, one iteration per two-week sprint.

## Status

Sprint 0 – Foundation. Nothing runs yet.
