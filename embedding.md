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
`{"format":2,"states":{"Stats":{"version":0,"fields":{"greetings":1}}},"handles":{}}`.

`out.diagnostics` is the rendered text of the errors and warnings; `out.messages` has each one with its severity,
[rule](tools.md#warnings), file and range, for a host that shows them its own way. `CompileOptions::rules` sets the
level of each warning rule as `--rule` does: with `{{"*", quartz::RuleLevel::Error}}`, any warning fails the
compilation.

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
That includes values nested a million levels deep: copying them into the `state`, between tasks or into a linked
package, and exporting or importing the state, walk them without the native stack, and what the walk needs counts
against `memoryBytes` (a value too deep for what is left traps with "value nested too deeply for the memory limit").
`setFuelPerCall` changes the budget at any time, for example to follow a wall-clock budget per tick.

### Traps and `state`

A trap does not roll back the `state`: what the call wrote before it stays, and the next call sees it. The memory is
always sound and the result is the same in both tiers, but the data may be halfway through what the program meant to
do. Undoing writes inside the VM would cost every write on the hot path, and a task that already waited has nothing to
go back to, since other calls saw what it wrote before the `wait`. What to do instead:

- When a call must be all or nothing, save the state first and load it back if the call traps. On a large state,
  exporting and importing take milliseconds, far more than a typical call, so keep this for the calls that matter:

  ```cpp
  auto saved = sandbox.exportState();
  auto r = sandbox.call(fn, args);
  if (!r && saved) {
      sandbox.importState(*saved);
  }
  ```

- A program that keeps trapping can be disabled, or replaced with `reload` once it is fixed.
- Program authors make the problem go away: compute in locals and write the `state` at the end of the call, so a trap
  in the middle leaves it untouched.

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

When a task finishes, `t->value` is the first slot of its result. A result wider than one slot (a struct, tuple,
`Result` or nullable) is read whole with `taskResult(task)`, right after the `spawn` or `resume` that finished it and
before the next call on the sandbox:

```cpp
if (t && t->kind == quartz::vm::TaskOutcome::Kind::Done) {
    auto loot = sandbox.taskResult(t->task);    // struct Loot { gold: int, item: str }: two slots
    std::int64_t gold = loot[0].i;
}
```

## Persistence and reload

- `exportState()` and `importState(json)` save and restore every `state`, with field names and versions. The
  document says `"format":2`, in which a recursive enum payload is written as the value it holds; documents without a
  format, or with `"format":1`, where such a payload was a list of one element, still load.
- `reload(newProgram)` builds a sandbox for a new version of the program with the same bindings and limits and the state
  migrated; on failure the old sandbox keeps running.
- `@persist(per = Player)` states have one instance per handle: `exportHandle`, `importHandle` and `dropHandle` save
  them when a player leaves and load them when one joins.

## Packages that call each other

A package lists its exported functions in `package.toml`; `quartz interface package.qzb` generates the `.qzi` that
other packages compile against, including the structs and enums its functions use. At run time,
`client.link("org.example.economy", provider)` binds the client's imports to the provider's sandbox. Values (lists, maps,
structs, tuples and enums included) are copied both ways, never shared, and each side spends its own fuel and memory.

The interface is what a caller reads, so it keeps the parameter names, the `///` comments of functions, types, fields
and variants, and the defaults that are literals (numbers, `bool`, `char`, strings without interpolation, `null`,
variants without payload, and lists and tuples of them). A default that names a constant or calls something is left
out, and callers must pass that argument. The `state` parameters are the provider's own and do not appear. With
`exports = ["deposit", "balance"]`, this provider:

```quartz
package org.example.economy

const Welcome = 5

/// What a deposit did.
pub struct Receipt {
    /// The balance after the deposit.
    total: int
    note: str?
}

state Bank {
    accounts: Map<str, int>
}

/// Adds `amount` to the account of `who`.
pub fn deposit(bank: Bank, who: str, amount: int = 10, bonus: int = Welcome) -> Receipt {
    let total = (bank.accounts.get(who) ?? 0) + amount + bonus
    bank.accounts[who] = total
    return Receipt(total)
}

pub fn balance(bank: Bank, who: str) -> int {
    return bank.accounts.get(who) ?? 0
}
```

gives this interface:

```quartz
package org.example.economy

/// What a deposit did.
struct Receipt {
    /// The balance after the deposit.
    total: int
    note: str? = null
}

/// Adds `amount` to the account of `who`.
fn deposit(who: str, amount: int = 10, bonus: int) -> Receipt

fn balance(who: str) -> int
```

The comments travel in the module, so an interface generated from a `.qzb` has them too; `qz_program_interface` and
`quartz::interfaceOf` give the same text to a host.

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
`qz_map_get`; `qz_sandbox_resume_wide` answers a `wait` that produces a value wider than one slot, and
`qz_sandbox_task_result` reads the whole result of a task that just finished.

`qz_compile_with` takes warning levels as `qz_rule_level` entries (`{"unused-variable", QZ_LEVEL_ERROR}`, or `"*"`)
and returns the diagnostics one by one: `qz_diagnostics_count`, then `qz_diagnostic_severity`, `qz_diagnostic_rule`,
`qz_diagnostic_file`, `qz_diagnostic_message` and `qz_diagnostic_range` for each, and `qz_diagnostics_free` at the
end. `qz_warning_rule_count` and `qz_warning_rule` list the rules the library knows.

### API level 5

`qz_api_level()` says which functions the library has (`QZ_API_LEVEL` in the header it was built from); a host that
needs the ones below checks for 5 before looking them up.

**Text from outside.** Process output, HTTP headers and file names are not always UTF-8, and `qz_sandbox_str` and
`qz_call_str` refuse such text. `qz_sandbox_str_lossy` and `qz_call_str_lossy` turn each ill-formed sequence into
U+FFFD, one per maximal subpart as JavaScript, Python and Rust decode, so they never fail for the content: the bytes
`caf\xC3\xA9 \xFF\xE2\x82 ok` become `café �� ok`. Valid text costs the same as with the strict functions. The
`_into` forms (`qz_sandbox_str_lossy_into`, `qz_call_str_lossy_into`) write the slot through a pointer, for FFIs that
cannot take a returned `qz_slot`.

```c
static bool read_line(qz_call* call, void* user) {
    char line[512];
    if (fgets(line, sizeof line, (FILE*)user) == NULL) {
        line[0] = '\0';
    }
    qz_call_set_result(call, qz_call_str_lossy(call, line, strlen(line)));
    return true;
}
```

**Compression.** `qz_deflate`, `qz_inflate` and `qz_crc32` are the code behind `org.quartzlang.compress`, so a host
that reads and writes archives does not need a zlib of its own. `qz_framing` picks raw DEFLATE (RFC 1951), zlib
(RFC 1950) or gzip (RFC 1952). `qz_deflate` takes a level from 0 (store) to 9 and returns `NULL` only without memory;
`qz_inflate` stops at `max_length` bytes of output and returns `NULL` with a message on a bad header, damaged data, a
checksum mismatch or more output than allowed. `qz_crc32` is the CRC-32 of zip and gzip, and continues over more data
when given the previous result. Buffers and messages are freed with `qz_free`.

```c
size_t packed_length = 0;
uint8_t* packed = qz_deflate(data, length, 6, QZ_FRAMING_GZIP, &packed_length);
size_t plain_length = 0;
char* error = NULL;
uint8_t* plain = qz_inflate(packed, packed_length, QZ_FRAMING_GZIP, 16 << 20, &plain_length, &error);
if (plain == NULL) {
    fprintf(stderr, "%s\n", error);
    qz_free(error);
}
uint32_t crc = qz_crc32(0, data, half);
crc = qz_crc32(crc, data + half, length - half);   /* the same as qz_crc32(0, data, length) */
qz_free(packed);
qz_free(plain);
```

**Documentation.** `qz_program_function_doc(program, function)`, `qz_type_doc(program, type)` and
`qz_type_member_doc(program, type, index)` (a field of a struct or a variant of an enum) give the `///` text the
generated interfaces carry, or `""` when there is none. The strings live as long as the program. A host that builds
facades or help pages from a program shows them without parsing its sources.

**Recursive payloads.** A payload of a recursive enum (`Link(int, Chain)`, `Add(Expr, Expr)`) is stored as a list of
one element, the value itself. `qz_type_variant_boxed(program, type, variant, index)` is true for such a payload; its
type from `qz_type_variant_payload` is then that list, and `qz_type_elem` of it is the value's type. Read the value
with `qz_list_get(slot, 0, ...)`, build it with `qz_sandbox_list` and one `qz_list_push`, and show it to users as the
value, not as a list: the bindings and `exportState` do the same.

## Threads

A compiled program is immutable and can be shared by any number of sandboxes on any threads. Each sandbox must be used
by one thread at a time. Compiling is thread-safe too.

## The native tier

With `libquartz_compiler` next to the host (built with `-DQUARTZ_COMPILER=ON`), functions that do enough work are
compiled with LLVM in the background and switched over transparently, tasks included. Results are bit-identical to the
interpreter. `QUARTZ_TIER=interp|auto|native` and `vm::Limits::tier` choose the policy, and
`vm::Limits::nativeCacheDir` (or `QUARTZ_NATIVE_CACHE`) keeps compiled code on disk between runs.
