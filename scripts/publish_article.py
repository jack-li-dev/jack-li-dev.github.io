#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = REPO_ROOT / "content" / "posts"
MERMAID_SOURCE_DIR = REPO_ROOT / "scripts" / "mermaid"
MERMAID_STATIC_DIR = REPO_ROOT / "static" / "mermaid"


def split_front_matter(text: str) -> tuple[str, dict[str, object], str]:
    if not text.startswith("---\n"):
        raise SystemExit("Source Markdown must start with YAML front matter.")
    end = text.find("\n---", 4)
    if end == -1:
        raise SystemExit("Source Markdown front matter is not closed.")
    raw = text[4:end].strip("\n")
    body = text[end + 4 :].lstrip("\n")
    data: dict[str, object] = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
      line = lines[i]
      if not line.strip() or line.lstrip().startswith("#"):
          i += 1
          continue
      if ": " not in line:
          i += 1
          continue
      key, value = line.split(": ", 1)
      key = key.strip()
      value = value.strip()
      if value == "":
          items = []
          i += 1
          while i < len(lines) and lines[i].startswith("  - "):
              items.append(lines[i][4:].strip())
              i += 1
          data[key] = items
          continue
      data[key] = value
      i += 1
    return raw, data, body


def yaml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    value_s = str(value)
    if value_s.startswith("[") and value_s.endswith("]"):
        return value_s
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T.+", value_s):
        return value_s
    if value_s in {"true", "false"}:
        return value_s
    if value_s.startswith('"') and value_s.endswith('"'):
        return value_s
    return '"' + value_s.replace('"', '\\"') + '"'


def dump_front_matter(data: dict[str, object]) -> str:
    order = [
        "title",
        "date",
        "lastmod",
        "draft",
        "slug",
        "description",
        "aliases",
        "categories",
        "tags",
        "translationKey",
    ]
    lines = ["---"]
    for key in order:
        if key not in data:
            continue
        value = data[key]
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {yaml_scalar(value)}")
    for key, value in data.items():
        if key in order:
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def unquote(value: object) -> str:
    s = str(value)
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "article"


def planned_publication_paths(source: Path) -> list[str]:
    """Predict the article and Mermaid paths an import may create, without mutating the repo."""
    text = source.read_text(encoding="utf-8")
    _, fm, body = split_front_matter(text)
    title = unquote(fm.get("title", source.stem))
    slug = slugify(unquote(fm.get("slug", title)))
    blocks = list(re.finditer(r"```mermaid\n(.*?)\n```", body, flags=re.S))

    paths = [f"content/posts/{slug}.en.md"]
    for idx in range(1, len(blocks) + 1):
        stem = slug if len(blocks) == 1 else f"{slug}-{idx}"
        paths.append(f"scripts/mermaid/{stem}.mmd")
    for idx in range(1, len(blocks) + 1):
        stem = slug if len(blocks) == 1 else f"{slug}-{idx}"
        paths.append(f"static/mermaid/{stem}.svg")
    return paths


def replace_mermaid_blocks(body: str, slug: str) -> tuple[str, list[Path]]:
    blocks = list(re.finditer(r"```mermaid\n(.*?)\n```", body, flags=re.S))
    if not blocks:
        return body, []

    MERMAID_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    MERMAID_STATIC_DIR.mkdir(parents=True, exist_ok=True)

    rendered = []
    new_parts = []
    cursor = 0
    for idx, match in enumerate(blocks, start=1):
        stem = slug if len(blocks) == 1 else f"{slug}-{idx}"
        mmd_path = MERMAID_SOURCE_DIR / f"{stem}.mmd"
        svg_name = f"{stem}.svg"
        mmd_path.write_text(match.group(1).rstrip() + "\n", encoding="utf-8")
        subprocess.run(
            [str(REPO_ROOT / "scripts" / "render-mermaid.sh"), str(mmd_path), svg_name],
            cwd=REPO_ROOT,
            check=True,
        )
        rendered.append(MERMAID_STATIC_DIR / svg_name)
        new_parts.append(body[cursor : match.start()])
        new_parts.append(f"[![](/mermaid/{svg_name})](/mermaid/{svg_name})")
        cursor = match.end()
    new_parts.append(body[cursor:])
    return "".join(new_parts), rendered


