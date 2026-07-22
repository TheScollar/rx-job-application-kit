# job-application-kit

A [Claude Code](https://claude.com/claude-code) workspace that turns a job
description into a decision, a tailored CV, a private resume on
[Reactive Resume](https://rxresu.me), and a tracked application, without
retyping your career history every time.

```
        one-time                          per opportunity
┌─────────────────────┐    ┌──────────────────────────────────────────────┐
│ /setup              │    │ /apply <JD URL or text>                      │
│  your CVs + an      │    │  fetch JD → pre-screen gate → fit analysis   │
│  interview become   │───▶│  → approval gate → tailored CV (md + JSON)  │
│  Positioning/ and a │    │  → private resume publish → tracked         │
│  canonical resume   │    │  application → commit                        │
└─────────────────────┘    └──────────────────────────────────────────────┘
                                            │
                           ┌────────────────▼─────────────────┐
                           │ /pipeline  (read-only status)    │
                           │ + the rxresu.me Applications     │
                           │   kanban for stage moves         │
                           └──────────────────────────────────┘
```

## Requirements

- [Claude Code](https://claude.com/claude-code) (CLI or desktop)
- Python 3.9+ (standard library only, no pip installs)
- git
- A [Reactive Resume](https://rxresu.me) account and API key
  (Settings -> Security -> API Keys)
- Self-hosting Reactive Resume? Application tracking needs v5+; on older
  instances the kit detects this and degrades to publish-only.

## Quickstart

1. Click **Use this template** on GitHub and **make your copy PRIVATE**.
   Your private copy will contain your real career data; this public
   template contains none.
2. Clone your copy and open it in Claude Code.
3. Drop your current CV and LinkedIn PDF export into `Materials/intake/`.
4. Run `/setup` and follow the interview (10-20 minutes, once).
5. For every opportunity: `/apply <JD URL>` (or paste the JD text).
6. Check status anytime with `/pipeline`; move cards on the
   [rxresu.me](https://rxresu.me) Applications kanban.

## The three commands

| Command | What it does |
|---|---|
| `/setup` | Extracts your documents, interviews you on targets/dealbreakers/salary, builds `Positioning/` (Target-Roles, Master-CV, Accomplishments), connects your API key, and creates `Materials/resume-canonical.json` (pulled from your account or bootstrapped) |
| `/apply` | Fetches the JD, pre-screens it against your criteria (Gate 1), maps requirements to your experience, gets your approval (Gate 2), writes one application folder (notes + tailored CV in markdown and JSON), publishes a private resume with your exact template/design, and creates a tracked application linked to it |
| `/pipeline` | Renders your current pipeline (grouped by status + totals) read-only from the Applications API |

## Data model

| Thing | Lives at | Committed in your private copy? |
|---|---|---|
| Raw CVs / LinkedIn PDFs | `Materials/intake/` | Never (gitignored) |
| Per-document extracts | `Materials/<Doc>-extract.md` | Yes |
| Canonical resume JSON | `Materials/resume-canonical.json` | Yes |
| Positioning (criteria, master CV, accomplishments) | `Positioning/` | Yes |
| One folder per application (notes + tailored CV) | `Applications/` | Yes |
| Live pipeline status | rxresu.me Applications kanban | Remote only |
| API key | `.env` | Never (gitignored) |

Local notes record a one-shot `outcome` (`pursued` or
`declined-at-prescreen`) and the remote resume/application IDs. Live status
has exactly one home: the Reactive Resume kanban.

## Safety guarantees

- Your API key lives only in `.env`: gitignored, never pasted into chat,
  never in command arguments, never printed by the scripts.
  `.claude/settings.json` additionally denies reading `.env`.
- Resumes are always created **private** (`isPublic: false`).
- The kit never overwrites or deletes existing remote resumes; duplicate
  slugs get `-2`, `-3` suffixes. The API client has no delete command at all.
- Declined-at-prescreen opportunities are logged locally only, so your
  remote board stays a true pipeline.
- Two mandatory approval gates before anything is written or published.

## Demo

`examples/alex-sample/` is a fully worked, fictional example (persona sheet
in `examples/README.md`): extracted materials, the Positioning trio, and one
complete application folder including a valid `CV-Tailored.json` with a
multi-position employer. Read it to see what `/setup` and `/apply` produce.

## Troubleshooting

| Symptom | Meaning | Fix |
|---|---|---|
| `reactive_resume_env=missing_or_empty` | `.env` absent or key empty | `cp .env.example .env`, paste your key after `=` |
| Script exit 1, stderr JSON | Nothing was created; message says why | Fix the reported issue; auth errors usually mean a wrong/revoked key |
| Script exit 2 | Remote object EXISTS but re-read verification failed | Do not re-run blindly; check rxresu.me, record the reported ID |
| `"applicationsApi": false` from check-auth | Self-hosted instance older than v5 | Publishing works; tracking is skipped with a warning |
| Validation error about multi-position employers | Top-level `position`/`period`/`description` not empty | Move all role content into `roles[]` (see the skill references) |

Exit codes for both scripts: `0` success and verified, `1` error (nothing
usable created), `2` created but verification incomplete (never delete).

## Not affiliated

This project is not affiliated with or endorsed by Reactive Resume. It uses
the documented public API (spec v5.2.2). Reactive Resume is a trademark of
its respective owners.

## License

MIT, see [LICENSE](LICENSE).
