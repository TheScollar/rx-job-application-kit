# Markdown to Reactive Resume HTML

Reactive Resume rich-text fields (`summary.content`, experience/role
`description`, and other description fields) take a restricted HTML dialect.
Convert markdown content with this table:

| Markdown | HTML |
|----------|------|
| Plain paragraph | `<p><span>text</span></p>` |
| Bullet list | `<ul><li><p><span>text</span></p></li></ul>` |
| **Bold** | `<strong>text</strong>` inside the span |
| `&` in text | `&amp;` |
| Paragraph followed by a list | Add `<p></p>` spacer between them |

Rules:

1. Every text run is wrapped `<p><span>...</span></p>`, including inside
   `<li>`.
2. The spacer rule is mandatory: when a paragraph and a bullet list appear in
   the same field, insert an empty `<p></p>` between them, otherwise they
   render without vertical spacing.
3. Escape `&` as `&amp;`. Keep other characters literal; do not HTML-encode
   umlauts or quotes.
4. No headings, links, tables, or nested lists inside description fields.
5. Keep bold for metrics and product names only; do not bold whole sentences.

Example. Markdown:

```markdown
Owned the analytics platform end to end.

- Grew weekly active dashboards by **40%** in two quarters
- Launched usage-based pricing & billing integration
```

HTML:

```html
<p><span>Owned the analytics platform end to end.</span></p><p></p><ul><li><p><span>Grew weekly active dashboards by <strong>40%</strong> in two quarters</span></p></li><li><p><span>Launched usage-based pricing &amp; billing integration</span></p></li></ul>
```
