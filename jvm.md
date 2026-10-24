# Quartz on the JVM

Java and Kotlin bindings for [Quartz](https://quartzlang.org), a statically typed, sandboxed language made to be
embedded. A JVM application compiles or loads Quartz programs and runs them in sandboxes with their own memory quota,
fuel budget and persistent state, and gives them host functions written in Java or Kotlin.

The bindings sit on Quartz's C interface (`quartz.h`) through the Foreign Function and Memory API
(`java.lang.foreign`). There is no JNI code and nothing to compile on the Java side: the jar carries `libquartz`
for each platform it was built with and loads the right one at run time.

## Requirements

- Java 22 or newer, 64-bit (the FFM API is final since 22). Tested with JDK 25.
- `libquartz` for the platform: inside the jar, on `java.library.path`, or named with `-Dquartz.library=<file>`.
- Native access enabled for the bindings, or the JVM prints a warning on first use:
  `--enable-native-access=ALL-UNNAMED` (or `=org.quartzlang.jvm` on the module path). An executable jar can set
  `Enable-Native-Access: ALL-UNNAMED` in its manifest instead.

## Example

```java
import org.quartzlang.jvm.*;

String host = "fn greet(name: str) -> str\n";
String plugin = """
        state Counter {
            total: int
        }
        fn hello(c: Counter, n: int) -> str {
            c.total = c.total + n
            return greet("n{c.total}")
        }
        fn divide(a: int, b: int) -> int {
            return a / b
        }
        """;

try (Program program = Quartz.compile(Source.of("host.qzi", host), Source.of("plugin.qz", plugin));
        Sandbox sandbox = new Sandbox(program, Limits.DEFAULT.withFuel(1_000_000))) {
    sandbox.bind("greet", call -> "hi " + call.stringArg(0));
    sandbox.start();
    String text = sandbox.call("hello", 5).asString();   // "hi n5"
    String saved = sandbox.exportState();                // every state as JSON
    try {
        sandbox.call("divide", 1, 0);
    } catch (TrapException trap) {
        // trap.code() == TrapCode.DIVIDE_BY_ZERO; the sandbox is still usable
    }
}
```

- `Quartz.compile(sources, options)` returns a `Program` or throws `CompileException` with the diagnostics.
  `Program.load(bytes, trustedKeys, requireSignature)` loads a `.qzb` module, checking its hash and signature.
- `Sandbox.call(name or Export, args...)` returns a `Value`. The arguments are checked against the function's
  `Signature` (`Export.signature()`) before anything reaches native code: a wrong count, a `String` where an `int` goes
  or a number that does not fit an `i32` throws `IllegalArgumentException`. Arguments are boxed numbers, `Boolean`,
  `Character`, `String`, `byte[]` (for `Bytes`), or a `Value` the same sandbox just returned.
- A trap throws `TrapException`, whose `code()` says what kind (`DIVIDE_BY_ZERO`, `OUT_OF_FUEL`, `HOST_ERROR`...);
  when a host function threw, the original exception is its cause.
- `Program.imports()` lists what a program imports with its signature (`builtIn()` for the standard library);
  `bind` reads it, so a host function's arguments are read by the declared type (`call.longArg(0)` on a `str`
  parameter throws, `call.listArg(0)` gives a list) and its result is checked the same way. Host functions return a
  boxed number, `Boolean`, `String`, `byte[]`, a `List`, or anything for void. Anything they throw becomes a trap of
  the running call and never reaches native code.
- Tasks: `spawn` starts a `suspend fn` and returns a `TaskOutcome` (`DONE`, `WAIT`, `AT_ENTER`, `AT_LEAVE`, `YIELD`);
  `resume(task, value)` continues it with what its `wait` produces; `cancel(task)` drops it.
- `exportState()` and `importState(json)` move every `state` as JSON. `exportHandle(id)`, `importHandle(id, json)`
  and `dropHandle(id)` do the same for the `@persist(per = Handle)` states of one handle (a player that leaves and
  comes back).
- `reload(program)` replaces the program in place, keeping bindings and limits and migrating every state; when the
  new version cannot take the old state it throws and nothing changes.
- `link(package, provider)` binds a sandbox's imports `package.fn` to another sandbox's exports;
  `Program.packageInterface(manifest)` generates the `.qzi` the client compiles against.
