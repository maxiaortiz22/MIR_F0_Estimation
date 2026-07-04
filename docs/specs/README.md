# Specs

This folder uses a lightweight SDD style: each document describes the intended behavior, the current implementation status, known gaps, and the next implementation slice.

The goal is to keep the project explainable during interviews while avoiding over-documenting unstable prototype code.

## Documents

- [00 Project Brief](00-project-brief.md)
- [01 Current Architecture](01-current-architecture.md)
- [02 F0 Pipeline](02-f0-pipeline.md)
- [03 Demo Roadmap](03-demo-roadmap.md)
- [04 F0 Review](04-f0-review.md)

## SDD Working Rules

1. Write or update a spec before changing a major workflow.
2. Keep specs tied to runnable demos.
3. Mark prototype behavior explicitly instead of hiding it.
4. Record assumptions, dependencies, and validation commands.
5. Promote exploratory scripts into stable CLI demos only after they produce reliable output.
