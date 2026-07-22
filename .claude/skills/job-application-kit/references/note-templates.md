# Note templates

Both notes live inside the application folder
`Applications/YYYY-MM-DD - [Company] - [Role]/`. Plain markdown, no wikilinks
(editor-agnostic). `related:` fields hold plain filenames.

Local notes never carry live pipeline status. The one-shot `outcome` field is
set once at Gate 1 (`pursued` or `declined-at-prescreen`) and does not change
afterwards; stage changes (applied, screening, interview, offer, rejected)
happen only on the Reactive Resume Applications kanban.

## Application.md

```yaml
---
company: "[Company]"
role: "[Role Title]"
outcome: pursued            # pursued | declined-at-prescreen (set once)
date_received: YYYY-MM-DD
source: "[linkedin/headhunter/direct/referral]"
jd_url: "[URL or empty]"
location: "[City / Remote / Hybrid, from JD]"
contact: "[Primary contact name, recruiter if via headhunter, else hiring manager]"
compensation: "[Stated range or empty]"
recruiter: "[Name if applicable]"
recruiter_contact: "[email if applicable]"
application_contact: "[direct contact at company, if listed in JD]"
language: "[en|de]"
reactive_resume_id: ""              # filled after publish (quote the value)
reactive_resume_name: ""            # filled after publish
reactive_resume_slug: ""            # filled after publish
reactive_resume_application_id: ""  # filled after app-create
related: "Communication.md"
tags:
  - job-application
---
```

Body sections, in order:

1. `## Quick facts` - table: location, format, stage, domain, comp band if
   stated
2. `## JD summary` - responsibilities and requirements bullets
3. `## Fit analysis` - the requirement-vs-experience table from the analysis
   phase
4. `## Gap` - the honest gap that wording cannot close
5. `## Verdict` - one short paragraph
6. `## Tailoring plan` - themes to lead with, roles to elevate, summary
   direction, skills order
7. `## Interview prep` - blank placeholder
8. `## Next steps` - checklist; after publish add
   `- [ ] Review and export PDF in Reactive Resume`

For a Gate 1 decline, create the folder with only `Application.md`
(`outcome: declined-at-prescreen`), fill Quick facts, JD summary, and a short
`## Decline rationale` section instead of sections 3-8, and make NO API call.

## Communication.md

```yaml
---
company: "[Company]"
contact: "[Contact Name] ([role, e.g. headhunter])"
channel: "[headhunter/linkedin/direct/email]"
related: "Application.md"
tags:
  - job-application
  - communication
---
```

Body: `# Communication log - [Company]` header, then one dated entry per
exchange, newest last:

```markdown
## YYYY-MM-DD - Inbound via [channel]

[Verbatim or summarized message]

<!-- Add new entries below: ## YYYY-MM-DD - [Direction] via [channel] -->
```
