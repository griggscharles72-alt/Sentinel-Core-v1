# Sentinel-Core-v1

Deterministic drift detection and restore decisioning for explicitly declared stable assets.

Sentinel Core v1 is not a backup monster, not a full system healer, and not a workspace tracker. It is a narrow, reliable layer that defines a known-good baseline, checks current state against that baseline, reports drift, and can optionally restore approved assets from a local known-good source.

---

## Purpose

Sentinel Core exists to protect the small set of files, services, directories, and packages that must remain stable.

Its job is to:

- define what should exist
- define the expected state of those assets
- compare live state against that baseline
- report drift deterministically
- optionally restore from a known-good local copy

That is the whole scope.

---

## Design Philosophy

The closest thing to “100% works” is minimum ambiguity.

Sentinel Core v1 is intentionally small:

- narrow watch scope
- explicit baseline
- explicit drift comparison
- explicit restore policy
- one local restore source
- no hidden automation
- no mixed concerns

This keeps the layer trustworthy.

---

## Core Model

### Drift Detection

Let:

- `X*` = declared known-good baseline state
- `Xt` = current observed state
- `Δ` = detected drift

Then:

```text
D(Xt, X*) -> Δ
