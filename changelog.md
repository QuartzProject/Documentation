# Changelog and the road to 1.0

## 0.1.0 (unreleased)

The first version: the whole language of the current specification, both execution tiers and the tools.

- **Language:** static types with inference; `int`, `float`, `byte` and fixed-width numbers; strings with
  interpolation and formats, multi-line strings in triple quotes and raw strings (`r"..."`, `r#"..."#`); structs,
  enums with data (recursive ones included) and exhaustive `match`; patterns that nest, with guards, ranges and
  alternatives (`A | B`), also in `let`, `is`, `if let` and `while let`; null safety with `??` (also `?? return`,
  `?? break` and `?? continue`), `?.`, comparison with `null`, `is null` and `null` arms on any nullable (handles,
  floats, lists and maps included) and narrowing after a `null` arm; `let` that takes apart an enum with one variant;
  generic variants that take their type from sibling arguments (`Opt.Some(1, Opt.None)`); map keys that are lists or
  recursive enums, compared by content;
  `Result` and `?`, with `Ok` and `Err` inferred from sibling branches and `Result<(), E>` for results without a value;
  generics with traits and `@derive(Eq, Hash, Ord, Show)`; iterators; functions as values and lambdas; fixed-size
  arrays `[T; N]`; `value with { field = x }` updates; constants evaluated at compile time; functions of a type called
  through its name (`Duration.parse`); nullable fields that default to `null`; packages with reverse-domain names and
  visibility; `state` with versions, renames, migrations and per-handle instances; coroutines (`suspend fn`, `wait`,
  `every`, `at`, `scope`); attributes for hosts (`@on`, `@command`, `@requires`, `@property`, `@handle`,
  `@awaitable`, `@repr(C)`) and for tools (`@test`, `@deprecated`, `@inline`, `@noinline`).
- **Runtime:** a validated IR as the security boundary; a register interpreter faster than Lua; an optional LLVM tier
  with the same results, tiered in the background, with an on-disk cache; fuel, memory quotas and recursion limits that
  are always on; arenas instead of a garbage collector; deterministic floats and math; values of any depth copied,
  stored, exported and linked without the native stack, the walk counted against the memory limit, while `==`,
  `Show` and `Encode` on values thousands of levels deep stop with a stack overflow trap.
- **Hosts:** a C++ API with typed bindings, a C API and `libquartz`; structured diagnostics with warning levels per
  rule; signed `.qzb` modules; hot reload with state migration; tasks whose results may be any value; packages linked
  across sandboxes with structs, lists and maps copied between them, and generated interfaces that keep parameter
  names, documentation and defaults; sandboxes on many threads; `exportState` documents in format 2 (older ones still
  load). The C API is at level 5: lossy text from outside (`qz_sandbox_str_lossy`, `qz_call_str_lossy`), DEFLATE with
  raw, zlib and gzip framing and CRC-32 (`qz_deflate`, `qz_inflate`, `qz_crc32`), the `///` documentation of functions,
  types and members, and `qz_type_variant_boxed` for recursive payloads (see
  [API level 5](embedding.md#api-level-5)). A trap leaves the `state` as the program left it, and
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
  configuration cache, tasks skipped while up to date and run in parallel, build plugins written in Quartz that run in
  a sandbox, warning levels per rule, `qiln add` and `qiln remove`, Maven layout repositories with signed `.qzmeta`
  files, publishing over HTTPS with credentials, `qiln.lock`, and `.qiln/api/`, from which `quartz-lsp` checks and
  completes build scripts. The package registry moved out of the `quartz` command: `quartz add`, `fetch`,
  `publish`, `owner` and `new`, `quartz.lock` and the `$QUARTZ_CACHE` cache are gone; `qiln` replaces them (see
  [Qiln](qiln.md) and [Repository format](registry-format.md)).
- **Embed:** Quartz as a source language of Gradle and CMake projects, with modules type checked against the host's
  API, typed facades, kits of capabilities granted per module, commands and listeners registered from `@command` and
  `@on`, and single-file native executables (see [Embed](embed.md)).
- **Bindings:** Java and Kotlin over the FFM API, and Kotlin Multiplatform for the JVM, Kotlin/Native, Android,
  Kotlin/JS and Kotlin/Wasm (see [Quartz on the JVM](jvm.md)), at C API level 5: recursive enum payloads read and
  taken as the value itself, lists and recursive enums as map keys, lossy text from the host, `///` docs of functions,
  types, fields and variants, and DEFLATE, zlib, gzip and CRC-32.
- **Platforms:** Linux x86-64 and arm64, Windows x64, Android, and WebAssembly in Node and browsers (the playground at
  quartzlang.org runs on it); macOS and FreeBSD written but not verified yet.

## Before 1.0

Each of these is either a change that would break programs or hosts later, or something a stable release needs:

1. **Language surface frozen:** the open corners closed before stability is promised: methods and patterns on
   fixed-size arrays and functions of a type used as values. A struct that holds a nullable of itself stays an error,
   since an enum covers the case with the same memory.
2. **Standard library shape:** the names of the essential library and of the packages beyond it (typed configuration,
   `Decimal`, `Duration`, cryptography, collections), fixed so that they will not change.
3. **Binary module format:** a runtime that loads every older minor version of the same major version.
4. **C interface:** reviewed once more, then frozen at `QZ_ABI_VERSION` 1 for all of 1.x.
5. **Package repository:** the public repository at repo.quartzlang.org, with namespace verification.
6. **Verified platforms:** macOS and FreeBSD tested in CI like the others.

After 1.0 the language, the C interface and the module format follow semantic versioning.
