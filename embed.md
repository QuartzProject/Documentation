# Embed

Quartz Embed makes Quartz a source language of a Gradle or CMake project. Quartz sources compile with the build, are
type-checked against the API your host offers them, and end up as validated modules inside your jar or your
executable. The host calls them through generated, typed code, and grants each module only the capabilities ("kits")
its code uses.

## Gradle

### Applying the plugin

Embed is not on the Gradle Plugin Portal yet. Include a checkout of the Embed repository in `settings.gradle.kts`:

```kotlin
pluginManagement {
    includeBuild("../Embed")
}
includeBuild("../Embed")
```

and apply the plugin next to Kotlin or Java:

```kotlin
plugins {
    kotlin("jvm") version "2.4.21"
    id("org.quartzlang.embed")
}
```

The plugin adds `org.quartzlang:embed-runtime` to `implementation`. It needs a JDK 22 or newer for the compiler, which
it takes from the Java toolchain (25 by default). Pass `-Pquartz.library=<libquartz>` to build against a libquartz of
your own instead of the one inside the bindings jar.

### Sources and modules

Every source set gets a Quartz directory: `src/main/quartz`, `src/test/quartz` and so on. Each directory holding a
`package.toml` is a module whose id is the manifest's `name`; the files outside any such directory form the default
module, named after the project (`quartz.moduleName` changes it, and other source sets add `-<sourceSet>`). A module
compiles as a whole, and a change recompiles only the modules it touches. Modules land in the jar under
`META-INF/quartz/modules/<id>.qzb`, with their metadata next to them.

### Tasks

| Task | What it does |
|---|---|
| `generateQuartzHostInterface` | Scans the classes for `@QuartzFunction` and `@QuartzHandle` and writes the host `.qzi` |
| `compileQuartz` | Compiles each module against the host interface, the kits and your own `.qzi` files; cacheable and incremental per module |
| `compileQuartzFacade` | Compiles the typed Java facades, when they cannot be sources of the source set itself |

### Settings

```kotlin
quartz {
    warnings = QuartzSeverity.WARN                    // every warning rule: IGNORE, WARN or ERROR
    rule("unused-parameter", QuartzSeverity.IGNORE)   // one rule, applied after `warnings`
    kits("fs", "terminal")                            // compile against these kits only; all by default
    hostPackage = "org.example.host"                  // package of the generated host interface
    handle("Player", "org.bukkit.entity.Player")      // a class you cannot annotate, as a handle
    hostSources.from(project(":api").file("src/main/kotlin"))  // where documentation is read from
    facadePackage = "org.example.quartz"
    scanOwnClasses = true
    keepLines = true
}
```

| Setting | Default | Meaning |
|---|---|---|
| `warnings` | `WARN` | Level of every warning rule |
| `rules` / `rule(name, level)` | none | Level of single rules (`unused-variable`, `discarded-result`, `unreachable-code`...) |
| `kits` | all | Kits whose interfaces modules compile against |
| `hostPackage` | empty | Package of the generated interface; empty puts functions at the top level |
| `handles` / `handle(name, class)` | none | Classes used as handles without `@QuartzHandle` |
| `hostSources` | the source set's Java and Kotlin directories | Sources whose KDoc and Javadoc the interface copies |
| `scanOwnClasses` | `true` | Scan the source set's own classes, not only its classpath |
| `generateFacade` | `true` | Generate a Java facade per module |
| `facadePackage` | `<group>.quartz` | Package of the facades |
| `moduleName` | project name | Id of the default module |
| `keepLines` | `true` | Keep source lines for trap messages |
| `compilerLauncher` | Java 25 toolchain | JVM that runs the compiler (22 or newer) |

A broken source fails the build at its place, the way IDEs link:

```text
src/main/quartz/greeter.qz:2:16: error: cannot multiply 'int' by 'str'
    return x * "two"
               ^
```

Every warning carries its rule, `[unused-variable]`, which is the name `rule(...)` takes. A warning raised to `ERROR`
fails the build like an error.

## The typed boundary

### From Quartz to the host

Annotate the methods Quartz may call. The build reads the compiled classes (Java or Kotlin, without loading them) and
generates the host interface your Quartz sources are checked against.

```kotlin
@QuartzHandle
class Player(val name: String) {
    @QuartzFunction(property = true)
    fun name(): String = name                // `player.name` in Quartz
}

object Server {
    @QuartzFunction
    fun broadcast(message: String) { ... }   // `broadcast("hi")`
}

@QuartzFunction
fun shout(text: String): String = text.uppercase()
```

- A static method, a Kotlin top-level function or a member of a Kotlin `object` is a free function, imported as
  `<hostPackage>.<name>`.
