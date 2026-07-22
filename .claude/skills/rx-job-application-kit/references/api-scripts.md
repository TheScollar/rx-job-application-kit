# API scripts: invocation recipes

All Reactive Resume API access goes through the two scripts in `scripts/`.
Both are stdlib-only Python (3.9+), read the key from `.env`, print exactly
one JSON object (result to stdout, safe errors to stderr), and never print
secrets.

## The `.env` invariant

**Never Read, cat, echo, grep-without-`-q`, or otherwise display `.env`.**
The only permitted check is this readiness snippet, run from the repo root,
which outputs a status string and nothing else:

```bash
if [[ -f .env ]] && awk '
  /^[[:space:]]*(export[[:space:]]+)?REACTIVE_RESUME_API_KEY[[:space:]]*=/ {
    value = $0
    sub(/^[[:space:]]*(export[[:space:]]+)?REACTIVE_RESUME_API_KEY[[:space:]]*=[[:space:]]*/, "", value)
    gsub(/[[:space:]]+$/, "", value)
    if (value ~ /^".*"$/ || value ~ /^\047.*\047$/) {
      value = substr(value, 2, length(value) - 2)
    }
    if (length(value) > 0) found = 1
  }
  END { exit(found ? 0 : 1) }
' .env; then
  printf '%s\n' 'reactive_resume_env=ready'
else
  printf '%s\n' 'reactive_resume_env=missing_or_empty'
fi
```

If the result is `missing_or_empty`, stop and tell the user to put their key
into `.env` (copy `.env.example` to `.env`, paste the key after the `=`).
The user pastes the key into the file themselves; never ask for the key in
chat.

## Exit code matrix (both scripts)

| Exit | Meaning | What to do |
|---|---|---|
| 0 | Success, verified | Record returned IDs/values, continue |
| 1 | Error, nothing usable was created (stderr JSON) | Report the safe error, stop, never auto-retry auth/validation failures |
| 2 | Created/updated but verification incomplete | The remote object EXISTS and must not be deleted or recreated. Report its ID and warnings, stop for user direction |

## Publisher: `scripts/reactive_resume_publish.py`

```bash
# Local validation only (no credentials, no network)
python3 scripts/reactive_resume_publish.py \
  --json "Applications/<folder>/CV-Tailored.json" --validate-only

# Publish (always private; duplicate slugs get -2, -3 suffixes)
python3 scripts/reactive_resume_publish.py \
  --json "Applications/<folder>/CV-Tailored.json" \
  --name "<resume name>" \
  --slug "<base-slug>" \
  --tag "job-application" --tag "<Company>" --tag "<EN|DE>"
```

Success stdout: `{"status": "published", "id": ..., "name": ..., "slug": ...,
"tags": [...], "isPublic": false, "apiUrl": ..., "verified": true, ...}`.
On exit 2 (`created_verification_incomplete`) the resume exists; keep it.
On exit 1 the helper deletes only its own empty shell if populating failed;
if that cleanup also fails, it reports the orphaned resume ID prominently.

## API client: `scripts/reactive_resume_api.py`

```bash
# Auth + capability check (start of /setup, and before tracking in /apply)
python3 scripts/reactive_resume_api.py check-auth
# -> {"status": "ok", "resumesCount": N, "applicationsApi": true|false, ...}

# Pull the canonical resume during /setup
python3 scripts/reactive_resume_api.py resumes-list
python3 scripts/reactive_resume_api.py resume-get \
  --id "<resume-id>" --out "Materials/resume-canonical.json"   # --force to overwrite

# Track an application after publish (in /apply)
python3 scripts/reactive_resume_api.py app-create \
  --company "<Company>" --role "<Role>" --status saved \
  --resume-id "<id from publish result>" \
  --source "<linkedin|headhunter|direct|referral>" \
  --source-url "<JD URL>" --location "<from JD>" \
  --jd-file "/tmp/jd-<slug>.txt" --tag "job-application"

# Pipeline reads (used by /pipeline)
python3 scripts/reactive_resume_api.py app-list
python3 scripts/reactive_resume_api.py app-list --status interview --include-archived
python3 scripts/reactive_resume_api.py app-stats
python3 scripts/reactive_resume_api.py app-get --id "<application-id>"

# Status/follow-up updates (only on explicit user request; the kanban is primary)
python3 scripts/reactive_resume_api.py app-update --id "<id>" --status applied
python3 scripts/reactive_resume_api.py app-update --id "<id>" \
  --follow-up-at 2026-08-01 --follow-up-note "Ping recruiter"
```

Notes:

- Application status enum (client-validated): `saved`, `applied`,
  `screening`, `interview`, `offer`, `rejected`.
- `--jd-file` avoids putting long JD text into argv; the script truncates to
  the API's 20,000-character maximum and reports a warning when it does.
- If `check-auth` reports `"applicationsApi": false` (older self-hosted
  instance), skip all `app-*` calls, warn the user once, and continue;
  publishing still works.
- There is deliberately NO delete subcommand. Never delete remote objects.
- `--env-file` and `--base-url` exist on every subcommand for testing;
  default is `.env` in the repo root and the hosted API.
