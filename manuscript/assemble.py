#!/usr/bin/env python3
"""Assemble manuscript.md from the front matter, chapter sources, and back matter."""
import pathlib

ROOT = pathlib.Path(__file__).parent
ORDER = [ROOT / "_front.md"]
ORDER += sorted((ROOT / "chapters").glob("*.md"))
ORDER += [ROOT / "project/matter/afterword.md",
          ROOT / "project/matter/a-note-on-history.md"]


def clean(text: str) -> str:
    text = text.strip("\n")
    while text.endswith("---"):
        text = text[:-3].rstrip("\n")
    return text


def body(path: pathlib.Path) -> str:
    text = path.read_text()
    if text.startswith("---\n"):
        text = text[text.index("\n---\n", 4) + 5:]
    return clean(text)


def matter(path: pathlib.Path) -> str:
    """Front-matter block whose `heading: true` asks for a heading line."""
    text = path.read_text()
    head, rest = text.split("\n---\n", 1)
    title = next(l.split(":", 1)[1].strip() for l in head.splitlines()
                 if l.startswith("title:"))
    want = any(l.strip() == "heading: true" for l in head.splitlines())
    text = clean(rest)
    return f"# {title}\n\n{text}" if want else text


parts = ([body(ORDER[0])] + [clean(p.read_text()) for p in ORDER[1:-2]]
         + [matter(p) for p in ORDER[-2:]])
out = "\n\n---\n\n".join(parts) + "\n"
(ROOT / "manuscript.md").write_text(out)
print(f"manuscript.md: {len(out.split()):,} words")
