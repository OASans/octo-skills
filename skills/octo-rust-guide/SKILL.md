---
name: octo-rust-guide
guide-scope: "**/*.rs"
description: >
  Print the shared Rust guide — this codebase's Rust-specific conventions for
  test layout, pattern matching, and global state. Inline skill — no sub-agents.
  Use as a reference for Rust code reviews, implementation decisions, and plan evaluation.
---

# Rust Guide

> **Guide family.** This is one guide in a family of scoped guides (`octo-*-guide`),
> each carrying a `guide-scope` in its frontmatter that says which changed files it
> covers. This guide's scope is `**/*.rs` — it adds Rust-specific rules on top of the
> general `octo-coding-guide` (scope `code`), which a Rust change is also reviewed
> against. Keep this guide to Rust specifics only; general code quality lives in the
> coding guide.
>
> **Structure contract.** Each `##` section below is a self-contained *review
> domain*: a single coherent focus, reviewable **only** against the rules within it,
> with no overlap onto another domain. `###` headings are rule groups inside a domain.
> Keep the `*Review focus:*` line accurate — it states the domain's one job in a sentence.

## Rust Guidance

*Review focus: where the change touches Rust, does it follow this codebase's conventions for test layout, pattern matching, and global state?*

### Test Layout

- **Sibling Test Files**: Unit tests live in a sibling file, never an inline `mod tests` block. In `foo.rs` write `#[cfg(test)] #[path = "foo_tests.rs"] mod tests;` and put the tests in `foo_tests.rs`.

### Pattern Matching

- **Match Ergonomics over `ref`**: Borrow at the scrutinee — `if let Some(x) = &expr` / `match &expr` — instead of `ref` bindings inside the pattern. `ref` is legacy pre-2018 style.

### Global State

- **No New Interior-Mutable Globals**: Don't add `static` items with interior-mutability types (`OnceLock`, `OnceCell`, `Lazy(Lock)?`, `Mutex`, `RwLock`, `Atomic*`). Hold state in a struct and pass it through. Pre-existing grandfathered globals are exempt; do not add more.
