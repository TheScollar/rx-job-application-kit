# Materials/intake - drop zone

Drop your raw career documents here before running `/setup`:

- Current CV(s) as PDF or markdown (any language)
- LinkedIn profile export (PDF: your profile page -> More -> Save to PDF)
- Reference letters, certificates, transcripts (optional)

`/setup` reads every file in this folder and writes a structured extract per
document to `Materials/<Doc>-extract.md`. The extracts feed the positioning
interview and your Master CV.

**Privacy:** everything in this folder except this README is gitignored, so
your raw documents are never committed to git. That is not the same as full
privacy: `/setup` reads these files, so their contents are processed by the
AI model like any other file you open in Claude Code, and Claude Code may
retain tool and file contents in local session transcripts according to your
account's data-retention settings (see
[Claude Code data usage](https://code.claude.com/docs/en/data-usage)). The
derived extracts in `Materials/` ARE committed (that is the point of your
private copy); do not make your copy public.
