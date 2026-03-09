# Sentinel Core v1 — Restore Model

## Purpose

The restore model defines how Sentinel Core moves from detected drift toward approved repair.

It is intentionally narrow.

Restore in v1 is not a general healing system.  
It is a controlled, explicit, local restore process for supported objects only.

The restore model answers:

- what can be restored
- what cannot be restored
- where restore truth comes from
- when restore is allowed
- how restore is applied
- how restore results are recorded

---

## Core Restore Equation

Sentinel first detects drift:

```text
D(Xt, X*) -> Δ
