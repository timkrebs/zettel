# Architecture Decision Records

Each ADR records one decision: the context, the decision and its consequences. New ADRs copy [`template.md`](template.md) and take the next number. A decision that changes later gets a new ADR that supersedes the old one; old ADRs are never rewritten.

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-monorepo-single-go-module.md) | Monorepo with a single Go module | Proposed |
| [0002](0002-grpc-through-ingress-no-gateway.md) | gRPC through the ingress, no API gateway | Proposed |
| [0003](0003-in-memory-sync-hub.md) | In-memory sync hub with a single replica | Proposed |
| [0004](0004-one-postgres-schema-per-service.md) | One Postgres schema per service | Proposed |
| [0005](0005-optimistic-locking.md) | Optimistic locking with a version column | Proposed |
| [0006](0006-own-jwts-with-sign-in-with-apple.md) | Own JWTs with Sign in with Apple | Proposed |
