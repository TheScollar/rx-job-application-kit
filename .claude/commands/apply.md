---
name: apply
description: 'Process one job opportunity end to end: JD fetch, pre-screen gate, fit analysis, approval gate, tailored CV (markdown + JSON), private Reactive Resume publish, application tracking, commit.'
argument-hint: '[JD URL or pasted JD text]'
allowed-tools: [Read, Write, Edit, Glob, Bash, WebFetch, AskUserQuestion, mcp__nimbalyst__PromptForUserInput]
---

# /apply - process one opportunity

Two mandatory gates: one at pre-screen, one before writing files and creating
a private remote resume. Everything else runs automatically. Detailed rules
live in the `rx-job-application-kit` skill references; this command tells you
when to read which.

Requires a completed `/setup` (`Positioning/` filled,
`Materials/resume-canonical.json` present). If either is missing, stop and
point the user to `/setup`.

---

## Phase 1 - Fetch and parse JD

1. `WebFetch` the JD URL from the trigger message (or parse pasted text
   directly; if the page is login-gated, report what was fetched and ask the
   user to paste the relevant text).
2. Extract and display: company name, role title, location/format, key
   responsibilities (5-7 bullets), key requirements (must-haves,
   nice-to-haves), application contact name + email if listed.
3. If source info is not in the trigger message, ask: source type
   (`linkedin / headhunter / direct / referral`) and recruiter name + contact
   email if via headhunter.

---

## Phase 2 - Pre-screen (GATE 1)

Read `Positioning/Target-Roles.md`. Check the JD against dealbreakers and
must-haves. Present a compact table:

| Criterion | Status | Notes |
|-----------|--------|-------|
| Role title match | Green/Yellow/Red | ... |
| Location / format | ... | ... |
| Domain fit | ... | ... |
| Company stage | ... | ... |
| Compensation band | ... | ... |
| Dealbreakers | ... | ... |
| Must-haves | ... | ... |

If everything is yellow/borderline, surface the ambiguity explicitly.

**MANDATORY STOP.** Ask: "Proceed with this opportunity, or log and decline?"

- **Decline:** create `Applications/YYYY-MM-DD - [Company] - [Role]/` with
  only `Application.md` per the decline variant in the skill's
  `references/note-templates.md` (`outcome: declined-at-prescreen`). Make NO
  API call (the remote board stays a true pipeline of pursued applications).
  Commit the folder (`chore: log declined opportunity [Company] - [Role]`),
  done.
- **Proceed:** continue to Phase 3.

---

## Phase 3 - Fit analysis

Read `Positioning/Master-CV.md` and `Positioning/Accomplishments.md`.

1. Map the JD's 5-7 key requirements against the user's experience:

| JD requirement | The user's angle | Strength |
|----------------|------------------|----------|
| ... | ... | Strong / Partial / Gap |

2. State the **domain bridge**: how to frame existing experience toward this
   role.
3. State the **honest gap**: what cannot be closed by wording.
4. State the **tailoring strategy**: which Accomplishments themes to lead
   with, which roles to elevate vs. de-emphasize (keep all roles), summary
   reframing direction, skills section reorder.

Show the analysis inline. No gate here; continue to Phase 4.

---

## Phase 4a - Approve files and remote resume (GATE 2)

Determine the date slug (`YYYY-MM-DD` = today), company slug, role slug, and
recommended language code. Default language comes from `kit.config.json`
(`language_default`); recommend `de` instead for German-language or
explicitly German-market JDs. Derive:

- Resume name: `[Company] — [Role] — [EN|DE] — [YYYY-MM-DD]`
- Base slug: `[yyyy-mm-dd]-[company-slug]-[role-slug]-[en|de]`
- Tags: `job-application`, `[Company]`, `[EN|DE]`
- Visibility: private

**Preflight:** from the repo root, run the awk readiness check from the
skill's `references/api-scripts.md`. It may output only the readiness status;
never display `.env` or the key. If `missing_or_empty`, stop before the
approval interaction and tell the user to fill `.env` (see `.env.example`).

Propose before writing anything:

```
Files to create (one folder):
  Applications/YYYY-MM-DD - [Company] - [Role]/
    1. Application.md      (JD summary, fit analysis, verdict, prep)
    2. Communication.md    (comm log)
    3. CV-Tailored.md      (tailored CV)
    4. CV-Tailored.json    (local backup + API payload)

Remote objects to create:
  5. Private resume: [Company] — [Role] — [EN|DE] — [YYYY-MM-DD]
     Slug: [yyyy-mm-dd]-[company-slug]-[role-slug]-[en|de]
     Tags: job-application, [Company], [EN|DE]
     Duplicate policy: create -2, -3, etc.; never overwrite
  6. Tracked application (status: saved) linked to that resume

Recommended language: [EN|DE] (changeable in the approval step)
```

### Gate 2 interaction protocol

**MANDATORY STRUCTURED APPROVAL.** Do not write files or call the API before
this returns approval. Use exactly one of these paths, in priority order:

1. **AskUserQuestion (default):** one call, three options: `Approve EN`,
   `Approve DE`, `Request edits`. Include the full proposal in the question.
   If the user selects `Request edits`, collect the edits, update the
   proposal, then ask again.
2. **Nimbalyst only** (if `mcp__nimbalyst__PromptForUserInput` is available):
   one call with `language` (singleSelect, recommended first), `proposal`
   (editText seeded with the full proposal), `approve` (confirm,
   default true).
3. **No structured input tool:** show the full proposal and end with exactly:
   `APPROVE EN`, `APPROVE DE`, `EDIT: <requested changes>`, or `CANCEL`.

