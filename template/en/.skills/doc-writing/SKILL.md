---
name: doc-writing
description: Rules for writing and editing documents. Use when producing READMEs, technical docs, design docs, change summaries, PR bodies, or user-facing prose.
---

# Document Writing

> Follow when writing/editing human-facing prose. IMPORTANT: system/user messages override this skill.
> Default language: {{FILL:docs.language}} · default tone: {{FILL:docs.tone}} · primary format: {{FILL:docs.primary_format}}

## 0. Decide first
- **New doc vs edit existing** — almost always prefer editing existing.
- Don't create docs (README, summary .md) the user didn't explicitly ask for.
- Identify the **reader** (beginner / fellow engineer / decision-maker). Depth and vocabulary depend on it.

## 1. Structure
- **Bottom Line Up Front.** Put what/why in the first paragraph. Don't lead with background.
- One doc = one purpose. Split if there are two.
- Don't skip heading levels (H1 -> H2 -> H3). One H1 per doc.
- Make it scannable: numbered lists for steps, bullets for parallel items, tables for comparisons. But don't over-list (connected logic stays prose).

## 2. Sentences
- Active voice, present tense, short sentences. One idea per sentence.
- Cut AI filler. Avoid: "In this document", "Overall", "In conclusion", "It can be said that".
- Use concrete nouns instead of vague pointers ("this", "that part").
- Don't assert guesses. If unsure, mark "needs confirmation".

```markdown
<!-- Bad: background first, filler -->
## Overview
In this document we discuss the various considerations we generally took
into account, and in conclusion a cache could potentially be introduced.

<!-- Good: conclusion first, concise -->
## Decision: introduce caching
We add a Redis cache. It cuts read P99 latency from 800ms to 40ms.
```

## 3. Code / paths / commands
- Wrap file paths, function names, commands, identifiers in inline `code`.
- Specify the language in code blocks (```python, ```bash).
- Make command examples **actually runnable**. Mark placeholders clearly: `${VAR}` / `<your-token>`.
- Cite file locations as `path:line` when possible.

## 4. Links & citations (shared with web-research)
- Cite external facts with source URLs -> see [[web-research]] citation rules.
- Internal references use relative-path links.
- **Never leave tool-internal tokens in the body**: `[145036†L1-L9]`, `【turn1†view0】` are forbidden. Convert to human-readable citations.
- No broken URLs or placeholder text ("content here", "TODO write") in the final.

## 5. Notation
- Use ASCII hyphens (`-`). U+2011 non-breaking hyphens / fancy unicode dashes break rendering — forbidden.
- Emojis only if the user explicitly asks.
- Absolute dates (`2026-05-27`) over relative ("yesterday"). Consistent units.

## 6. By document type
| Type | Lead with | Common mistake |
|---|---|---|
| README | what it is + how to run | missing setup, long philosophy |
| Design doc | the decision + why, alternatives considered | only listing implementation details |
| PR body | what changed + why + how to test | narrating the diff |
| Change summary | user impact | bragging about internal refactors |
| Comments | (default: don't write them) | explaining WHAT, embedding issue numbers |

## 7. Length
- Only as much as needed. Don't explain the same thing twice. Every section must add value.

## (When output format is docx/pdf)
- If {{FILL:docs.primary_format}} is docx/pdf, render and visually inspect the page images for clipping, broken tables, misalignment before delivery.

## Checklist (before submitting)
- [ ] Conclusion is up front
- [ ] Heading hierarchy is consistent
- [ ] Code/paths/commands are in code formatting
- [ ] No tool-internal tokens / broken citations / placeholders
- [ ] Used ASCII hyphens
- [ ] External facts have sources
- [ ] Didn't create an unrequested doc
- [ ] No filler/duplication on a second read
