#!/usr/bin/env python3
"""Copy prose from chapters/*.md into project/chapters/*.md, keeping frontmatter."""
import pathlib

ROOT = pathlib.Path(__file__).parent


def split_frontmatter(text: str):
    end = text.index("\n---\n", 4)
    return text[: end + 5], text[end + 5:]


for i in range(1, 11):
    proj = next((ROOT / "project/chapters").glob(f"chapter-{i:02d}.md"))
    src = next((ROOT / "chapters").glob(f"{i:02d}-*.md"))
    front, remainder = split_frontmatter(proj.read_text())
    lines = remainder.split("\n")
    head = "\n".join(lines[: lines.index("## Chapter Text") + 1])
    prose = "\n\n".join(src.read_text().split("\n\n")[1:]).strip("\n")
    proj.write_text(f"{front}{head}\n\n{prose}\n")
print("synced project chapters")
