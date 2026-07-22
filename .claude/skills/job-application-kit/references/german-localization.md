# German resume localization

For a German (`de`) resume, keep the canonical picture, template, layout, page
geometry, colors, typography, icons, and all non-language presentation fields
exactly as in `Materials/resume-canonical.json`. Change only what language
requires.

## Locale

Set `metadata.page.locale` to `de-DE`.

## Section titles

| JSON path | German title |
|-----------|--------------|
| `summary.title` | Profil |
| `sections.profiles.title` | Online-Profile |
| `sections.experience.title` | Berufserfahrung |
| `sections.education.title` | Ausbildung |
| `sections.projects.title` | Projekte |
| `sections.skills.title` | Kompetenzen |
| `sections.languages.title` | Sprachen |
| `sections.interests.title` | Interessen |
| `sections.awards.title` | Auszeichnungen |
| `sections.certifications.title` | Weiterbildungen & Zertifizierungen |
| `sections.publications.title` | Veröffentlichungen |
| `sections.volunteer.title` | Ehrenamt |
| `sections.references.title` | Referenzen |

## Content rules

- Preserve static IDs, dates, URLs, and numeric levels.
- Translate user-facing static labels, fluency values (e.g. "Native" ->
  "Muttersprache"), and descriptions consistently without changing facts.
- Dates in periods keep the `Mon YYYY - Mon YYYY` pattern with German month
  abbreviations (Jan, Feb, Mär, Apr, Mai, Jun, Jul, Aug, Sep, Okt, Nov, Dez)
  and "heute" for present.
- Numbers use German formatting in prose (e.g. `130.000+`), but keep metric
  style consistent within the resume.
- File naming: the tailored markdown becomes `CV-Tailored-DE.md` when a German
  and an English version coexist in the same application folder; the JSON
  filename stays `CV-Tailored.json` unless both languages are published (then
  `CV-Tailored-DE.json`).
- Resume name and slug use the `DE` language marker per the naming convention
  in `/apply`.
