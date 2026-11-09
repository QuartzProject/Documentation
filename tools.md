# Tools

## `quartz`

| Command | |
|---|---|
| `quartz check <files or folder>` | Type check and validate; prints errors and warnings |
| `quartz run <files, folder or .qzb> [--entry name]` | Run `main` (or `--entry`) with `print` and `n.ticks` available |
| `quartz run ... --profile [--profile-out out.json]` | Run and report calls, fuel and time per function and per call path |
| `quartz debug --dap` | The debugger: speaks the Debug Adapter Protocol on standard input and output for an editor |
| `quartz test <files or folder> [--filter text]` | Run every `@test` function, each in a fresh sandbox |
| `quartz build <files or folder> -o out.qzb [--sign seed] [--strip-lines]` | Build a validated module; a folder brings its `package.toml` |
| `quartz interface <package.qzb>` | Print the `.qzi` other packages compile against, with parameter names, `///` comments and defaults |
| `quartz keygen <seed file>` | Create an Ed25519 signing key for `build --sign`; prints the public key |
| `quartz repl` | Interactive prompt: expressions print their value; declarations, imports and `state` carry over |
| `quartz doc <files or folder> [-o api.md]` | Markdown reference of the public declarations and their `///` comments |
| `quartz fmt [--check] <files or folders>` | Format in place, or list unformatted files |
| `quartz ir`, `quartz dis` | Print the IR or the bytecode |

