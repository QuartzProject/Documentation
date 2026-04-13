# Tools

## `quartz`

| Command | |
|---|---|
| `quartz check <files or folder>` | Type check and validate; prints errors and warnings |
| `quartz run <files or .qzb> [--entry name]` | Run `main` (or `--entry`) with `print` and `n.ticks` available |
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
security rules are in [`registry/FORMAT.md`](../registry/FORMAT.md).

## `quartz fmt`

One style, no options: four spaces, 120 columns, comments kept where they were. Formatting is idempotent, so running
it twice changes nothing the second time.

## `quartz-lsp`

A language server over standard input and output. It analyses every package in the open folder together and offers
diagnostics as you type, hover with types and signatures, go to definition, document symbols, completion (including
names from other packages, adding the `import`), formatting, and the editor features the extension advertises.

## VS Code

`editors/vscode` holds the extension: syntax highlighting for `.qz` and `.qzi`, and the language server, found on the
`PATH` or set with `quartz.server.path`.
