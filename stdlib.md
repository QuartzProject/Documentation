# The standard library

Everything here charges fuel in proportion to the work it does, and gives the same results on every platform and in
both execution tiers.

## Built in, no import

| | |
|---|---|
| Functions | `panic(message)`, `assert(cond, message = "assertion failed")`, `Ok(value)`, `Err(error)`, `List()`, `Map()` |
| `str` | `len()`, `lower()`, `upper()`, `contains(s)`, `startsWith(s)`, `endsWith(s)`, `find(s) -> int?`, `slice(begin, end)` (negative indices count from the end), `byteAt(i)`, `toBytes()`, `toInt() -> int?`, `toFloat() -> float?`, `replace(from, to)`, `split(sep) -> [str]`, `trim()`, `trimStart()`, `trimEnd()`, `repeat(n)`, `equalsIgnoreCase(s)`, `chars() -> [char]` |
| `char` and `int` | `c.code() -> int`, `n.toChar() -> char?`, `n.abs()`, `n.clamp(lo, hi)` |
| `float` | `sqrt()`, `floor()`, `ceil()`, `round()`, `abs()`, `sin()`, `cos()`, `tan()`, `asin()`, `acos()`, `atan()`, `exp()`, `log()`, `log10()`, `clamp(lo, hi)` |
| `[T]` | `len()`, `push(v)`, `pop() -> T?`, `clear()`, `xs[i]`, `insert(i, v)`, `removeAt(i) -> T`, `insertAll(i, other)`, `reverse()`, `slice(a, b)`; for numbers, `bool`, `char` and `str` also `contains(v)`, `indexOf(v) -> int?`, `sort()`; `[str]` has `join(separator)` |
| `[T]` with functions | `map(f)`, `filter(keep)`, `any(test)`, `all(test)`, `find(test) -> T?`, `indexWhere(test) -> int?`, `sortBy(key)`, `sortWith(cmp)` |
| `Map<K, V>` | `len()`, `get(k) -> V?`, `set(k, v)`, `has(k)`, `remove(k)`, `m[k]` |
| `Result<T, E>` | `isOk()`, `isErr()`, `unwrap()`, `unwrapOr(fallback)`, `?` |
| `T?` | `unwrap()`, `unwrapOr(fallback)`, `??`, `?.`, `if let` |

Sorting is stable. Floats sort by IEEE total order (`-0.0` before `0.0`, NaN last); strings sort by bytes.

```quartz
let names = " ada, bo ,cy ".split(",").map((w) => w.trim())   // ["ada", "bo", "cy"]
names.sortBy((n) => n.len())                                     // ["bo", "cy", "ada"]
let long = names.filter((n) => n.len() > 2)                      // ["ada"]
```

## `org.quartzlang.math`

`sqrt`, `floor`, `ceil`, `round`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2(y, x)`, `exp`, `log`, `log10`,
`fmod`, `pow(x, y)` on `float`; `abs`, `min`, `max`, `clamp(x, lo, hi)` on `int` or `float`; constants `PI`, `TAU`,
`INFINITY`, `MAX_INT`, `MIN_INT`. Every function is computed by Quartz itself, not by the platform's math library, so
results are bit-identical everywhere (within one ulp of the exact value, correctly rounded in almost every case).

```quartz
import org.quartzlang.math.{PI, atan2, clamp}
```

## `org.quartzlang.random`

A deterministic generator (xoroshiro128++): the same seed gives the same sequence on every platform.

```quartz
import org.quartzlang.random.Random

var rng = Random(42)
let roll = rng.nextInt(6) + 1     // also nextLong(), nextIntIn(from, until), nextFloat(), nextBool(), shuffle(list)
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
`writeUInt(data, offset, size, value, bigEndian = false)`, `crc32(data)`.

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
