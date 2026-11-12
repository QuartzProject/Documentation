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

Strings interpolate any expression whose type implements `Show` between braces: `"{a + b}"`. A literal brace is
`\{`. After a colon comes a format: `[[fill]align][+][0][width][.precision][x|X|b|o]`, as in Rust and Python.

```quartz
fn main() -> int {
    let price = 3.14159
    print("[{price:.2}] [{42:>6}] [{42:06}] [{255:x}] [{"ok":-^6}]") // [3.14] [    42] [000042] [ff] [--ok--]
    return 0
}
```

Numbers align right and everything else left unless the format says otherwise. Floats round half to even on their
exact value, so the same format prints the same text on every platform.

A string between triple quotes can span lines and keeps them as written, indentation included; it still takes escapes
and interpolation. A raw string, `r"..."`, takes neither: every character is literal, which suits regular expressions
and paths. `r#"..."#` ends only at `"#`, so it can hold quotes; with more `#` (`r##"..."##`) it can hold `"#` too.
Raw strings can span lines.

```quartz
fn main() -> int {
    let digits = r"\d{4}-\d{2}"             // the regex \d{4}-\d{2}
    let quoted = r#"say "hi" to {name}"#    // quotes and braces kept as written
    let report = """
total: {2 + 3}
done"""
    print("{digits} {quoted}{report}")
    return 0
}
```

In a plain string, `"\\d{4}"` interpolates the number 4 and gives `\d4`. The compiler warns when a number literal is
interpolated right after something that looks like a regular expression, and suggests `\{` or a raw string.

## Functions

```quartz
fn greet(name: str, punctuation: str = "!") -> str {
    return "Hello, {name}{punctuation}"
}
```

Parameters can have defaults, and arguments can be named: `greet("Bo", punctuation = "?")`. A function without
`-> Type` returns nothing.

A `const` is computed by the compiler: its value may use literals, arithmetic, comparisons, `+` on strings, `as`
between numbers, other constants and constructors of structs, tuples, enum variants and fixed-size arrays, but no
function calls, lists or maps (`const Area = Side * Side` is fine, `const Now = clock()` is an error).

