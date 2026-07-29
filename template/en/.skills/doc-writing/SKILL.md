---
name: doc-writing
description: Rules for writing and editing documents. Use when producing READMEs, technical docs, design docs, change summaries, PR bodies, or user-facing prose.
---

# Writing documents

> Default language **{{FILL:docs.language}}** · tone **{{FILL:docs.tone}}** · primary format **{{FILL:docs.primary_format}}**

## Before starting
- **Don't create documents nobody asked for.** No spontaneous READMEs or summary `.md` files.
- Prefer editing an existing document over adding a new one.
- Pick the reader (newcomer / fellow engineer / decision-maker). Depth and vocabulary follow from that.

## Structure
- **Conclusion first.** What and why in the opening paragraph. Don't lead with background.
- One document, one purpose. Two purposes means two documents.
- Make it scannable: numbered lists for procedures, bullets for parallel items, tables for comparisons.
  Connected reasoning goes in sentences — don't turn everything into a list.

## Notation
- Wrap file paths, function names, commands, and identifiers in inline code. Tag code blocks with a language.
- Command examples must **actually run**. Make placeholders obvious: `${VAR}` / `<your-token>`.
- Use ASCII hyphens (`-`). Exotic unicode dashes break rendering.
- Absolute dates (`2026-05-27`), not relative ones ("yesterday").
- Emoji only when the user asks for them.

## Citation rules that matter
- Cite a source URL for external facts → see `.skills/web-research/SKILL.md`.
- **Never leave tool-internal tokens in the prose**: things like `[145036†L1-L9]` or `【turn1†view0】`.
  Convert them to normal human-readable citations.
- No broken URLs or leftover placeholders (`TODO: write this`) in the final version.

## By document type
| Type | Put first | Common failure |
|---|---|---|
| README | What it is and how to run it | Missing install steps, long philosophy |
| Design doc | The decision, the reason, alternatives considered | Only implementation detail |
| PR body | What changed and why + how to test | Narrating the diff |
| Change summary | Impact on the user | Showing off internal refactors |

## If the output is docx/pdf
When {{FILL:docs.primary_format}} is docx or pdf, render it and **look at the page images yourself**
for clipping, broken tables, and misalignment before handing it over.