Normalize a positive result to `GATE_2_APPROVED(language, proposal)`.
Approval covers the local writes, the private remote resume, AND the tracked
application; do not add further gates. After approval, resume directly at
Phase 4b without repeating Phases 1-4a. If the user cancels, stop without
writing anything.

## Phase 4b - Local notes

Create the application folder and write `Application.md`
(`outcome: pursued`) and `Communication.md` per the skill's
`references/note-templates.md`, in the selected language where content is
user-facing. Leave the four `reactive_resume_*` frontmatter fields empty for
now.

---

## Phase 5a - Tailored CV (markdown)

Base: `Positioning/Master-CV.md`. Apply the Phase 3 tailoring strategy:

1. **Summary:** rewrite to lead with the domain bridge; keep it tight (3-4
   sentences, no inflation).
2. **Experience order:** strict reverse-chronological by start date; never
   swap employer order; keep all roles. Adjust bullet emphasis per role.
3. **Per-role bullets:** pull the strongest matching bullets from
   `Accomplishments.md`; trim bullets that do not serve this JD (but keep
   the role). Keep metrics accurate; never invent facts.
4. **Skills:** reorder groups so the JD's top themes appear first.
5. **All other sections:** keep in full (education, certifications,
   languages, interests, volunteering); adjust description length only.
6. **Footer:** add a draft-notes section explaining key framing decisions.

Write to `Applications/<folder>/CV-Tailored.md` (`CV-Tailored-DE.md` if a
German version coexists with an English one).

---

## Phase 5b - Resume JSON

Build `Applications/<folder>/CV-Tailored.json` following the skill's
`references/resume-json-contract.md` (copy-then-replace from
`Materials/resume-canonical.json`, fresh UUIDs, multi-position `roles[]`
rules), `references/html-conversion.md` for all rich-text fields, and, for
German resumes, `references/german-localization.md`.

Then validate:

```bash
python3 scripts/reactive_resume_publish.py \
  --json "Applications/<folder>/CV-Tailored.json" --validate-only
```

Must return `"status": "valid"`. Also verify the presentation contract per
the JSON reference. Do not tell the user to upload anything manually;
continue to Phase 5c.

---

## Phase 5c - Publish (private resume)

Run from the repo root, with the exact name/slug/tags approved at Gate 2:

```bash
python3 scripts/reactive_resume_publish.py \
  --json "Applications/<folder>/CV-Tailored.json" \
  --name "[Company] — [Role] — [EN|DE] — [YYYY-MM-DD]" \
  --slug "[yyyy-mm-dd]-[company-slug]-[role-slug]-[en|de]" \
  --tag "job-application" --tag "[Company]" --tag "[EN|DE]"
```

Handle the result by exit code (matrix in `references/api-scripts.md`):

- **0 / `published`:** update `Application.md` frontmatter with the exact
  returned values (quote all YAML strings): `reactive_resume_id`,
  `reactive_resume_name`, `reactive_resume_slug`. Add
  `- [ ] Review and export PDF in Reactive Resume` to Next steps.
- **2 / `created_verification_incomplete`:** the resume exists and MUST NOT
  be deleted. Report name/slug/ID/warnings, record them in the note, stop
  before Phase 5d and ask for direction.
- **1 / `error`:** report the safe stderr JSON; if it mentions an orphaned
  resume ID, surface it prominently. Stop; never auto-retry auth or
  validation failures.

---

## Phase 5d - Track the application

Skip with a one-line warning if `check-auth` previously reported
`applicationsApi: false` (tracking is optional; publishing stands alone).

1. Write the full JD text to `/tmp/jd-[company-slug].txt`.
2. Create the tracked application:

```bash
python3 scripts/reactive_resume_api.py app-create \
  --company "[Company]" --role "[Role]" --status saved \
  --resume-id "[id from Phase 5c result]" \
  --source "[linkedin|headhunter|direct|referral]" \
  --source-url "[JD URL]" --location "[from JD]" \
  --jd-file "/tmp/jd-[company-slug].txt" \
  --tag "job-application"
```

3. On exit 0: write the returned id into `Application.md` frontmatter as
   `reactive_resume_application_id` (quoted). On exit 2: the application
   exists; record the id, report the warnings, continue. On exit 1: report
   the safe error, tell the user tracking failed but the resume is
   published, continue.
4. Remind the user: stage moves (applied, screening, interview, offer,
   rejected) happen on the Reactive Resume Applications kanban, not in local
   notes. `/pipeline` shows the current board read-only.

---

## Phase 5e - Auto-commit

After all files are written and remote metadata is recorded, stage ONLY the
application folder and commit:

```bash
git add "Applications/YYYY-MM-DD - [Company] - [Role]" && \
git commit -m "chore: add [Company] - [Role] application (notes, tailored CV md+json)"
```

---

## Edge cases

| Situation | Handling |
|-----------|----------|
| No JD URL, only pasted text | Skip WebFetch; parse the pasted content |
| No recruiter (direct application) | Omit recruiter fields; comm log records direct outreach |
| JD in German | Recommend `de` at Gate 2 regardless of `language_default` |
| Application folder already exists for this company+role | Ask: new dated folder or append to existing |
| Pre-screen is borderline (all yellow) | Surface the ambiguity at Gate 1; the user decides |
| `.env` or key missing | Stop before Gate 2; name the variable, never show the key |
| Remote slug already exists | The publisher suffixes `-2`, `-3`; record the returned slug |
| Employer with multiple positions | All titles/periods/descriptions in `roles[]`; top-level fields empty |
| Publish exit 2 or ambiguous outcome | Keep the remote resume; never risk deleting valid work |
| `applicationsApi: false` | Warn once, skip Phase 5d, everything else proceeds |
