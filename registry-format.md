# Quartz repository format

A Quartz package repository is a Maven repository. Packages are laid out with Maven's directory structure and listed
in `maven-metadata.xml`, so anything that serves a Maven repository serves Quartz packages unchanged: a plain
directory, a static web server, Maven Central, GitHub Packages, Reposilite, Nexus, Artifactory or an S3 bucket. What
Maven cannot express (Quartz version ranges, the kind of package, capabilities, a signature) goes into a `.qzmeta`
file next to each artifact, the way Gradle adds a `.module` file.

[Qiln](qiln.md) reads and writes this format: it resolves dependencies, verifies what it downloads, writes `qiln.lock`
and publishes. This chapter describes `.qzmeta` format 1 and `qiln.lock` format 1.

## Layout

A package name is a reverse domain (`org.example.text`): two or more segments of lower case letters, digits and `_`.
Its last segment is the Maven artifact id and the rest is the group id, so `org.example.text` is group `org.example`,
artifact `text`. The paths follow:

```
org/example/text/maven-metadata.xml              the published versions
org/example/text/0.1.0/text-0.1.0.qzs            the artifact: sources of a library
org/example/text/0.1.0/text-0.1.0.qzmeta         what the artifact is, signed by the publisher
org/example/text/0.1.0/text-0.1.0.pom            a minimal POM, for Maven hosts that require one
org/example/shop/greeter/1.0.0/greeter-1.0.0.qzb a signed module: a host plugin or an application
```

Every file has a `.sha256` and a `.sha512` beside it, as Maven tools expect. Versions are always written as
`major.minor.patch`.

A client builds every path from a validated package name and version; nothing read from a repository is ever used as
a path.

### Kinds

| Kind | Artifact | Content |
|---|---|---|
| `library` | `.qzs` | the sources, compiled into every package that depends on it |
| `build-plugin` | `.qzs` | the sources of a [build plugin](qiln-plugins.md): `api/` and `src/` |
| `plugin` | `.qzb` | a signed module that a host links at run time in its own sandbox |
| `application` | `.qzb` | a signed module that runs on its own |

Libraries are published as source because every user compiles them in: generics, inlining and direct calls work across
the boundary, and a call into a library costs what any call costs.

### `maven-metadata.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<metadata>
  <groupId>org.example</groupId>
  <artifactId>bundle</artifactId>
  <versioning>
    <latest>1.0.0</latest>
    <release>1.0.0</release>
    <versions>
      <version>1.0.0</version>
    </versions>
    <lastUpdated>20261120003310</lastUpdated>
  </versioning>
</metadata>
```

A client reads only `groupId` and `artifactId`, which must match the package asked for, and the `version` entries.
Versions that are not `major.minor.patch` are ignored, since a shared repository may hold other artifacts; at most
10 000 versions are read, from a file of at most 1 MiB. This is the only file of a repository that changes after it is
written, so clients do not cache it.

## `.qzmeta`

```toml
format = 1
name = "org.example.bundle"
version = "1.0.0"
kind = "build-plugin"
quartz = "0.1.0"
qzb-format = 0
archive = "bundle-1.0.0.qzs"
checksum = "ccd322be68b7ddf7c16b867ae81b5880b202e1dd74c17585281f0db3df30b167"
dependencies = []
capabilities = []
interfaces = []
exports = []
key = "42e96ccad2af7b98a559d460dc31800f875d522a3e3d961e9124f05ebd340c12"
signature = "fd57764876b694baa5cf71412f24ade73f167d91d079ed46a6ff16ca988a461f033f154ca9a1aab6746d4a6aab20447337888300f8a0e0c580d01db1b8c9de01"
```

| Field | |
|---|---|
| `format` | `1`; a reader refuses any other number |
| `name`, `version` | the package and version; they must be the ones the path asked for |
| `kind` | `library`, `build-plugin`, `plugin` or `application` |
| `quartz` | the version of the compiler that checked the package before it was published |
| `qzb-format` | the `.qzb` format version of a module artifact; `0` for sources |
| `archive` | the artifact's file name in the same directory; it must be `<artifact>-<version>.qzs` or `.qzb` as the kind says |
| `checksum` | BLAKE2b-256 of the artifact, in hex |
| `dependencies` | `name@range` entries, sorted by name and unique; ranges use the syntax of [Qiln](qiln.md#values-from-the-prelude) |
| `capabilities` | the capabilities the package asks its host for |
| `interfaces` | the host interfaces (`.qzi` file names) it compiles against |
| `exports` | the functions a plugin offers other packages |
| `key` | the publisher's Ed25519 public key (RFC 8032), in hex |
| `signature` | the publisher's Ed25519 signature, in hex, over the text below |

The file is TOML restricted to a subset that is easy to parse safely: one `key = value` per line; values are basic
strings without escapes or control characters, integers or single-line lists of strings. Lists hold at most 256
entries and the whole file at most 64 KiB.

### What is signed

The signature covers this exact text, every line ending in `\n`: the fixed first line, then one line per field in this
order, then one line per dependency, capability, interface and export in the order of their lists.

```
qiln-artifact-v1
name org.example.text
version 0.3.1
kind library
quartz 0.1.0
qzb-format 0
archive text-0.3.1.qzs
checksum c40f6a40216ebc40ebc0cc759617fee21d4e0d7054d3b049f637e4057235e719
dependency org.example.mathx >=1.1, <2
capability log
export greet
```

The signature binds the artifact (through its checksum) to its name, version, kind, dependencies and declared
capabilities: a server cannot swap the artifact, widen a dependency range, relabel a plugin as a library or hide a
capability without the publisher's key. The `.sha256` and `.sha512` files are written for Maven tools but not checked
by Qiln: the signed BLAKE2b checksum, pinned again in the lock file, is stronger and saves a request per artifact.

## Artifacts

### Sources: `.qzs`

Libraries and build plugins are published as a source archive:

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
and strictly increasing in byte order, so there is exactly one encoding of a given set of files. Only `package.toml`,
`.qz` and `.qzi` files are allowed, and `package.toml` is required: Qiln generates it with the package's name, version
and kind (a build plugin is labelled `library` there; its real kind is in the `.qzmeta`), so the core library and other
tools can read the archive too. A library's archive holds its main sources; a build plugin's holds `api/` and `src/`.
Tests are not published.

### Modules: `.qzb`

Host plugins and applications are published as the binary module the compiler produces (the `.qzb` container: header,
BLAKE2b content hash, payload with the `package.toml` text, Ed25519 signatures), signed with the same key as the
`.qzmeta`. A host plugin keeps its own sandbox and `state`; the packages that use it compile against the interface
derived from its module. A client loads it only with a valid module signature by the key of its `.qzmeta`.

## Publishing

Publishing writes the files of a version first (artifact, `.qzmeta`, `.pom` and their sums) and `maven-metadata.xml`
last, so a reader never sees a version listed before its files exist. A version that is already listed, or whose
`.qzmeta` exists, is never written again: published versions are immutable, and a fix is a new version.

`qiln publish` writes to a directory. A web repository is filled by publishing to a directory and uploading it with
any Maven tool or by syncing it to the server.

The public repository at `repo.quartzlang.org` will use this same layout, adding what a plain Maven repository does
not give: accounts, ownership of a namespace verified through DNS or a GitHub organization (as Maven Central does),
moderation, search, and a page per package showing the capabilities it asks for. Namespace ownership is checked by
the repository when a version is uploaded; the client needs no DNS code, because it pins keys itself.

## Resolution

Qiln resolves two graphs per workspace, each from its own repositories:

- **packages**: what the projects compile, from the repositories every `build.qz` declares;
- **plugins**: the build plugins `settings.qz` requests and the libraries they use, from its plugin repositories.

They never share versions: a plugin's library cannot force a version on the projects, nor the other way round.

Repositories are searched in the order they were declared. The first repository whose `maven-metadata.xml` lists a
package serves every version of that package, so one package never mixes origins.

For each package, the resolver picks the highest version that satisfies every range that requires it: the ranges of
the projects and the ranges in the `.qzmeta` of every package already chosen. It repeats until the choice no longer
changes (at most 64 rounds). There is one version of each package in a graph, because two versions of the same
package would declare the same names. When no version satisfies the ranges of a package, the resolver rules out the
version of the package that brought the conflicting range and starts again (at most 256 times), so an older version of
that package with a looser requirement can still be found. A conflict that remains names every range and who asked
for it.

### The lock file

`qiln.lock`, at the root of the workspace, pins the exact result:

```toml
# Written by qiln: the exact packages this workspace builds with.
format = 1

