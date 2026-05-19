# The standard library

Everything here charges fuel in proportion to the work it does, and gives the same results on every platform and in
both execution tiers.

## Built in, no import

| | |
|---|---|
| Functions | `panic(message)`, `assert(cond, message = "assertion failed")`, `Ok(value)`, `Err(error)`, `List()`, `Map()` |
| `str` | `len()`, `lower()`, `upper()`, `contains(s)`, `startsWith(s)`, `endsWith(s)`, `find(s) -> int?`, `slice(begin, end)` (negative indices count from the end), `byteAt(i)`, `toBytes()`, `toInt() -> int?`, `toFloat() -> float?`, `replace(from, to)`, `split(sep) -> [str]`, `trim()`, `trimStart()`, `trimEnd()`, `repeat(n)`, `equalsIgnoreCase(s)`, `chars() -> [char]` |
| `char` and `int` | `c.code() -> int`, `n.toChar() -> char?`, `n.abs()`, `n.clamp(lo, hi)` |
| every integer type | `checkedAdd(b)`, `checkedSub(b)`, `checkedMul(b)`, `checkedDiv(b)` return `T?` (null on overflow or division by zero); `saturatingAdd(b)`, `saturatingSub(b)`, `saturatingMul(b)` clamp to the type's range |
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

## `org.quartzlang.collections`

| Type | What it is | Main methods |
|---|---|---|
| `Set<T: Hash>` | insertion-ordered set | `add`, `remove`, `contains`, `union`, `intersect`, `difference`, `symmetricDifference`, `isSubsetOf`, `isDisjoint`, `copy` |
| `SortedMap<K: Ord, V>` | map in key order | `get`, `set`, `has`, `remove`, `first`, `last`, `floor`, `ceiling`, `lower`, `higher`, `popFirst`, `range(from, until)`, `rangeFrom`, `rangeUntil` |
| `SortedSet<T: Ord>` | set in order | the same queries, on elements |
| `PriorityQueue<T: Ord>` | binary min-heap | `push`, `pop`, `peek`, `toSortedList` |
| `PriorityQueueBy<T>` | the same, ordered by a function | built with `PriorityQueueBy::<Job>((a, b) => a.due - b.due)` |
| `Deque<T>` | ring buffer | `pushBack`, `pushFront`, `popBack`, `popFront`, `first`, `last`, `get`, `set` |
| `LruCache<K: Hash, V>` | the `capacity` most recently used entries | `get` (makes the entry the newest), `peek`, `set` (returns the evicted entry), `remove` |
| `BitSet` | set of non-negative integers | `set`, `unset`, `flip`, `get`, `count`, `nextSet`, `highest`, `union`, `intersect`, `difference` |

Each has `len()`, `isEmpty()`, `clear()` and works in `for`: sets and sorted sets give their elements, sorted maps and
caches `(key, value)` tuples (in key order, or from the newest entry), deques front to back and bit sets their bits from
the lowest. `range` and the other ranges are iterators too. Adding or removing elements while a `for` walks one of them
stops the program with a trap, as with maps. `setOf(list)` and `sortedSetOf(list)` build sets; the others start empty
(`Deque::<int>()`, `LruCache::<str, int>(100)`). They implement `Eq` and `Show` when their elements do.

These types are structs that hold lists and maps, so a copy shares the elements: after `let b = a`, `b.add(x)` also
changes `a`. `copy()` on a set gives an independent one. `PriorityQueueBy` holds a function, so it cannot be stored
in a `state`.

```quartz
import org.quartzlang.collections.*

let scores = SortedMap::<int, str>()
scores.set(120, "ada")
scores.set(95, "bo")
for e in scores.rangeFrom(100) {
    let (points, name) = e
    print("{name}: {points}")
}
let best = scores.last()          // (120, ada)
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
`writeUInt(data, offset, size, value, bigEndian = false)`, `crc32(data)`, and `floatToBits`, `floatFromBits`,
`f32ToBits`, `f32FromBits` for IEEE 754 bit patterns.

`ByteReader(data, bigEndian = false)` reads at a cursor: `readU8`, `readI8`, `readU16`, `readI16`, `readU32`,
`readI32`, `readI64`, `readF32`, `readF64`, `readBytes(n)`, `readStr(n)`, `readVarUInt()` (LEB128), `readVarInt()`
(zigzag, like protobuf's `sint64`) and `readVarInt32()` (a 32-bit two's complement value in at most 5 bytes), each
returning `Result<_, str>`; `position()`, `remaining()`, `seek(p)`. `ByteWriter(bigEndian = false)` has the matching
`write` methods, `len()` and `toBytes()`.

```quartz
import org.quartzlang.bytes.{ByteReader, ByteWriter}