`run` and `ir` also accept `--trust <public key>` and `--require-signature` to load only signed modules. `check`,
`run`, `test` and `build` take `--deny-warnings` and `--rule <rule>=ignore|warning|error` (see [Warnings](#warnings)),
`--host-only` to compile against the host's own `.qzi` alone, without the `print` and `ticks` the command adds, and
`--source-name <name>` before a file to record it under that name in traces and line tables instead of its path.

The `quartz` command works on files and folders on their own. Dependencies, workspaces of several projects,
repositories and publishing belong to [Qiln](qiln.md), the build tool (see [Packages](#packages)).

## Warnings

The compiler warns while it type checks, so warnings cost nothing at run time. Each one ends with the id of its rule:

```text
shop.qz:2:9: warning: unused variable 'unused' [unused-variable]
shop.qz:3:18: warning: '{4}' interpolates a number literal; write '\{' for a brace, or use a raw string (r"...") [literal-interpolation]
```

| Rule | Warns about |
|---|---|
| `unused-variable`, `unused-parameter`, `unused-import` | a name that is never read (a leading `_` silences it) |
| `unused-assignment` | a variable that is assigned and never read |
| `unused-private` | a `private` function, or a method without `pub` or `internal`, that nothing calls (other functions may be called by the host) |
| `discarded-result` | a `Result` that is dropped; handle it or write `let _ = ...` |
| `shadowed-variable` | a local that hides another one in the same function (`if let x = x` is fine) |
| `unreachable-pattern`, `unreachable-code` | a `match` arm that can never run; code that can never run, such as after a `return` |
| `deprecated` | a call to something marked `@deprecated` |
| `unknown-attribute` | an attribute that is not one of the [language's](tour.md#attributes) |
| `unscoped-wait-loop` | a loop that waits and allocates outside a `scope` |
| `literal-interpolation` | `"\\d{4}"`, which interpolates the number 4 where a regular expression was meant |
| `unknown-rule` | a `--rule` that names no rule |

Each rule has a level: `ignore`, `warning` (the default) or `error`. `--rule unused-parameter=ignore` sets one,
`--rule '*=error'` sets them all, and when several apply the last one wins, so `--rule '*=error' --rule
deprecated=warning` fails on everything but deprecations. `--deny-warnings` is `*=error`. A warning raised to an error
fails `check`, `run`, `test` and `build` like any other error. Interfaces, the standard library and dependencies never
warn, and the unused rules stay quiet while there are errors.

Hosts set the same levels with `CompileOptions::rules` (or `qz_compile_with` in C) and read each diagnostic with its
rule, file and range; the language server sends the rule as the diagnostic's code, and Qiln has `p.denyWarnings`
and `p.warning`.

## Debugging

`quartz debug --dap` is a debug adapter: editors start it and talk the
[Debug Adapter Protocol](https://microsoft.github.io/debug-adapter-protocol/) to it over standard input and output.
The VS Code extension and the JetBrains plugin use it; any editor with a DAP client can too. A `launch` request
takes:

| Attribute | |
|---|---|
| `program` | A `.qz` file, a package folder (as `quartz run` takes it) or a `.qzb` module |
| `entry` | The function to run, `main` by default |
| `tests` | `true` runs every `@test` function, each in a fresh sandbox, instead of `entry` |
| `filter` | With `tests`: only the tests whose name contains this text |
| `stopOnEntry` | Stop at the first line that runs |
| `tasks` | More `suspend fn`s to start next to the entry, as `quartz run --task` does |
| `trapFilters` | The trap kinds the *All traps* breakpoint covers |

What it does:

- **Breakpoints** on lines. A line without code moves the breakpoint to the next line that has some. A breakpoint
  can carry a condition: a variable, a field path or an index (`p.x`, `xs[2]`, `m["key"]`) alone (it must be
  `true`), or compared with `==`, `!=`, `<`, `<=`, `>` or `>=` to a literal or another variable (`i == 3`,
  `total > limit`).
- **Function breakpoints** by short name (`len`), type-qualified (`Point.len`) or fully qualified
  (`org.example.Point.len`); they stop at the function's first line and can take a condition.
- **Trap breakpoints**: *All traps* plus one entry per kind (division by zero, panics and failed checks, index out
  of bounds, null unwrapped, out of fuel, out of memory, stack overflow, invalid handle, host errors, unreachable
  code). In JetBrains IDEs, tick the kinds in the properties of the **Quartz Traps** breakpoint.
- **Inline breakpoints**: one arm of a `match`, or one statement, that shares its line with others (Shift+F9 in VS
  Code).
- **Stepping**: over, into, out of a call, and pause. Stepping into the standard library shows its source.
- **Call stack** with the function, file and line of every frame.
- **Variables**: arguments and locals in scope at the stopped line, with their types. Structs, tuples, lists, maps,
  enums with data, nullables and `state` values expand. Hovering a name (or a path like `p.x`) shows its value.
- **Traps** stop the program where they happen, with the whole stack and its variables still there; the trap and its
  trace show as the exception. Continuing ends the program as `quartz run` would.
- **Changing values**: *Set Value* changes numbers, booleans, characters (`'x'`) and text (`"..."`, only in the
  current frame's locals).
- **Threads**: each task is a thread in the call stack, and a step stays on the thread you asked for.
- `print` and the log go to the debug console.

The program runs in the interpreter, compiled with a probe at the start of every line, without the IR optimizer and
without fused instructions, so every local keeps its own register. A normal build has no probes and pays nothing for
the debugger. The names of locals and their scopes travel in the line table of a `.qzb` (`--strip-lines` drops both),
so a module built without `--strip-lines` can be debugged with names; a `.qzb` keeps lines but not columns.

### Tasks and the tick clock

`quartz run` and `quartz test` drive tasks on a virtual clock. `wait 20.ticks` resumes the task 20 ticks later without
sleeping, and a task that spends its fuel slice resumes on the next tick. `quartz run file.qz --task ticker --task
saver` starts more `suspend fn`s next to the entry function; they share the program's `state`, and the first trap ends
the run. A `@test` may be a `suspend fn`; it runs as a task on the same clock.

## Profiling

`quartz run --profile` runs the program with a probe at the entry of each function and before each return, and
prints, after it ends:

- per function: calls, fuel spent in the function itself and in total with what it called, and the same for wall
  time;
- the call tree with total fuel, its share and calls per path (paths under 0.5% are left out).

Fuel is the unit a host budgets a call in (one unit per call made and per loop iteration, plus the bytes that string
and list operations touch), and it is exact: the same program with the same input always gives the same numbers, so a
change can be judged without timing noise. Wall time includes the probes' own cost, so it is a guide, not a
measurement. `--profile-out profile.json` also writes the tree as a [speedscope](https://www.speedscope.app) file
with a fuel and a time view.

A host gets the same from its own sandboxes: compile with `CompileOptions::probes.calls = true` (or pass
`{.calls = true}` to `quartz::load`), attach a `vm::Profiler` to the sandbox, and read `functions()`, `tree()`,
`report()` or `speedscope()`. `Sandbox::setProbe` is the lower level hook both tools are built on.

## Documentation comments

A comment of three slashes right above a declaration (attributes may sit in between) documents it: `quartz doc`
puts it in the reference and the language server shows it on hover.

```quartz
/// Totals the quantities; 0 for an empty list.
pub fn total(orders: [Order]) -> int {
    ...
}
```

## Packages

`package.toml` says what a package is:

```toml
name = "org.example.app"
version = "0.1.0"
kind = "library"            # or "plugin"; library is the default
exports = ["greet"]         # functions other packages may call, for a plugin
```

`quartz check`, `run`, `test` and `build` on a folder compile every `.qz` and `.qzi` file below it, and `build`
carries its `package.toml` into the module. A folder whose `package.toml` declares `[dependencies]` is refused with a
message that points to Qiln: the `quartz` command does not resolve or download anything.

A **library** is compiled into every package that uses it, so generics and inlining work across it and a call costs
what any call costs. A **plugin** keeps its own sandbox and `state` and is linked at run time; the packages that use it
compile against the interface `quartz interface` derives from its module (see
[Packages that call each other](embedding.md#packages-that-call-each-other)).

Dependencies on other packages, workspaces, repositories, `qiln.lock` and publishing are handled by
[Qiln](qiln.md): dependencies are declared in `build.qz`, `qiln deps` resolves them, `qiln publish` signs and
publishes, and `qiln init` starts a project. The repository layout and its security rules are in
[Repository format](registry-format.md).

## `quartz fmt`

One style, no options: four spaces, 120 columns, comments kept where they were. Formatting is idempotent, so running
it twice changes nothing the second time.

## `quartz-lsp`

A language server over standard input and output. It analyses every package in the open folder together and offers
diagnostics as you type, hover with types and signatures, go to definition, document symbols, completion (including
names from other packages, adding the `import`), formatting, and the editor features the extension advertises.

A Qiln build script (`build.qz` or `settings.qz` under a workspace Qiln has configured) is analysed on its own
against the build interface and the plugins' APIs that Qiln writes to `.qiln/api/`, as Qiln compiles it, without the
runner's `print`; see [Qiln: Editors](qiln.md#editors).

## VS Code

The extension ([QuartzProject/VSCode-Extension](https://github.com/QuartzProject/VSCode-Extension)) gives syntax highlighting for `.qz` and `.qzi`, the language server, found on the
`PATH` or set with `quartz.server.path`, and the debugger, which runs `quartz debug --dap` (`quartz` on the `PATH` or
set with `quartz.cli.path`). F5 on a `.qz` file debugs it; `launch.json` offers "Run current file" and "Run tests".

## JetBrains IDEs

The plugin ([QuartzProject/JetBrains-Plugin](https://github.com/QuartzProject/JetBrains-Plugin)) works in IntelliJ
IDEA, CLion and the other IDEs of the IntelliJ Platform from 2026.2: highlighting with the same TextMate grammar as VS
Code, `quartz-lsp` through the IDE's own LSP client (set its path, and the `quartz` command's, under **Settings |
Languages & Frameworks | Quartz**), run configurations for `quartz run`, `test` and `check`, and the debugger over
`quartz debug --dap`. Android Studio lacks the IDE's LSP support, so the plugin does not install there.
