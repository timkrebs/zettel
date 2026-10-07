# 0002. gRPC through the ingress, no API gateway

- Status: Proposed
- Date: 2026-10-07

## Context

The iOS app needs to call three services. Options are a dedicated API gateway service (or gRPC-Gateway/REST), or routing gRPC calls directly through the cluster ingress by service path. Both k3d and K3s ship Traefik, which supports HTTP/2 cleartext (h2c) backends.

## Decision

The app speaks gRPC directly. Traefik routes by the gRPC path prefix (`/zettel.<service>.v1.<Service>/`) to the matching Kubernetes service. Internal services (`MembershipService`, `SyncInternalService`) get no route. Every service verifies the JWT itself with a shared interceptor from `internal/platform/auth`.

## Consequences

- No extra hop and no extra service to build and run.
- Auth runs in every service; it must live in one shared, well-tested package.
- Routing rules have to be kept in sync with proto service names.
- Cross-cutting concerns such as rate limiting are interceptors, not gateway features.
