# Sentinel Core v1 — Architecture

## Purpose

Sentinel Core v1 is a deterministic drift-detection and restore-decision layer for explicitly declared stable assets.

It exists to protect a narrow set of files, directories, services, and packages by:

- defining known-good state
- observing current state
- detecting drift
- reporting drift
- optionally restoring from a known-good local source

This layer is intentionally small and explicit.

---

## Core Model

Let:

- `X*` = declared known-good baseline state
- `Xt` = current observed state
- `Δ` = detected drift

Then:

```text
D(Xt, X*) -> Δ
