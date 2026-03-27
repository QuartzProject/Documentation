# The standard library

Everything here is implemented natively by the runtime, charges fuel in proportion to the bytes it processes, and gives
the same results on every platform.

## Built in, no import

| | |
|---|---|
| Functions | `panic(message)`, `Ok(value)`, `Err(error)`, `List()`, `Map()` |
| `str` | `len()`, `lower()`, `upper()`, `contains(s)`, `startsWith(s)`, `endsWith(s)`, `find(s) -> int?`, `slice(begin, end)`, `byteAt(i)`, `toBytes()` |
| `[T]` | `len()`, `push(v)`, `pop() -> T?`, `clear()`, `xs[i]`; `[str]` also has `join(separator)` |
| `Map<K, V>` | `len()`, `get(k) -> V?`, `set(k, v)`, `has(k)`, `remove(k)`, `m[k]` |
| `float` | `sqrt()`, `floor()`, `ceil()`, `abs()`, `sin()`, `cos()` |
| `int` | `abs()` |
| `Result<T, E>` | `isOk()`, `isErr()`, `unwrap()`, `unwrapOr(fallback)`, `?` |
| `T?` | `unwrap()`, `unwrapOr(fallback)`, `??`, `?.`, `if let` |

## `org.quartzlang.math`

`sqrt`, `floor`, `ceil`, `sin`, `cos`, `pow(x, y)` on `float`; `abs`, `min`, `max` on `int` or `float`. `sin`, `cos`
and `pow` are computed by Quartz itself, not by the platform's math library, so they are bit-identical everywhere.

```quartz
import org.quartzlang.math.{max, sqrt}
```

## `org.quartzlang.data`

One tree for every format:

```quartz
pub enum Value {
    Null
    Bool(bool)
    Int(int)
    Float(float)
    Str(str)
    List([Value])
    Table(Map<str, Value>)
}
```

`Value` has `get(key) -> Value?`, `item(index) -> Value?`, `len()`, `isNull()`, `asBool()`, `asInt()`, `asFloat()` and
`asStr()`, each returning `null` when the value is something else.

| Function | |
|---|---|
| `parseJson(text) -> Result<Value, str>` | RFC 8259 JSON |
| `toJson(value, indent = 0) -> str` | compact, or indented with `indent` spaces |
| `parseToml(text) -> Result<Value, str>` | TOML 1.0; dates and times come back as `Str` with their text |
| `parseYaml(text) -> Result<Value, str>` | a defined subset of YAML 1.2: block and flow maps and lists, scalars, multi-line strings, comments |

Errors name the line and what was expected.

## `org.quartzlang.bytes`

`Bytes` methods: `len()`, `get(i)`, `slice(begin, end)`, `toStr() -> str?` (when it is valid UTF-8), `toList()`,
`hex()`. Functions: `bytesOf([int])`, `concatBytes([Bytes])`, `readUInt(data, offset, size, bigEndian = false)`,
`crc32(data)`.

## `org.quartzlang.compress`

| Compress | Decompress |
|---|---|
| `deflate(data, level = 6)` | `inflate(data)` |
| `zlibCompress(data, level = 6)` | `zlibDecompress(data)` |
| `gzip(data, level = 6)` | `gunzip(data)` |
| `zstdCompress(data, level = 3)` | `zstdDecompress(data)` |

Decompression returns `Result<Bytes, str>` and stops at 64 MiB of output, so a small malicious input cannot exhaust
memory. The output interoperates with zlib, gzip and the `zstd` tool in both directions.

## `org.quartzlang.zip`

`readZip(data) -> Result<[ZipEntry], str>` and `writeZip(entries, level = 6) -> Bytes`, where
`struct ZipEntry { name: str, data: Bytes }`.
