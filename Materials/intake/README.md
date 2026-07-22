# Materials/intake - drop zone

Drop your raw career documents here before running `/setup`:

- Current CV(s) as PDF or markdown (any language)
- LinkedIn profile export (PDF: your profile page -> More -> Save to PDF)
- Reference letters, certificates, transcripts (optional)

`/setup` reads every file in this folder and writes a structured extract per
document to `Materials/<Doc>-extract.md`. The extracts feed the positioning
interview and your Master CV.

**Privacy:** everything in this folder except this README is gitignored. Your
raw PDFs never leave your machine, even in a private repo copy. The derived
extracts in `Materials/` ARE committed (that is the point of your private
copy); do not make your copy public.
