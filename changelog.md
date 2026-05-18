# Changelog and the road to 1.0

## 0.1.0 (unreleased)

The first version: the whole language of the current specification, both execution tiers and the tools.

- **Language:** static types with inference; `int`, `float`, `byte` and fixed-width numbers; structs, enums with data
  and exhaustive `match`; null safety; `Result` and `?`; generics with traits; functions as values and lambdas; packages with reverse-domain names and
  visibility; `state` with versions, renames, migrations and per-handle instances; coroutines (`suspend fn`, `wait`,
  `every`, `at`, `scope`); attributes for hosts (`@on`, `@command`, `@requires`, `@property`, `@handle`,
  `@awaitable`, `@repr(C)`) and for tools (`@test`, `@deprecated`, `@inline`, `@noinline`).
- **Runtime:** a validated IR as the security boundary; a register interpreter faster than Lua; an optional LLVM tier
  with the same results, tiered in the background, with an on-disk cache; fuel, memory quotas and recursion limits that
  are always on; arenas instead of a garbage collector; deterministic floats and math.
- **Hosts:** a C++ API with typed bindings, a C API and `libquartz`; signed `.qzb` modules; hot reload with state
  migration; packages linked across sandboxes with structs, lists and maps copied between them; sandboxes on many
  threads.
- **Library:** `org.quartzlang.data` (JSON, TOML, YAML), `bytes` (with readers, writers and varints), `compress`
  (deflate, zlib, gzip, zstd), `zip`, `math`, `random`, `crypto` (SHA-2, HMAC, BLAKE2b, Ed25519, Argon2id),
  `encoding` (base64, hex, UUID), `time` (durations, instants, cron), `decimal`, `text` (globs, edit distance, ICU-style
  messages with plurals), `regex` (linear-time regular expressions), `formats` (CSV, properties, MessagePack),
  `geometry`, `noise`, `semver`, and the `http` and `log` shapes over host capabilities; checked and saturating
  arithmetic on every integer type.
- **Tools:** `quartz` (check, run, test, build, new, interface, fmt), `quartz-lsp`, a VS Code extension, a tree-sitter
  grammar for Neovim, Helix and Zed.
- **Platforms:** Linux x86-64 and arm64, Windows x64; macOS and FreeBSD written but not verified yet.

## Before 1.0

Each of these is either a change that would break programs or hosts later, or something a stable release needs:

1. **Language surface frozen:** complete traits (`Eq`, `Hash`, `Ord`, `Show`, `@derive`), full pattern
   matching, iterators. These change how code is written, so they come before stability is promised.
2. **Standard library shape:** the essential library (text, lists, random numbers, the rest of `math`) and the packages
   beyond it (typed configuration, `Decimal`, `Duration`, cryptography, collections), with names that will not change.
3. **Binary module format:** a runtime that loads every older minor version of the same major version.
4. **C interface:** reviewed once more against the JVM and Kotlin bindings, then frozen at `QZ_ABI_VERSION` 1 for all of
   1.x.
5. **Package repository:** a public index at quartzlang.org with publisher verification.
6. **Verified platforms:** macOS and FreeBSD tested in CI like the others.

After 1.0 the language, the C interface and the module format follow semantic versioning.
