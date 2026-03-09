# Sentinel Core v1 — Baseline Model

## Purpose

The baseline model defines what Sentinel Core considers approved known-good state.

This is the center of the system.

Without a baseline, Sentinel can observe current state, but it cannot determine drift.

The baseline answers:

- what objects are in scope
- what state those objects are expected to have
- what data will be compared during checks
- what file content can be used for restore

---

## Baseline Definition

A baseline is a deterministic record of approved state for explicitly declared watched objects.

In Sentinel Core v1, that includes:

- watched files
- watched directories
- watched services
- watched packages

The baseline is created only by an explicit baseline operation.

It is never inferred automatically.

---

## Baseline Trust Rule

A baseline is the operator-approved definition of good state.

Sentinel does not try to infer whether a change was intentional.

It trusts only what has been explicitly baselined.

So the trust model is:

```text
declared watchlist + approved baseline = trusted state
