# Changelog and the road to 1.0

## 0.1.0 (unreleased)

The first version: the whole language of the current specification, both execution tiers and the tools.

- **Language:** static types with inference; `int`, `float`, `byte` and fixed-width numbers; strings with
  interpolation and formats, multi-line strings in triple quotes and raw strings (`r"..."`, `r#"..."#`); structs,
  enums with data (recursive ones included) and exhaustive `match`; patterns that nest, with guards, ranges and
  alternatives (`A | B`), also in `let`, `is`, `if let` and `while let`; null safety with `??` (also `?? return`,
  `?? break` and `?? continue`), `?.`, comparison with `null` on any nullable and narrowing after a `null` arm;
  `Result` and `?`, with `Ok` and `Err` inferred from sibling branches and `Result<(), E>` for results without a value;
  generics with traits and `@derive(Eq, Hash, Ord, Show)`; iterators; functions as values and lambdas; fixed-size
  arrays `[T; N]`; `value with { field = x }` updates; constants evaluated at compile time; functions of a type called
  through its name (`Duration.parse`); nullable fields that default to `null`; packages with reverse-domain names and
  visibility; `state` with versions, renames, migrations and per-handle instances; coroutines (`suspend fn`, `wait`,
  `every`, `at`, `scope`); attributes for hosts (`@on`, `@command`, `@requires`, `@property`, `@handle`,
  `@awaitable`, `@repr(C)`) and for tools (`@test`, `@deprecated`, `@inline`, `@noinline`).
- **Runtime:** a validated IR as the security boundary; a register interpreter faster than Lua; an optional LLVM tier
  with the same results, tiered in the background, with an on-disk cache; fuel, memory quotas and recursion limits that
  are always on; arenas instead of a garbage collector; deterministic floats and math.
- **Hosts:** a C++ API with typed bindings, a C API and `libquartz`; structured diagnostics with warning levels per
  rule; signed `.qzb` modules; hot reload with state migration; tasks whose results may be any value; packages linked
  across sandboxes with structs, lists and maps copied between them, and generated interfaces that keep parameter
  names, documentation and defaults; sandboxes on many threads. A trap leaves the `state` as the program left it, and
  the [embedding chapter](embedding.md#traps-and-state) says what hosts do about it.
- **Library:** `org.quartzlang.data` (JSON, TOML, YAML, and typed decoding and encoding with
  `@derive(Decode, Encode)`), `collections` (sets, sorted maps and sets, priority queues, deques, LRU caches, bit
  sets), `bytes` (with readers, writers and varints), `compress` (deflate, zlib, gzip, zstd), `zip`, `math`, `random`,
  `crypto` (SHA-2, HMAC, BLAKE2b, Ed25519, Argon2id), `encoding` (base64, hex, UUID), `time` (durations, instants,
  cron), `decimal`, `text` (globs, edit distance, ICU-style messages with plurals), `regex` (linear-time regular
  expressions, with named groups), `formats` (CSV, properties, MessagePack), `geometry`, `noise`, `semver`, and the
  `http` and `log` shapes over host capabilities; checked and saturating arithmetic on every integer type; `sort`,
  `sorted`, `min` and `max` on lists of any `Ord` type.
- **Tools:** `quartz` (check, run, test, build, interface, keygen, fmt, doc, repl, debug); compiler warnings with a
  rule id each and a level per rule (`--rule`, `--deny-warnings`); a debugger over the Debug Adapter Protocol, with
  conditional breakpoints, stepping, variables and stops on traps; a profiler (`quartz run --profile`) that counts
  calls, fuel and time per function and per call path and writes speedscope files; `quartz-lsp`.
- **Editors:** the VS Code extension and the JetBrains plugin, both with the language server and the debugger; the
  tree-sitter grammar for Neovim, Helix and Zed; the TextMate grammar; Notepad++.
- **Qiln:** the build and package tool, with builds configured in Quartz (`build.qz`, `settings.qz`), a
  configuration cache, build plugins written in Quartz that run in a sandbox, Maven layout repositories with signed
  `.qzmeta` files, and `qiln.lock`. The package registry moved out of the `quartz` command: `quartz add`, `fetch`,
  `publish`, `owner` and `new`, `quartz.lock` and the `$QUARTZ_CACHE` cache are gone; `qiln` replaces them (see
  [Qiln](qiln.md) and [Repository format](registry-format.md)).
- **Embed:** Quartz as a source language of Gradle and CMake projects, with modules type checked against the host's
  API, typed facades, kits of capabilities granted per module, commands and listeners registered from `@command` and
  `@on`, and single-file native executables (see [Embed](embed.md)).
- **Bindings:** Java and Kotlin over the FFM API, and Kotlin Multiplatform for the JVM, Kotlin/Native, Android,
  Kotlin/JS and Kotlin/Wasm (see [Quartz on the JVM](jvm.md)).
- **Platforms:** Linux x86-64 and arm64, Windows x64, Android, and WebAssembly in Node and browsers (the playground at
  quartzlang.org runs on it); macOS and FreeBSD written but not verified yet.

## Before 1.0

Each of these is either a change that would break programs or hosts later, or something a stable release needs:

1. **Language surface frozen:** the open corners closed before stability is promised: methods and patterns on
   fixed-size arrays, functions of a type used as values, `is null` on nullable handles, and recursive types beyond
   enums (`Hash` on recursive enums, structs that hold a nullable of themselves).
2. **Standard library shape:** the names of the essential library and of the packages beyond it (typed configuration,
   `Decimal`, `Duration`, cryptography, collections), fixed so that they will not change.
3. **Deep values:** copying a value nested hundreds of thousands of levels deep between a call, a task and the `state`
   must not exhaust the native stack.
4. **Binary module format:** a runtime that loads every older minor version of the same major version.
5. **C interface:** the JVM and Kotlin bindings brought up to its current level (structured diagnostics, exports, task
   results), reviewed once more, then frozen at `QZ_ABI_VERSION` 1 for all of 1.x.
6. **Package repository:** the public repository at repo.quartzlang.org, with namespace verification.
7. **Verified platforms:** macOS and FreeBSD tested in CI like the others.

After 1.0 the language, the C interface and the module format follow semantic versioning.
