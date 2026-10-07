# 0001. Monorepo with a single Go module

- Status: Proposed
- Date: 2026-10-07

## Context

Zettel consists of three Go services, shared protobuf definitions, Kubernetes manifests and an iOS app. It is built by one person with 3–5 hours per week. Keeping versions of shared code in sync across repositories would cost time that should go into features.

## Decision

All code lives in one repository, `github.com/timkrebs/zettel`, with a single `go.mod`. Services live under `cmd/<service>` and `internal/<service>`; shared code under `internal/platform`. Protobuf definitions live in `proto/`, generated Go code in `gen/go/` and is committed.

## Consequences

- A change to a proto and all its callers is one commit and one PR.
- `internal/` prevents other modules from importing the services' code.
- All services share the same dependency versions; one service cannot upgrade a library alone.
- CI builds and tests everything on every change, which is fine at this size.
