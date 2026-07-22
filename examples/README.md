# examples/alex-sample - fully fictional demo

Everything under `examples/` is invented for demonstration. No real person,
company, recruiter, metric, or ID appears here. All UUIDs are obviously fake
(`00000000-0000-4000-8000-...`). `CV-Tailored.json` doubles as the kit's
validation test fixture (it must pass `--validate-only` and contains one
multi-position employer).

## Persona sheet (single source for every file below)

| Field | Value |
|---|---|
| Name | Alex Sample |
| Email | alex.sample@example.com |
| Phone | +49 555 0100 |
| Location | Berlin, Germany |
| LinkedIn | linkedin.com/in/alex-sample-demo (fictional) |
| Experience | ~9 years product management, B2B SaaS / analytics |

Fictional employers:

| Employer | Roles | Period |
|---|---|---|
| Acme Analytics GmbH (Berlin, B2B SaaS) | Senior Product Manager, Data Platform; before that Product Manager, Dashboards | Jun 2022 - present (multi-position) |
| Globex Digital GmbH (Berlin, e-commerce platform) | Product Manager | Aug 2019 - May 2022 |
| Initech Solutions AG (Hamburg, enterprise software) | Junior Product Manager / Business Analyst | Sep 2016 - Jul 2019 |

Fictional target: **NimbusWorks GmbH**, Senior Product Manager (Analytics
Platform), Berlin/hybrid, via recruiter **Kim Muster** (fictional).

## What each file demonstrates

| File | Produced by | Shows |
|---|---|---|
| `alex-sample/Materials/CV-Alex-Sample-extract.md` | `/setup` step 2 | The extract format from an intake document |
| `alex-sample/Positioning/Target-Roles.md` | `/setup` step 3 | Filled criteria after the interview |
| `alex-sample/Positioning/Master-CV.md` | `/setup` step 4 | Source-of-truth CV |
| `alex-sample/Positioning/Accomplishments.md` | `/setup` step 4 | Themed STAR bullets + numbers cheat sheet |
| `alex-sample/Applications/2026-07-15 - NimbusWorks GmbH - Senior Product Manager/` | `/apply` | One complete application: notes, comm log, tailored CV (md + JSON with a multi-position employer), filled remote IDs |