- `setFuelPerCall`, `fuelPerCall`, `fuelLeft`, `memoryUsed` and `liveTasks` read and tune the budget.

### Kotlin

The `quartz-kotlin` module adds a few extensions on top of the Java API (which Kotlin can already call directly,
`sandbox.call("f", 1, "x")` included):

```kotlin
val program = compileQuartz("host.qzi" to "fn shout(text: str) -> str\n", "plugin.qz" to source)
program.use {
    it.withSandbox { sandbox ->
        sandbox.bind("shout") { call -> call.stringArg(0).uppercase() }
        sandbox.start()
        val n: Long = sandbox.callAs("twice", 21)
        val s: String = sandbox.callAs("loud", "hey")
    }
}
```

### Kotlin Multiplatform

`quartz-kmp` has the same API in common Kotlin (`org.quartzlang.kmp`: `Quartz`, `Program`, `Sandbox`, `Value`,
`HostCall`, `TrapException`...), so a library that embeds Quartz can be written once for every target:

```kotlin
Quartz.initialize() // suspends while the WebAssembly runtime loads on js and wasmJs; does nothing elsewhere
val program = compileQuartz("host.qzi" to "fn greet(name: str) -> str\n", "plugin.qz" to source)
program.withSandbox(Limits(fuelPerCall = 1_000_000)) { sandbox ->
    sandbox.bind("greet") { call -> "hi " + call.string(0) }
    sandbox.start()
    val text: String = sandbox.callAs("hello", 5)
    try {
        sandbox.call("divide", 1, 0)
    } catch (trap: TrapException) {
        check(trap.code == TrapCode.DIVIDE_BY_ZERO)
    }
}
```

| Target | Implementation |
|---|---|
| `jvm` | delegates to `quartz-java` (FFM, Java 22+) |
| `linuxX64` | `cinterop` over `quartz.h`, libquartz linked statically into the klib |
| `android` | JNI shim over `quartz.h` in `libquartz_jni.so` (ART has no `java.lang.foreign`), arm64 and x86-64 |
| `js`, `wasmJs` | `quartz-capi.wasm`, Quartz's WebAssembly build of `quartz.h`, as an npm package; Node and browsers |

The Kotlin/Native, JNI and JavaScript targets share one implementation over the C interface (`capiMain`). There a
sandbox is not confined to a thread by the library: keep each one on one thread at a time, and close it, since
nothing frees a forgotten one.

The native target needs a Quartz checkout to build libquartz from: `./gradlew :quartz-kmp:linuxX64Test
-Pquartz.source=/path/to/Quartz`. libquartz is C++23, and Kotlin/Native's own Linux sysroot has GCC 8 and glibc 2.19,
so the build links against the host's glibc and static libstdc++ (`libstdc++-static` on Fedora) through a sysroot of
links in `build/host-sysroot`; the binaries need the host's glibc or newer.

The Android target is configured when `ANDROID_HOME` and an NDK (`-Pquartz.ndk=<dir>` or `ANDROID_NDK_HOME`) are
there. `buildQuartzJni` builds the shim and libquartz together for each ABI (`c++_static`, API 26), and
`connectedAndroidDeviceTest` runs the common tests on a device or emulator:

```sh
ANDROID_HOME=/path/to/sdk ./gradlew :quartz-kmp:connectedAndroidDeviceTest \
    -Pquartz.source=/path/to/Quartz -Pquartz.ndk=/path/to/android-ndk-r30
```

`-Pquartz.androidSource=<dir>` builds the Android library from another Quartz tree than `quartz.source`.

`js` and `wasmJs` are configured with `-Pquartz.wasm=<dir>`, the directory of `quartz-capi.js` and `quartz-capi.wasm`
from Quartz's `wasm` preset (`cmake --preset wasm && cmake --build build/wasm`, in `build/wasm/wasm`). The build turns
them into a local npm package, `quartz-capi`; in a browser bundle it is resolved like any other package. Only the
interpreter runs there.

```sh
./gradlew :quartz-kmp:jsNodeTest :quartz-kmp:wasmJsNodeTest -Pquartz.wasm=/path/to/Quartz/build/wasm/wasm
```

