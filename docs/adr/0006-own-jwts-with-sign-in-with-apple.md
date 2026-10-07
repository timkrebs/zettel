# 0006. Own JWTs with Sign in with Apple

- Status: Proposed
- Date: 2026-10-07

## Context

Users sign in with their Apple ID. Apple's identity token proves who the user is, but it is short-lived and meant for the backend to verify once. Services need a cheap way to authenticate every call.

## Decision

- user-service verifies Apple's identity token (signature via Apple's JWKS, `iss`, `aud`, `exp`) only at sign-in.
- user-service then issues its own access JWT (Ed25519, 15 minutes) and a refresh token (opaque, 30 days, stored hashed, rotated on every use).
- Only user-service holds the private key. All services verify access tokens with the public key.
- Until sprint 10 a `DevSignIn` RPC issues tokens for a display name; it is disabled outside the local overlay.

## Consequences

- Every call is verified locally without a network round trip.
- Revoking access takes effect only when the access token expires (at most 15 minutes).
- Key rotation needs a small plan later (key ID in the JWT header).
- The app must refresh tokens transparently when a call returns `Unauthenticated`.
