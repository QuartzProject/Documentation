# Tools

## `quartz`

| Command | |
|---|---|
| `quartz check <files or folder>` | Type check and validate; prints errors and warnings |
| `quartz run <files or .qzb> [--entry name]` | Run `main` (or `--entry`) with `print` and `n.ticks` available |
| `quartz run ... --profile [--profile-out out.json]` | Run and report calls, fuel and time per function and per call path |
| `quartz debug --dap` | The debugger: speaks the Debug Adapter Protocol on standard input and output for an editor |
| `quartz test <files or folder> [--filter text]` | Run every `@test` function, each in a fresh sandbox |
| `quartz build <files or folder> -o out.qzb [--sign seed] [--strip-lines]` | Build a validated module; a folder brings its `package.toml` |
| `quartz interface <package.qzb>` | Print the `.qzi` other packages compile against |
| `quartz keygen <seed file>` | Create an Ed25519 signing key; prints the public key |
| `quartz new <org.example.name>` | Start a package |
| `quartz repl` | Interactive prompt: expressions print their value; declarations, imports and `state` carry over |
| `quartz doc <files or folder> [-o api.md]` | Markdown reference of the public declarations and their `///` comments |
| `quartz add <name>[@range] [folder]` | Add a dependency to `package.toml` (the newest version, `^x.y.z`, without a range) |
| `quartz fetch [folder] [--update] [--allow-key-change]` | Resolve dependencies, verify and cache them, write `quartz.lock` |
| `quartz publish [folder] --registry <dir> --sign <seed>` | Add the package to a local registry directory |
| `quartz owner <prefix> <public key> --registry <dir>` | Let a key publish names under a prefix |
| `quartz fmt [--check] <files or folders>` | Format in place, or list unformatted files |
| `quartz ir`, `quartz dis` | Print the IR or the bytecode |

`run` and `ir` also accept `--trust <public key>` and `--require-signature` to load only signed modules.

## Debugging

`quartz debug --dap` is a debug adapter: editors start it and talk the
[Debug Adapter Protocol](https://microsoft.github.io/debug-adapter-protocol/) to it over standard input and output.
The VS Code extension and the JetBrains plugin use it; any editor with a DAP client can too. A `launch` request
takes:

| Attribute | |
|---|---|
| `program` | A `.qz` file, a package folder (with its dependencies and plugins, as `quartz run` does) or a `.qzb` module |
| `entry` | The function to run, `main` by default |
| `tests` | `true` runs every `@test` function, each in a fresh sandbox, instead of `entry` |
| `filter` | With `tests`: only the tests whose name contains this text |
| `stopOnEntry` | Stop at the first line that runs |

What it does:

- **Breakpoints** on lines. A line without code moves the breakpoint to the next line that has some. A breakpoint
  can carry a condition: a variable, a field path or an index (`p.x`, `xs[2]`, `m["key"]`) alone (it must be
  `true`), or compared with `==`, `!=`, `<`, `<=`, `>` or `>=` to a literal or another variable (`i == 3`,
  `total > limit`).
- **Stepping**: over, into, out of a call, and pause.
- **Call stack** with the function, file and line of every frame.
- **Variables**: arguments and locals in scope at the stopped line, with their types. Structs, tuples, lists, maps,
  enums with data, nullables and `state` values expand. Hovering a name (or a path like `p.x`) shows its value.
- **Traps** stop the program where they happen, with the whole stack and its variables still there; the trap and its
  trace show as the exception. Continuing ends the program as `quartz run` would.
- `print` and the log go to the debug console.

The program runs in the interpreter, compiled with a probe at the start of every line, without the IR optimizer and
without fused instructions, so every local keeps its own register. A normal build has no probes and pays nothing for
the debugger. The names of locals and their scopes travel in the line table of a `.qzb` (`--strip-lines` drops both),
so a module built without `--strip-lines` can be debugged with names. The program is one thread, named after the
entry function or the test that is running.

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

## Packages and registries

`package.toml` says what a package is and what it needs:

```toml
name = "org.example.app"
version = "0.1.0"
kind = "library"            # or "plugin"; library is the default
registry = "https://packages.example.org"   # a directory or file:// URL works offline

[dependencies]
"org.example.text" = "^0.3"
"org.example.bank" = ">=2.0, <3"
```

A **library** is published as source and compiled into every package that uses it, so generics and inlining work
across it and a call costs what any call costs. A **plugin** is published as its signed `.qzb`, keeps its own sandbox
and `state`, and is linked at run time; the packages that use it compile against the interface `quartz interface`
derives from it.

`check`, `build`, `test` and `run` on a folder use its dependencies: they read `quartz.lock` (or resolve and write it
the first time), take the archives from the cache (fetching and verifying what is missing), add library sources and
plugin interfaces to the compile, and `run` and `test` start and link the plugins. The registry layout and the
security rules are in [`registry/FORMAT.md`](https://github.com/QuartzProject/Quartz/blob/main/registry/FORMAT.md).

## `quartz fmt`

One style, no options: four spaces, 120 columns, comments kept where they were. Formatting is idempotent, so running
it twice changes nothing the second time.

## `quartz-lsp`

A language server over standard input and output. It analyses every package in the open folder together and offers
diagnostics as you type, hover with types and signatures, go to definition, document symbols, completion (including
names from other packages, adding the `import`), formatting, and the editor features the extension advertises.

## VS Code

The extension ([QuartzProject/VSCode-Extension](https://github.com/QuartzProject/VSCode-Extension)) gives syntax highlighting for `.qz` and `.qzi`, the language server, found on the
`PATH` or set with `quartz.server.path`, and the debugger, which runs `quartz debug --dap` (`quartz` on the `PATH` or
set with `quartz.cli.path`). F5 on a `.qz` file debugs it; `launch.json` offers "Run current file" and "Run tests".
