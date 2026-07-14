# ADR 001: Mock-First API Architecture

## Status
Approved

## Context
We have a team of two developers: one focused primarily on the Next.js frontend and AI engine, and the other on the backend APIs, database persistence, and infrastructure. To allow both to work in parallel without blocking each other, we need a mechanism where the frontend can run with high-fidelity simulated API responses that exactly match the backend contracts.

## Decision
We will define a typescript interface `CurioApi` in `frontend/lib/api/client.ts`. 

We will build two implementations:
1. `MockCurioApi` (runs entirely in-memory on the client, simulating state transitions, delay times, message histories, and reports).
2. `HttpCurioApi` (uses `fetch` to connect to the actual FastAPI endpoints).

The client will choose the provider at runtime using the environment variable:
`NEXT_PUBLIC_USE_MOCK_API=true`

Both clients must return the exact same data shapes.

## Consequences
- Chinmay can build, test, and style the entire interactive UI, mode switches, and evaluation dashboard without starting the Python server.
- The contract files in `contracts/` become the single source of truth.
- Integrating the frontend with the real backend becomes a simple matter of changing the environment variable to `false` and validating network connectivity.
