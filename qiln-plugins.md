# Writing a Qiln plugin

A build plugin adds its own vocabulary to `build.qz` and its own tasks to `qiln`. It is an ordinary Quartz package
of kind `Kind.BuildPlugin`, published to a repository like any other, and its tasks run in a sandbox of their own.
This chapter builds one step by step, using the `bundle` plugin from
[`Qiln/examples/bundle`](https://github.com/QuartzProject/Qiln/tree/main/examples/bundle) as the running example. The
build scripts that apply plugins are described in [Qiln](qiln.md).

## Two halves

A build plugin has two source directories, and they run in different places:

```
bundle/
  build.qz          p.kind = Kind.BuildPlugin
  api/bundle.qz     the extension: compiled into every build.qz that applies the plugin
  src/tasks.qz      the task actions: compiled apart, run in the plugin's own sandbox
  test/tasks_test.qz
```

| | `api/` | `src/` |
|---|---|---|
| Compiled with | the `build.qz` that applies the plugin, against `qiln.qzi` | the plugin's other sources, against `task.qzi` |
| Runs | while the workspace is configured, in the script's sandbox | when one of its tasks runs, in a fresh sandbox per task |
| Sees | the `Project` handle and the rest of the build API | a `TaskContext`: the project's files, its build directory, its options |
| Budget | the script's (20 million fuel, 16 MiB) | 2 000 million fuel, 256 MiB |
| Purpose | types, defaults and functions for the user; registering tasks | the work: reading, checking, generating, packing |

The split is Gradle's: an extension is configuration, a task action is plugin code. The `api/` half can do nothing
a build script cannot, because it runs in the same sandbox with the same build API. The `src/` half never sees the
build script and gets only what `TaskContext` offers.

`qiln init --kind build-plugin` creates this layout with a `hello` task that writes a file into the build directory.

## The `api/` half

`api/` declares a package of its own (the plugin's package name) and imports `org.quartzlang.qiln.*`. It usually
offers a struct with default values and a function that takes the `Project`:

```quartz
package org.example.bundle

import org.quartzlang.qiln.*

/// How `qiln bundle` packages a host plugin.
pub struct Bundle {
    manifest: str = "plugin.toml"
    extension: str = "bundle"
    level: int = 9
}

/// Adds a `bundle` task: validates the manifest, then zips it with the compiled module.
pub fn bundle(p: Project, b: Bundle = Bundle()) {
    p.applyPlugin("org.example.bundle")
    let t = p.task("bundle")
    t.description = "Validates {b.manifest} and packs it with the module into build/distributions"
    t.group = "distribution"
    t.dependsOn("build")
    t.action("org.example.bundle", "bundle")
    t.option("manifest", b.manifest)
    t.option("extension", b.extension)
    t.option("level", "{b.level}")
}
```

- `p.applyPlugin(name)` records that the plugin configures this project. It fails unless `settings.qz` requested the
  plugin, so a project cannot use a plugin the workspace did not ask for. `p.hasPlugin(name)` lets one plugin react
  to another.
- `p.task(name)` creates the task (or returns it, if a script or another plugin created it first).
- `t.action(plugin, function)` names the exported function of `src/` that does the work. A built-in task (`check`,
  `test`, `build`, `run`, `publish`, `clean`) cannot take an action: give the plugin's task its own name and make it
  depend on the built-in one.
- `t.option(key, value)` passes settings to the action as text. The action reads them with `t.option(key)`, which
  falls back to the project's options (`p.option(key, value)`), so a plugin can also read settings a script set once
  for the whole project.

A user applies it with one call in `build.qz`, overriding only what differs from the defaults:

```quartz
import org.quartzlang.qiln.*
import org.example.bundle.{bundle, Bundle}

fn build(p: Project) {
    p.group = "org.example.shop"
    p.version = "1.0.0"
    p.kind = Kind.Plugin
    bundle(p, Bundle(manifest = "plugin.toml"))
}
```

Because the API is Quartz compiled into the script, the language server type checks every use, completes the fields
of `Bundle` and shows the `///` comments on hover: every configuration writes the API of each requested plugin to
`.qiln/api/plugins/<name>/` at the workspace root, and `quartz-lsp` compiles `build.qz` against it (see
[Editors](qiln.md#editors)).

## The `src/` half

Task actions live in a package of their own, usually the plugin's name plus `.tasks`, and import
`org.quartzlang.qiln.task.*`. Each action is a public function with exactly this shape:

```quartz
pub fn bundle(t: TaskContext) -> Result<(), str>
```

`Ok(())` means the task succeeded; what it has to say goes through `log`, which `qiln` prints under the task. `Err`
fails the task (and the build) with its message. A trap (a `panic`, running out of fuel, an index out of range) fails
it too, with the trace. The older shape `-> Result<str, str>`, whose `Ok` carried a summary line, still runs but
prints a deprecation warning each time the action runs.

### `task.qzi`

`TaskContext` is a handle to the task being run. It is the whole interface a plugin's tasks have to the outside:

| Member | |
|---|---|
| `t.name`, `t.projectPath`, `t.projectName`, `t.projectVersion`, `t.packageName` | who is running: the task and its project |
| `t.artifact` | where `build` wrote the project's artifact, relative to the build directory (`libs/greeter-1.0.0.qzb`) |
| `t.option(key) -> str?` | the task's option, else the project's option of that name |
| `t.sources() -> [str]` | the project's main source files, relative to the project directory |
| `t.exists(path)`, `t.readText(path) -> str?`, `t.readBytes(path) -> Bytes?` | read a file of the project |
| `t.readBuild(path) -> Bytes?` | read a file under the project's `build/` directory |
| `t.writeBuild(path, data) -> bool`, `t.writeBuildText(path, text) -> bool` | write a file under `build/`, creating directories |
| `log(message)` | print a line under the task, prefixed with its name |

### Capabilities

A task's sandbox has no other host functions: no network, no processes, no clock, no access to other projects. What
it may touch is fixed by `task.qzi`:

- It reads only inside its project directory and writes only inside the project's `build/` directory. Paths are
  relative and made of plain segments (no `..`, no hidden names), and they are resolved and checked against the
  directory, so a symbolic link cannot lead outside it.
- Reading and writing cost fuel like Quartz work does: one unit for every 64 bytes moved.
- Each task runs in a fresh sandbox with 2 000 million fuel and 256 MiB of memory. Nothing survives from one task to
  the next except the files it wrote.

The standard library is available, since it is pure computation: the `bundle` example decodes TOML with
`org.quartzlang.data`, hashes with `org.quartzlang.crypto` and writes a ZIP archive with `org.quartzlang.zip`. A
plugin may also depend on library packages from a repository (`p.dependencies([...])` in its own `build.qz`); they
are compiled into its tasks. It cannot depend on host plugins or on projects of a workspace.

### The `bundle` action

```quartz
package org.example.bundle.tasks

import org.quartzlang.crypto.sha256
import org.quartzlang.data.decodeToml
import org.quartzlang.qiln.task.*
import org.quartzlang.zip.{writeZip, ZipEntry}

/// The manifest a bundle carries next to its module.
@derive(Decode)
internal struct Manifest {
    name: str
    version: str
    main: str
    authors: [str] = []
    @key("api-version")
    apiVersion: int = 1
    description: str = ""
}

pub fn bundle(t: TaskContext) -> Result<(), str> {
    let path = t.option("manifest") ?? "plugin.toml"
    let extension = t.option("extension") ?? "bundle"
    let level = (t.option("level") ?? "9").toInt() ?? 9
    let text = t.readText(path) ?? ""
    if text.len() == 0 {
        return Err("{path} is missing or empty")
    }
    let decoded = decodeToml::<Manifest>(text)
    if decoded is Err(e) {
        return Err("{path}: {e}")
    }
    let m = decoded.unwrapOr(Manifest("", "", ""))
    let wrong = problems(m, t.projectVersion)
    if wrong.len() > 0 {
        return Err("{path}: {wrong.join("; ")}")
    }
    if let module = t.readBuild(t.artifact) {
        return pack(t, m, text, module, extension, level)
    }
    return Err("build/{t.artifact} is missing; the build task writes it")
}

fn pack(t: TaskContext, m: Manifest, text: str, module: Bytes, extension: str, level: int) -> Result<(), str> {
    let index = "name={m.name}\nversion={m.version}\nmain={m.main}\nmodule=plugin.qzb\nsha256={sha256(module).hex()}\n"
    let entries = [
        ZipEntry("plugin.toml", text.toBytes()),
        ZipEntry("plugin.qzb", module),
        ZipEntry("META-INF/BUNDLE", index.toBytes()),
    ]
    let archive = writeZip(entries, level = level)
    let out = "distributions/{m.name}-{m.version}.{extension}"
    if !t.writeBuild(out, archive) {
        return Err("cannot write build/{out}")
    }
    log("{m.name} {m.version} by {m.authors.join(", ")}")
    log("wrote build/{out} ({archive.len()} bytes)")
    return Ok(())
}
```

`problems` (left out here) returns every mistake in the manifest, so one run reports all of them. The task depends
on `build`, so the module it reads is always fresh, and it reads that module only through `t.artifact`.

### Up to date

A plugin task that succeeds is skipped on the next run while nothing it used changed, like the built-in tasks (see
[Up-to-date checks](qiln.md#up-to-date-checks)). Its fingerprint is the plugin's sources, the task's options, the
project's name, version and source list, plus every file the action read, every `exists` it asked and every file it
wrote, as the host recorded them while serving the calls. The record is exact because the action is deterministic
and sees the world only through `TaskContext`: an action needs no declared inputs or outputs. Deleting an output, or
changing a file it read, runs it again; `qiln --rerun` runs it regardless.

### Testing

`test/` holds `@test` functions in the package of `src/`; `qiln test` in the plugin's directory runs them like any
project's tests. Test the logic that does not need a `TaskContext` (here, `problems`) directly:

```quartz
package org.example.bundle.tasks

@test
fn reportsEveryProblem() {
    let m = Manifest("Greeter!", "2.0.0", "")
    if problems(m, "1.0.0").len() != 4 {
        panic("found {problems(m, "1.0.0")}")
    }
}
```

`qiln check` on a build plugin compiles `api/` against the build interface and `src/` against `task.qzi`, both with
the plugin's own warning levels (`p.denyWarnings`, `p.warning`), so both halves are checked before anything uses them.

## The plugin's `build.qz`

```quartz
import org.quartzlang.qiln.*

fn build(p: Project) {
    p.group = "org.example"
    p.name = "bundle"
    p.version = "1.0.0"
    p.kind = Kind.BuildPlugin
    p.description = "Packages a host plugin and its manifest into one archive"
    p.denyWarnings = true
    p.publishTo(Repository.local("../repo"))
}
```

The package name is the group and the name joined by a dot, `org.example.bundle`: it is the name `settings.qz`
requests, the one `applyPlugin` and `t.action` use, and the package `api/` declares.

## Developing against a workspace

While the plugin is being written, a workspace uses its sources directly, without publishing (the equivalent of
Gradle's `includeBuild`):

```quartz
fn settings(s: Settings) {
    s.includeAll(["core", "greeter", "app"])
    s.includePlugin("../bundle")
}
```

The plugin's `build.qz` and `api/` are inputs of the [configuration cache](qiln.md#the-configuration-cache), so a
change to them configures the workspace again; a change to `src/` is picked up the next time a task runs.

## Publishing

A build plugin publishes like a library: its `api/`, `src/` and a generated `package.toml` in one `.qzs` archive,
described by a signed `.qzmeta` whose kind is `build-plugin` (see [Repository format](registry-format.md)).

```console
$ qiln keygen
wrote ~/.qiln/signing.key; public key 6a3d5972c4aa470a962122b2c1be1e1c033f2d9ba19a8596bcf1feede4314df3
$ qiln publish
> :build
  wrote build/libs/bundle-1.0.0.qzs (1515 bytes)
> :publish
  published org.example.bundle 1.0.0 (build-plugin, 1515 bytes, blake2b 44748f174de3bfdf) to ../repo
```

Workspaces then request it by name and range from a plugin repository:

```quartz
fn settings(s: Settings) {
    s.includeAll(["core", "greeter", "app"])
    s.pluginRepository(Repository.local("../repo"))
    s.plugin("org.example.bundle:^1.0")
}
```

Plugins resolve in a graph of their own, recorded under `[[plugin]]` in `qiln.lock`: a plugin's libraries never
change the versions the projects compile with, and the projects' dependencies never change the plugin's. The key that
signed the plugin is pinned in the lock like any package's.
