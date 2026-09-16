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

Every package has a reverse-domain name you control. A package is a folder with a `package.toml` and its sources:

```
hello/
  package.toml      name, version and the functions the package exports
  src/main.qz       a function and a test
```

```toml
name = "org.example.hello"
version = "0.1.0"
exports = ["greet"]
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

## Dependencies and projects

The `quartz` command builds and runs a package on its own. To use packages from a repository, split a program into
several projects or publish a package, use [Qiln](qiln.md), the build tool. It sets up a project with a `build.qz`
written in Quartz:

```console
$ qiln init hello
created application org.example.hello in hello; try 'qiln test' and 'qiln run'
$ cd hello
$ qiln run
> :build
  wrote build/libs/hello-0.1.0.qzb (913 bytes)
> :run
Hello, Quartz!
```

Dependencies are declared in `build.qz` and pinned in `qiln.lock`:

```quartz
import org.quartzlang.qiln.*

fn build(p: Project) {
    p.group = "org.example"
    p.version = "0.1.0"
    p.kind = Kind.Application
    p.repository(Repository.local("../repo"))
    p.dependencies([implementation("org.example.text:^0.1")])
}
```

## Editor

The [VS Code extension](https://github.com/QuartzProject/VSCode-Extension) and the
[JetBrains plugin](https://github.com/QuartzProject/JetBrains-Plugin) add syntax highlighting and start `quartz-lsp` for
diagnostics, completion with automatic imports, go to definition, references, rename and formatting. Neovim, Helix, Zed
and Notepad++ use the definitions in [QuartzProject/Grammars](https://github.com/QuartzProject/Grammars).
