# Rust Guide

Use alongside the common coding guide when changing Rust.

### Test Layout

- **Sibling Test Files**: Unit tests live in a sibling file, never an inline `mod tests` block. In `foo.rs` write `#[cfg(test)] #[path = "foo_tests.rs"] mod tests;` and put the tests in `foo_tests.rs`.

### Pattern Matching

- **Match Ergonomics over `ref`**: Borrow at the scrutinee — `if let Some(x) = &expr` / `match &expr` — instead of `ref` bindings inside the pattern. `ref` is legacy pre-2018 style.

### Global State

- **No New Interior-Mutable Globals**: Don't add `static` items with interior-mutability types (`OnceLock`, `OnceCell`, `Lazy(Lock)?`, `Mutex`, `RwLock`, `Atomic*`). Hold state in a struct and pass it through. Pre-existing grandfathered globals are exempt; do not add more.

### Module Layout

- **`mod.rs` Is Declaration-Only**: A `mod.rs` holds only module wiring — `mod`/`pub use`/`pub mod` declarations and re-exports — never functions, types, or other logic; put those in a sibling or child module. Because it carries no logic, a `mod.rs` needs no unit tests (it is exempt from the **Sibling Test Files** rule).
