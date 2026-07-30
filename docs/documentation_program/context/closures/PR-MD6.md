# PR-MD6 documentation closure

- **Status:** REVIEWABLE
- **Repository commit inspected:** `65e8c0d`
- **Human acceptance required:** yes

Classified historical/supporting surfaces, bannered PR-era runbooks, preserved unique evidence, added maintenance/coverage policy, and introduced `make docs-check` for relative links, canonical metadata/names, and Mermaid context. No historical evidence or pipeline behavior was deleted.

Verification: `make docs-check`, focused contract tests, and `git diff --check`. Known gaps remain recorded in the coverage report.

Proposed final carry: after human review, set `accepted_through: PR-MD6`, `status: COMPLETE`, and clear `next_pr`; future work follows the maintenance policy rather than this bounded sequence.
