---
name: setup
description: 'One-time kit setup: extract your CVs, run the positioning interview, build Master-CV and Accomplishments, connect Reactive Resume, and create the canonical resume JSON.'
allowed-tools: [Read, Write, Edit, Glob, Bash, AskUserQuestion]
---

# /setup - one-time onboarding

Builds everything `/apply` depends on. Re-runnable: at each step, if the
artifact already exists, say so and ask skip / update / rebuild before
touching it. Detailed rules live in the `rx-job-application-kit` skill
references; read them when a step points there.

## Step 0 - Welcome and privacy check

1. Greet briefly: what setup will produce (Positioning trio, extracts,
   canonical resume JSON, connected API key) and that it takes 10-20 minutes.
2. Run `git remote -v`. If a remote exists, remind the user: this repo will
   contain their real career data from here on, so the remote copy MUST be
   private. Ask them to confirm the remote is a private repo (from "Use this
   template" with Private selected) before continuing. If they cannot
   confirm, stop.

## Step 1 - Prerequisites and API key

1. Check `python3 --version` (need 3.9+) and `git --version`.
2. If `.env` does not exist: `cp .env.example .env`, then ask the user to
   open `.env` in their editor and paste their API key after the `=` sign
   (Reactive Resume -> Settings -> Security -> API Keys). **The key must
   never be pasted into chat.** Wait for them to say it is done.
3. Run the awk readiness check from the skill's `references/api-scripts.md`.
   If `missing_or_empty`, help them fix `.env` (without ever displaying it)
   and re-check.
4. Run `python3 scripts/reactive_resume_api.py check-auth`. On a hard error
   (auth, rate limit, server, or network), report the safe error and stop.
   Record whether `applicationsApi` is true; `false` means the instance
   genuinely lacks the Applications API (an older self-hosted instance), so
   tell the user tracking will be unavailable but publishing still works.

## Step 2 - Extract intake documents

1. Glob `Materials/intake/*` (excluding README.md). If empty, ask the user to
   drop in their CV and LinkedIn PDF export now (explain: profile page ->
   More -> Save to PDF), or continue with interview-only setup.
2. Read each document. PDFs: read in chunks with the `pages` parameter.
3. For each source, write `Materials/<Doc>-extract.md`: contact block, role
   history (employer, title, period, location, bullets verbatim), education,
   certifications, skills, languages, volunteering. Flag conflicts between
   sources (e.g. differing dates) for the interview.

## Step 3 - Positioning interview

Run the question batches from the skill's `references/setup-interview.md`
(role targets, domain and stage, location and format, compensation band,
dealbreakers, must-haves). Seed options from the extracts. Write
`Positioning/Target-Roles.md` using the template in
`references/positioning-templates.md`, show it, and apply requested edits.

## Step 4 - Master CV and accomplishments

1. Draft `Positioning/Master-CV.md` from the extracts (template in
   `references/positioning-templates.md`): every role, strictly
   reverse-chronological, facts only from the extracts.
2. Run the accomplishment-mining interview from
   `references/setup-interview.md` (metric / scope / before-after / decision
   probes, newest roles first).
3. Write `Positioning/Accomplishments.md` and fold the mined bullets into
   Master-CV.
4. **Explicit review gate:** tell the user to open and edit both files
   directly, then confirm in chat. Do not continue until they confirm.

## Step 5 - Canonical resume JSON

Ask: pull an existing resume from your Reactive Resume account, or bootstrap
a fresh one?

- **Pull:** run `resumes-list`, show id/name/slug, let the user pick, then
  `resume-get --id <id> --out Materials/resume-canonical.json` (add
  `--force` only if the user confirmed overwriting an existing file).
- **Bootstrap:** copy
  `.claude/skills/rx-job-application-kit/assets/canonical-default.json` to
  `Materials/resume-canonical.json`, then fill it from Master-CV per the
  bootstrap variant in `references/resume-json-contract.md` (fresh UUIDs for
  every item; `picture.url` stays empty, the photo is uploaded later in the
  Reactive Resume UI).

## Step 6 - Validate, configure, commit

1. `python3 scripts/reactive_resume_publish.py --json Materials/resume-canonical.json --validate-only`
   must return `"status": "valid"`. Fix and re-run if not.
2. Write `kit.config.json`: `language_default` (ask: en or de),
   `languages`, `currency` (from the compensation question).
3. Summarize what was created. Then stage **only** the explicit paths this
   flow created or updated that exist, for example
   `git add Positioning kit.config.json Materials/*-extract.md Materials/resume-canonical.json`
   (skip any path that is absent). Never use `git add -A` or `git add .`;
   intake documents (`Materials/intake/`) and `.env` are gitignored and must
   never be staged. Show the user exactly what is staged with
   `git status --short` and `git --no-pager diff --cached --stat`, and wait
   for their confirmation. Only after they confirm, run
   `git commit -m "chore: complete kit setup"`.
4. Point the user at `/apply` for their first JD and
   `examples/alex-sample/` for a worked reference.
