---
name: pipeline
description: 'Read-only pipeline overview: current applications grouped by status plus totals, from the Reactive Resume Applications API.'
allowed-tools: [Bash]
---

# /pipeline - status overview (read-only)

Renders the current application pipeline in chat. This command never changes
anything; stage moves happen on the Reactive Resume Applications kanban at
https://rxresu.me.

## Steps

1. Run both (from the repo root):

```bash
python3 scripts/reactive_resume_api.py app-list
python3 scripts/reactive_resume_api.py app-stats
```

If `app-list` exits 1, report the safe error. If the error indicates the
Applications API is unavailable (older self-hosted instance), say tracking
is not supported on this instance and stop.

2. Render ONE table from `app-list`, grouped by status in funnel order
   (`saved`, `applied`, `screening`, `interview`, `offer`, `rejected`),
   newest first within each group:

| Status | Company | Role | Source | Location | Follow-up |
|---|---|---|---|---|---|

Omit empty columns. Mark archived entries only if `--include-archived` was
requested by the user.

3. Below the table, one stats line from `app-stats`, e.g.:
   `12 total | saved 3 · applied 4 · screening 2 · interview 2 · offer 0 · rejected 1`

4. Close with: move cards on the kanban at https://rxresu.me; use
   `/apply` to add a new opportunity. If the user asks for a status change
   or follow-up reminder, use `app-update` per the skill's
   `references/api-scripts.md` after confirming the exact change.