def replace_scalar(raw: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^({re.escape(key)}:\s*).*$", flags=re.M)
    if pattern.search(raw):
        return pattern.sub(rf"\g<1>{value}", raw)
    return raw.rstrip() + f"\n{key}: {value}"


def append_aliases(raw: str, aliases: list[str]) -> str:
    if not aliases:
        return raw

    lines = raw.splitlines()
    alias_index = next((i for i, line in enumerate(lines) if line.startswith("aliases:")), None)
    if alias_index is None:
        lines.append("aliases:")
        lines.extend(f"  - {alias_path}" for alias_path in aliases)
        return "\n".join(lines)

    existing = set()
    insert_at = alias_index + 1
    while insert_at < len(lines) and lines[insert_at].startswith("  - "):
        existing.add(lines[insert_at][4:].strip())
        insert_at += 1

    new_lines = list(lines)
    offset = 0
    for alias_path in aliases:
        if alias_path in existing:
            continue
        new_lines.insert(insert_at + offset, f"  - {alias_path}")
        offset += 1
    return "\n".join(new_lines)


def drop_hugo_removed_keys(raw: str) -> str:
    lines = []
    for line in raw.splitlines():
        if re.match(r"^lang:\s*", line):
            continue
        lines.append(line)
    return "\n".join(lines)


def update_front_matter(
    raw: str,
    date: str | None,
    aliases: list[str],
    *,
    draft: bool | None = None,
) -> str:
    updated = drop_hugo_removed_keys(raw)
    if date:
        updated = replace_scalar(updated, "date", date)
        updated = replace_scalar(updated, "lastmod", date)
    if draft is not None:
        updated = replace_scalar(updated, "draft", "true" if draft else "false")
    updated = append_aliases(updated, aliases)
    return "---\n" + updated.rstrip() + "\n---\n\n"


def audit_ordering(text: str) -> list[str]:
    issues = []
    bad_patterns = [
        "Workflow vs Subagent vs Skill",
        "Workflow vs Skill vs Subagent",
        "| Item | Subagent | Skill | Workflow |",
        "Subagent/Skill",
    ]
    for pattern in bad_patterns:
        if pattern in text:
            issues.append(f"ordering mismatch: {pattern}")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--date")
    parser.add_argument("--draft", choices=("true", "false"))
    parser.add_argument("--alias", action="append", default=[])
    parser.add_argument("--replace-slug")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    text = source.read_text(encoding="utf-8")
    raw_fm, fm, body = split_front_matter(text)

    title = unquote(fm.get("title", source.stem))
    slug = slugify(unquote(fm.get("slug", title)))

    body, rendered = replace_mermaid_blocks(body, slug)
    draft_override = None if args.draft is None else args.draft == "true"
    output = update_front_matter(
        raw_fm,
        args.date,
        args.alias,
        draft=draft_override,
    ) + body.rstrip() + "\n"

    issues = audit_ordering(output)
    if issues:
        print("Ordering audit failed:", file=os.sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=os.sys.stderr)
        raise SystemExit(1)

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    if args.replace_slug:
        old_path = CONTENT_DIR / f"{args.replace_slug}.en.md"
        if old_path.exists():
            old_path.unlink()
    target = CONTENT_DIR / f"{slug}.en.md"
    target.write_text(output, encoding="utf-8")

    print(f"source: {source}")
    print(f"target: {target}")
    print(f"url: /posts/{slug}/")
    if rendered:
        for svg in rendered:
            print(f"mermaid: {svg}")


if __name__ == "__main__":
    main()
