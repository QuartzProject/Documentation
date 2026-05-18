# Embedding Quartz

A host is the application that runs Quartz programs. It decides what a program can call, how much it can spend, and
when it runs. This chapter uses the C++ interface (`quartz/Quartz.hpp`, `quartz/Bind.hpp`); the C interface at the end
covers the same ground for other languages.

## A complete host

```cpp
#include "quartz/Bind.hpp"
#include "quartz/Quartz.hpp"

#include <cstdio>

void logLine(std::string_view text) { std::printf("[plugin] %.*s\n", int(text.size()), text.data()); }
std::int64_t onlinePlayers() { return 12; }

constexpr std::string_view kInterface = R"(fn logLine(text: str)
fn onlinePlayers() -> int
)";

constexpr std::string_view kPlugin = R"(state Stats {
    greetings: int
}

fn welcome(stats: Stats, name: str) -> str {
    stats.greetings += 1
    logLine("welcomed {name}")
    return "Welcome, {name}! {onlinePlayers()} players online, greeting {stats.greetings}"
}
)";

int main() {
    quartz::SourceInput sources[] = {{"host.qzi", std::string(kInterface)}, {"plugin.qz", std::string(kPlugin)}};
    quartz::CompileOutput out = quartz::compile(sources);
    if (!out.program) {
        std::fprintf(stderr, "%s", out.diagnostics.c_str());
        return 1;
    }
    quartz::vm::Limits limits;
    limits.memoryBytes = 16u << 20;
    limits.fuelPerCall = 1'000'000;
    quartz::vm::Sandbox sandbox(out.program, limits);
    quartz::bind<&logLine>(sandbox, "logLine");
    quartz::bind<&onlinePlayers>(sandbox, "onlinePlayers");
    if (auto s = sandbox.start(); !s) {
        std::fprintf(stderr, "%s\n", s.error().describe().c_str());
        return 1;
    }
    quartz::vm::Slot arg{};
    arg.p = sandbox.newStr("Ada");
    auto r = sandbox.call(out.program->findFunction("welcome"), std::span(&arg, 1));
    if (!r) {
        std::fprintf(stderr, "%s\n", r.error().describe().c_str());
    }
}
```

Link it with the `quartz` library target. The program prints
`Welcome, Ada! 12 players online, greeting 1`, and `sandbox.exportState()` then returns
`{"states":{"Stats":{"version":0,"fields":{"greetings":1}}},"handles":{}}`.

## Host interfaces (`.qzi`)

A `.qzi` file declares, without bodies, everything the host offers. A program can call nothing else.

```quartz
package org.example.server

fn broadcast(text: str)

@handle
struct Player {}

impl Player {
    @property
    fn health(self) -> int
    fn setHealth(self, value: int)
    fn send(self, text: str)
}

@handle
@awaitable(int)
struct Delay {}

impl int {
    @property
    fn ticks(self) -> Delay
}
```

- A `@handle` struct is an opaque host object: the program holds a 64-bit value it cannot forge into memory access.
- `@property` methods are read as fields (`p.health`). A matching `setX` method makes the property assignable
  (`p.health = 10`).
- `@awaitable(T)` makes a handle something `wait` accepts; `wait` produces a `T`, any value the host can build: scalars,
  `str`, handles, lists, maps, structs, tuples, enums and nullables. Attribute arguments are expressions, so the type is
  written as one: `@awaitable([str])`, `@awaitable((int, str)?)`, `@awaitable(Map::<str, int>)`.
- Methods are bound by their full name: `Player.health`, `int.ticks`.

## Limits

| `vm::Limits` field | Default | What happens when it runs out |
|---|---|---|
| `memoryBytes` | 64 MiB | trap `out of memory` |
| `fuelPerCall` | 100 000 000 | a call traps `out of fuel`; a task yields and resumes later |
| `maxDepth` | 4096 | trap on deep recursion |
| `tier` | default | interpreter, automatic tiering or native from the start |

A trap aborts only the current call or task. The sandbox stays usable, and nothing a program does can crash the host.
`setFuelPerCall` changes the budget at any time, for example to follow a wall-clock budget per tick.

## Binding functions

`quartz::bind<&fn>(sandbox, "name")` converts arguments and results from their C++ types (`std::int64_t` is `int`,
`double` is `float`, `std::string_view` and `std::string` are `str`, `bool`, `char32_t`, the fixed-width integers and
`float`) and checks the function against the interface. A mismatch is an error naming both signatures. A first
parameter `quartz::vm::HostCall&` gives access to the call: `call.charge(units)` charges fuel for native work,
`call.error = "why"` with a `false` result traps, `call.string(text)` builds a string.

`sandbox.bind("name", fn, user)` binds a raw `bool (*)(vm::HostCall&, void*)`, for handles and anything the typed form
does not cover. Every import must be bound before `start()`.

### Capabilities of the standard library

Two standard functions stand for capabilities only the host can grant, and come bound to a safe default: binding the
same name again replaces it.

