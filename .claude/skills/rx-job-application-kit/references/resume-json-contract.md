# Resume JSON contract (copy-then-replace)

How to build any Reactive Resume `ResumeData` JSON in this kit: the canonical
file is copied completely, then only the tailored fields are replaced. Never
reconstruct presentation or section settings from memory.

## Step 1: Load the canonical reference

Read `Materials/resume-canonical.json`. It is the canonical baseline for
contact details, static content, picture, and visual presentation. Start from
its complete JSON object.

**Copy unchanged (same-language resumes):**

- `picture` (URL, size, crop, border, and shadow settings)
- `basics.name`, `email`, `phone`, `location`, `website`, and `customFields`
- The complete `summary` presentation shell: every field except `content`
- Every `sections.*` presentation shell: every field except `items`
- Complete static section items from `profiles`, `education`, `projects`,
  `languages`, `interests`, `awards`, `certifications`, `publications`,
  `volunteer`, and `references`
- `customSections`
- `metadata` (template, layout, page, colors, typography, and style rules)

**Replace with tailored content:**

- `basics.headline`
- `summary.content`
- `sections.experience.items`
- `sections.skills.items`

This preserves the template, picture, sidebar width, page settings, section
titles, typography, colors, and any future presentation fields added to the
canonical file. For German resumes, additionally apply
`german-localization.md`.

## Step 2: Generate UUIDs

Run once to generate enough UUIDs for all new items (experience entries,
role entries within multi-tenure companies, skill items):

```bash
python3 -c "import uuid; [print(uuid.uuid4()) for _ in range(20)]"
```

Assign one UUID per newly generated experience item, nested role, and skill
item. Never reuse canonical IDs for these dynamic items. Preserve the IDs of
static items copied from the canonical reference.

## Step 3: Construct dynamic sections

**`basics.headline`** - rewrite to match the role framing (not the master CV
default).

**`summary.content`** - HTML version of the tailored summary
(see `html-conversion.md`):

```
<p><span>Plain paragraph text here.</span></p>
```

**`sections.experience.items`** - one item per employer, sorted strictly
reverse-chronologically by start date. For single-tenure employers:

```json
{
  "id": "<uuid>",
  "hidden": false,
  "company": "Company Name",
  "position": "Role Title",
  "location": "City, format",
  "period": "Mon YYYY - Mon YYYY",
  "website": {"url": "", "label": "", "inlineLink": false},
  "description": "<HTML content>",
  "roles": []
}
```

For every employer with multiple positions, `roles` is the exclusive owner of
all titles, periods, and role descriptions. The employer-level `position`,
`period`, and `description` fields MUST all be empty strings. Never mirror the
latest or current title into the employer-level `position` field.

```json
{
  "id": "<uuid>",
  "hidden": false,
  "company": "Acme Analytics GmbH",
  "position": "",
  "location": "Berlin, hybrid",
  "period": "",
  "website": {"url": "", "label": "", "inlineLink": false},
  "description": "",
  "roles": [
    {
      "id": "<uuid>",
      "position": "Senior Product Manager",
      "period": "Mar 2024 - present",
      "description": "<HTML content>"
    },
    {
      "id": "<uuid>",
      "position": "Product Manager",
      "period": "Jun 2022 - Feb 2024",
      "description": "<HTML content>"
    }
  ]
}
```

Multi-position rules:

1. Include every position in `roles`, including the latest/current one.
2. Sort roles reverse-chronologically by start date.
3. Give the employer item and every nested role its own UUID.
4. Keep `company`, `location`, `website`, and `hidden` at employer level.
5. Repeated role titles with different periods are valid; only employer-level
   duplication is forbidden.
6. Use top-level `position`, `period`, and `description` only when
   `roles: []`.

The publisher's `--validate-only` mode enforces the empty-string rule and
rejects violations before any API call.

**`sections.skills.items`** - reordered so the JD's top themes appear first:

```json
{
  "id": "<uuid>",
  "hidden": false,
  "icon": "acorn",
  "iconColor": "",
  "name": "Skill group name",
  "proficiency": "Comma-separated list of skills",
  "level": 5,
  "keywords": []
}
```

Level scale: 5 = expert/lead, 4 = strong, 3 = solid.

## Step 4: Validate before any API call

Write the complete JSON with the Write tool, then run:

```bash
python3 scripts/reactive_resume_publish.py \
  --json "Applications/<folder>/CV-Tailored.json" \
  --validate-only
```

Validation MUST return `"status": "valid"`. Also verify the presentation
contract against `Materials/resume-canonical.json`:

- `picture` matches exactly
- Same-language `metadata` matches exactly; German differs only where
  localization requires it (at minimum `metadata.page.locale`)
- Summary and section presentation shells match, excluding tailored content,
  dynamic item arrays, and localized German titles

## Bootstrap variant (used by /setup)

When the user has no existing Reactive Resume account content, `/setup` copies
`.claude/skills/rx-job-application-kit/assets/canonical-default.json` to
`Materials/resume-canonical.json` and fills it FROM `Positioning/Master-CV.md`:
`basics.*` values, `summary.content`, and items for experience, education,
skills, languages, certifications, volunteer, interests, and profiles. Every
item gets a fresh UUID (same generator as Step 2). `picture.url` stays empty;
the user uploads a photo later in the Reactive Resume UI. The filled file must
pass `--validate-only` before `/setup` completes.
