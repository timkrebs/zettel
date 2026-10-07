# 0004. One Postgres schema per service

- Status: Proposed
- Date: 2026-10-07

## Context

Microservices should own their data. Running one database server per service is costly in a homelab and adds operational work. A single shared schema would let services couple through tables.

## Decision

One PostgreSQL instance and database `zettel`. Each service gets its own schema and its own DB role with rights only on that schema: `user_svc` and `list_svc`. sync-service has no database. Each service runs its own migrations on startup.

## Consequences

- One Postgres to run, back up and monitor.
- Ownership is enforced by permissions, not just by convention.
- No foreign keys across schemas: list-service stores `household_id` without a constraint and asks user-service for membership.
- Splitting into separate databases later only changes connection strings.
