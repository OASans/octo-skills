---
---

Dependency audit. Check for outdated, unused, and insecure dependencies.

Usage: `/deps`

Context:
- Rust toolchain: `!rustc --version`
- Dependency count: `!cargo metadata --format-version 1 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin)['packages']))" 2>/dev/null || echo "unknown"`

Steps:

1. Run `cargo update --dry-run` to check for outdated deps.
2. Run `cargo audit` if installed. If not, suggest installing: `cargo install cargo-audit`.
3. Scan for unused deps:
   - Read `Cargo.toml` dependency list.
   - For each dep, Grep for its crate name in `src/`. Flag deps with zero references (excluding proc macros and build deps).
4. Check feature flags: Read `Cargo.toml` features section. Flag features that enable unused functionality.
5. Check for duplicate deps: `cargo tree --duplicates` if available.
6. Report:
   - **Security:** vulnerabilities found by cargo-audit
   - **Outdated:** deps with available updates (major/minor/patch)
   - **Unused:** deps with no code references
   - **Duplicates:** different versions of the same crate
   - **Recommendations:** specific actions ordered by priority
