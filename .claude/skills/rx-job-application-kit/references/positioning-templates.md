# Positioning templates

Blank structures for the three `Positioning/` files. `/setup` copies these and
fills them from the intake extracts plus the interview answers. Keep the
heading structure intact; `/apply` parses these files on every run.

## Target-Roles.md

```markdown
---
type: target-criteria
status: active
last_updated: YYYY-MM-DD
---
# Target roles & criteria

> What I am open to and what I am filtering out. Update when priorities
> shift. /apply pre-screens every JD against this file.

## Role titles I'd consider

- 

## Stage / company profile

- 

## Domain preferences

**Strong yes:**
- 

**Open:**
- 

**Filter out:**
- 

## Location & format

- Primary location: 
- Onsite/hybrid/remote: 
- Relocation: 

## Compensation band

- Base salary: 
- Variable / OTE: 
- Equity: 
- Notice period: 

## Dealbreakers

- 

## Must-haves

- 
```

## Master-CV.md

```markdown
---
type: master-cv
language: en
status: source-of-truth
last_updated: YYYY-MM-DD
---
# Master CV - [Name]

> Source-of-truth. Edit when facts change (new role, new metric, new
> education). /apply copies from here and trims/reorders per JD; it never
> invents facts that are missing here.

## Contact

- **Name:** 
- **Location:** 
- **Phone:** 
- **Email:** 
- **LinkedIn:** 

## Summary

[3-5 sentences: seniority, domains, 2-3 headline metrics, what you optimize
for.]

## Experience

### [Employer] - [Role Title]
**[Mon YYYY - Mon YYYY] · [City / remote] · [Domain]**

[1-2 sentence role scope.]

- [Accomplishment bullet with metric]
- [Accomplishment bullet with metric]

<!-- Repeat per role, strictly reverse-chronological. For multiple roles at
the same employer, use one ### heading per role. -->

## Education

**[Degree]** - [Institution], [YYYY - YYYY]. [Grade, thesis if notable.]

## Continuing education & certifications

- **[Course/Cert]** - [Provider] ([Mon YYYY])

## Skills

**[Group]:** [comma-separated skills]

## Languages

- **[Language]:** [level]

## Volunteering

- **[Role] - [Organization]** ([period]) - [one line]
```

## Accomplishments.md

```markdown
---
type: accomplishments-bank
status: source-of-truth
last_updated: YYYY-MM-DD
---
# Accomplishments bank

> Reusable STAR-style bullets, tagged by theme. When tailoring a CV to a JD,
> pull the bullets that match the role's keywords. Each bullet must be
> specific and verifiable: a metric, a scope, or a named decision.

**How to use:**
1. Read the JD; note 3-5 themes the role emphasizes.
2. For each theme, pick the 1-2 strongest bullets below.
3. Paste into the tailored CV under the relevant role, trimming to fit.
4. Cross-check that company, metric, and date stay accurate.

**Anti-pattern:** no bullet without a number, scope, or named decision.

## Theme: [e.g. Growth]

- [Bullet with metric, employer, and period]

<!-- Repeat per theme. Typical themes: AI & data, growth, B2B SaaS,
leadership, platform/API, domain-specific expertise. -->

## Numbers cheat sheet (most-used)

| Metric | Context |
|---|---|
| | |
```
