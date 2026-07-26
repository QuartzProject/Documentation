# Examples

Runnable projects in [QuartzProject/Examples](https://github.com/QuartzProject/Examples), one folder each.

## Language tour programs (`language/`)

Standalone programs, each a short tour of one part of Quartz. They need nothing but the `quartz` tool, print what they
do, and pass `quartz check --deny-warnings`.

| Program | Shows |
|---|---|
| [`traits.qz`](https://github.com/QuartzProject/Examples/blob/main/language/traits.qz) | traits with default methods, generic functions bounded by a trait, `impl` for a built-in type, `@derive(Eq, Hash, Ord, Show)`, associated functions, structs as map keys |
| [`patterns.qz`](https://github.com/QuartzProject/Examples/blob/main/language/patterns.qz) | enums with payloads, nested patterns on tuples, enums and structs, ranges, `null` and guards in patterns, `is` tests, destructuring `let` |
| [`collections.qz`](https://github.com/QuartzProject/Examples/blob/main/language/collections.qz) | lists with lambdas (`filter`, `map`, `any`, `find`, `sortBy`), maps in insertion order, `Set`, `SortedMap` ranges, `PriorityQueue`, `Deque`, `LruCache` |
| [`config.qz`](https://github.com/QuartzProject/Examples/blob/main/language/config.qz) | one set of `@derive(Decode, Encode)` structs read from TOML, YAML and JSON, defaults, renamed keys, enums by name, errors that name the line and the path |
| [`regex.qz`](https://github.com/QuartzProject/Examples/blob/main/language/regex.qz) | linear-time regular expressions: named groups, `findAll`, replacement references, `split` with a limit, `escapeRegex`, compile errors |
| [`coroutines.qz`](https://github.com/QuartzProject/Examples/blob/main/language/coroutines.qz) | `suspend fn`, `wait` and `every` resumed by the host (`quartz run` counts ticks), a `state` passed to `main` |
| [`values.qz`](https://github.com/QuartzProject/Examples/blob/main/language/values.qz) | value semantics: `with` copies, fixed-size arrays `[T; N]` (also nested, in a `const`), `const` arithmetic, `if` and `match` as expressions |

### Running

With the `quartz` tool of a [Quartz](https://github.com/QuartzProject/Quartz) build on the `PATH`:

```console
$ quartz run traits.qz
circle with area 3.14
circle with area 19.63
...
$ quartz check --deny-warnings *.qz
```

`quartz run` prints the value `main` returns after the program's own output; `coroutines.qz` also prints how many ticks
its tasks waited.

## Paper plugin with its commands and listeners in Quartz (`paper-plugin/`)

A [Paper](https://papermc.io) plugin for Minecraft 26.3 whose behaviour is written in Quartz under
[`plugin/src/main/quartz`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/plugin/src/main/quartz). Kotlin is only wiring: it offers a typed host API to Quartz, hands
commands and events over, and saves the plugin's state. It is a port of a good part of
[MawuExample-Paper](https://github.com/BluevaDevelopment/MawuExample-Paper), where the same plugin is written in Lua.

[Quartz Embed](https://github.com/QuartzProject/Embed)'s Gradle plugin compiles the Quartz sources against the host API
at build time, so a typo in a method name or a wrong argument type fails the build at `file:line:col`, and packs the
validated modules into the jar.

### What is where

| Quartz | |
|---|---|
| [`commands/registry.qz`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/plugin/src/main/quartz/commands/registry.qz) | the list of commands, the dispatcher and tab completion |
| [`commands/info.qz`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/plugin/src/main/quartz/commands/info.qz) | `/greet`, `/quartzinfo`, `/whois` |
| [`commands/heal.qz`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/plugin/src/main/quartz/commands/heal.qz) | `/heal [player]`, with a permission |
| [`commands/kit.qz`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/plugin/src/main/quartz/commands/kit.qz) | `/kit [name]`: kits read from [`kits.toml`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/plugin/src/main/resources/kits.toml) with `@derive(Decode)`, cooldowns as durations (`5m`) kept in a `state` |
| [`commands/places.qz`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/plugin/src/main/quartz/commands/places.qz) | `/sethome`, `/home`, `/delhome`, `/setwarp`, `/warp`, `/delwarp`, kept in states |
| [`commands/talk.qz`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/plugin/src/main/quartz/commands/talk.qz) | `/msg`, `/r` (sharing who wrote last), `/announce` |
| [`events/players.qz`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/plugin/src/main/quartz/events/players.qz) | join and quit messages, the first visit (spawn, sound, action bar, broadcast), protected blocks and TNT |
| [`chat/filter.qz`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/plugin/src/main/quartz/chat/filter.qz) | the chat filter with regular expressions, a module of its own with its own sandbox |
| [`state.qz`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/plugin/src/main/quartz/state.qz), [`common.qz`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/plugin/src/main/quartz/common.qz) | the states and small helpers |

| Kotlin | |
|---|---|
| [`bridge/`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/bridge/src/main/kotlin/org/quartzlang/examples/paper/host) | the host API: `@QuartzHandle` classes `Sender` and `Player`, and `@QuartzFunction` methods on them, on `Server` and on `PluginHost` |
| [`QuartzExamplePlugin.kt`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/plugin/src/main/kotlin/org/quartzlang/examples/paper/QuartzExamplePlugin.kt) | opens the modules, registers the commands Quartz lists, saves and loads the states |
| [`Listeners.kt`](https://github.com/QuartzProject/Examples/blob/main/paper-plugin/plugin/src/main/kotlin/org/quartzlang/examples/paper/Listeners.kt) | passes each event to Quartz and applies the answer |

The host API is a project of its own (`:bridge`) because Embed generates the facades (`ExampleQuartz`, `ChatQuartz`)
from the classes it scans: with the annotated classes elsewhere (`scanOwnClasses = false`), the facades are sources the
plugin's own Kotlin can call. The generated interface is in `plugin/build/generated/quartz/main/host/host.qzi`.

Messages are MiniMessage text; anything a player typed goes through `plain(...)` first, so nobody can inject tags.
Everything in the `state` blocks is written to `plugins/QuartzExample/state.json` every five minutes and on shutdown,
and read back on start, so homes, warps and kit cooldowns survive restarts. Chat arrives on Paper's async threads, which
is why the filter lives in its own module, entered under a lock, and never blocks the main thread's sandbox.

### Building

Nothing of Quartz is published yet, so the build takes it from checkouts:

```console
$ cmake -S <Quartz> -B <libquartz build> -G Ninja -DCMAKE_BUILD_TYPE=Release -DQUARTZ_SHARED=ON
$ cmake --build <libquartz build> --target quartz_shared
$ ./gradlew build -Pquartz.jvm=<Quartz>/bindings/jvm -Pquartz.library=<libquartz build>/src/libquartz.so
```

- `quartz.embed`: the Embed checkout, `../../Embed` when not given.
- `quartz.jvm`: the JVM bindings of the core, built as part of this build.
- `quartz.library`: the libquartz packed into the plugin jar (under `natives/<os>-<arch>/`).

The result is `plugin/build/libs/QuartzExample-0.1.0.jar`, with Kotlin, the Embed runtime, the bindings and libquartz
inside. The JDK needs to be 25 (Paper 26.3's).

### Running it

Drop the jar into `plugins/` of a Paper 26.3 server and start the server with native access enabled for the bindings:

```console
$ java --enable-native-access=ALL-UNNAMED -jar paper-26.3.jar --nogui
[QuartzExample] Quartz modules [example, org.quartzlang.examples.paper.chat] running 14 commands
> greet Ada
Hello, Ada!
> quartzinfo
Runtime: Quartz, sandboxed, 256 KiB in use
...
```

Without the flag the JDK prints a warning about restricted methods and the plugin still works.

Permissions (all `op` by default): `quartzexample.heal`, `quartzexample.setwarp`, `quartzexample.announce`,
`quartzexample.protected` (break bedrock, end portal frames and spawners), `quartzexample.tnt`, and a kit's own
`permission` from `kits.toml`.

## qlog: a log analyzer in Quartz (`cli-tool/`)

A command line tool written entirely in Quartz and built into **one native executable** with
[Quartz Embed](https://github.com/QuartzProject/Embed)'s `quartz_add_executable`: no JVM, no interpreter to install,
about 3 MB, started in a few milliseconds. It summarizes log files offline: lines per level and per source, the most
frequent messages with their numbers folded into `#`, and the first error.

```console
$ cd samples
$ qlog app.log worker.log billing.log --top 3
app.log: 14 lines, 13 parsed as 'app'
worker.log: 7 lines, 7 parsed as 'logback'
billing.log: 4 lines, 4 parsed as 'pipes'
matched: 24
levels:  ERROR 4, WARN 6, INFO 12, DEBUG 2
sources: net 4, db 4, shop 4
top messages:
      3  slow query took #ms
      3  order # paid
      3  job # done in #ms
first error at 2026-11-19 10:04:44: app.log:6: connection reset by peer after 3 retries
$ qlog --level warn --grep 'slow|failed' --json app.log worker.log
{
  "files": [ ... ],
  "matched": 5,
  ...
}
$ qlog --fail-on error app.log > /dev/null; echo $?
3
```

`qlog --help` lists the options. Exit codes: 0 done, 1 a file or the configuration could not be read, 2 bad usage, 3
`--fail-on` matched, so it can gate a CI job.

### What it shows

| File | |
|---|---|
| [`src/main.qz`](https://github.com/QuartzProject/Examples/blob/main/cli-tool/src/main.qz) | argument parsing (short and long options, `--opt=value`, `-` for standard input), help text, exit codes |
| [`src/formats.qz`](https://github.com/QuartzProject/Examples/blob/main/cli-tool/src/formats.qz) | log formats as regular expressions with named groups; extra ones from `qlog.toml`, decoded with `@derive(Decode)`; format detection per file |
| [`src/report.qz`](https://github.com/QuartzProject/Examples/blob/main/cli-tool/src/report.qz) | counting, ranking and the text and JSON (`@derive(Encode)`) reports |
| [`samples/`](https://github.com/QuartzProject/Examples/blob/main/cli-tool/samples) | three logs in different formats and a [`qlog.toml`](https://github.com/QuartzProject/Examples/blob/main/cli-tool/samples/qlog.toml) that adds the third format |

The program gets the `terminal`, `fs` and `process` kits and nothing else. `fs` is rooted at the current directory, so
qlog reads files under it and cannot reach anything above it; it says so instead of trapping.

### Building

```console
$ cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_C_COMPILER=clang
$ cmake --build build
$ ./build/qlog --version
qlog 0.1.0
```

The build compiles the Quartz sources with `--deny-warnings` and links them with Embed's small C++ host. It takes the
core and Embed from checkouts: `../../Quartz` and `../../Embed` by default (the sibling clones), or
`-DQUARTZ_SOURCE_DIR=<Quartz>` and `-DQUARTZ_EMBED_SOURCE_DIR=<Embed>`.

#### Why native and not the JVM kits

The same sources would build with Embed's Gradle plugin into a jar run by `QuartzEmbed.run`, but a tool like this is
started many times, often in scripts and CI, where a JVM's start-up and a Java installation are the whole cost. The
native path gives one self-contained binary with the same sandbox and the same kits.

## C++ host: a scripted arena (`cpp-host/`)

A terminal arena whose zombies and villagers are driven by a Quartz script, embedded through the C++ interface
(`quartz/Quartz.hpp`). It shows what a game host does with Quartz:

- **Entities as handles.** The script sees `Entity` as an opaque `@handle` with properties (`e.x`, `e.hp`) and methods
  declared in [`scripts/game.qzi`](https://github.com/QuartzProject/Examples/blob/main/cpp-host/scripts/game.qzi); the C++ side owns the entities and checks every handle it gets
  back.
- **A call per entity per tick**, each with its own fuel budget (`--fuel`, 200 000 by default). A script stuck in a loop
  traps with `out of fuel` for that entity, and the arena keeps running.
- **Hot reload keeping state.** The host watches [`scripts/brain.qz`](https://github.com/QuartzProject/Examples/blob/main/cpp-host/scripts/brain.qz). When it changes, the host
  compiles it and calls `Sandbox::reload`: the new version starts with the values of `state Arena` (new fields take their
  defaults). If the edit does not compile, the diagnostics are printed and the old version keeps running.

### Building

```console
$ cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_C_COMPILER=clang
$ cmake --build build
```

The core is built from a Quartz checkout, `../../Quartz` by default (the sibling clone); pass
`-DQUARTZ_SOURCE_DIR=<Quartz>` for another one. Clang with C++23 is required, as for Quartz itself.

### Running

From this directory, so the default script is found:

```console
$ ./build/arena --tick-ms 100
  zombie#4 says: braaains (zombie number 1)
tick 10, player hp 10
+------------------------------------------------+
|     v                                          |
...
```

While it runs, edit `scripts/brain.qz`: change `zombieSpeed`'s default, add a field to `Arena`, or put a `while true`
loop in `wander`. Each save is picked up on the next tick:

```
== brain.qz changed, recompiling
== reloaded, state kept: {"states":{"Arena":{"version":0,"fields":{..., "spawned":4, "caught":0, ...}}}}
!! think for entity 2 trapped, the world goes on: trap: out of fuel in 'wander' at brain.qz:74
```

`--ticks N` stops after N ticks and prints the final state; `--tick-ms 0` runs as fast as it can; `--help` lists the
options.

### How it is put together

| File | |
|---|---|
| [`src/World.cpp`](https://github.com/QuartzProject/Examples/blob/main/cpp-host/src/World.cpp) | the entities and the ASCII view; nothing in it knows about Quartz |
| [`src/Script.cpp`](https://github.com/QuartzProject/Examples/blob/main/cpp-host/src/Script.cpp) | compiling, the host functions bound with `Sandbox::bind`, the calls each tick, the reload |
| [`src/Main.cpp`](https://github.com/QuartzProject/Examples/blob/main/cpp-host/src/Main.cpp) | arguments and the tick loop |

The host functions use the raw binding (`bool (*)(vm::HostCall&, void*)`) with the world as user data, because
`quartz::bind<&fn>` has no handle type and no user pointer yet.

## C host: a fleet steered by a script (`c-host/`)

The C version of the [C++ arena](https://github.com/QuartzProject/Examples/blob/main/c-host/cpp-host), smaller: four ships fly to a beacon, steered each tick by
[`scripts/pilot.qz`](https://github.com/QuartzProject/Examples/blob/main/c-host/scripts/pilot.qz) through the C interface (`quartz/quartz.h`), in one file of plain C17,
[`fleet.c`](https://github.com/QuartzProject/Examples/blob/main/c-host/fleet.c).

- Host functions are bound with `qz_sandbox_bind_direct` and get the fleet as user data.
- `steer` returns a struct, `Thrust { dx, dy }`, read as two slots with `qz_sandbox_call_wide`.
- Each call has a fuel budget; a trap (`qz_sandbox_trap_code` tells `QZ_TRAP_OUT_OF_FUEL` apart) costs that ship one
  step, not the program.
- When `pilot.qz` changes on disk, it is compiled again and swapped in with `qz_sandbox_reload`, which keeps
  `state Fleet`.

### Building and running

```console
$ cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_C_COMPILER=clang
$ cmake --build build
$ ./build/fleet                       # scripts/pilot.qz, scripts/fleet.qzi, 60 ticks
tick  10: (  7.2,   3.6) ( 32.8,   3.6) (  7.2,  16.4) ( 27.9,  14.2)
tick  20: ( 14.3,   7.2) ( 25.7,   7.2) ( 14.3,  12.8) ( 20.9,  10.5)
  ship 3: at the beacon (fleet step 88)
...
-- tick 30: the beacon moves to (5, 5)
...
state: {"states":{"Fleet":{"version":0,"fields":{"steps":240,...}}},"handles":{}}
$ ./build/fleet scripts/pilot.qz scripts/fleet.qzi 600   # longer, to edit the script while it flies
```

The program is C, but `libquartz` is C++, so the executable is linked with the C++ driver. The core comes from
`../../Quartz` by default, or `-DQUARTZ_SOURCE_DIR=<Quartz>`. File times come from POSIX `stat`.
