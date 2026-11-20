# Checks every relative link and heading anchor in the tracked Markdown files.
import os
import re
import subprocess
import sys
from pathlib import Path

roots = sys.argv[1:] or ["."]
files = subprocess.run(["git", "ls-files", "--", *[f"{r.rstrip('/')}/*.md" if r != "." else "*.md" for r in roots]],
                       capture_output=True, text=True, check=True).stdout.split()
FENCE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.M | re.S)
CODE = re.compile(r"(`+)(?:(?!\1).)+?\1", re.S)
LINK = re.compile(r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*<?([^)\s>]*)>?(?:\s+\"[^\"]*\")?\s*\)")
HTML = re.compile(r"""\b(?:href|src)\s*=\s*["']([^"']+)["']""")
HEADING = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t#]*$", re.M)
ANCHOR = re.compile(r"""<a\s[^>]*\b(?:id|name)\s*=\s*["']([^"']+)["']""")
cache = {}


def slugs(path):
    if path not in cache:
        text = FENCE.sub("", path.read_text(encoding="utf-8"))
        found, seen = set(ANCHOR.findall(text)), {}
        for heading in HEADING.findall(text):
            heading = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
            slug = re.sub(r"[^\w\- ]", "", heading.replace("`", "").lower()).replace(" ", "-")
            count = seen.get(slug, 0)
            seen[slug] = count + 1
            found.add(slug if count == 0 else f"{slug}-{count}")
        cache[path] = found
    return cache[path]


errors = 0
for name in files:
    source = Path(name)
    text = CODE.sub("", FENCE.sub("", source.read_text(encoding="utf-8")))
    for target in LINK.findall(text) + HTML.findall(text):
        if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:|^//", target):
            continue
        path, _, anchor = target.partition("#")
        resolved = source if not path else (Path(path.lstrip("/")) if path.startswith("/") else source.parent / path)
        resolved = Path(os.path.normpath(resolved))
        if not resolved.exists():
            print(f"::error file={name}::broken link {target}")
            errors += 1
        elif anchor and resolved.suffix == ".md" and anchor not in slugs(resolved):
            print(f"::error file={name}::no heading #{anchor} in {resolved}")
            errors += 1
print(f"checked {len(files)} files, {errors} broken links")
sys.exit(1 if errors else 0)