The compiler also warns about unused variables, parameters, imports and private functions, a `Result` that is
dropped, a local that hides another one and `match` arms that can never run; a name that starts with `_` is never
reported as unused. Each warning ends with its rule, such as `[unused-variable]`: `--rule unused-variable=ignore`
silences that rule, `=error` makes it fail the build, and `--deny-warnings` turns every warning into an error (see
[Warnings](tools.md#warnings)).

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

`Point(3.0, 4.0).length()` is `5.0`. Structs are values: assigning one copies it. Fields can have defaults, a nullable
field without one starts as `null`, and a constructor call can name its fields like any other call.
`p with { x = 0.0 }` is a copy of `p` with some fields changed; several go on one line separated by commas, or one per
line.

A function in an `impl` block without `self` belongs to the type and is called through its name, also from another
package (`Point.origin()`, `time.Duration.parse("90s")`):

```quartz
impl Point {
    fn origin() -> Point {
        return Point(0.0, 0.0)
    }
}
```

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

An enum can contain itself, directly or through structs, nullables and other enums, which is how chains, trees and
expressions are written:

```quartz
enum Expr {
    Num(int)
    Add(Expr, Expr)
    Neg(Expr)
}

fn eval(e: Expr) -> int {
    return match e {
        Num(n) => n
        Add(a, b) => eval(a) + eval(b)
        Neg(a) => -eval(a)
    }
}
```

`eval(Expr.Add(Expr.Num(2), Expr.Neg(Expr.Num(5))))` is `-3`. A struct cannot contain itself by value, since it would
have no end: keep the children in a list or a map, or make the type an enum. Recursive enums derive `Eq`, `Hash`, `Ord`
and `Show` like any other, so they can be map keys.

A generic variant takes its type arguments from what it carries, and a variant that carries nothing, such as `None`
below, takes them from its siblings in the same call:

```quartz
enum Opt<T> {
    Some(T, Opt<T>)
    None
}

fn count<T>(o: Opt<T>) -> int {
    return match o {
        Some(_, rest) => 1 + count(rest)
        None => 0
    }
}

fn main() {
    let one = Opt.Some(1, Opt.None)
    let words = Opt.Some("a", Opt.Some("b", Opt.None))
    print("{count(one)} {count(words)}")     // 1 2
}
```

Values can be as deep as memory allows. A chain of a million links is copied between calls, tasks and the `state`,
exported with the state and passed to a linked package without running out of native stack: the runtime walks such
values with a stack of its own, and what that walk needs beyond a small fixed part counts against the sandbox's memory
limit (a value too deep for it traps with "value nested too deeply for the memory limit"). Code that recurses is a
different matter: `==`, `Show` and `Encode` derived for a recursive enum are ordinary Quartz functions, so on a value
thousands of levels deep they stop with a `stack overflow` trap, like any function that recurses past the depth limit.
Walk such values with a loop:

```quartz
enum Chain {
    Link(int, Chain)
    End
}

fn build(n: int) -> Chain {
    var c = Chain.End
    for i in 0..n {
        c = Chain.Link(i, c)
    }
    return c
}

fn length(c: Chain) -> int {
    var n = 0
    var cur = c
    while cur is Link(_, rest) {
        n += 1
        cur = rest
    }
    return n
}

fn main() {
    print("{length(build(200000))}")     // 200000
}
```

Patterns nest, and also take apart tuples and structs (`Point(x, y)`, in field order); literals, ranges such as
`1..=9` and `null` fit anywhere inside, and an arm can add a guard with `if`. The compiler checks the whole tree, so
`Node(Rect(_, _), _)` is reported when nothing covers it.

```quartz
fn describe(pair: (Shape, int?)) -> str {
    return match pair {
        (Circle(r), _) if r > 10.0 => "a big circle"
        (Circle(_), null) => "a circle"
        (Circle(_), n) => "a circle, {n}"
        (Rect(w, h), _) => "{w}x{h}"
        (Empty, _) => "nothing"
    }
}
```

`A | B` matches either alternative, at any depth, and every alternative binds the same names. After an arm that takes
`null` without a guard, the arms below see the value as not null:

```quartz
fn label(n: int?) -> str {
    return match n {
        null => "none"
        0 | 1 => "few"
        k => "{k * 2}"      // k is an int here
    }
}
```

`let (a, b) = pair` and `let Point(x, y) = p` destructure where the pattern cannot fail, and so does an enum with a
single variant, the usual way to give a number a unit:

```quartz
enum Meters {
    Meters(float)
}

fn main() {
    let d = Meters.Meters(2.5)
    let Meters(m) = d
    print("{m * 2.0}")     // 5.0
}
```

`value is Pattern` tests a
pattern anywhere, and in an `if` or `while` condition (alone or joined with `&&`) its names are bound inside the
block: `if s is Circle(r) && r > 1.0 { ... }`, `while tokens[i] is Num(n) { ... }`.

## Null safety

A plain type is never `null`; `T?` may be.

```quartz
fn findUser(id: int) -> str? {
    if id == 1 {
        return "ada"
    }
    return null
}

fn firstKnown(ids: [int]) -> str {
    for id in ids {
        let name = findUser(id) ?? continue
        return name
    }
    return "nobody"
}
```

- `findUser(2) ?? "nobody"` gives a default, and `?? return`, `?? break` or `?? continue` leave instead.
- `findUser(1)?.len()` is `null` when the user is missing, otherwise the length.
- `if let user = findUser(1) { ... }` runs the block with the value when there is one, and
  `while let top = stack.pop() { ... }` repeats it while there is one. After `let` you can also write any pattern:
  `while let Route.Step(_, rest) = r { r = rest }` loops while the value matches, and
  `if let Circle(r) | Square(r) = shape { ... }` binds `r` in the block. A pattern that can never fail is an error; use
  a plain `let`.
- After an `if` whose block always leaves (`return`, `break`, `continue`) and whose condition is `x is null` or
  `x == null` (possibly joined with `||`), `x` has its non-null type for the rest of the block. This works for `let`
  bindings and parameters, and for a `var` that is not assigned again in the rest of the block.
- `x == null` and `x != null` work on any nullable, even when its type has no `Eq`, and so do `x is null` and a `null`
  arm in a `match`: on handles, floats, lists and maps as on everything else.

```quartz
fn describe(xs: [int]?, ratio: float?) -> str {
    if xs is null {
        return "no list"
    }
    let items = xs
    return match ratio {
        null => "{items.len()} items, no ratio"
        r => "{items.len()} items at {r}"
    }
}
```

`describe(null, 0.5)` is `"no list"`, `describe([1, 2], null)` is `"2 items, no ratio"` and `describe([1, 2, 3], 1.5)`
is `"3 items at 1.5"`. With `fn findPlayer(name: str) -> Player?` in a host interface, `findPlayer("ada") is null`
tests the handle the same way.

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

`Ok` and `Err` take their type from where they go: the function's result, or, without one, the other branches of the
`if` or `match`, so `let r = if n > 0 { Ok(n) } else { Err("negative") }` is a `Result<int, str>`. A function that can
fail but has nothing to return gives `Result<(), E>` and ends with `Ok(())`:

```quartz
fn save(name: str) -> Result<(), str> {
    if name.len() == 0 {
        return Err("empty name")
    }
    return Ok(())
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

Lists have `len`, `push`, `pop`, `clear` and indexing (out of range is a trap); lists of `str` have `join`, and lists
of any type with `Ord` (your own included) have `sort`, `sorted` (a sorted copy), `min` and `max`. Maps have
`len`, `get` (which returns `V?`), `set`, `has`, `remove`, `keys`, `values` and indexing. Keys are integers, `bool`,
`char`, `str`, handles, lists and tuples of them, or structs and enums that derive `Eq` and `Hash`, recursive enums
included. Keys are compared by content, so a list built elsewhere finds the entry:

```quartz
@derive(Eq, Hash)
enum Path {
    End
    Step(str, Path)
}

fn main() {
    let routes: Map<[str], int> = Map()
    routes[["home", "docs"]] = 1
    let key = ["home"]
    key.push("docs")
    print("{routes.get(key) ?? 0}")     // 1

    let seen: Map<Path, bool> = Map()
    seen[Path.Step("a", Path.Step("b", Path.End))] = true
    print("{seen.has(Path.Step("a", Path.End))}")     // false
}
```

```quartz
for k, v in scores {    // insertion order, the same in every run
    print("{k}: {v}")
}
for c in "héllo" {      // chars; invalid UTF-8 from a host reads as U+FFFD
    print("{c}")
}
```

A fixed-size array `[T; N]` is a value like a struct: its N elements are stored inline, it is copied on assignment,
and an element can only be changed through a `var`. N is a constant expression. Indexing out of range is a trap,
`len()` is N, `toList()` copies it into a list, `for` walks it, and arrays can be fields of `@repr(C)` structs, where
they have the C layout (`[i32; 4]` is `int32_t a[4]`).

```quartz
var cells: [int; 4] = [0; 4]
cells[2] = 7
let corners: [float; 2] = [1.0, 2.5]
```

`for i, x in list` gives the index too, and `for i, c in text` the byte offset. Adding or removing a key while a
`for` walks the map stops the program with a trap; changing the value of a key is fine.

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
by hand. Traits can be implemented for your types and for built-in ones (`impl Describe for int`). A trait method
with a body is a default that an `impl` may leave out, and generic types can bound their parameters
(`struct Sorted<T: Ord>`).

Four traits belong to the language: `Eq` (`==`), `Ord` (`<` and `cmp`, which returns -1, 0 or 1), `Show`
(interpolation) and `Hash` (map keys). Built-in types already have them (lists compare element by element and
lexicographically, maps show as `{k=v, k2=v2}` in insertion order); your types derive them:

```quartz
@derive(Eq, Hash, Ord, Show)
struct Version {
    major: int
    minor: int
}
```

`@derive(Decode, Encode)` reads a type from JSON, TOML or YAML and writes it as JSON or TOML (see
`org.quartzlang.data`).

Derived methods compare fields in declaration order (variants in declaration order first, then their payloads) and
show `Version(major=1, minor=2)`. `Eq`, `Ord` and `Show` can also be written by hand; `Hash` is always derived,
together with `Eq`. A type that implements `Iterator` with `fn next(self) -> (T, Self)?` (the next item and the
advanced iterator, or `null`) works in `for`, and so does a type with a method `fn iter(self)` that returns one (or a
list, map or `str`): `for x in c` loops over `c.iter()`.

## Functions as values

Function types are written `fn(A, B) -> R` (`fn(A)` returns nothing). Lambdas capture what they read, by value:

```quartz
fn map<T, U>(xs: [T], f: fn(T) -> U) -> [U] {
    var out: [U] = []
    for x in xs {
        out.push(f(x))
    }
    return out
}

fn adder(k: int) -> fn(int) -> int {
    return (x) => x + k
}
```

`map([1, 2, 3], (n) => "#{adder(3)(n)}")` gives `["#4", "#5", "#6"]`: the lambda's parameter type comes from where it is
used. A named function is a value too (`map(xs, double)`). A lambda cannot assign what it captured, and a captured
`var` cannot be reassigned afterwards. Functions cannot be stored in a `state` or passed to the host.

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
host. `every d { ... }` repeats a block, waiting `d` before each round. `at lane { ... }` runs a block in another
context the host names with a handle, such as an I/O thread, and continues where it was when the block ends; inside
it, the block can use plain values (numbers, strings, structs without lists or maps) but not the `state` or lists and
maps of the task, and it cannot `return`. A suspended task uses a few hundred bytes, so a program can keep thousands of
them.

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
| `@derive(Eq, Hash, Ord, Show, Decode, Encode)` | generated implementations of the language traits and of typed decoding |
| `@key("max-players")` | the key a field has in TOML, JSON or YAML, for `@derive(Decode, Encode)` |
| `@version(n)`, `@renamed("old")`, `@persist(per = T)` | on a `state` and its fields: its version, a field's old name, one instance per handle |
| `@on`, `@command`, `@requires` | metadata the host reads, such as event handlers and commands |
| `@property`, `@handle`, `@awaitable` | in host interfaces: properties, opaque host objects and what `wait` accepts |
