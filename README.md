# FirmsLedger company description runner

Runs every 6 hours on GitHub Actions: fetch company sites -> Nemotron writes -> fixer -> AI fact-check -> clean -> SQL.
Progress is committed back to `work/`. Finished batches have `work/batch-NNN/DONE` and SQL in `work/batch-NNN/sql/`.
Run those SQL files in the Neon SQL Editor, then redeploy the site.

Secret required: `NEMOTRON_KEY_2`. No database credentials live here.