let w = ByteWriter(bigEndian = true)
w.writeVarInt32(25565)
w.writeStr("hi")
let r = ByteReader(w.toBytes(), bigEndian = true)
let port = r.readVarInt32()?
```

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

## `org.quartzlang.crypto`

| Function | |
|---|---|
| `sha1(data)`, `sha256(data)`, `sha512(data)` | digests as `Bytes` (SHA-1 only for old protocols and name-based UUIDs) |
| `hmacSha256(key, data)`, `hmacSha512(key, data)` | HMAC (RFC 2104) |
| `blake2b(data, size = 64)`, `blake2bKeyed(key, data, size = 64)` | BLAKE2b, 1 to 64 bytes of digest |
| `publicKey(seed)`, `sign(seed, message)`, `verify(publicKey, message, signature)` | Ed25519 (RFC 8032) from a 32-byte seed |
| `hashPassword(password, salt, memoryKiB = 19456, iterations = 2, parallelism = 1)` | Argon2id in the PHC string format (`$argon2id$v=19$m=...`) |
| `verifyPassword(password, hash) -> Result<bool, str>` | checks a PHC string; a malformed one is an `Err` |
| `constantTimeEquals(a, b)` | compares without leaking where the bytes differ |

There is no hidden randomness: salts and seeds come from the caller, so a host that wants random ones passes them in.
Argon2's memory counts against the sandbox's quota and its time against the fuel.

## `org.quartzlang.encoding`

`base64Encode(data, urlSafe = false, padding = true)`, `base64Decode(text, urlSafe = false) -> Result<Bytes, str>`
(padding optional, anything else strict), `hexDecode(text)` (the other way is `data.hex()`).

`Uuid` is a value with `toStr()`, `toBytes()`, `version()`, `equals` and `compareTo`; `parseUuid(text)`,
`uuidFromBytes(data)`, `uuidV4(random)` from 16 bytes the caller supplies, `uuidV5(namespace, name)` and the constants
`NAMESPACE_DNS`, `NAMESPACE_URL` and `NIL_UUID`.

## `org.quartzlang.time`

Quartz has no clock: the host passes instants in. `Duration` and `Instant` are nanosecond counts (about 292 years
either way of 1970; overflowing them is a panic).

```quartz
import org.quartzlang.time

let cooldown = time.parseDuration("1h30m")?      // also 1.5s, 250ms, 2d 4h, -90s; units ns us ms s m h d w
let later = now.plus(cooldown)                    // now: an Instant from the host, e.g. time.fromEpochMillis(ms)
print("{cooldown.toStr()} {later.toStr()}")      // 1h30m 2026-11-19T16:10:00Z
let daily = time.parseCron("0 4 * * *")?
let next = daily.next(now)                        // Instant?, in UTC
```

`Duration`: `nanos(n)`, `micros`, `millis`, `seconds`, `minutes`, `hours`, `days`; `plus`, `minus`, `times`, `div`,
`negate`, `abs`, `compareTo`, `toSeconds()` and friends, `toStr()`. `Instant`: `fromEpochMillis`, `fromEpochSeconds`,
`fromEpochNanos`, `instantOf(year, month, day, hour, minute, second, nano)`, `parseInstant` (RFC 3339); `plus`,
`minus`, `since`, `isBefore`, `utc() -> DateTime`, `toStr()` (RFC 3339 in UTC).

Cron expressions are the classic five fields of Vixie cron (minute, hour, day of month, month, day of week) with `*`,
lists, ranges, steps, month and day names, Sunday as 0 or 7, and `@hourly`, `@daily`, `@weekly`, `@monthly`,
`@yearly`. As in Vixie cron, when both day fields are restricted a day matching either runs, and a field that starts
with `*` (even `*/2`) counts as unrestricted. There are no seconds and no `L`, `W`, `#` or `?`.

## `org.quartzlang.decimal`

`Decimal` is exact: `unscaled / 10^scale` with up to 18 digits and a scale of 0 to 18, enough for money. It never
rounds unless asked, and then the rounding is explicit.

