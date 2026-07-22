---
name: rx-job-application-kit
description: 'End-to-end job application workflow: one-time setup from your CVs (/setup), per-JD tailoring and publishing to Reactive Resume (/apply), and pipeline status (/pipeline). Use when the user runs one of those commands, pastes a job description or JD URL, or asks to prepare, tailor, track, or evaluate a job application.'
---

# Job Application Kit

Turn a job description into a decision, a tailored CV, a private resume on
[Reactive Resume](https://rxresu.me), and a tracked application, without
retyping your career history every time.

## The three commands

| Command | What it does | Frequency |
|---|---|---|
| `/setup` | Interview + document extraction that builds `Positioning/` and `Materials/resume-canonical.json`, connects the API key | Once (re-runnable) |
| `/apply` | JD fetch, pre-screen gate, fit analysis, approval gate, tailored CV (md + JSON), private resume publish, application tracking | Per opportunity |
| `/pipeline` | Read-only status table from the Reactive Resume Applications API | Whenever |

The command files under `.claude/commands/` hold the flow; the detailed rules
live in the references below. Read a reference when the routing table says so,
not before.

## Reference routing table

| When you are... | Read |
|---|---|
| Building or modifying any `CV-Tailored.json` / canonical resume JSON | `references/resume-json-contract.md` |
| Converting markdown content to Reactive Resume HTML | `references/html-conversion.md` |
| Producing a German (`de`) resume | `references/german-localization.md` |
| Creating `Application.md` or `Communication.md` | `references/note-templates.md` |
| Creating blank `Positioning/` files during `/setup` | `references/positioning-templates.md` |
| Running the `/setup` positioning or accomplishment interview | `references/setup-interview.md` |
| Calling either script (publish or API client) or checking `.env` readiness | `references/api-scripts.md` |
| Confirming which API endpoints exist and what they accept | `references/api-endpoints.md` |

## Data model

| Thing | Lives at | Committed? |
|---|---|---|
| Raw CVs / LinkedIn PDFs | `Materials/intake/` | No (gitignored) |
| Per-document extracts | `Materials/<Doc>-extract.md` | Yes (private copy) |
| Canonical resume JSON | `Materials/resume-canonical.json` | Yes (private copy) |
| Positioning trio | `Positioning/` | Yes (private copy) |
| One folder per application | `Applications/YYYY-MM-DD - Company - Role/` | Yes (private copy) |
| Live pipeline status | Reactive Resume Applications kanban | Remote only |
| API key | `.env` | Never |

Local application notes carry a one-shot `outcome` (`pursued` or
`declined-at-prescreen`) plus remote IDs. They never mirror live status; the
Reactive Resume kanban is the single source of truth for stage changes.

## Invariants (never violate)

1. **Never Read, cat, echo, or print `.env`** or any API key. Readiness is
   checked only with the awk snippet in `references/api-scripts.md`; the key
   reaches the API only inside the two scripts.
2. **All Reactive Resume API access goes through the two scripts** in
   `scripts/`. Never call the API with curl or ad-hoc code.
3. **Never delete or overwrite remote resumes or applications.** Duplicate
   slugs get `-2`, `-3` suffixes. The API client has no delete subcommand by
   design.
4. **Resumes are always created private** (`isPublic: false`).
5. **Respect the gates.** `/apply` has two mandatory stops: pre-screen
   (Gate 1) and file/publish approval (Gate 2). Never write application files
   or call the API before the corresponding gate passes.
6. **Multi-position employers** keep top-level `position`, `period`, and
   `description` as empty strings; all role content lives in `roles[]`
   (details in `references/resume-json-contract.md`).
