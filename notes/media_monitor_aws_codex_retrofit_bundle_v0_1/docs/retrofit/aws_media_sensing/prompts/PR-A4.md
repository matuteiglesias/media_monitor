# Codex Prompt — PR-A4: S3 adapters, sensing container, and task-safe entrypoint

Prerequisite: PR-A3 is accepted.

## Goal

Implement AWS-facing storage and task seams without provisioning AWS infrastructure.

## Scope

- immutable S3 key layout and adapter;
- compactor input/output adapter;
- local fake/contract tests;
- sensing-only container;
- cloud task entrypoint;
- structured logs with run/lane/stage identity;
- explicit task timeout/resources/config;
- task role expectations;
- source commit/image/run linkage.

## Hard constraints

- sensing task writes only its run prefix;
- only compactor writes compacted/latest prefixes;
- no editorial/enrich/site invocation;
- no shared JSONL append;
- no `.env` or credentials in image.

Produce `context/closures/PR-A4.md` and propose `PR-A5`.