- An instance method of a `@QuartzHandle` class is a method of that handle.
- A Kotlin extension function on a handle class is a method of that handle too, and so is a static method marked
  `@QuartzFunction(method = true)` whose first parameter is a handle. This is how classes you cannot annotate get
  methods: declare them as handles with `handle("Player", "org.bukkit.entity.Player")` and write extensions.
- Any other instance method is called on the object given to `QuartzEmbed.Builder.host(...)`.
- `@QuartzFunction(name = "...")` renames it; `@QuartzFunction(property = true)` makes a handle method without
  parameters a property.
- KDoc and Javadoc become `///` comments in the generated interface, so editors show them.

Types cross like this:

| Java or Kotlin | Quartz |
|---|---|
| `boolean`, `byte`, `short`, `int`, `long` | `bool`, `i8`, `i16`, `i32`, `int` |
| `float`, `double`, `char` | `f32`, `float`, `char` |
| `String`, `byte[]` | `str`, `Bytes` |
| `List<T>`, `Collection<T>`, `Iterable<T>` | `[T]` |
| `Map<K, V>` | `Map<K, V>` |
| a nullable type (`String?`, `Int?`, `@Nullable`) | `T?` |
| a `@QuartzHandle` class or a declared handle | that handle |
| a record or Kotlin data class | a struct with its components |
| an enum | an enum |
| a sealed type whose subclasses are records, data classes or objects | an enum with one variant per subclass |
| `org.quartzlang.jvm.Result<T, E>` | `Result<T, E>` |

A record or data class used by no function (an event the host passes in by itself) is declared with `@QuartzType`. A
type that cannot cross fails the build with the class, the method and the parameter.

### From the host to Quartz: facades

Each module gets a Java class, `<Module>Quartz`, with a method per `pub fn`, read from the compiled program:

```quartz
pub fn visit(visits: Visits, player: Player) -> int     // a state parameter
pub fn spot(world: str, owner: Player?) -> Spot          // a Quartz struct
pub suspend fn later(n: int) -> int                      // a task
```

become

```java
long visit(Player player)                // states are supplied by the sandbox
GreeterQuartz.Spot spot(String world, Player owner)
TaskOutcome later(long n)
```

Quartz structs become records nested in the facade, enums become Java enums (or sealed interfaces of records when
variants carry values), `Result` becomes the bindings' `Result`, and the structs and enums of the host interface come
back as the host's own classes. Use the facade from Kotlin or Java:

```kotlin
GreeterQuartz.open(embed).use { greeter ->
    val spot = greeter.spot("world", player)
}
```

When `scanOwnClasses` is on (the default), the facade compiles after the source set, so tests and other projects call
it; when the host API lives in another project, turn it off and the facade becomes a source of the source set.

## The runtime API

```kotlin
val embed = QuartzEmbed.builder()
    .classLoader(javaClass.classLoader)
    .grant(Kits.terminal(), Kits.fileSystem(dataFolder.toPath()))
    .host(PluginHost(this))
    .limits(EmbedLimits.PLUGIN)
    .build()
val module = embed.module("example")
```

- `QuartzEmbed.modules()` lists the modules on the classpath; `module(id)` starts a sandbox with the kits it needs and
  its host methods bound, and refuses to start when the application did not grant a kit the module calls.
- `QuartzModule.invoke(name, args...)` calls a function by name (with or without its package); host objects pass as
  handles and come back as themselves. `invokeAs(type, name, args...)` converts the result to a class or to a generic
  type (`TypeRef`). `spawn` and `resume` drive `suspend fn` tasks.
- `QuartzModule.sandbox()` gives the sandbox: `exportState()` and `importState()` keep `state` across restarts.
- `QuartzModule.handles().release(obj)` forgets an object Quartz held.
- A trap throws `QuartzScriptException` (with the trap code and the Quartz trace; a host exception is its cause). A
  module that cannot start throws `EmbedException`.
- `EmbedLimits.PLUGIN` (32 MiB, 10 million fuel per call) suits a plugin; `EmbedLimits.CLI` a tool.
- A module is used by one thread at a time; give an asynchronous event its own module or a lock.

### Commands and listeners from attributes

Functions marked with attributes are listed at run time, so a host registers them without a registration function in
the script:

```quartz
@command("heal", description = "Heals a player", permission = "example.heal", suggest = suggestPlayers)
fn heal(sender: Sender, args: [str]) { ... }

@on(BlockPlace, where = event.block == "tnt")
fn guardTnt(event: BlockEvent) -> bool { ... }
```

```kotlin
for (f in module.functions("command")) {
    val name = f.attribute().value()                       // "heal"
    val permission = f.attribute().get("permission", "")
    register(name) { sender, args -> module.invoke(f.function(), sender, args) }
}
for (h in module.functions("on")) {
    if (h.attribute().value() == "BlockPlace" && module.accepts(h, event)) module.invoke(h.function(), event)
}
```

