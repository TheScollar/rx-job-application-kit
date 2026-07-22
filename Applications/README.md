# Applications

One folder per application, created by `/apply`:

```
Applications/
└── YYYY-MM-DD - Company - Role/
    ├── Application.md       # JD summary, fit analysis, verdict, prep notes
    ├── Communication.md     # message log with the recruiter or company
    ├── CV-Tailored.md       # tailored CV, human-readable
    └── CV-Tailored.json     # exact Reactive Resume payload (local backup)
```

**Where status lives:** live pipeline status (saved, applied, screening,
interview, offer, rejected) is tracked in your Reactive Resume account via the
Applications API; open the Applications kanban at https://rxresu.me to move
cards. Local notes record only a one-shot `outcome` (`pursued` or
`declined-at-prescreen`) plus the remote resume and application IDs, so there
is no duplicate state to keep in sync.

Run `/pipeline` for a read-only status table in chat. A worked example lives
in `examples/alex-sample/Applications/`.