```quartz
import org.quartzlang.decimal.*

let price = parseDecimal("19.99")?
let total = price.times(decimalOf(3))                         // 59.97
let each = total.div(decimalOf(7), 2, Rounding.HalfEven)      // 8.57
```

`plus`, `minus`, `times` (exact), `timesRounded(other, scale, mode)`, `div(other, scale, mode)`, `rescale(scale,
mode)`, `negate`, `abs`, `sign`, `compareTo` and `equals` (by value: 1.5 equals 1.50), `toStr()` (keeps the scale),
`toFloat()`. `Rounding` has Java's modes: `Down`, `Up`, `Ceiling`, `Floor`, `HalfUp`, `HalfDown`, `HalfEven`,
`Unnecessary`. Overflow, division by zero and needed rounding under `Unnecessary` are panics.

## `org.quartzlang.text`

| Function | |
|---|---|
| `globMatch(pattern, text, separator = "")` | `*`, `?`, `[a-z]`, `[!x]`, `\` escapes; with a separator such as `"/"`, `*` stays in one segment and `**` crosses them |
| `levenshtein(a, b)` | edit distance in characters |
| `closest(word, candidates, maxDistance = -1)` | the nearest candidate for a "did you mean" hint, or `null` |
| `formatMessage(template, args, locale = "en") -> Result<str, str>` | ICU-style messages |
| `pluralCategory(locale, n)` | `zero`, `one`, `two`, `few`, `many` or `other` |

`globMatch` is also how permission nodes match: `globMatch("essentials.*", "essentials.home")`.

Messages take their arguments as a `Map<str, Value>` and support `{name}`, `{n, number}`, `{n, plural, =0 {none} one
{# item} other {# items}}` (with `offset:`), `{g, select, female {...} other {...}}`, nesting, and ICU quoting (`''`,
`'{'`). Plural rules are CLDR's for English, Spanish, French, German, Russian and Arabic; other languages only have
`other`. Numbers print as Quartz prints them, without grouping.

## `org.quartzlang.regex`

Regular expressions in a subset of RE2 syntax, matched in time linear in the text for **every** pattern: there is no
backtracking, so a hostile pattern or text cannot stall the host. That is also why there are no backreferences and no
lookaround; both make matching non-linear, and patterns that use them are rejected with an error.

| Function | |
|---|---|
| `compileRegex(pattern) -> Result<Regex, str>` | the error names the problem and its byte position, `missing ')' at position 3` |
| `r.isMatch(text)` | a match anywhere in `text` |
| `r.fullMatch(text)` | a match of the whole of `text` |
| `r.find(text) -> Match?` | the leftmost match |
| `r.findAll(text) -> [Match]` | every match, left to right, without overlaps |
| `r.replace(text, replacement)`, `r.replaceAll(text, replacement)` | `$1` or `${1}` by number, `${name}` by name, `$0` the whole match, `$$` a dollar |
| `r.split(text, limit = 0)` | the pieces between matches; at most `limit` pieces when positive |
| `r.groupCount()` | capturing groups, not counting the whole match |
| `escapeRegex(text)` | a pattern that matches exactly `text` |
| `m.start`, `m.end`, `m.text` | byte offsets into the text (what `slice` takes) and the matched text |
| `m.group(i) -> str?`, `m.named(name) -> str?`, `m.span(i) -> (int, int)?` | null for a group that took no part; an index or name the pattern lacks panics |

```quartz
let mention = compileRegex("@(?P<user>\\w\{3,16})").unwrap()
for m in mention.findAll("hi @ada and @bob_7") {
    print(m.named("user") ?? "")                                // ada, then bob_7
}
let dates = compileRegex("(\\d+)/(\\d+)/(\\d+)").unwrap()
print(dates.replaceAll("due 3/14/2026", "$3-$1-$2"))            // due 2026-3-14
```

**Syntax.** Literals and `\` escapes of punctuation; `\n \r \t \f \v \a`, `\xHH` and `\x{H...}`; `.` (any character but
`\n`); classes `[a-z]`, `[^...]` with ranges and `\d \w \s` inside; `\d \w \s \D \W \S`; `^ $ \A \z \b \B`; groups
`(...)`, `(?:...)`, `(?P<name>...)` and `(?<name>...)`; `|`; `* + ? {n} {n,} {n,m}` and their lazy forms with a
trailing `?`; flags `(?i)`, `(?m)`, `(?s)`, combined and negated (`(?i-s)`), for the rest of the group or scoped as
`(?i:...)`. Repetition counts go up to 1000, groups nest up to 200 deep, and a pattern compiles to at most 50 000
instructions; anything bigger is a compile error, not a slow match.

**Characters.** Matching works on code points of the UTF-8 text, so `.` and `[^a]` take a whole `é` or emoji, and
classes may hold any code points (`[à-ü]`). `\d`, `\w`, `\s` and `\b` are ASCII only (`\s` is space, `\t \n \v \f
\r`), and `(?i)` folds ASCII letters only, so `(?i)é` does not match `É`; as with `lower` and `upper`, rules that
depend on a language are left out.

**Semantics.** Matches are leftmost, and among the matches that start there the first alternative and the greedier
repeat win, as in Perl, Python and RE2. Without `(?m)`, `$` matches only at the very end, as in RE2; Python's `$`
also matches before a final `\n`. `findAll`, `replaceAll` and `split` iterate as Python 3.7 and later do: an empty
match right after another match counts (`a*` on `baaa` gives `""`, `"aaa"`, `""`, while RE2 and Go skip the last one).
`split` does not add the groups to the result, unlike Python's. When a repeat's last iteration matches empty, the
groups inside it keep the values of the iteration before, as in RE2: `(a|)+b` on `aab` gives group 1 `a`, Python `""`.
`{,n}` is a literal, as in RE2; Python reads it as `{0,n}`.

**Cost.** Each call charges fuel for the instructions it simulates per character, about one unit each, and the
prefilter that jumps to a required first byte or literal prefix charges a fraction of a unit per byte it skips.
Compiled patterns are cached per sandbox (64 at most) and their memory counts against the sandbox's quota; a pattern is
compiled, and charged for it, the first time it is used after the cache lost it. A `Regex` is only its pattern text and
group names, so it can be kept in a `state`, saved and reloaded; a `Regex` built by hand around an invalid pattern
traps when used.

## `org.quartzlang.formats`

| Read | Write |
|---|---|
| `parseCsv(text, separator = ",") -> Result<[[str]], str>` | `toCsv(rows, separator = ",", crlf = true)` |
| `parseProperties(text) -> Result<Map<str, str>, str>` | `toProperties(values)` (keys sorted) |
| `parseMsgPack(data) -> Result<Value, str>` | `toMsgPack(value) -> Bytes` |

CSV follows RFC 4180; Java properties follow `Properties.load`, escapes and continuations included; MessagePack maps
onto `Value` (string keys only, no extension types). There is no CBOR yet: MessagePack covers the same tree and is the
one game backends use.

## `org.quartzlang.geometry` and `org.quartzlang.noise`

`Vec2` and `Vec3` (float components) with `plus`, `minus`, `times`, `div`, `dot`, `cross`, `length`, `distance`,
`normalize`, `lerp`, rotations, `equals` and `toStr`; `lerp`, `inverseLerp` and `smoothstep` on floats; the easing
curves of easings.net (`easeInQuad` ... `easeInOutBounce`: Quad, Cubic, Sine, Expo, Back, Elastic and Bounce, each In,
Out and InOut). `perlin(seed)` gives Ken Perlin's improved noise with `noise2(x, y)`, `noise3(x, y, z)` and `fbm3`;
the same seed gives the same values everywhere.

## `org.quartzlang.semver`

`parseSemver(text) -> Result<Semver, str>` and `Semver` with `toStr`, `compareTo`, `equals` and
`satisfies(range) -> Result<bool, str>`, with the same rules as `package.toml` (`^1.2`, `~1.4`, `>=1.0, <2`, `*`).

## `org.quartzlang.http` and `org.quartzlang.log`

`parseUrl(text) -> Result<Url, str>` splits a URL (RFC 3986) and `url.toStr()` puts it back; `percentEncode`,
`percentDecode`, `encodeQuery([(name, value)])` and `decodeQuery(text)` handle the escaping. `Request` (url, method,
headers, body, timeout) and `Response` (status, headers, body; `header(name)`, `text()`, `json()`) describe an
exchange, and `send(request) -> Result<Response, str>` runs it **through the host**: Quartz has no network, so a host
that grants HTTP binds `org.quartzlang.http.send`, and in any other host `send` returns an error.

`log.logger("shop").with("player", name).info("bought")` sends a record (level, logger name, message and the fields
as key, value pairs) to the host's sink, `org.quartzlang.log.emit`, which drops it unless the host binds it; `quartz
run` writes the records to stderr.
