# Qiln

Qiln is the build and package tool of Quartz: it compiles, tests, runs and publishes packages, resolves their
dependencies from repositories and runs build plugins. The `quartz` command works on files and folders without
dependencies; anything with dependencies, workspaces of several projects or publishing goes through Qiln.

- **Builds are configured in Quartz.** Each project has a `build.qz` and a workspace of several projects has a
  `settings.qz`, in the spirit of Gradle's Kotlin DSL. They are type checked against Qiln's build interface, so a
  mistake is a compile error with a line number, and the language server completes and checks them against the
  same interface (see [Editors](#editors)).
- **Configuration runs in a sandbox.** A build script can only call the build API: it cannot read files, reach the
  network or start processes, and it has a fuel and memory budget. Because Quartz is deterministic, the configured
  workspace is cached by the hash of its inputs, and later runs skip the scripts.
- **Plugins are Quartz packages.** A build plugin adds its own types and functions to `build.qz` and its own tasks,
  which run in a separate sandbox that reads the project and writes only to its build directory. See
  [Writing a Qiln plugin](qiln-plugins.md).
- **Packages come from Maven repositories.** A Quartz repository uses the Maven layout, so a directory, a static web
  server, Nexus, Artifactory or GitHub Packages can serve it. Every version carries a `.qzmeta` signed with Ed25519,
  `qiln.lock` pins every package by hash, and publisher keys are trusted on first use. The format is in
  [Repository format](registry-format.md).

## Install

Qiln is built from source next to a checkout of the Quartz core, which it links as a library. You need Clang with
C++23, CMake 3.28 or newer and Ninja.

```bash
git clone https://github.com/QuartzProject/Quartz
git clone https://github.com/QuartzProject/Qiln
cd Qiln
cmake --preset release
cmake --build build/release
```

The binary is `build/release/src/qiln`; put it on your `PATH`. To build against a Quartz checkout somewhere else, add
`-DQILN_QUARTZ_SOURCE=<path>`; without a checkout, CMake looks for an installed Quartz package with `find_package`.
Downloads from `https://` repositories use the system `curl`, which ships with Linux, macOS, Windows 10 and later and
FreeBSD.

```console
$ qiln version
qiln 0.1.0 (quartz 0.1.0)
```

## A first project

```console
$ qiln init hello
created application org.example.hello in hello; try 'qiln test' and 'qiln run'
$ cd hello
$ qiln test
> :test
  ok      greetsByName (0.0 ms)
  1 passed, 0 failed
$ qiln run
> :build
  wrote build/libs/hello-0.1.0.qzb (960 bytes)
> :run
Hello, Quartz!
```

When run again, the tasks whose inputs did not change are skipped (see [Up-to-date checks](#up-to-date-checks)):

```console
$ qiln run
> :build UP-TO-DATE
> :run
Hello, Quartz!
```

`qiln init` wrote a `.gitignore` (for `build/` and `.qiln/`), the sources in `src/`, the tests in `test/` and this
`build.qz`:

```quartz
import org.quartzlang.qiln.*

fn build(p: Project) {
    p.group = "org.example"
    p.version = "0.1.0"
    p.kind = Kind.Application
}
```

`qiln init [dir] --kind library|application|plugin|build-plugin --group org.example` picks another kind or group;
the default is an application in `org.example`, named after the directory.

## Projects and workspaces

A **project** is a directory with a `build.qz`. Its main sources are the `.qz` and `.qzi` files under `src/`, its
tests the ones under `test/` (both can be changed with `p.sourceDir`). Its package name is its group and its name
joined by a dot: `org.example.hello`.

A **workspace** is a directory with a `settings.qz` that includes several projects, each in its own subdirectory with
its own `build.qz`:

```
shop/
  settings.qz
  core/build.qz      core/src/core.qz       core/test/core_test.qz
  greeter/build.qz   greeter/src/greeter.qz greeter/server.qzi  greeter/plugin.toml
  app/build.qz       app/src/main.qz
```

Projects are named by path: `:core` is the project in `core/`, `:libs:text` the one in `libs/text/`, and `:` the root
project (a `build.qz` next to `settings.qz`). A project without a `settings.qz` above it is a workspace of one.

`qiln` looks for the nearest `settings.qz`, or else `build.qz`, in the current directory and above it. A task named
without a project runs in the project of the current directory, or in every project when run from the workspace
root; `qiln :core:test` names one.

## `build.qz`

A build script is a Quartz program with one function, `fn build(p: Project)`, compiled against the build interface
`org.quartzlang.qiln` (`qiln.qzi` plus a prelude written in Quartz). `Project` is a handle: its properties are set
with `=` and its methods add to the project.

```quartz
import org.quartzlang.qiln.*
import org.example.bundle.{bundle, Bundle}

fn build(p: Project) {
    p.group = "org.example.shop"
    p.version = "1.0.0"
    p.kind = Kind.Plugin
    p.hostOnly = true
    p.hostInterface("server.qzi")
    p.exports(["onJoin"])
    p.repository(Repository.maven("https://repo.example.org/quartz"))
    p.dependencies([
        project(":core"),
        implementation("org.example.text:^1.2"),
        testImplementation("org.example.check:~0.4"),
    ])
    p.limits(Limits(fuel = 10000000) with { memoryMiB = 16 })
    bundle(p, Bundle(manifest = "plugin.toml"))
    let release = p.task("release")
    release.description = "Everything a release needs"
    release.dependsOn("bundle")
}
```

Every setter checks its argument. A wrong value stops the configuration with the line of the script that set it:

```console
$ qiln check
build.qz: trap: host error: '1.0' is not a major.minor.patch version in 'build' at build.qz:5
```

### Properties

| Property | Type | |
|---|---|---|
| `p.path` | `str`, read only | `:` for the root project, `:core` for the project in `core/` |
| `p.name` | `str` | lower case letters, digits and `_`; the directory name by default |
| `p.group` | `str` | a reverse domain like `org.example`; needed to publish |
| `p.packageName` | `str`, read only | the group and the name joined by a dot |
| `p.version` | `str` | `major.minor.patch` |
| `p.description` | `str` | up to 1024 bytes; goes into the published `.pom` |
| `p.kind` | `Kind` | what the project produces (below); `Kind.Library` by default |
| `p.entry` | `str` | the function `qiln run` starts; `main` by default |
| `p.denyWarnings` | `bool` | every compiler warning fails `check`, `build` and `test`, except rules given another level with `p.warning` |
| `p.hostOnly` | `bool` | compile only against the declared host interfaces, without the runner's `print` |

| Kind | Published as | Used by |
|---|---|---|
| `Kind.Library` | `.qzs` sources | compiled into every package that depends on it |
| `Kind.Application` | `.qzb` module | `qiln run` |
| `Kind.Plugin` | signed `.qzb` module | its host, which links it at run time in its own sandbox |
| `Kind.BuildPlugin` | `.qzs` with `api/` and `src/` | `settings.qz`, to extend `build.qz` and add tasks |

### Functions

| Function | |
|---|---|
| `p.sourceDir(set, dir)` | add a source directory to `"main"` or `"test"`; without any, they are `src` and `test` |
| `p.hostInterface(path)` | a `.qzi` of the host the package runs in, relative to the project |
| `p.repository(r)`, `p.repositories([r, ...])` | where dependencies are resolved from, searched in order |
| `p.publishTo(r)` | where `qiln publish` writes this project's versions (the first one given) |
| `p.dependency(d)`, `p.dependencies([d, ...])` | add dependencies (below) |
| `p.exports([name, ...])` | functions other packages may call, for a host plugin |
| `p.capabilities([name, ...])` | capabilities the package asks its host for; recorded in its `.qzmeta` |
| `p.warning(rule, level)`, `p.warnings([rule, ...], level)` | the level of a warning rule (like `unused-variable`), or of every rule with `"*"`; the last call wins |
| `p.limits(Limits(...))` | the sandbox budget of `qiln run` and `qiln test` |
| `p.task(name) -> Task` | the task called `name`, created on first use |
| `p.option(key, value)` | an option plugin tasks read when their own task has none of that name |
| `p.property(key) -> str?` | a `-P key=value` from the command line |
| `p.applyPlugin(name)`, `p.hasPlugin(name) -> bool` | used by build plugins (see [Writing a Qiln plugin](qiln-plugins.md)) |
| `log(message)` | print a line while the script runs (a cached configuration does not print it again) |

The underlying handle methods (`addRepository`, `addPublishRepository`, `addDependency`, `addExport`,
`addCapability`, `setLimits`) take plain strings and numbers; the prelude functions above wrap them and are what
scripts normally use.

### Values from the prelude

```quartz
pub struct Repository {
    url: str
    name: str = ""
}

impl Repository {
    pub fn local(path: str) -> Repository          // a directory, relative to the project that declares it
    pub fn maven(url: str, name: str = "") -> Repository
    pub fn quartz() -> Repository                  // https://repo.quartzlang.org/releases
}

pub struct Dependency {
    notation: str
    configuration: str = "implementation"
}

pub fn implementation(notation: str) -> Dependency     // compiled into the package and everything that uses it
pub fn testImplementation(notation: str) -> Dependency // only compiled into the tests
pub fn project(path: str) -> Dependency                // a project of the workspace, like ":core"

pub struct Limits {
    fuel: int = 100000000
    memoryMiB: int = 64
    maxDepth: int = 4096
    testTicks: int = 1000000   // the virtual tick a suspend test may reach; 0 is no limit
}

pub enum RuleLevel {   // what the compiler does with the warnings of one rule
    Ignore
    Warning
    Error
}
```

A repository URL is a directory path, a `file://` URL or an `https://` URL; `http://` is refused. A dependency
notation is a package name and a version range separated by a colon, `org.example.text:^1.2`. Ranges:

| Range | Accepts |
|---|---|
| `1.2.3` or `^1.2.3` | `>=1.2.3, <2.0.0`; below 1.0 the leftmost non-zero part is fixed: `^0.2` is `>=0.2.0, <0.3.0` |
| `~1.2` | `>=1.2.0, <1.3.0` |
| `=1.2.3` | exactly that version |
| `>=1.0`, `>1.0`, `<=2.0`, `<2.0` | comparisons |
| `>=1.1, <2` | every comparison separated by commas must hold |
| `*` | any version |

`Limits` accepts fuel from 1 000 to 10^12, memory from 1 to 4096 MiB, a call depth from 16 to 10^6 and `testTicks` from 0 (no limit) up.

### Warning levels

Warnings are reported and do not fail the build. `p.denyWarnings = true` (or `--deny-warnings` for every project)
turns every warning into an error; `p.warning` sets the level of one rule, and wins over `denyWarnings` whatever the
order:

```quartz
fn build(p: Project) {
    p.denyWarnings = true
    p.warning("unused-variable", RuleLevel.Warning)
    p.warnings(["unused-import", "unused-parameter"], RuleLevel.Ignore)
}
```

The rules are the compiler's (see [Warnings](tools.md#warnings)); a name it does not know stops the configuration
with the list of valid ones. When a compilation fails only because of warnings raised to errors, Qiln says how many
and of which rules:

```console
$ qiln check
> :check
src/main.qz:8:9: error: unused variable 'unused' [unused-variable]
        let unused = 1
            ^^^^^^
:check failed: project : does not compile: 1 warning(s) are errors (unused-variable 1)
```

A build plugin's `api/` and `src/` are checked with the plugin's own levels.

### Tasks

```quartz
let release = p.task("release")
release.description = "Everything a release needs"
release.group = "distribution"
release.dependsOnAll(["check", "bundle", ":core:build"])
```

| Task member | |
|---|---|
| `t.name` | read only |
| `t.description`, `t.group` | shown by `qiln tasks` |
| `t.dependsOn(task)`, `t.dependsOnAll([task, ...])` | `build` for a task of the same project, `:core:build` for another |
| `t.action(plugin, function)` | run the exported `function` of `plugin`, a build plugin applied to the project |
| `t.option(key, value)` | a setting the action reads |

A script can also add dependencies to a built-in task (`p.task("build").dependsOn("generate")`), but only build
plugins provide actions: a task without one only groups the tasks it depends on.

## `settings.qz`

```quartz
import org.quartzlang.qiln.*

fn settings(s: Settings) {
    s.name = "shop"
    s.includeAll(["core", "greeter", "app"])
    s.pluginRepository(Repository.local("../repo"))
    s.plugin("org.example.bundle:^1.0")
}
```

| Member | |
|---|---|
| `s.name` | the workspace name; the directory name by default |
| `s.include(path)`, `s.includeAll([path, ...])` | add the project in `path`, relative to the workspace root and `/` separated |
| `s.pluginRepository(r)` | where build plugins are resolved from |
| `s.plugin(notation)` | a build plugin from the plugin repositories, like `org.example.bundle:^1.0` |
| `s.includePlugin(path)` | a build plugin from its sources in `path` (which may start with `../`), for developing it |
| `s.property(key) -> str?` | a `-P key=value` from the command line |

Plugins are requested here, not in `build.qz`, because every `build.qz` is compiled against the API of the plugins it
uses, so they must be known before any build script is compiled.

## Built-in tasks

| Task | |
|---|---|
| `check` | compile the sources and the tests without running anything |
| `test` | run every `@test` function, each in its own sandbox (`--filter text` keeps the names that contain `text`) |
| `build` | compile and write the artifact to `build/libs/<name>-<version>.qzs` or `.qzb` |
| `run` | applications only: build, then run the entry function; its `int` result is the exit code |
| `publish` | build, sign and publish to the project's publish repository (or `--to <dir or URL>`) |
| `clean` | delete the project's `build/` directory |

Tasks run in dependency order, each at most once per invocation, independent ones in parallel, and a task whose
inputs did not change since it last succeeded is skipped (below).

`run` and `test` give programs the same interface as `quartz run`: `print`, `n.ticks` for `wait`, and the log sink
on standard error. A project with `p.hostOnly = true` gets only its declared host interfaces; the functions of those
interfaces are linked to stubs that fail with their name when called, so tests of code that does not call them pass
outside the real host.

A `@test` may be a `suspend fn`. `qiln test` then runs it as a task on a virtual tick clock, the same one `quartz test`
uses: `wait n.ticks` resumes n ticks later without sleeping, a task that runs out of fuel resumes on the next tick, and
the first trap fails the test. A suspend test still running when its next resumption would pass `Limits.testTicks` (one
million ticks by default) fails with `still running after N ticks`; `testTicks = 0` lets it run without a limit, as
`quartz test` does.

## Up-to-date checks

A task that succeeds writes a stamp to `<project>/build/.qiln/<task>.stamp`: a BLAKE2b fingerprint of everything it
used and of what it wrote. On the next run, a task whose fingerprint still matches is skipped:

```console
$ qiln test
> :core:test UP-TO-DATE
> :greeter:test UP-TO-DATE
> :app:test UP-TO-DATE
```

| Task | Its fingerprint |
|---|---|
| `check`, `test`, `build` | every source compiled in (its own, its project dependencies' and its libraries'), the host interfaces, the checksum of every host plugin it links, the generated `package.toml`, the warning levels and the versions of Qiln and of the core; `test` adds the limits and `--filter`, `build` its artifact |
| a plugin task | the plugin's sources, the task's options, the project's name, version and sources, and every file the action read or wrote (see [Writing a Qiln plugin](qiln-plugins.md#up-to-date)) |
| `run`, `publish`, `clean` | never up to date |

Changing a source of `:core` runs again the tasks of `:core` and of every project that compiles it in. The stamps live
in `build/`, so `qiln clean` makes every task of the project run again, `check` and `test` included. `--rerun`
ignores the stamps for one invocation. On the shop, a run with everything up to date spends about 4.3 million
instructions, against 30 million to run it all again.

## Parallel tasks

Independent tasks run at once on a pool of workers: `-j N` sets how many (1 to 256), and the default is one per
hardware thread. Each task's output is held back and printed in the order of the plan, so the output is the same
with `-j 1` and `-j 8`. `clean` keeps its place among the tasks of its project and `run` runs alone, since it owns the
terminal. After a failure no new task starts, and every failure is reported in order. On the shop, a full
`check test build bundle` drops from 8.0 ms with `-j 1` to 5.3 ms with the default.

## Dependencies

A project depends on packages from its repositories and on other projects of the workspace:

```quartz
p.repository(Repository.local("../repo"))
p.dependencies([implementation("org.example.text:^0.1")])
```

```console
$ qiln run
locked org.example.text 0.1.0 (library)
> :build
  wrote build/libs/app2-0.1.0.qzb (1059 bytes)
> :run
Hello, repository!
$ qiln deps
: (org.example.app2 0.1.0, application)
└── org.example.text ^0.1 -> 0.1.0
```

- A **library** is compiled from source into every package that uses it, so generics and inlining work across it
  and a call into it costs what any call costs.
- A **host plugin** is linked at run time in its own sandbox; the package that uses it compiles against the interface
  derived from its module.
- A **project** dependency (`project(":core")`) compiles the project's sources in. When the project is published,
  it becomes a dependency on the published package at `^` its current version.

The first resolution writes `qiln.lock` at the workspace root. From then on builds use exactly the locked versions,
download nothing that is already in the cache, and check every archive against its locked hash. When a range in a
script changes, Qiln resolves again, keeping every locked version that still fits:

```console
$ qiln deps --locked
qiln.lock is out of date (org.example.text is locked at 0.1.0, outside '^0.2' asked by project :); run without --locked to update it
$ qiln deps
locked org.example.text 0.2.0 (library), was 0.1.0
: (org.example.app2 0.1.0, application)
└── org.example.text ^0.2 -> 0.2.0
```

`--update` moves every package to the newest version its ranges accept, and `--locked` (for CI) fails instead of
changing the lock. A version signed by a different key than earlier versions of the same package stops the build:

```console
$ qiln deps --update
org.example.text 0.3.0 is signed by key e2bed7fb56e5116729a44e81574d8c7f84ae1431ef3a2a14ccc60ef0cc9d2776, not by 6a3d5972c4aa470a962122b2c1be1e1c033f2d9ba19a8596bcf1feede4314df3 which signed it before; if the publisher really changed keys, run again with --allow-key-change
```

The resolution rules, the lock file and the trust model are described in
[Repository format](registry-format.md#resolution).

### Adding dependencies

`qiln add` and `qiln remove` edit `build.qz` in place and update `qiln.lock`, from the directory of the project:

```console
$ qiln add org.example.text@^0.1
locked org.example.text 0.1.0 (library)
added org.example.text:^0.1 in build.qz
$ qiln add org.example.text@~0.2 --test
locked org.example.text 0.2.0 (library), was 0.1.0
changed to org.example.text:~0.2 (test) in build.qz
$ qiln remove org.example.text
removed org.example.text from build.qz
```

| Command | |
|---|---|
| `qiln add <package>[@range]` | add an `implementation` dependency; without a range, `^` the newest version the project's repositories have |
| `qiln add :<project>` | add a `project(":core")` dependency |
| `--test` | as a `testImplementation` |
| `qiln remove <package>` or `qiln remove :<project>` | remove it |

The edit touches only the dependency: a package that is already listed gets its range or configuration changed in
place; otherwise the element goes at the end of the `p.dependencies([...])` list, with the indentation of the others,
or below the last `p.dependency(...)` call, or in a new `p.dependencies([...])` block at the end of `fn build`. Removing
deletes the element and its comma, its line when it stood alone, and the whole call when it was the only one.
Before writing, Qiln runs the edited script and checks that the project gained (or lost) the dependency, so a
dependency declared inside an `if` is refused; if resolving the new lock fails, `build.qz` is left as it was.

## Publishing

`qiln publish` publishes to the repository `p.publishTo` names, or to `--to <dir or URL>`:

```console
$ qiln keygen
wrote ~/.qiln/signing.key; public key 6a3d5972c4aa470a962122b2c1be1e1c033f2d9ba19a8596bcf1feede4314df3
$ qiln publish --to ../repo
> :build
  wrote build/libs/text-0.1.0.qzs (150 bytes)
> :publish
  published org.example.text 0.1.0 (library, 150 bytes, blake2b ea22f59e293c9e7d) to ../repo
```

`qiln keygen [file]` writes an Ed25519 seed (by default `~/.qiln/signing.key`, readable only by you) and prints the
public key. `publish` signs with `--sign <file>`, else `$QILN_SIGNING_KEY`, else `~/.qiln/signing.key`. Host plugins
and applications are signed twice: the `.qzb` module itself, and the `.qzmeta` that describes it.

A published version never changes: publishing it again is an error, so fixes go into a new version.

### Publishing over HTTPS

To an `https://` repository (Nexus, Artifactory, GitHub Packages), Qiln uploads with HTTP PUT: first
it reads the package's `maven-metadata.xml` and checks that the version is not there, then it uploads the archive, the
`.qzmeta`, the `.pom` and their `.sha256` and `.sha512` with `If-None-Match: *`, so a file that already exists is
never overwritten, and the updated `maven-metadata.xml` last. The credentials come from `~/.qiln/credentials.toml`:

```toml
[company]
url = "https://repo.example.org/quartz"
username = "ada"
password = 'p@ss"word'
```

Each section has a `url` and either `username` and `password` (HTTP Basic) or `token` (a Bearer token); literal
strings in single quotes keep quotes and backslashes as they are. A repository uses the section whose `url` is the
longest prefix of its own URL, never one picked by name, because `build.qz` chooses both the name and the URL of its
repositories. The same file serves downloads from private repositories. For CI, `$QILN_PUBLISH_USERNAME` and
`$QILN_PUBLISH_PASSWORD`, or `$QILN_PUBLISH_TOKEN`, take precedence, and only for the upload of `qiln publish`.
Credentials reach `curl` through a private configuration file, never on its command line.

A server that refuses the credentials gets a hint, and plain `http://` is refused except to a test server on the same
machine with `--allow-insecure-localhost`:

```console
$ qiln publish --to http://127.0.0.1:8765/releases
> :build UP-TO-DATE
> :publish
:publish failed: repository 'http://127.0.0.1:8765/releases': plain http is refused, use https:// (or --allow-insecure-localhost for a test server)
$ qiln publish --to http://127.0.0.1:8765/releases --allow-insecure-localhost
> :build UP-TO-DATE
> :publish
:publish failed: http://127.0.0.1:8765/releases refused http://127.0.0.1:8765/releases/org/example/bundle/1.0.0/bundle-1.0.0.qzs (HTTP 401); add credentials for http://127.0.0.1:8765/releases in ~/.qiln/credentials.toml or $QILN_PUBLISH_USERNAME and $QILN_PUBLISH_PASSWORD (or $QILN_PUBLISH_TOKEN)
```

With a `[local-test]` section for that URL in `credentials.toml`:

```console
$ qiln publish --to http://127.0.0.1:8765/releases --allow-insecure-localhost
> :build UP-TO-DATE
> :publish
  published org.example.bundle 1.0.0 (build-plugin, 1515 bytes, blake2b 44748f174de3bfdf) to http://127.0.0.1:8765/releases
```

Two publications of the same package at the same moment can lose one entry of `maven-metadata.xml`, as with
`mvn deploy`. An upload cut halfway leaves files that `If-None-Match` will not overwrite; delete them on the server.

## Commands and options

| Command | |
|---|---|
| `qiln <task>...` | run tasks: `check`, `test`, `build`, `run`, `publish`, `clean`, or one a script or plugin declares |
| `qiln :core:test` | a task of one project |
| `qiln init [dir] [--kind ...] [--group ...]` | a new project with a test |
| `qiln tasks` | the tasks of each project, with their group, description and plugin |
| `qiln deps [--update]` | the dependency trees, resolving first if needed |
| `qiln add <package>[@range]`, `qiln add :<project>` | add a dependency to `build.qz` and update `qiln.lock` (see [Adding dependencies](#adding-dependencies)) |
| `qiln remove <package>`, `qiln remove :<project>` | remove one |
| `qiln keygen [file]` | an Ed25519 signing key |
| `qiln version`, `qiln help` | |

| Option | |
|---|---|
| `-p <dir>`, `--project-dir <dir>` | work in `dir` instead of the current directory |
| `-P key=value` | a property scripts read with `p.property("key")` or `s.property("key")` |
| `-j <n>`, `--jobs <n>` | run up to `n` tasks at once (1 to 256); one per hardware thread by default |
| `--rerun` | run every task, ignoring the up-to-date checks |
| `--filter <text>` | `test`: only the tests whose name contains `text` |
| `--to <dir or URL>` | `publish`: publish there instead of the project's publish repository |
| `--sign <file>` | `publish`: the signing seed |
| `--allow-insecure-localhost` | allow plain `http://` to `127.0.0.1`, `[::1]` or `localhost`, for test servers |
| `--test` | `add`: as a test dependency |
| `--deny-warnings` | compiler warnings fail the build, in every project (rules a project sets with `p.warning` keep their level) |
| `--update` | resolve to the newest versions the ranges accept |
| `--locked` | fail when `qiln.lock` would change |
| `--allow-key-change` | accept a package version signed by a new key, and pin the new key |
| `--no-cache` | evaluate the build scripts even when the configuration cache is valid |
| `-q`, `--quiet` | leave out the `locked ...` lines and cache warnings |

## The configuration cache

Configuring a workspace means compiling and running `settings.qz` and every `build.qz`. Quartz programs are
deterministic, so the result depends only on their inputs, and Qiln keeps it in `.qiln/configuration.bin` together
with a BLAKE2b hash of each input:

- `settings.qz` and every `build.qz` (including ones that do not exist yet, so adding one is noticed);
- the `build.qz` and `api/` sources of plugins included from source;
- the versions of Qiln and of the Quartz core, and the text of the build interface;
- the `-P` properties, the name of the workspace directory and the plugin section of `qiln.lock`.

When every input still hashes the same, no script is compiled or run. On the shop workspace, configuring costs about
16.8 million instructions and loading the cache 0.31 million: a whole `qiln tasks` drops from 3.9 ms to 1.3 ms. A
`log` line in a script shows when it really runs:

```console
$ qiln :app:run
[app/build.qz] configuring :app for dev
> :app:build
  wrote app/build/libs/app-1.0.0.qzb (1438 bytes)
> :app:run
Welcome to the shop, Ada!
Today's special costs 4.99 EUR
$ qiln :app:run
> :app:build UP-TO-DATE
> :app:run
Welcome to the shop, Ada!
Today's special costs 4.99 EUR
$ qiln :app:run -P profile=release
[app/build.qz] configuring :app for release
> :app:build UP-TO-DATE
> :app:run
Welcome to the shop, Ada!
Today's special costs 4.99 EUR
```

(Here `app/build.qz` has `let profile = p.property("profile") ?? "dev"` and `log("configuring {p.path} for
{profile}")`.) `--no-cache` evaluates the scripts anyway. The cache needs no invalidation by hand: it can be deleted
at any time. A plugin included from source keeps its evaluated `build.qz` in the cache too, so an up-to-date run does
not compile it again.

## Editors

Every configuration (and a cached one when the files are missing) writes the interfaces the build scripts compile
against to `.qiln/api/` at the workspace root, rewriting a file only when its text changed:

```
.qiln/api/qiln.qzi                                the build interface
.qiln/api/qiln.qz                                 its prelude (Repository, Dependency, Limits...)
.qiln/api/task.qzi                                what a plugin's task actions see
.qiln/api/plugins/org.example.bundle/bundle.qz    the api/ of every plugin settings.qz requests
```

`quartz-lsp` reads them: a file named `build.qz` or `settings.qz` with a `.qiln/api/qiln.qzi` in its directory or one
above it is analysed on its own, as Qiln compiles it, together with every `.qz` and `.qzi` under that `.qiln/api/` and
without the `print` of the command line runner. Errors show as you type, hover shows the `///` comments of the build
API and of the plugins, completion offers their members, and go to definition opens the file in `.qiln/api/`. Other
files in a project directory are analysed as usual. Run any `qiln` command once (`qiln tasks` is enough) after cloning
a project or adding a plugin; the language server picks the files up on the next edit.

## Walkthrough: the shop

[`examples/shop`](https://github.com/QuartzProject/Qiln/tree/main/examples/shop) in the Qiln repository is a workspace
of three projects: `core`, a library with prices and greetings; `greeter`, a host plugin for an imaginary server; and
`app`, an application. The greeter applies the build plugin in
[`examples/bundle`](https://github.com/QuartzProject/Qiln/tree/main/examples/bundle), which validates its
`plugin.toml` and packs it with the compiled module into one archive. Every command below was run as shown (with the
home directory shortened to `~`, and `...` where repeated output is left out).

```quartz
// settings.qz
import org.quartzlang.qiln.*

fn settings(s: Settings) {
    s.name = "shop"
    s.includeAll(["core", "greeter", "app"])
    s.includePlugin("../bundle")
}
```

```quartz
// core/build.qz
import org.quartzlang.qiln.*

fn build(p: Project) {
    p.group = "org.example.shop"
    p.version = "1.0.0"
    p.description = "Prices and greetings shared by the shop's programs"
}
```

```quartz
// app/build.qz
import org.quartzlang.qiln.*

fn build(p: Project) {
    p.group = "org.example.shop"
    p.version = "1.0.0"
    p.kind = Kind.Application
    p.dependency(project(":core"))
    p.limits(Limits(fuel = 10000000, memoryMiB = 16))
}
```

```quartz
// greeter/build.qz
import org.quartzlang.qiln.*
import org.example.bundle.{bundle, Bundle}

fn build(p: Project) {
    p.group = "org.example.shop"
    p.version = "1.0.0"
    p.kind = Kind.Plugin
    p.hostOnly = true
    p.hostInterface("server.qzi")
    p.exports(["onJoin"])
    p.dependency(project(":core"))
    bundle(p, Bundle(manifest = "plugin.toml"))
}
```

The tasks of each project, including the one the plugin added:

```console
$ cd examples/shop
$ qiln tasks
:core (org.example.shop.core 1.0.0, library)
  build    build        Compiles the project and writes its artifact to build/libs
  clean    build        Deletes the build directory
  check    verification Compiles the sources and the tests without running anything
  test     verification Runs every @test function, each in its own sandbox
  publish  publishing   Signs the artifact and publishes it to a repository
:greeter (org.example.shop.greeter 1.0.0, plugin)
  build    build        Compiles the project and writes its artifact to build/libs
  clean    build        Deletes the build directory
  check    verification Compiles the sources and the tests without running anything
  test     verification Runs every @test function, each in its own sandbox
  publish  publishing   Signs the artifact and publishes it to a repository
  bundle   distribution Validates plugin.toml and packs it with the module into build/distributions [org.example.bundle]
:app (org.example.shop.app 1.0.0, application)
  build    build        Compiles the project and writes its artifact to build/libs
  clean    build        Deletes the build directory
  check    verification Compiles the sources and the tests without running anything
  test     verification Runs every @test function, each in its own sandbox
  run      application  Runs the entry function in the runner's sandbox
  publish  publishing   Signs the artifact and publishes it to a repository
```

Test everything, bundle the plugin and run the application:

```console
$ qiln test
> :core:test
  ok      showsCents (0.0 ms)
  1 passed, 0 failed
> :greeter:test
  ok      greetsByName (0.0 ms)
  1 passed, 0 failed
> :app:test
  no tests
$ qiln bundle
> :greeter:build
  wrote greeter/build/libs/greeter-1.0.0.qzb (1467 bytes)
> :greeter:bundle
  [bundle] greeter 1.0.0 by Ada
  [bundle] wrote build/distributions/greeter-1.0.0.bundle (1514 bytes)
$ qiln :app:run
> :app:build
  wrote app/build/libs/app-1.0.0.qzb (1438 bytes)
> :app:run
Welcome to the shop, Ada!
Today's special costs 4.99 EUR
$ qiln deps
:core (org.example.shop.core 1.0.0, library)
  (no dependencies)
:greeter (org.example.shop.greeter 1.0.0, plugin)
└── :core (project)
:app (org.example.shop.app 1.0.0, application)
└── :core (project)
build plugins
└── org.example.bundle 1.0.0 (../bundle)
```

The greeter's tests pass outside its server: `broadcast`, from `server.qzi`, is linked to a stub that would fail if a
test called it.

Nothing changed since, so a second run skips every task; after an edit to `core/src/core.qz`, the tasks of `:core`
run again, and so do those of `:greeter` and `:app`, which compile `:core` in:

```console
$ qiln test
> :core:test UP-TO-DATE
> :greeter:test UP-TO-DATE
> :app:test UP-TO-DATE
$ qiln bundle
> :greeter:build UP-TO-DATE
> :greeter:bundle UP-TO-DATE
$ echo "// rounding is by cents" >> core/src/core.qz
$ qiln test
> :core:test
  ok      showsCents (0.0 ms)
  1 passed, 0 failed
> :greeter:test
  ok      greetsByName (0.0 ms)
  1 passed, 0 failed
> :app:test
  no tests
```

The configuration also wrote the build interface and the plugin's API to `.qiln/api/`, where the language server
finds them (see [Editors](#editors)):

```console
$ find .qiln/api -type f | sort
.qiln/api/plugins/org.example.bundle/bundle.qz
.qiln/api/qiln.qz
.qiln/api/qiln.qzi
.qiln/api/task.qzi
```

Next, publish the plugin and use it from a repository instead of its sources:

```console
$ cd ../bundle
$ qiln test
> :test
  ok      acceptsAGoodManifest (0.0 ms)
  ok      reportsEveryProblem (0.0 ms)
  2 passed, 0 failed
$ qiln keygen
wrote ~/.qiln/signing.key; public key 6a3d5972c4aa470a962122b2c1be1e1c033f2d9ba19a8596bcf1feede4314df3
$ qiln publish
> :build
  wrote build/libs/bundle-1.0.0.qzs (1515 bytes)
> :publish
  published org.example.bundle 1.0.0 (build-plugin, 1515 bytes, blake2b 44748f174de3bfdf) to ../repo
```

In `shop/settings.qz`, replace `s.includePlugin("../bundle")` with
`s.pluginRepository(Repository.local("../repo"))` and `s.plugin("org.example.bundle:^1.0")`:

```console
$ cd ../shop
$ qiln bundle
locked org.example.bundle 1.0.0 (build-plugin)
> :greeter:build
  wrote greeter/build/libs/greeter-1.0.0.qzb (1467 bytes)
> :greeter:bundle
  [bundle] greeter 1.0.0 by Ada
  [bundle] wrote build/distributions/greeter-1.0.0.bundle (1514 bytes)
$ qiln deps
...
build plugins
└── org.example.bundle 1.0.0 (repository)
```

The repository now holds the archive with its `.qzmeta`, `.pom` and their `.sha256` and `.sha512`, plus the
package's `maven-metadata.xml`:

```
repo/org/example/bundle/maven-metadata.xml
repo/org/example/bundle/1.0.0/bundle-1.0.0.qzs
repo/org/example/bundle/1.0.0/bundle-1.0.0.qzmeta
repo/org/example/bundle/1.0.0/bundle-1.0.0.pom
```

and the workspace's `qiln.lock` pins the archive's BLAKE2b hash and the publisher's key:

```toml
# Written by qiln: the exact packages this workspace builds with.
format = 1

[[plugin]]
name = "org.example.bundle"
version = "1.0.0"
kind = "build-plugin"
dependencies = []
checksum = "44748f174de3bfdf8786447447ac20af2a8deb654077e6132dec6f87b98fbfff"
key = "6a3d5972c4aa470a962122b2c1be1e1c033f2d9ba19a8596bcf1feede4314df3"
```

## Files

| Path | Written by | |
|---|---|---|
| `<project>/build/` | tasks | artifacts in `build/libs`, and whatever plugin tasks write; `qiln clean` deletes it |
| `<project>/build/.qiln/<task>.stamp` | tasks | the fingerprint of each task's last successful run (see [Up-to-date checks](#up-to-date-checks)) |
| `.qiln/configuration.bin` | configuration | the [configuration cache](#the-configuration-cache), at the workspace root |
| `.qiln/api/` | configuration | the build interface and the plugins' APIs, for [editors](#editors) |
| `qiln.lock` | resolution | the exact packages and plugins the workspace builds with; commit it |
| `~/.qiln/signing.key` | `qiln keygen` | the default signing seed |
| `~/.qiln/credentials.toml` | you | repository credentials, matched by URL prefix (see [Publishing over HTTPS](#publishing-over-https)) |
| `~/.qiln/cache/meta/` | resolution | verified `.qzmeta` files, checked again when read |
| `~/.qiln/cache/artifacts/` | builds | downloaded archives, named by their BLAKE2b hash |

`$QILN_HOME` replaces `~/.qiln`. With the lock and the cache filled, a build does not touch the network.

## Budgets

| Sandbox | Fuel | Memory |
|---|---|---|
| `settings.qz` and `build.qz` | 20 million | 16 MiB |
| A plugin task | 2 000 million | 256 MiB |
| `qiln run` and `qiln test` | `p.limits`, by default 100 million per call | 64 MiB |

A configuration typically spends a few thousand units of fuel, so an endless loop in a script is cut off in
milliseconds instead of hanging the build.
