# Rust Coding Guide

## Unit tests

Rust unit tests always live in a sibling file via `#[cfg(test)] #[path = "foo_tests.rs"] mod tests;` in `foo.rs`, with tests in `foo_tests.rs`. Never inline `mod tests` blocks in source files.

## Patterns

Prefer match-ergonomics `if let Some(x) = &expr` / `match &expr` over `ref` bindings inside the pattern. `ref` is legacy pre-2018 style; borrow at the scrutinee instead.

## Global state

No new `static` items with interior-mutability types (`OnceLock`, `OnceCell`, `Lazy(Lock)?`, `Mutex`, `RwLock`, `Atomic*`). Hold state in a struct, pass it through. Existing globals (`TMUX_SOCKET`, `PROCESS_CONTEXT`, tracing subscriber) are grandfathered; do not add more.
