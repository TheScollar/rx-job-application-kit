# rx-job-application-kit

A Claude Code workspace for preparing and tracking job applications with
Reactive Resume (rxresu.me). Act as a careful assistant on personal career
data: precise, no invented facts, no leaked secrets.

## Project map

```
.claude/
├── commands/            # thin flows: setup.md, apply.md, pipeline.md
├── skills/rx-job-application-kit/
│   ├── SKILL.md         # routing table + invariants (read this first)
│   ├── references/      # the actual rules (JSON contract, HTML, German,
│   │                    #   note templates, interview banks, API recipes)
│   └── assets/canonical-default.json   # blank presentation shell
scripts/
├── reactive_resume_publish.py   # create + verify a private resume
└── reactive_resume_api.py       # applications tracking + resume pull
Materials/               # intake/ (gitignored) + extracts + resume-canonical.json
Positioning/             # Target-Roles.md, Master-CV.md, Accomplishments.md
Applications/            # one folder per application
examples/alex-sample/    # fictional worked example (persona: examples/README.md)
kit.config.json          # language_default, languages, currency
.env                     # API key (gitignored; NEVER read or print)
```

## Invariants (never violate)

1. **Never Read, cat, echo, grep-display, or print `.env`** or any API key.
   The only permitted check is the awk readiness snippet in
   `.claude/skills/rx-job-application-kit/references/api-scripts.md`.
2. **All Reactive Resume API access goes through the two scripts** in
   `scripts/`. No curl, no ad-hoc HTTP code.
3. **No remote deletes, ever.** Neither script has any delete path. Never
   overwrite existing remote resumes; duplicate slugs get suffixed. Exit code
   2 means the remote object exists (including a shell that was created but
   not fully populated): keep it and stop for direction.
4. Resumes are always created **private**.
5. Respect `/apply`'s two gates; never write files or call the API before
   the corresponding gate passes.
6. Never invent career facts. Everything in a tailored CV traces back to
   `Positioning/` or the user's explicit input.

## Commands

| Command | Purpose |
|---|---|
| `/setup` | One-time onboarding (re-runnable): extracts, interview, Positioning trio, canonical resume, API key check |
| `/apply` | One opportunity end to end: JD -> gates -> tailored CV -> publish -> track -> commit |
| `/pipeline` | Read-only status table from the Applications API |

## Conventions

- Python: 3.9-compatible, standard library only.
- Application folders: `Applications/YYYY-MM-DD - Company - Role/` with
  `Application.md`, `Communication.md`, `CV-Tailored.md`, `CV-Tailored.json`.
- Plain markdown everywhere, no wikilinks; `related:` holds plain filenames.
- Commits: stage only what the current flow created; short `chore:` messages.

## Plugin migration note (future)

This repo is laid out so a Claude Code plugin wrapper can be added without
restructuring: all logic lives in the skill + references, commands are thin
triggers, scripts sit at the repo root. To package as a plugin later, copy
`.claude/skills/`, `.claude/commands/`, and `scripts/` verbatim and swap
path prefixes to `${CLAUDE_PLUGIN_ROOT}`.