## Diagnostics and warning levels

`Quartz.compile` reports every diagnostic as data. `Program.diagnostics()` holds the warnings of a program that
compiled, and `CompileException.diagnostics()` everything of one that did not (`errors()` keeps only the errors). Each
`Diagnostic` has a `severity()` (`ERROR`, `WARNING`, `NOTE`), the warning `rule()` (`unused-variable`; empty for other
errors), the `file()` as you named it, a range (`line`, `column`, `endLine`, `endColumn`, from 1, columns in UTF-8
bytes, all 0 when there is no place) and the `message()`. `diagnosticsText()` and `text()` give them as the compiler
prints them.

Warning rules can be set per compilation; a later entry wins and `*` is every rule:

```java
CompileOptions options = CompileOptions.DEFAULT
        .denyWarnings()                                     // every warning is an error...
        .withRule("unused-parameter", WarningLevel.IGNORE); // ...except this one
Program program = Quartz.compile(sources, options);
```

`Quartz.warningRules()` lists the rule ids the library knows. An unknown id is reported as an `unknown-rule` warning.

## Introspection

A program describes itself:

- `program.exports()` lists the functions a host may call. Each `Export` has its `name()` with its package
  (`org.example.greet`), `simpleName()`, `packageName()`, `parameterNames()`, `signature()`, `visibility()` (`PUBLIC`
  for `pub`, `PRIVATE`...), `isSuspend()` and `attributes()`. `find(name)` takes the name with or without its package,
  and throws `IllegalArgumentException` when several functions share a short name.
- An `Attribute` is written as in the source: `@command("heal", perm = "x.heal")` has `name()` `command`,
  `positional(0)` `"heal"` and `named("perm")`. Arguments are typed: `asLong()`, `asDouble()`, `asBoolean()` and
  `asString()` (also for names such as `Join`). For `@on(Join, where = event.level > 3)`, `filter()` is the exported
  function that tests the handler's first argument: call it and skip the handler when it returns `false`.
- `program.imports()` gives each `Import` its `packageName()` and `required()`, which is false when no code calls it:
  `start()` does not ask for its binding.
- A `Type` has its `name()` as the source writes it (`Player`, `[int]`, `Map<str, Pt>`), its `packageName()` and
  `qualifiedName()`.

## Converting values, handles included

`Values` converts between what the bindings give and take (a `Value`, `Struct`, `Variant`, `Result`, lists, maps,
boxed scalars) and your classes: records, Kotlin data classes, enums and sealed types, matched by field and variant
name.

```java
Point p = Values.to(value, Point.class);
List<Point> line = Values.to(value, new TypeRef<List<Point>>() {});
Object arg = Values.from(new Event.Leave(player, "bye"), export.signature().params().get(0), handles);
```

`Values.from(object, type)` gives what `Value.get()` would give for a value of that Quartz type, ready to pass to a
call or to return from a host function. Give a `HandleMapper` (two methods: the object behind an id, and the id of an
object) and `@handle` values are mapped wherever they sit: in lists, maps, struct fields, tuples, `Result`s and enum
variants. A `long` or `Long` target keeps the id. `Value.to(target, handles)` and `HostCall.arg(i, target, handles)`
do the same from a result or an argument. In Kotlin: `value.read<Event>(handles)`, `call.argAs<Event>(0, handles)` and
`handleMapper({ id, _ -> ... }, { obj, _ -> ... })`.

In Kotlin Multiplatform, `QuartzValues.from(value, type, handles)` normalizes a value and turns host objects into ids,
and `QuartzValues.resolveHandles(value, type, handles)` turns the ids of a result back into objects. `@Serializable`
classes keep handles as `Long` fields. The common API has the same diagnostics, warning levels, introspection
(`exports`, `attributes`, `Import.required`) and wide task results on every target.

## Task results

When a task finishes, `TaskOutcome.value()` is its whole result, structs and tuples included, read like the result of
`call`.

## Values and lifetimes

A `Value` knows its type: `kind()` is the `Kind` the function declares (`I64`, `F64`, `STR`, `LIST`...). The
accessors check it, so `asString()` on an `int` result throws instead of reading an integer as a pointer.
`asLong`, `asInt`, `asDouble`, `asFloat`, `asBoolean`, `asCodePoint`, `asString` and `asBytes` read scalars and
strings, `get()` boxes whatever it is. Narrow integers are widened by their sign (`u8` 255 reads as 255, `i8` -1 as -1).

