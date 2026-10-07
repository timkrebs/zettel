# 0005. Optimistic locking with a version column

- Status: Proposed
- Date: 2026-10-07

## Context

Several household members edit the same list at the same time. Without protection, the last write silently overwrites earlier ones. Pessimistic locks do not fit a request/response API used from phones.

## Decision

`lists` and `items` carry a `version` integer. Mutating RPCs take `expected_version`. Updates run as `UPDATE … SET version = version + 1 WHERE id = $1 AND version = $2`. If no row is affected, the handler returns `codes.Aborted`.

## Consequences

- Conflicts are detected, never lost silently.
- The app must handle `Aborted`: reload the item and show a short hint.
- Checking off an item that someone else just renamed fails once and needs a retry; acceptable for a shopping list.
