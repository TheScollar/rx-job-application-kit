# Setup interview question banks

Question banks for `/setup` steps 3 and 4. Ask in batches with
AskUserQuestion (up to 4 questions per call, multiSelect where marked).
Seed options from the intake extracts where possible: propose what the
documents suggest, let the user correct. Every answer lands in
`Positioning/Target-Roles.md` (positioning) or `Positioning/Accomplishments.md`
(mining).

## Batch 1: Role targets

1. **Target titles** (multiSelect): derive 4 plausible title tiers from the
   extracts, e.g. `Senior PM`, `Lead/Principal PM`, `Group PM / Head of`,
   `IC specialist track`. Follow up in "Other" for exact title wording.
2. **Seniority direction**: `Same level, better company` / `Step up (lead or
   principal)` / `People management track` / `Open to both IC and lead`.

## Batch 2: Domain and stage

1. **Industries: strong yes** (multiSelect): offer the 4 domains most visible
   in their experience; "Other" for more.
2. **Industries: filter out** (multiSelect): common exclusions, e.g.
   `Crypto/gambling`, `Defense`, `Ad-tech`, `None of these`.
3. **Company stage** (multiSelect): `Early startup (Seed/A)` /
   `Scale-up (B+)` / `Bootstrapped and profitable` / `Corporate/enterprise`.

## Batch 3: Location and format

1. **Primary location**: seed from the extracts (their current city);
   options: `[City] only` / `[City] + remote` / `Remote (country)` /
   `Remote (EU/international)`.
2. **Onsite tolerance**: `Fully remote` / `Up to 1-2 days onsite` /
   `Up to 3 days onsite` / `Onsite is fine`.
3. **Relocation**: `No` / `Within country` / `Internationally for the right
   role`.

## Batch 4: Compensation and constraints

1. **Base salary band**: ask as ranges in the currency from `kit.config.json`
   (offer 4 bands around what the extracts suggest for their seniority and
   market; "Other" for an exact number). Record the floor, not the hope.
2. **Notice period**: `Immediately` / `1 month` / `3 months` / `Other`.

## Batch 5: Dealbreakers and must-haves (freeform after seeding)

1. **Dealbreakers** (multiSelect seed, then "anything else?" freeform):
   `No product strategy / engineering-led by default`,
   `Founder won't let go of product`, `Hire-and-fire culture`,
   `Heavy travel (>1 day/week)`.
2. **Must-haves** (multiSelect seed, then freeform): `Clear product mandate
   (strategy + execution)`, `Team to build or lead`, `Modern data/AI story`,
   `Sustainable pace`.

Write `Positioning/Target-Roles.md` from the answers using the template in
`positioning-templates.md`. Show the file and ask for a review edit before
continuing.

## Accomplishment mining (step 4)

Goal: turn flat CV lines into bullets with a metric, a scope, or a
before/after. For each significant role in the extracts, probe until each
claimed strength has at least one anchored bullet:

- **Metric probe:** "You [did X] at [Employer]. What number moved, by how
  much, over what period?" (revenue, users, conversion, retention, cost,
  time saved)
- **Scope probe:** "How big was this? Team size, budget, user count, number
  of markets or countries?"
- **Before/after probe:** "What was true before you started that was no
  longer true when you left?"
- **Decision probe:** "What is one named decision you made that someone can
  ask about in an interview?"

Rules:

- Never invent or inflate a number. If the user cannot recall one, record the
  scope instead ("owned the checkout flow for a 7-country marketplace").
- Ask per-role, newest first, max 3 probes per role; respect "skip".
- Tag each resulting bullet with a theme heading (AI & data, growth,
  leadership, platform, domain expertise, etc.).
- Numbers land twice: in the themed bullet and in the "Numbers cheat sheet"
  table.

Write `Positioning/Accomplishments.md` and the Experience bullets of
`Positioning/Master-CV.md` from the mined material, then stop for the explicit
review gate: the user edits the files, then confirms in chat before `/setup`
continues.