Lists cross both ways by their type: a Java `List` is accepted for a list parameter, a list a host function returns
or a list awaitable given to `resume`, and each element is checked against the element type. A list result is read
with `asList()` (nested lists included) or `asLongList()`, `asDoubleList()`, `asBooleanList()`, `asStringList()`,
which check the element type first. A nullable `str`, `Bytes` or list is `null` or the value. A struct or tuple result
comes back as its raw slots, `Value.slots()`.

A `str` or list result lives in the sandbox's arena until the next call into that sandbox (or into any sandbox linked
to it). The accessors copy it out; called after that point they throw `IllegalStateException` instead of reading
freed memory. Strings a host function receives are copied out when read, and are only readable while it runs.

## Threads and native memory

- A `Program` is immutable and can be shared by any number of threads and sandboxes.
- A `Sandbox` is used by one thread at a time. This is enforced: a second thread that calls in while a call runs gets
  `IllegalStateException`, which costs one compare-and-set per call. Linked sandboxes share this rule, since a call into
  one runs code in the others. Separate sandboxes run in parallel.
- A sandbox cannot be re-entered from its own host functions; a host function may call other sandboxes.
- `close()` frees the native object exactly once. A forgotten `Program` or `Sandbox` is freed by a `Cleaner` when it
  becomes unreachable, even when its host functions capture it; that waits for the garbage collector, so close
  sandboxes when done. A provider closed while a client is still linked to it stays alive natively until the client
  is closed.

## Building

```sh
# with a libquartz built elsewhere
./gradlew build -Pquartz.library=/path/to/libquartz.so

# or let Gradle build libquartz for this host from a Quartz checkout (CMake, Ninja and Clang required)
./gradlew :quartz-java:buildNative build -Pquartz.source=/path/to/Quartz
```

Either way the library ends up in the jar under `natives/<os>-<arch>/` (`linux-x86_64/libquartz.so`,
`linux-aarch64/libquartz.so`, `macos-aarch64/libquartz.dylib`, `macos-x86_64/libquartz.dylib`,
`windows-x86_64/quartz.dll`). `buildNative` links the C++ runtime statically on Linux and strips the result
(about 3.5 MB), so the library only needs glibc.

A release jar with every platform is put together in CI: one job per runner (Linux x86-64 and arm64, macOS arm64 and
x86-64, Windows x86-64) runs `buildNative` and uploads `quartz-java/build/native-host/`; a final job downloads them
into one directory and runs `./gradlew build -Pquartz.natives=<that directory>`.

## Performance

`quartz-bench` measures the cost of one call of a trivial exported function and of one host function call from
inside the interpreter, against the same through the C interface from C:

```sh
quartz-bench/run.sh /path/to/Quartz /path/to/libquartz.so [cpu] [runs]
```

15 runs alternating the bindings before the typed C interface and now, both on the same release `libquartz`,
interpreter tier, pinned to one core with `taskset` and `nice`, on a shared Linux x86-64 machine (load average 17 to
22 on 16 threads, so the spread is wide: fastest run and median):

| | C | Java before | Java now |
|---|---|---|---|
| `Sandbox.call` of `fn id(x: int) -> int` | 31 / 36 ns | 45 / 57 ns | 54 / 66 ns |
| one host function call (`hostId(i)` in a loop) | 12 / 13 ns | 34 / 56 ns | 36 / 40 ns |
| the same, bound with `qz_sandbox_bind_direct` | 7 / 9 ns | | |

Calls check every argument against the signature, which costs about 10 ns. Host functions are bound with
`qz_sandbox_bind_direct`: the arguments are read and the result written in place, with no downcall, which takes a
quarter off the median host call. Most of what is left of a Java host call is the FFM upcall itself.

## Limitations

- `Program.imports()` also lists the runtime's own natives, marked `builtIn()`; the sandbox binds those by itself.
- On Windows the extracted DLL cannot be deleted while loaded, so a copy stays in the temporary directory.
- 64-bit platforms only.
