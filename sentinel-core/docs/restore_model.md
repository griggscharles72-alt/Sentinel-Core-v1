# Sentinel Core v1 — Runbook

## Purpose

This runbook defines the practical operator workflow for Sentinel Core v1.

It explains:

- how to prepare the repo
- how to validate the environment
- how to create a baseline
- how to run checks
- how to generate reports
- how to plan restore
- how to apply restore
- how to handle intentional protected changes

This is the operational guide for using the layer safely.

---

## Core Principle

Sentinel Core works by comparing approved baseline state against live observed state.

It does not decide intent.

It does not guess whether a change was authorized.

It uses explicit baseline approval.

So the practical rule is:

```text
approved baseline = trusted state