[[package]]
name = "org.example.text"
version = "0.1.0"
kind = "library"
dependencies = []
checksum = "ea22f59e293c9e7d06cb4730fa17883985007b312ef1719c2a28da51ffb4879b"
key = "42e96ccad2af7b98a559d460dc31800f875d522a3e3d961e9124f05ebd340c12"

[[plugin]]
name = "org.example.bundle"
version = "1.0.0"
kind = "build-plugin"
dependencies = []
checksum = "ccd322be68b7ddf7c16b867ae81b5880b202e1dd74c17585281f0db3df30b167"
key = "42e96ccad2af7b98a559d460dc31800f875d522a3e3d961e9124f05ebd340c12"
```

`[[package]]` entries belong to the projects' graph and `[[plugin]]` entries to the plugins' graph, each in load order
(every package after its dependencies), with the same subset of TOML as `.qzmeta`. A package appears once per graph.

- While the lock covers every range of the scripts and of the locked packages, builds use it exactly.
- When a range changes, the resolver runs again and keeps every locked version that still fits, like Cargo.
- `--update` ignores the locked versions (but keeps their keys) and moves to the newest ones the ranges accept.
- `--locked` turns any change to the lock into an error, for continuous integration.
- A lock with another `format` is refused; deleting it resolves from scratch.

## Trust

Everything downloaded is hostile until verified:

- A `.qzmeta` must parse, name the package and version that was asked for, name the expected archive and carry a valid
  signature by its own key. A bad one is an error, not a skipped version.
- An artifact must match the checksum in the lock (which came from the signed `.qzmeta`). A locked version whose
  artifact changed in the repository is an error: versions never change.
- A module (`.qzb`) must also carry a valid module signature by the package's key before anything is compiled or run.
- **Trust on first use.** The key a package was locked with, or else the key that signed its oldest published
  version, is the only key accepted for its other versions. A version signed by another key stops resolution with
  both keys in the message; `--allow-key-change` accepts it and pins the new key.

So a compromised repository cannot slip in a version from another publisher without the user seeing it, and cannot
change a locked version at all.

## Downloads and the cache

- A repository is a directory path, a `file://` URL or an `https://` URL; `http://` is refused.
- `https://` repositories are read with the system `curl`, started directly (no shell) with `--proto =https` for the
  request and for redirects, a size limit and a timeout; a nonzero exit is an error. Size limits are checked again
  when the file is read: 1 MiB for `maven-metadata.xml`, 64 KiB for a `.qzmeta`, 64 MiB for an artifact.
- Verified `.qzmeta` files are kept in `~/.qiln/cache/meta/` (they never change, and they are verified again when
  read) and artifacts in `~/.qiln/cache/artifacts/`, named by their BLAKE2b hash. `$QILN_HOME` replaces `~/.qiln`.
- With the lock and the cache filled, a build does not touch the network.
