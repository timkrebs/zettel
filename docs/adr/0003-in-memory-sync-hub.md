# 0003. In-memory sync hub with a single replica

- Status: Proposed
- Date: 2026-10-07

## Context

Changes to a list must show up instantly on all devices of a household. Clients hold a gRPC server stream (`Subscribe`). Something has to fan out events from list-service to every open stream. A message broker (NATS, Redis) would add infrastructure before the basics work.

## Decision

sync-service keeps subscriptions in memory, keyed by household ID, and runs with exactly one replica. list-service calls `SyncInternalService.Publish` after every successful change. sync-service forwards the event to all subscribers of that household. Slow clients with a full buffer get their stream closed.

## Consequences

- Simple to build and test; teaches goroutines, channels and stream lifecycles.
- Events are lost when sync-service restarts. The app reloads data after every reconnect, so it converges again.
- No horizontal scaling. Moving to NATS later is a backlog item and a new ADR.
- A failed `Publish` must not fail the user's write; list-service logs it and carries on.
