# Reactive Resume API endpoints (pinned)

Pinned against the hosted Reactive Resume **OpenAPI spec v5.2.2**
(`https://docs.rxresu.me/spec.json`). Auth is an `x-api-key` header. The
hosted base URL is `https://rxresu.me/api/openapi`; self-hosters override via
`REACTIVE_RESUME_BASE_URL` in `.env`. The Applications API requires v5+.

The kit's scripts wrap these; never call them directly.

## Resumes (used by the kit)

| Method | Path | Operation |
|---|---|---|
| GET | `/resumes` | list resumes |
| POST | `/resumes` | create (name, slug, tags, `withSampleData: false`) |
| GET | `/resumes/{id}` | get (includes `data` = ResumeData) |
| PUT | `/resumes/{id}` | replace data, set `isPublic: false` |
| DELETE | `/resumes/{id}` | used ONLY by the publisher's own empty-shell cleanup |

## Applications

| Method | Path | Operation | Used by kit |
|---|---|---|---|
| GET | `/applications` | list (query: `status`, `tags`, `includeArchived`) | yes |
| POST | `/applications` | create; response body is the new ID (string) | yes |
| GET | `/applications/{id}` | get | yes |
| PUT | `/applications/{id}` | partial update; adds `archived: boolean` | yes |
| DELETE | `/applications/{id}` | delete | **never** |
| GET | `/applications/stats` | `{total, byStage, bySource}` | yes |
| GET | `/applications/tags` | list tags | no |
| POST | `/applications/{id}/notes` | add activity note | no |
| POST | `/applications/import` | CSV import (max 500) | no |
| POST | `/applications/bulk-update` | bulk ops | no |
| POST | `/applications/bulk-delete` | bulk ops | **never** |
| POST | `/applications/ai/autofill` | AI ops | no |
| POST | `/applications/{id}/ai/match-score` | AI ops | no |
| POST | `/applications/{id}/ai/tailor-resume` | AI ops | no |
| POST | `/applications/{id}/ai/draft-message` | AI ops | no |

## Application create/update fields

Create requires only `company` + `role`. Optional: `location`, `salary`,
`source`, `sourceUrl`, `jobDescription` (max 20,000 chars), `notes`,
`resumeId` (links a published resume), `tags[]`, `contacts[]`,
`followUpAt` (ISO date-time) / `followUpNote`, `status`.

Status enum is FIXED: `saved | applied | screening | interview | offer |
rejected`. PUT is a partial update and additionally accepts
`archived: boolean`.

## Spec drift

If a call fails in a way that suggests the API changed, re-download the spec
(`https://docs.rxresu.me/spec.json`), diff against this table, and update the
constants block at the top of `scripts/reactive_resume_api.py` plus this file
together.
