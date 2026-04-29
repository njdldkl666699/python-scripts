import argparse
import re
import sys

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def iter_headings(md_text: str):
    in_fence = False
    fence_marker = ""
    for line in md_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            continue
        if in_fence:
            continue

        match = HEADING_RE.match(line)
        if not match:
            continue

        level = len(match.group(1))
        title = match.group(2).strip()
        title = re.sub(r"\s+#+\s*$", "", title).strip()
        if title:
            yield level, title


def slugify(title: str) -> str:
    slug_chars = []
    prev_dash = False
    for ch in title.strip().lower():
        if ch.isalnum():
            slug_chars.append(ch)
            prev_dash = False
        elif ch.isspace() or ch == "-":
            if not prev_dash and slug_chars:
                slug_chars.append("-")
                prev_dash = True
    if slug_chars and slug_chars[-1] == "-":
        slug_chars.pop()
    return "".join(slug_chars)


def format_toc(headings):
    lines = []
    slug_counts: dict[str, int] = {}
    for level, title in headings:
        base_slug = slugify(title)
        count = slug_counts.get(base_slug, 0)
        slug_counts[base_slug] = count + 1
        slug = f"{base_slug}-{count}" if count else base_slug
        indent = "  " * (level - 1)
        lines.append(f"{indent}- [{title}](#{slug})")
    return "\n".join(lines)


def read_input(path: str | None) -> str:
    if path and path != "-":
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return sys.stdin.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract Markdown headings (levels 1-6) as a nested list."
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Path to Markdown file. Use '-' or omit to read from stdin.",
    )
    args = parser.parse_args(argv)

    md_text = read_input(args.path)
    toc = format_toc(iter_headings(md_text))
    if toc:
        sys.stdout.write(toc)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