`f.parameters()` names what a caller passes (states excluded), `attribute().named(key)` and `positional(i)` read the
arguments with their kind, and `accepts(handler, event)` evaluates the `where` filter. Which events exist and what
handlers take is the host's contract; the Paper plugin in [Examples](examples.md) is a complete one.

## Kits

A kit is a capability: a host interface in Quartz and its implementation on the JVM (`Kits.*`) and in C++. Modules
compile against every kit the build lists and ask the application only for the ones their code calls.

| Kit | Package | What it gives | JVM | Native |
|---|---|---|---|---|
| `fs` | `org.quartzlang.embed.fs` | files inside the granted paths | `Kits.fileSystem(root)` | yes |
| `terminal` | `org.quartzlang.embed.terminal` | standard output, error and input | `Kits.terminal()` | yes |
| `process` | `org.quartzlang.embed.process` | arguments, environment, exit, other programs | `Kits.process(args)` | POSIX |
| `http` | `org.quartzlang.http` (`send`) | HTTP requests | `Kits.http()` | through `curl` |
| `archives` | `org.quartzlang.embed.archives` | zip, jar, tar, tar.gz | `Kits.archives(root)` | yes |

File operations return `Result`, so a missing file or a path outside the granted ones is a value to handle, not a
trap:

```quartz
match fs.readText(name) {
    Ok(text) => println(text)
    Err(why) => eprintln(why)
}
```

Paths use `/`. Relative paths start at the first granted directory; absolute ones must lie inside a granted path, and
neither `..` nor a symbolic link can leave them. A command line tool may grant exactly the paths its user named:
`Kits.fileSystem(Path.of("."), Kits.argumentPaths(*args))` on the JVM, `GRANT_ARGUMENT_PATHS` in CMake.

`http` binds the library's `send(Request) -> Result<Response, str>`, which fails without the kit; network failures are
`Err` values.

## Shading a plugin

A Paper or other JVM plugin ships Embed, the bindings and libquartz in one jar:

```kotlin
plugins {
    kotlin("jvm")
    id("com.gradleup.shadow")
    id("org.quartzlang.embed")
}
tasks.shadowJar {
    archiveClassifier = ""
    filesMatching("META-INF/*.kotlin_module") { duplicatesStrategy = DuplicatesStrategy.INCLUDE }
}
tasks.build { dependsOn(tasks.shadowJar) }
```

Pass the class loader of the plugin to `QuartzEmbed.builder().classLoader(...)`. Relocation is not needed: each plugin
has its own class loader and extracts its own copy of the library. Start the server with
`--enable-native-access=ALL-UNNAMED` (Java 22 or newer; without it, Java 25 only warns).

## CMake

```cmake
list(APPEND CMAKE_MODULE_PATH "<Embed>/cmake")
include(QuartzEmbed)

quartz_add_sources(host NAME scores SOURCES scores.qz INTERFACES host.qzi RULES unused-variable=error)
quartz_add_executable(qwc SOURCES wc.qz GRANT_ARGUMENT_PATHS)
```

Quartz comes from existing `Quartz::quartz_c` and `Quartz::quartz-cli` targets, from a checkout added with
`-DQUARTZ_SOURCE_DIR=<Quartz>`, or from an installed tree (`cmake --install`) found by `find_package(Quartz)` through
`CMAKE_PREFIX_PATH`.

- `quartz_add_sources(<target> NAME <module> SOURCES ... [INTERFACES ...] [KITS ...] [RULES rule=level...]
  [DENY_WARNINGS])` compiles a module at build time and links it into the target as
  `extern "C" const uint8_t quartz_module_<module>[]` and `..._size`. Load it with `qz_load` and bind your host
  functions with `qz_sandbox_bind_direct` (C) or `quartz::bind` (C++).
- `quartz_add_executable(<name> SOURCES ... [INTERFACES ...] [KITS ...] [ENTRY fn] [RULES ...] [DENY_WARNINGS]
  [GRANT_ARGUMENT_PATHS])` builds a standalone executable.

Sources are recorded under their path relative to the project, so traces and modules carry no machine paths. `KITS`
defaults to every kit.

## Native executables

`quartz_add_executable` links the module with the native host: the C++ kits and a runner. The runner loads and
validates the embedded module, binds the kits it imports (the working directory as the `fs` root, the command line as
`process.args()`, plus the paths named on it with `GRANT_ARGUMENT_PATHS`), runs `main` (or `ENTRY`) and exits with its
`int` result, the code given to `process.exit`, 1 after a trap or 2 when the module cannot run. It runs with 1 GiB and
fuel that does not run out in practice. The result is one binary of about 3 MB on Linux x86-64 that needs only libc
and libstdc++.
