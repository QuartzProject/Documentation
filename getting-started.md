# Getting started

## Build the tools

You need Clang with C++23 support, CMake 3.28 or newer and Ninja.

```bash
cmake --preset release
cmake --build build/release
```

This builds `quartz` (the command line tool) in `build/release/cli/` and `quartz-lsp` (the language server) in
`build/release/lsp/`. Put them on your `PATH`.

The optional native tier needs LLVM 23 (`-DQUARTZ_COMPILER=ON`). Without it everything runs in the interpreter, which is
already faster than Lua.

## Create a package

Every package has a reverse-domain name you control:

```bash
quartz new org.example.hello
```

That creates:

```
hello/
  package.toml      name, version and the functions the package exports
  src/main.qz       a function and a test
```

```quartz
package org.example.hello

pub fn greet(name: str) -> str {
    return "Hello, {name}!"
}

@test
fn greetsByName() {
    if greet("Ada") != "Hello, Ada!" {
        panic("unexpected greeting")
    }
}
```

## Run and test

```bash
quartz test hello                 # runs every @test function in its own sandbox
quartz check hello/src/main.qz    # type checks without running
quartz run program.qz             # runs `main`, or another function with --entry
quartz build hello -o hello.qzb   # a portable, validated module; --sign signs it
```

`quartz run` gives programs a `print` function and `n.ticks` for `wait`; a real host gives them its own interface
instead (see [Embedding](embedding.md)).

## Editor

The VS Code extension in `editors/vscode` adds syntax highlighting and starts `quartz-lsp` for diagnostics, completion
with automatic imports, go to definition, references, rename and formatting.