| Import | Default | Arguments, in slots |
|---|---|---|
| `org.quartzlang.log.emit(level: int, logger: str, message: str, fields: [str])` | drops the record | level 0 (trace) to 4 (error); `fields` alternates key and value |
| `org.quartzlang.http.send(request: Request) -> Result<Response, str>` | `Err("http: this host does not grant network access")` | the fields of `Request` in order: url, method, headers (`[(str, str)]`), body (`Bytes?`, null pointer when absent), timeoutMillis; the result goes to `call.out`: tag 0 and status, headers list, body, or tag 1 and the message |

```cpp
bool logToServer(quartz::vm::HostCall& call, void*) {
    auto text = [](const quartz::vm::Slot& s) { return static_cast<const quartz::vm::Str*>(s.p)->view(); };
    myLogger(call.args[0].i, text(call.args[1]), text(call.args[2]));
    return true;
}

sandbox.bind("org.quartzlang.log.emit", logToServer);
```

A server should not block its tick on HTTP: run the plugin call that sends on a worker, or answer `send` from a cache
and let a task poll. Unused capabilities cost nothing, since the compiler drops the standard functions a program does
not reach.

## Tasks

`suspend fn` calls run as tasks:

```cpp
auto t = sandbox.spawn(fn, args);           // runs until it finishes, waits or spends its fuel slice
while (t && t->kind != quartz::vm::TaskOutcome::Kind::Done) {
    // Wait: t->value is the awaited handle; resume when it is ready, with what `wait` produces
    t = sandbox.resume(t->task, value);
}
```

A host usually keeps waiting tasks in its scheduler and resumes them later; `cancel` frees one. `sandbox.waitType(task)`
is the type the `wait` produces: build a list with `hostList` and `hostListPush`, a map with `hostMap` and `hostMapSet`,
and pass a struct, tuple, enum or nullable as its slots to `resume(task, std::span<const Slot>)`. The value is copied
into the task, so the host's copy only has to live until `resume` returns. `hostMapEntry` (in insertion order) and
`hostMapGet` read maps a program returns.

## Persistence and reload

- `exportState()` and `importState(json)` save and restore every `state`, with field names and versions.
- `reload(newProgram)` builds a sandbox for a new version of the program with the same bindings and limits and the state
  migrated; on failure the old sandbox keeps running.
- `@persist(per = Player)` states have one instance per handle: `exportHandle`, `importHandle` and `dropHandle` save
  them when a player leaves and load them when one joins.

## Packages that call each other

A package lists its exported functions in `package.toml`; `quartz interface package.qzb` generates the `.qzi` that
other packages compile against, including the structs and enums its functions use. At run time,
`client.link("org.example.economy", provider)` binds the client's imports to the provider's sandbox. Values (lists, maps,
structs, tuples and enums included) are copied both ways, never shared, and each side spends its own fuel and memory.

`quartz::loadPackage(bytes, policy)` loads a `.qzb` only if it is signed by the key the host trusts for that package
name.

## The C interface

`include/quartz/quartz.h` exposes the same model with opaque types and status codes, for any language with a C FFI.
Build `libquartz` with `-DQUARTZ_SHARED=ON`; it exports only `qz_*` symbols.

```c
qz_program* program = qz_compile(sources, 2, NULL, &diagnostics);
qz_sandbox* sandbox = qz_sandbox_new(program, NULL);
qz_sandbox_bind(sandbox, "logLine", log_line, NULL);
qz_sandbox_start(sandbox);
qz_slot arg = qz_sandbox_str(sandbox, "Ada", 3);
if (qz_sandbox_call(sandbox, qz_program_function(program, "welcome"), &arg, 1, &result) == QZ_TRAP) {
    fprintf(stderr, "%s\n", qz_sandbox_error(sandbox));
}
```

Host functions receive a `qz_call*`: `qz_call_args`, `qz_call_set_result`, `qz_call_str`, `qz_call_charge` and
`qz_call_fail`. Memory the library returns is freed with `qz_free`. Lists are built with `qz_sandbox_list` and
`qz_list_push`, maps with `qz_sandbox_map` and `qz_map_set` and read with `qz_map_length`, `qz_map_entry` and
`qz_map_get`; `qz_sandbox_resume_wide` answers a `wait` that produces a value wider than one slot.

## Threads

A compiled program is immutable and can be shared by any number of sandboxes on any threads. Each sandbox must be used
by one thread at a time. Compiling is thread-safe too.

## The native tier

With `libquartz_compiler` next to the host (built with `-DQUARTZ_COMPILER=ON`), functions that do enough work are
compiled with LLVM in the background and switched over transparently, tasks included. Results are bit-identical to the
interpreter. `QUARTZ_TIER=interp|auto|native` and `vm::Limits::tier` choose the policy, and
`vm::Limits::nativeCacheDir` (or `QUARTZ_NATIVE_CACHE`) keeps compiled code on disk between runs.
