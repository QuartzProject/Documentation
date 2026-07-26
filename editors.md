# Editors

VS Code and JetBrains IDEs have their own extensions (see [Tools](tools.md)). The other editors use the syntax
definitions in [QuartzProject/Grammars](https://github.com/QuartzProject/Grammars).

## tree-sitter: Neovim, Helix and Zed

A [tree-sitter](https://tree-sitter.github.io) grammar for Quartz (`.qz` and `.qzi` files).

It follows the parser in `src/syntax/`: newlines end statements (an external scanner in `src/scanner.c` decides when
a line break is a terminator), strings support nested `{expr}` interpolation and `"""` multi-line strings, and block
comments nest. The queries in `queries/` use the Neovim capture names.

### Build and test

```sh
npm install                 # installs the tree-sitter CLI locally
npm run generate            # only after editing grammar.js; src/parser.c is committed (ABI 14)
npx tree-sitter test        # corpus in test/corpus
npx tree-sitter build       # builds quartz.so (quartz.dylib, quartz.dll)
npx tree-sitter parse path/to/program.qz
```

### Neovim

No plugin is needed (Neovim 0.10 or later). Build the parser into the runtime path and copy the queries:

```sh
npx tree-sitter build -o ~/.local/share/nvim/site/parser/quartz.so
mkdir -p ~/.config/nvim/queries/quartz && cp queries/*.scm ~/.config/nvim/queries/quartz/
```

```lua
vim.filetype.add({ extension = { qz = "quartz", qzi = "quartz" } })
vim.api.nvim_create_autocmd("FileType", {
  pattern = "quartz",
  callback = function() vim.treesitter.start() end,
})
```

With nvim-treesitter you can instead register the parser (`url = "https://github.com/QuartzProject/Grammars"`,
`location = "tree-sitter"`, `files = { "src/parser.c", "src/scanner.c" }`) and run
`:TSInstall quartz`; its indent module reads `indents.scm`.

### Helix

In `~/.config/helix/languages.toml`:

```toml
[[language]]
name = "quartz"
scope = "source.quartz"
file-types = ["qz", "qzi"]
comment-token = "//"
block-comment-tokens = { start = "/*", end = "*/" }
indent = { tab-width = 4, unit = "    " }
language-servers = ["quartz-lsp"]

[language-server.quartz-lsp]
command = "quartz-lsp"

[[grammar]]
name = "quartz"
source = { git = "https://github.com/QuartzProject/Grammars", rev = "<commit>", subpath = "tree-sitter" }
```

Then run `hx --grammar fetch && hx --grammar build` and copy `queries/highlights.scm`, `locals.scm` and
`injections.scm` to `~/.config/helix/runtime/queries/quartz/`. Helix gives the first matching pattern priority, so
move the generic `(identifier) @variable` pattern from the top of `highlights.scm` to the end. `indents.scm` is
Neovim only.

### Zed

Create a dev extension with this layout and install it with `zed: install dev extension`:

```
quartz-zed/
  extension.toml
  languages/quartz/config.toml
  languages/quartz/highlights.scm     (copied from queries/)
```

```toml
# extension.toml
id = "quartz"
name = "Quartz"
version = "0.1.0"
schema_version = 1

[grammars.quartz]
repository = "https://github.com/QuartzProject/Grammars"
rev = "<commit>"
path = "tree-sitter"
```

```toml
# languages/quartz/config.toml
name = "Quartz"
grammar = "quartz"
path_suffixes = ["qz", "qzi"]
line_comments = ["// "]
block_comment = ["/* ", " */"]
tab_size = 4
```

## Notepad++

Syntax highlighting and folding for `.qz` and `.qzi` files, as a Notepad++ User Defined Language.

### Install

1. In Notepad++, open **Language > User Defined Language > Define your language...**
2. Click **Import...** and choose `Quartz.udl.xml` (light themes) or `Quartz-dark.udl.xml` (dark themes).
3. Restart Notepad++. Files ending in `.qz` or `.qzi` open as Quartz.

### What it covers

Keywords, built-in types and the language traits, attributes (`@test`, `@derive(...)`), `true`/`false`/`null`, built-in
functions, numbers (decimal, `0x`, `0b`, `0o`, `_` separators), strings and characters with escapes, `//` and `/* */`
comments, operators, and folding of `{ }` blocks.

A User Defined Language works on keyword lists, so it cannot tell a type from a variable by position, nor colour the
expressions inside `"{...}"` interpolation: the whole string keeps the string colour. For full highlighting and
diagnostics, use an editor with the Quartz language server.
