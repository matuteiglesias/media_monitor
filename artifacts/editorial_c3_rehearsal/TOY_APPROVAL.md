# P1-C3 toy-approved tranche

This acceptance layer deliberately exercises the **real** `published_article.v1` promotion and index path with `review_status=human_approved`, but only inside an isolated output directory.

It is **not a public editorial approval** and must never be copied into the production published-article bus. The manifest emitted by `scripts/materialize_toy_approved_tranche.py` therefore carries:

- `scope = SIMULATED_TOY_HUMAN_APPROVAL_NOT_PUBLICATION`
- `not_for_publication = true`
- `production_bus_touched = false`

The differentiated simulated judgment from the earlier C3 rehearsal is preserved:

- July CPI: toy approve
- July trade: toy approve
- June retail: revise/hold

The purpose is to give downstream snapshot, metadata, feed, social-card and adopter-demo machinery realistic approved article objects without falsely claiming that a real public editorial sign-off occurred.
