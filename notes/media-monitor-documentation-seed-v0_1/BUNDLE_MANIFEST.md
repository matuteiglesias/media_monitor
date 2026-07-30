# media_monitor documentation seed bundle

This is a repository-root overlay for `matuteiglesias/media_monitor`.

It adds a documentation governance and production program without rewriting the
existing root README, owner runbooks, PR-era runbooks, or AWS retrofit records.

Recommended seed commit:

```bash
git add AGENTS.md docs/documentation_program
git commit -m "docs: seed governed documentation program"
```

After merge, instruct Codex:

> Read `docs/documentation_program/CODEX_START_HERE.md` and execute only the PR
> named by `next_pr`.
