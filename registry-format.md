# Quartz package registry format

A registry is a static tree of files. Any web server that serves files over HTTPS can host one, and a plain
directory works offline. The client never asks the server to compute anything: it reads one index file per package
and downloads archives whose checksum and signature it verifies before using a single byte of them.

This document describes format 1.

## Layout

```
owners.toml                                   which key may publish under which name prefix
index/org/example/economy.toml                every version of org.example.economy
packages/org/example/economy/1.4.2.qzs        a library archive (sources)
packages/org/example/bank/2.1.0.qzb           a plugin archive (signed binary module)
```

Package names are reverse domains (`org.example.economy`): two or more segments of `[a-z][a-z0-9_]*`. A name maps to
a path by turning its dots into slashes, so `org.example` (`index/org/example.toml`) and `org.example.economy`
(`index/org/example/economy.toml`) never collide. Versions are always written as `major.minor.patch`.

A client builds every path from a validated name and version; nothing read from the server is ever used as a path.

## Text files

`owners.toml`, the index files and the client's `quartz.lock` are valid TOML restricted to a subset that is easy to
parse safely: one `key = value` per line, values are basic strings without escapes or control characters, integers,
booleans or single-line lists of strings, and tables are `[name]` or `[[name]]`. Each file starts with `format = 1`;
a reader refuses any other number. Unknown keys inside a release are ignored so later formats can add fields.

## Index files

```toml
format = 1
name = "org.example.text"

[[release]]
version = "0.3.1"
kind = "library"
dependencies = ["org.example.mathx@>=1.1, <2"]
checksum = "c40f6a40216ebc40ebc0cc759617fee21d4e0d7054d3b049f637e4057235e719"
key = "a5c7ccc7c4f26878d180e10d7c64111cae8d4252d8b303d88cf746e269112e29"
signature = "cfbb6133...310c"
```

- `name` must be the package the file belongs to.
- One `[[release]]` per published version, sorted by version. A version appears once and never changes.
- `kind` is `library` or `plugin`.
- `dependencies` lists `name@range` entries sorted by name; ranges use the `package.toml` syntax (`^1.2`, `~1.2`,
  `>=1.0, <2`, `=1.0.0`, `*`).
- `checksum` is the BLAKE2b-256 of the archive file, in hex.
- `key` is the publisher's Ed25519 public key (RFC 8032), in hex.
- `signature` is the publisher's Ed25519 signature, in hex, over this exact text (each line ends in `\n`, one
  `dependency` line per entry in the same order as the list):

```
quartz-registry-v1
name org.example.text
version 0.3.1
kind library
checksum c40f6a40216ebc40ebc0cc759617fee21d4e0d7054d3b049f637e4057235e719
dependency org.example.mathx >=1.1, <2
```

The signature binds the name, version, kind, dependencies and archive together: a server cannot swap the archive,
widen a range or relabel a plugin as a library without the publisher's seed.

## Archives

### Libraries: `.qzs`

A library is published as source, because every package that uses it compiles it in (generics, inlining and direct
calls work across the boundary).

```
"QZSA"  format byte 1  one zstd frame
```

The zstd frame must declare its content size (at most 32 MiB) and be the whole rest of the file. Its content is:

```
count                        unsigned LEB128, at most 4096
count times:
    path length, path        LEB128 then UTF-8 bytes
    data length, data        LEB128 then the file
```

Paths are relative, `/` separated, made of `[A-Za-z0-9._-]` segments that do not start with a dot, at most 255 bytes,
and strictly increasing in byte order (so there is exactly one encoding of a given set of files). Only
`package.toml`, `.qz` and `.qzi` files are allowed, and `package.toml` is required. Its name, version, kind and
dependencies must match the index entry.

### Plugins: `.qzb`

A plugin is published as the signed binary module that `quartz build` produces (the `.qzb` container: header,
BLAKE2b content hash, payload with the `package.toml` text, Ed25519 signatures). It keeps its own sandbox and state,
and a package that uses it compiles against the interface `quartz interface` derives from it. The module must carry
a valid signature by the key in the index entry, and its embedded `package.toml` must match the entry.

## Owners and name prefixes

```toml
format = 1

[[owner]]
prefix = "org.example"
key = "a5c7ccc7c4f26878d180e10d7c64111cae8d4252d8b303d88cf746e269112e29"
```

A key may publish a name equal to one of its prefixes or below it (`org.example` covers `org.example.text`, not
`org.examples`). A prefix has at least two segments, so nobody owns a whole top level domain. `quartz publish`
refuses a name outside the prefixes `owners.toml` lists for the signing key; `quartz owner` adds an entry to a local
registry.

A public registry adds an owner only after the publisher proves control of the domain. For the prefix
`org.example` the publisher creates a DNS TXT record on `_quartz.example.org` (the prefix reversed) holding
`quartz-key=<public key hex>`. The registry looks the record up over DNSSEC validated DNS or DNS over HTTPS from more
than one vantage point, then writes the owner entry. A longer prefix (`org.example.games`) can be delegated the same
way with a record on `_quartz.games.example.org`. Removing the record does not remove published versions; it stops
new ones once the registry rechecks. The client needs no DNS code: it trusts the keys in the index, pins them in the
lockfile and refuses key changes it was not told about.

## Client rules

- Everything downloaded is hostile until verified: index files are parsed with size limits (4 MiB) and every release
  signature in an index is checked before any version is chosen; an invalid signature anywhere in the file is an
  error, not a skipped entry. Archives (at most 64 MiB) must match the checksum, the archive's own manifest must match
  the entry, and plugins must also carry a valid module signature by the entry's key.
- Resolution picks, for each package, the highest version that satisfies every range that requires it, repeating
  until the choice is stable; there is one version of each package. A range nothing satisfies is a conflict that
  names every range and who asked for it; cycles are errors with their path.
- Trust on first use: the key a package was locked with, or else the key of its oldest published version, is the only
  key accepted for later versions. A version signed by another key stops resolution with both keys in the message;
  `--allow-key-change` accepts it and records the new key.
- `quartz.lock` pins name, version, kind, dependencies, checksum and key of every package, dependencies first. When it
  exists builds use it exactly and only download archives missing from the cache, checking each against the lock;
  `quartz fetch` resolves again keeping locked versions that still fit, and `--update` moves to the newest.
- The cache is `$QUARTZ_CACHE`, else `$XDG_CACHE_HOME/quartz`, `~/.cache/quartz`, `~/Library/Caches/quartz` on macOS or
  `%LOCALAPPDATA%\quartz` on Windows. Archives are stored by checksum and verified again on every build.
- `https://` registries are fetched with the system `curl` started directly (no shell) with `--proto =https` for the
  request and for redirects and a size limit; a nonzero exit is an error. `http://` is refused. A plain path or
  `file://` URL reads the directory directly.
