# A tour of the language

Quartz looks like a mix of Kotlin, Rust and Python: braces, no semicolons, `name: Type`, type inference for locals,
string interpolation and null safety. Every example in this chapter compiles as written.

## Values and types

| Type | Meaning |
|---|---|
| `int` | 64-bit signed integer, the type of `42` |
| `float` | 64-bit IEEE 754 float, the type of `3.14` |
| `byte` | 8-bit unsigned integer |
| `bool`, `char`, `str` | truth values, Unicode scalars, immutable UTF-8 strings |
| `Bytes` | binary data |
| `i8` to `i64`, `u8` to `u64`, `f32`, `f64` | fixed widths, for binary formats and C structs; `i64` is `int`, `f64` is `float`, `u8` is `byte` |
| `[T]`, `Map<K, V>` | lists and hash maps |
| `T?` | a `T` or `null` |
| `Result<T, E>` | a value or an error |

Integers wrap on overflow and division by zero stops the program with a trap. Floats are strict IEEE 754: the same
program gives the same bits on every platform.

```quartz
const Limit = 3

fn main() -> int {
    let fixed = 10        // immutable
    var total = 0         // mutable
    for i in 0..Limit {   // 0, 1, 2
        total += i
    }
    print("{fixed} {total} {fixed / 4} {fixed as float / 4.0}")
    return 0
}
```

Strings interpolate any expression between braces: `"{a + b}"`. A literal brace is `\{`.

## Functions

```quartz
fn greet(name: str, punctuation: str = "!") -> str {
    return "Hello, {name}{punctuation}"
}
```

Parameters can have defaults, and arguments can be named: `greet("Bo", punctuation = "?")`. A function without
`-> Type` returns nothing.

## Structs and methods

```quartz
import org.quartzlang.math.sqrt

struct Point {
    x: float
    y: float
}

impl Point {
    fn length(self) -> float {
        return sqrt(self.x * self.x + self.y * self.y)
    }
}
```

`Point(3.0, 4.0).length()` is `5.0`. Structs are values: assigning one copies it. Fields can have defaults, and a
constructor call can name its fields like any other call.

## Enums and match

```quartz
enum Shape {
    Circle(float)
    Rect(float, float)
    Empty
}

fn area(s: Shape) -> float {
    return match s {
        Circle(r) => 3.14159 * r * r
        Rect(w, h) => w * h
        Empty => 0.0
    }
}
```

`match` must cover every variant; the compiler names the missing ones. Variants are built with `Shape.Circle(1.0)`.

## Null safety

A plain type is never `null`; `T?` may be.

```quartz
fn findUser(id: int) -> str? {
    if id == 1 {
        return "ada"
    }
    return null
}
```

- `findUser(2) ?? "nobody"` gives a default.
- `findUser(1)?.len()` is `null` when the user is missing, otherwise the length.
- `if let user = findUser(1) { ... }` runs the block with the value when there is one.

## Errors

Recoverable errors are values of `Result<T, E>`; `?` returns the error early.

```quartz
enum ParseError {
    Empty
    NotANumber(str)
}

fn parseDigit(s: str) -> Result<int, ParseError> {
    if s.len() == 0 {
        return Err(ParseError.Empty)
    }
    let b = s.byteAt(0)
    if b < 48 || b > 57 {
        return Err(ParseError.NotANumber(s))
    }
    return Ok(b - 48)
}

fn sumDigits(a: str, b: str) -> Result<int, ParseError> {
    return Ok(parseDigit(a)? + parseDigit(b)?)
}
```

`panic("message")` is for bugs, not for errors: it stops the program and the host gets a trap with the message.
Nothing in Quartz can crash the host.

## Lists and maps

```quartz
var names: [str] = []
names.push("ada")
let scores: Map<str, int> = Map()
scores["ada"] = 3
let three = scores.get("ada") ?? 0
```

Lists have `len`, `push`, `pop`, `clear` and indexing (out of range is a trap); lists of `str` have `join`. Maps have
`len`, `get` (which returns `V?`), `set`, `has`, `remove` and indexing.

## Generics and traits

```quartz
trait Describe {
    fn describe(self) -> str
}

impl Describe for Point {
    fn describe(self) -> str {
        return "({self.x}, {self.y})"
    }
}

fn describeAll<T: Describe>(items: [T]) -> str {
    var parts: [str] = []
    for item in items {
        parts.push(item.describe())
    }
    return parts.join(", ")
}
```

Generic code is type checked once and specialised for each type it is used with, so it costs the same as writing it
by hand. Traits can be implemented for your types and for built-in ones (`impl Describe for int`).

## Packages and imports

A file starts with its package, a reverse-domain name: `package org.example.shop`. Names are private to their file
unless marked `internal` (visible in the package) or `pub` (visible to other packages).

```quartz
import org.example.geo.Point          // one name
import org.example.geo.{distance}     // several names
import org.example.text.*             // every public name
import org.quartzlang.data            // the package itself: data.parseJson(...), data.Value
import org.example.geo.Point as GeoPoint
```

The standard library lives under `org.quartzlang`. The core types and `panic`, `Ok` and `Err` never need an import.

## State

Local variables live for one call. Data that must survive between calls goes in a `state`, which the sandbox creates
once and passes to every function that asks for it:

```quartz
state Counter {
    total: int
    byName: Map<str, int>
}

fn count(c: Counter, who: str) -> int {
    c.total += 1
    c.byName[who] = (c.byName.get(who) ?? 0) + 1
    return c.byName[who]
}
```

The host can export every `state` as JSON, load it back, and reload a new version of the program keeping it. Fields
can be renamed with `@renamed("old")`, and `@version(n)` with a `migrate` function upgrades old data. `@persist(per =
Player)` keeps one instance per host handle, such as one per player.

## Coroutines

A `suspend fn` can pause with `wait` until the host resumes it, without blocking anything:

```quartz
suspend fn countdown(n: int) -> int {
    var left = n
    every 1.ticks {
        left -= 1
        if left == 0 {
            break
        }
    }
    return n
}
```

`wait x` pauses until the host resumes the task with the value `x` produces; what can be waited on is declared by the
host. `every d { ... }` repeats a block, waiting `d` before each round. A suspended task uses a few hundred bytes, so a
program can keep thousands of them.

Memory in Quartz is managed by arenas, without a garbage collector: everything a call or a task allocates is freed at
once when it ends. A long loop that waits should allocate inside `scope { ... }`, which frees its allocations at the end
of the block; `every` does this for each round, and the compiler warns about loops that do not.

## Attributes

| Attribute | Meaning |
|---|---|
| `@test` | a test for `quartz test` |
| `@deprecated("use x")` | callers get a warning |
| `@inline`, `@noinline` | inlining hints for the native tier |
| `@repr(C)` | a struct with the C layout, passed to the host as a C struct |
| `@on`, `@command`, `@requires` | metadata the host reads, such as event handlers and commands |
| `@property`, `@handle`, `@awaitable` | in host interfaces: properties, opaque host objects and what `wait` accepts |
