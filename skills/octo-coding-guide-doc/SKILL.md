---
name: octo-coding-guide-doc
guide-scope: "**/*.md"
description: >
  Print the shared documentation guide — the bar every Markdown document must meet:
  compact, self-contained, internally correct. Covers all `.md` files: design docs,
  handover docs, skill definitions, CLAUDE.md, READMEs. Inline skill — no sub-agents.
  Use as a reference when writing or reviewing any Markdown document.
---

# Documentation Guide

> **Guide family.** This is one guide in a family of scoped guides (`octo-coding-guide-*`),
> each carrying a `guide-scope` in its frontmatter that says which changed files it
> covers. This guide's scope is `**/*.md` — every Markdown document, whatever its job:
> design docs, handover notes, skill definitions (`SKILL.md`), `CLAUDE.md`, READMEs.
> They differ in content but share one quality bar, captured below. A Markdown change
> is reviewed against this guide and no code guide — Markdown is prose, not code, so
> code-correctness rules do not apply to it.
>
> **Structure contract.** The `##` section below is a self-contained *review domain*:
> a single coherent focus, reviewable **only** against the rules within it. `###`
> headings are rule groups inside it. Keep the `*Review focus:*` line accurate — it
> states the domain's one job in a sentence.

## Documentation

*Review focus: is this document compact, self-contained, shaped for its job, and correct about everything it states?*

### Compact

- **Only What's Needed**: Say the necessary thing once and stop — cut preamble, recaps, and restated context. Shorter is better as long as nothing required is lost.
- **Plain Words**: Prefer plain, direct prose over padded or ceremonial phrasing. Easy to read beats impressive.
- **No Decorative Markdown**: No decorative headings, emoji, or formatting that carries no information. Structure should reflect real structure, not dress up the page.

### Self-Contained

- **No Cross-Document References**: A document stands on its own — don't make it depend on the reader having another doc open, and don't point at sibling docs for meaning the reader needs here. Linking to a canonical source for *more* is fine; requiring it to understand *this* is not.
- **No Duplication Across Docs**: Don't copy content that already lives in another document. One fact, one home — restating it elsewhere creates two things to keep in sync and one to forget.

### Instructional Documents

*Applies to skills (`SKILL.md`), guides, and any document whose job is to tell a reader what to do.*

- **Lead With The Spine**: Give the reader a walkable list — ordered steps for a procedure, a flat rule list for a catalogue — and hang everything else off it as reference. Themed prose with no list makes every reader re-derive one, and nothing is ever deleted from it.
- **One Rule, Two Sentences Max**: State each rule once, imperatively, in at most two sentences — don't restate it from a second angle and don't argue for it. If it won't fit, stop and discuss it with the user instead of writing a paragraph.
- **Cut The Incident**: Keep the rule, drop the bug that produced it. Name a case only when the rule is unusable without it, and then in a clause, not a paragraph.
- **Rules, Not Internals**: Carry the rule, not the mechanism. Identifiers, thresholds, file layouts, and failure modes belong to the code that owns them — leave them there.
- **Guides Cite Nothing**: A coding-guide skill carries only its own rules — never point at another skill, doc, or file. A reader follows it with the guide alone open.

### Internally Correct

- **Accurate About Itself**: Every claim, path, command, filename, and example the document states must be true and current. A doc that describes behavior, structure, or commands that no longer exist is worse than no doc.
- **Internally Consistent**: The document must not contradict itself — terminology, names, and stated rules stay consistent from top to bottom.
