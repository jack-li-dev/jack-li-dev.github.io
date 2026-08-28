#!/usr/bin/env python3
"""Deterministic release helpers for jack-li.me publication automation."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from scripts.publish_article import (
        planned_publication_paths,
        split_front_matter,
        unquote,
        update_front_matter,
    )
except ModuleNotFoundError:  # Direct execution: python3 scripts/blog_release.py
    from publish_article import planned_publication_paths, split_front_matter, unquote, update_front_matter


EASTERN = ZoneInfo("America/New_York")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE_ROOT = REPO_ROOT / "drafts" / "prepublish"
AUTOPUBLISH_FLAG = REPO_ROOT / ".bin" / "autopublish.enabled"
RELEASE_LOCK = REPO_ROOT / ".bin" / "blog-release.lock"
EXPECTED_REMOTE_URL = "git@github.com:jack-li-dev/jack-li-dev.github.io.git"
EXPECTED_BRANCH = "main"
EXPECTED_HUGO_VERSION = "v0.164.0+extended"
PRODUCTION_NAME = "Jack Li"
PRODUCTION_EMAIL = "16163394+jack-li-dev@users.noreply.github.com"


class ReleaseError(RuntimeError):
    """Raised when a release guardrail rejects an operation."""


def autopublish_is_enabled(flag_path: Path = AUTOPUBLISH_FLAG) -> bool:
    """Return whether the repository-local scheduled-publication kill switch is ON."""
    return flag_path.is_file()


@contextmanager
def release_lock(lock_path: Path = RELEASE_LOCK):
    """Serialize all mutating release transactions inside WSL."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ReleaseError("another release transaction is already running") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


REQUIRED_PREPUBLISH_GATES = (
    "publish_value",
    "canonical_alignment",
    "primary_source_factcheck",
    "runtime_verification",
    "bilingual_alignment",
    "links",
    "hugo_build",
    "hugo_version_pin",
    "render",
    "rights_security",
    "creation_proof",
)

WIKILINK_RE = re.compile(r"\[\[([^\]\n]+)\]\]")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
FENCE_RE = re.compile(r"^[ \t]{0,3}```")


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reader_facing_wikilink_residues(text: str) -> list[tuple[int, str]]:
    """Return Obsidian Wiki links that leaked into rendered Markdown prose."""
    residues: list[tuple[int, str]] = []
    in_fence = False
    for line_no, line in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        scan_line = INLINE_CODE_RE.sub(lambda match: " " * (match.end() - match.start()), line)
        residues.extend((line_no, match.group(0)) for match in WIKILINK_RE.finditer(scan_line))
    return residues


def sha256_package(package: Path) -> str:
    """Hash the immutable prepublish package tree, excluding mutable release state."""
    digest = hashlib.sha256()
    excluded = {"release.json", ".release.json.tmp"}
    for path in sorted(package.rglob("*"), key=lambda item: item.relative_to(package).as_posix()):
        if path.is_symlink():
            raise ReleaseError(f"release package must not contain symlinks: {path}")
        if not path.is_file() or path.name in excluded:
            continue
        relative = path.relative_to(package).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def parse_eastern_local_time(value: str) -> datetime:
    """Interpret a wall-clock timestamp in America/New_York using real DST rules."""
    try:
        naive = datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ReleaseError("publish time must use YYYY-MM-DD HH:MM") from exc
    fold0 = naive.replace(tzinfo=EASTERN, fold=0)
    fold1 = naive.replace(tzinfo=EASTERN, fold=1)

    def roundtrips(candidate: datetime) -> bool:
        back = candidate.astimezone(timezone.utc).astimezone(EASTERN)
        return back.replace(tzinfo=None) == naive

    valid0 = roundtrips(fold0)
    valid1 = roundtrips(fold1)
    if not valid0 and not valid1:
        raise ReleaseError(
            f"America/New_York local time does not exist because of DST transition: {value}"
        )
    if valid0 and valid1 and fold0.utcoffset() != fold1.utcoffset():
        raise ReleaseError(
            f"America/New_York local time is ambiguous because of DST transition: {value}"
        )
    return fold0 if valid0 else fold1


def _canonical_root(repository: str) -> Path:
    """Resolve a known read-only Canonical repository used by release freshness checks."""
    if repository != "Knowledge":
        raise ReleaseError(f"unsupported Canonical repository: {repository}")
    return Path(os.environ.get("KNOWLEDGE_REPO", "/home/dev/github/Knowledge")).expanduser().resolve()


def _validate_canonical_reference(reference: dict[str, str]) -> None:
    """Fail closed when the current Canonical file no longer matches the frozen SHA."""
    repository = reference.get("repository", "")
    relative = reference.get("path", "")
    expected = reference.get("sha256", "")
    if not repository or not relative or not expected:
        raise ReleaseError("Canonical reference must include repository, path, and sha256")

    root = _canonical_root(repository)
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ReleaseError(f"Canonical path escapes repository root: {relative}") from exc
    if not target.is_file():
        raise ReleaseError(f"Canonical file not found: {target}")

    try:
        actual = sha256_file(target)
    except OSError as exc:
        raise ReleaseError(f"Canonical file is not readable: {target}: {exc}") from exc
    if actual != expected:
        raise ReleaseError(
            f"Canonical SHA-256 changed for {repository}/{relative}: expected {expected}, got {actual}"
        )


def eastern_week_key(value: datetime) -> tuple[int, int]:
    """Return the ISO year/week for a timestamp after conversion to New York time."""
    local = value.astimezone(EASTERN)
    iso = local.isocalendar()
    return iso.year, iso.week


def has_publication_in_week(articles: list[dict[str, str]], when: datetime) -> bool:
    """Return whether any published article consumes the Eastern week containing ``when``."""
    target_week = eastern_week_key(when)
    for article in articles:
        raw_date = article.get("date")
        if not raw_date:
            continue
        try:
            published = datetime.fromisoformat(raw_date)
        except ValueError as exc:
            raise ReleaseError(f"invalid publication date in {article.get('path', '<unknown>')}: {raw_date}") from exc
        if published.tzinfo is None:
            raise ReleaseError(f"publication date lacks timezone in {article.get('path', '<unknown>')}")
        if eastern_week_key(published) == target_week:
            return True
    return False


def _validate_frozen_release(package: Path, release: dict[str, object]) -> None:
    """Validate immutable approval content independently from transaction state."""
    if release.get("schema_version") != 1:
        raise ReleaseError("unsupported release schema_version")
    if release.get("approved_by") != "human":
        raise ReleaseError("release must be explicitly approved by the Human")
    if release.get("timezone") != "America/New_York":
        raise ReleaseError("release timezone must be America/New_York")
    article_name = str(release.get("article", ""))
    if not article_name or Path(article_name).name != article_name:
        raise ReleaseError("release article must be a package-local filename")
    article_path = package / article_name
    if not article_path.is_file():
        raise ReleaseError(f"approved article not found: {article_path}")

    expected = str(release.get("article_sha256", ""))
    actual = sha256_file(article_path)
    if not expected or actual != expected:
        raise ReleaseError(
            f"approved article SHA-256 changed: expected {expected or '<missing>'}, got {actual}"
        )

    expected_package = str(release.get("package_sha256", ""))
    if not expected_package:
        raise ReleaseError("approved release is missing package SHA-256")
    actual_package = sha256_package(package)
    if actual_package != expected_package:
        raise ReleaseError(
            f"approved package SHA-256 changed: expected {expected_package}, got {actual_package}"
        )

    canonical = release.get("canonical")
    if canonical is not None:
        if not isinstance(canonical, dict):
            raise ReleaseError("release canonical field must be an object")
        _validate_canonical_reference({str(key): str(value) for key, value in canonical.items()})


def validate_approved_release(package: Path) -> dict[str, object]:
    """Load release.json and reject any mutation of the Human-approved release package."""
    release_path = package / "release.json"
    if not release_path.is_file():
        raise ReleaseError(f"release metadata not found: {release_path}")
    try:
        release = json.loads(release_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReleaseError("release.json is not valid JSON") from exc

    if release.get("state") != "approved":
        raise ReleaseError("release state must be approved")
    _validate_frozen_release(package, release)

    try:
        publish_at = datetime.fromisoformat(str(release["publish_at"]))
    except (KeyError, ValueError) as exc:
        raise ReleaseError("release publish_at must be a valid ISO-8601 timestamp") from exc
    if publish_at.tzinfo is None:
        raise ReleaseError("release publish_at must include an offset")

    return release


def _manifest_scalar(text: str, key: str) -> str | None:
    """Read one top-level scalar from the constrained publication manifest."""
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+?)\s*$", text)
    return match.group(1).strip('"\'') if match else None


def _manifest_section_scalar(text: str, section: str, key: str) -> str | None:
    """Read one two-space-indented scalar from a named manifest section."""
    lines = text.splitlines()
    in_section = False
    for line in lines:
        if re.fullmatch(rf"{re.escape(section)}:\s*", line):
            in_section = True
            continue
        if in_section and line and not line.startswith(" "):
            break
        if in_section:
            match = re.fullmatch(rf"  {re.escape(key)}:\s*(.+?)\s*", line)
            if match:
                return match.group(1).strip('"\'')
    return None


def _manifest_scalar_section(text: str, section: str) -> dict[str, str]:
    """Read simple two-space-indented scalar keys from one manifest section."""
    values: dict[str, str] = {}
    lines = text.splitlines()
    in_section = False
    for line in lines:
        if re.fullmatch(rf"{re.escape(section)}:\s*", line):
            in_section = True
            continue
        if in_section and line and not line.startswith(" "):
            break
        if not in_section:
            continue
        match = re.fullmatch(r"  ([a-zA-Z0-9_-]+):\s*(.+?)\s*", line)
        if match:
            values[match.group(1)] = match.group(2).strip('"\'')
    return values


def _manifest_blockers(text: str) -> list[dict[str, str]]:
    """Read the constrained blocker list from the publication manifest."""
    blockers: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_section = False

    for line in text.splitlines():
        if line == "blockers:":
            in_section = True
            continue
        if in_section and line and not line.startswith(" "):
            break
        if not in_section:
            continue

        item = re.fullmatch(r"  - id:\s*(.+?)\s*", line)
        if item:
            if current is not None:
                blockers.append(current)
            current = {"id": item.group(1).strip('"\'')}
            continue

        field = re.fullmatch(r"    ([a-zA-Z0-9_-]+):\s*(.+?)\s*", line)
        if field and current is not None:
            current[field.group(1)] = field.group(2).strip('"\'')

    if current is not None:
        blockers.append(current)
    return blockers


def validate_prepublish_package(package: Path) -> dict[str, object]:
    """Validate machine-owned gates before a Human can approve a release package."""
    manifest_path = package / "manifest.yaml"
    article_path = package / "article.en.md"
    if not manifest_path.is_file():
        raise ReleaseError(f"manifest not found: {manifest_path}")
    if not article_path.is_file():
        raise ReleaseError(f"English article not found: {article_path}")

    text = manifest_path.read_text(encoding="utf-8")
    state = _manifest_scalar(text, "state")
    if state != "ready-for-human-review":
        raise ReleaseError("manifest state must be ready-for-human-review")

    doc_id = _manifest_scalar(text, "content_id")
    slug = _manifest_section_scalar(text, "publication", "slug")
    expected_hash = _manifest_section_scalar(text, "publication", "article_en_sha256")
    if not doc_id or not slug or not expected_hash:
        raise ReleaseError("manifest is missing content_id, publication.slug, or article_en_sha256")

    actual_hash = sha256_file(article_path)
    if actual_hash != expected_hash:
        raise ReleaseError(
            f"prepublish article SHA-256 does not match manifest: expected {expected_hash}, got {actual_hash}"
        )

    wikilink_residues = _reader_facing_wikilink_residues(article_path.read_text(encoding="utf-8"))
    if wikilink_residues:
        line_no, residue = wikilink_residues[0]
        raise ReleaseError(
            "Obsidian Wiki link residue is not publishable Markdown: "
            f"article.en.md:{line_no}: {residue}"
        )

    gates = _manifest_scalar_section(text, "gates")
    for gate in REQUIRED_PREPUBLISH_GATES:
        status = gates.get(gate)
        if not status or not status.startswith("pass"):
            raise ReleaseError(f"machine gate is not PASS: {gate}={status or '<missing>'}")

    for gate, status in gates.items():
        if gate in {"human_mastery", "human_final"}:
            continue
        if not status.startswith("pass"):
            raise ReleaseError(f"machine gate is not PASS: {gate}={status}")

    # Human-only release blockers are resolved by the explicit approval command.
    # Any other blocker means the machine review is internally inconsistent and
    # must stop before Human approval can be frozen.
    for blocker in _manifest_blockers(text):
        blocker_id = blocker.get("id", "<missing-id>")
        status = blocker.get("status", "<missing-status>")
        if blocker_id == "human-release-gates" and status == "pending-human":
            continue
        raise ReleaseError(f"machine blocker remains: {blocker_id}={status}")

    canonical_repository = _manifest_section_scalar(text, "canonical", "repository")
    canonical_path = _manifest_section_scalar(text, "canonical", "path")
    canonical_sha256 = _manifest_section_scalar(text, "canonical", "sha256")
    canonical_values = [canonical_repository, canonical_path, canonical_sha256]
    if any(canonical_values) and not all(canonical_values):
        raise ReleaseError("manifest Canonical reference is incomplete")

    canonical: dict[str, str] | None = None
    if all(canonical_values):
        canonical = {
            "repository": str(canonical_repository),
            "path": str(canonical_path),
            "sha256": str(canonical_sha256),
        }
        _validate_canonical_reference(canonical)

    result: dict[str, object] = {
        "doc_id": doc_id,
        "slug": slug,
        "article": "article.en.md",
        "article_sha256": actual_hash,
    }
    if canonical is not None:
        result["canonical"] = canonical
    return result


def approve_release_package(
    package: Path,
    *,
    publish_at_local: str,
    approved_at: datetime | None = None,
    auto_eligible: bool = True,
) -> dict[str, object]:
    """Freeze one reviewed package for manual or scheduled production publication."""
    checked = validate_prepublish_package(package)
    publish_at = parse_eastern_local_time(publish_at_local)
    approved_at_value = (approved_at or datetime.now(tz=EASTERN)).astimezone(EASTERN)

    release: dict[str, object] = {
        "schema_version": 1,
        "state": "approved",
        "article": checked["article"],
        "article_sha256": checked["article_sha256"],
        "package_sha256": sha256_package(package),
        "slug": checked["slug"],
        "doc_id": checked["doc_id"],
        "publish_at": publish_at.isoformat(),
        "timezone": "America/New_York",
        "approved_by": "human",
        "approved_at": approved_at_value.isoformat(),
        "human_gates": ["mastery", "final-editorial-approval"],
        "auto_eligible": auto_eligible,
        "target_file": f"content/posts/{checked['slug']}.en.md",
        "production_commit": None,
        "published_at": None,
    }
    if "canonical" in checked:
        release["canonical"] = checked["canonical"]
    (package / "release.json").write_text(
        json.dumps(release, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return release


def due_release_packages(queue_root: Path, *, now: datetime | None = None) -> list[tuple[Path, dict[str, object]]]:
    """Return valid approved packages whose Eastern not-before time has arrived."""
    current = (now or datetime.now(tz=EASTERN)).astimezone(EASTERN)
    due: list[tuple[Path, dict[str, object], datetime]] = []
    if not queue_root.is_dir():
        return []

    for release_path in sorted(queue_root.glob("*/release.json")):
        try:
            raw = json.loads(release_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ReleaseError(f"invalid JSON: {release_path}") from exc
        if raw.get("state") != "approved":
            continue
        if raw.get("auto_eligible") is not True:
            continue
        package = release_path.parent
        release = validate_approved_release(package)
        publish_at = datetime.fromisoformat(str(release["publish_at"]))
        if publish_at.astimezone(EASTERN) <= current:
            due.append((package, release, publish_at))

    due.sort(key=lambda item: item[2])
    return [(package, release) for package, release, _ in due]


def select_articles(
    articles: list[dict[str, str]],
    *,
    filenames: list[str],
    publication_dates: list[str],
) -> list[dict[str, str]]:
    """Select articles by basename or America/New_York publication date."""
    filename_set = set(filenames)
    date_set = set(publication_dates)
    selected: list[dict[str, str]] = []

    for article in articles:
        path = article["path"]
        matched = Path(path).name in filename_set
        if date_set and article.get("date"):
            try:
                published = datetime.fromisoformat(article["date"])
            except ValueError as exc:
                raise ReleaseError(f"invalid publication date in {path}: {article['date']}") from exc
            if published.tzinfo is None:
                raise ReleaseError(f"publication date lacks timezone in {path}")
            matched = matched or published.astimezone(EASTERN).date().isoformat() in date_set
        if matched:
            selected.append(article)

    return selected


def purge_tail_base(commits: list[dict[str, object]], target_files: set[str]) -> str:
    """Return the reset base only when target publication commits form the exact HEAD suffix."""
    if not target_files:
        raise ReleaseError("purge requires at least one target file")

    remaining = set(target_files)
    for commit in commits:
        publication_file = commit.get("publication_file")
        if publication_file in remaining:
            remaining.remove(str(publication_file))
            if not remaining:
                parent = commit.get("parent")
                if not parent:
                    raise ReleaseError("cannot purge the repository root commit")
                return str(parent)
            continue

        raise ReleaseError(
            "history purge is allowed only when selected publication commits are the contiguous tail of HEAD"
        )

    raise ReleaseError("selected publication commits were not found at the contiguous tail of HEAD")


def select_publication_commits(
    commits: list[dict[str, object]],
    *,
    filenames: list[str],
    publication_dates: list[str],
) -> list[dict[str, object]]:
    """Select publication commits by publication-file basename or Eastern publication date."""
    filename_set = set(filenames)
    date_set = set(publication_dates)
    selected: list[dict[str, object]] = []

    for commit in commits:
        publication_file = commit.get("publication_file")
        if not publication_file:
            continue
        matched = Path(str(publication_file)).name in filename_set
        publication_date = commit.get("publication_date")
        if date_set and publication_date:
            try:
                published = datetime.fromisoformat(str(publication_date))
            except ValueError as exc:
                raise ReleaseError(f"invalid Publication-Date trailer: {publication_date}") from exc
            if published.tzinfo is None:
                raise ReleaseError(f"Publication-Date trailer lacks timezone: {publication_date}")
            matched = matched or published.astimezone(EASTERN).date().isoformat() in date_set
        if matched:
            selected.append(commit)

    return selected


def build_publication_commit_message(
    *,
    title: str,
    doc_id: str,
    slug: str,
    target_path: str,
    publish_at: str,
    article_sha256: str,
    mode: str,
    changed_paths: list[str] | None = None,
) -> str:
    """Create a human-readable commit subject plus machine-readable publication trailers."""
    if mode not in {"manual", "auto"}:
        raise ReleaseError("publication mode must be manual or auto")
    message = (
        f"post: publish {title}\n\n"
        f"Publication-Doc-ID: {doc_id}\n"
        f"Publication-Slug: {slug}\n"
        f"Publication-File: {target_path}\n"
        f"Publication-Date: {publish_at}\n"
        f"Publication-Content-SHA256: {article_sha256}\n"
        f"Publication-Mode: {mode}\n"
    )
    for path in changed_paths or [target_path]:
        message += f"Publication-Path: {path}\n"
    return message


def build_withdraw_commit_message(paths: list[str], *, withdrawn_at: str) -> str:
    """Create a safe-withdraw commit message with one trailer per removed article."""
    if not paths:
        raise ReleaseError("withdraw requires at least one article")
    noun = "article" if len(paths) == 1 else "articles"
    lines = [f"post: withdraw {len(paths)} {noun}", ""]
    lines.extend(f"Withdrawn-File: {path}" for path in paths)
    lines.append(f"Withdrawn-Date: {withdrawn_at}")
    lines.append("Withdrawn-Mode: safe")
    return "\n".join(lines) + "\n"


def publication_asset_is_referenced(
    repo_root: Path,
    asset_path: str,
    *,
    excluding: set[str],
) -> bool:
    """Return whether a generated public asset is referenced by any article that will remain published."""
    asset = Path(asset_path)
    if asset.parts[:2] != ("static", "mermaid"):
        return False
    needle = f"/mermaid/{asset.name}"
    for article in (repo_root / "content" / "posts").glob("*.md"):
        relative = article.relative_to(repo_root).as_posix()
        if relative in excluding:
            continue
        if needle in article.read_text(encoding="utf-8"):
            return True
    return False


def article_mermaid_paths(repo_root: Path, article_path: str) -> set[str]:
    """Discover Mermaid SVG/MMD pairs referenced by one article, including legacy posts."""
    root = repo_root.resolve()
    article = (root / article_path).resolve()
    try:
        article.relative_to(root)
    except ValueError as exc:
        raise ReleaseError(f"article path escapes repository: {article_path}") from exc
    if not article.is_file():
        return set()

    names = set(
        re.findall(
            r"/mermaid/([A-Za-z0-9._-]+\.svg)",
            article.read_text(encoding="utf-8"),
        )
    )
    paths: set[str] = set()
    for name in names:
        paths.add(f"static/mermaid/{name}")
        paths.add(f"scripts/mermaid/{Path(name).stem}.mmd")
    return paths


def _run(
    args: list[str],
    *,
    cwd: Path = REPO_ROOT,
    check: bool = True,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run one bounded local command and return decoded text output."""
    return subprocess.run(
        args,
        cwd=cwd,
        check=check,
        text=True,
        capture_output=capture,
    )


def _git(*args: str, cwd: Path = REPO_ROOT, check: bool = True) -> str:
    """Run git and return stdout without trailing whitespace."""
    return _run(["git", *args], cwd=cwd, check=check).stdout.strip()


def _queue_root(value: str | None = None) -> Path:
    """Resolve the private release queue root from CLI, environment, or repository default."""
    raw = value or os.environ.get("BLOG_RELEASE_QUEUE")
    return Path(raw).expanduser().resolve() if raw else DEFAULT_QUEUE_ROOT.resolve()


def _resolve_package(value: str, queue_root: Path) -> Path:
    """Resolve a package and require it to live under the configured private queue."""
    package = Path(value).expanduser().resolve()
    try:
        package.relative_to(queue_root)
    except ValueError as exc:
        raise ReleaseError(f"package must live under queue root {queue_root}: {package}") from exc
    if not package.is_dir():
        raise ReleaseError(f"package directory not found: {package}")
    return package


def _ensure_identity() -> None:
    """Set and verify the repository-local production commit identity."""
    _git("config", "--local", "user.name", PRODUCTION_NAME)
    _git("config", "--local", "user.email", PRODUCTION_EMAIL)
    if _git("config", "user.name") != PRODUCTION_NAME:
        raise ReleaseError("production git user.name mismatch")
    if _git("config", "user.email") != PRODUCTION_EMAIL:
        raise ReleaseError("production git user.email mismatch")


def _working_tree_changes() -> list[str]:
    """Return tracked/untracked non-ignored working-tree entries."""
    output = _git("status", "--porcelain=v1", "--untracked-files=normal")
    return [line for line in output.splitlines() if line.strip()]


def _ensure_clean_main_and_fetch() -> tuple[str, str]:
    """Require a clean production main that exactly matches origin/main."""
    changes = _working_tree_changes()
    if changes:
        raise ReleaseError("production working tree is not clean:\n" + "\n".join(changes))
    if _git("branch", "--show-current") != EXPECTED_BRANCH:
        raise ReleaseError("production publication requires branch main")
    remote_url = _git("remote", "get-url", "origin")
    if remote_url != EXPECTED_REMOTE_URL:
        raise ReleaseError(f"origin URL mismatch: {remote_url}")

    _ensure_identity()
    _git("fetch", "origin", EXPECTED_BRANCH)
    local = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", f"origin/{EXPECTED_BRANCH}")
    if local != remote:
        raise ReleaseError(
            f"local main must exactly match origin/main before a new transaction: local={local} remote={remote}"
        )
    return local, remote


def _resolve_hugo() -> Path:
    """Find the preinstalled pinned Hugo Extended binary; never download at publish time."""
    candidates = [REPO_ROOT / ".bin" / "hugo"]
    system_hugo = shutil.which("hugo")
    if system_hugo:
        candidates.append(Path(system_hugo))
    for candidate in candidates:
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            continue
        version = _run([str(candidate), "version"]).stdout.strip()
        if version.startswith(EXPECTED_HUGO_VERSION):
            return candidate
    raise ReleaseError(
        f"verified Hugo Extended 0.164.0 not found; expected version prefix {EXPECTED_HUGO_VERSION}"
    )


def _build_site(hugo: Path) -> None:
    """Run a clean production-style Hugo build into an ignored temporary directory."""
    bin_dir = REPO_ROOT / ".bin"
    bin_dir.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="release-build-", dir=bin_dir) as destination:
        _run(
            [
                str(hugo),
                "--gc",
                "--minify",
                "--baseURL",
                "https://jack-li.me/",
                "--destination",
                destination,
            ],
            capture=True,
        )


def _read_article_metadata(path: Path) -> dict[str, str]:
    """Read the small front-matter subset needed by release and withdrawal logic."""
    text = path.read_text(encoding="utf-8")
    _, fm, _ = split_front_matter(text)
    return {key: unquote(value) for key, value in fm.items() if isinstance(value, str)}


def load_published_articles(repo_root: Path = REPO_ROOT) -> list[dict[str, str]]:
    """Return current non-draft article paths and their publication dates."""
    articles: list[dict[str, str]] = []
    for path in sorted((repo_root / "content" / "posts").glob("*.md")):
        metadata = _read_article_metadata(path)
        if metadata.get("draft", "false").lower() == "true":
            continue
        articles.append(
            {
                "path": path.relative_to(repo_root).as_posix(),
                "date": metadata.get("date", ""),
                "slug": metadata.get("slug", path.stem),
                "title": metadata.get("title", path.stem),
            }
        )
    return articles


def _publication_commit_for_doc_id(doc_id: str) -> str | None:
    """Find an existing publication commit for one stable DOC-ID on current main."""
    result = _run(
        [
            "git",
            "log",
            "--fixed-strings",
            f"--grep=Publication-Doc-ID: {doc_id}",
            "-n",
            "1",
            "--format=%H",
        ],
        check=True,
    ).stdout.strip()
    return result or None


def _write_release(package: Path, release: dict[str, object]) -> None:
    """Atomically replace ignored release.json."""
    target = package / "release.json"
    temp = package / ".release.json.tmp"
    temp.write_text(json.dumps(release, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(target)


def _verify_generated_target(path: Path, actual_publish_at: datetime) -> None:
    """Verify production front matter after the deterministic import step."""
    metadata = _read_article_metadata(path)
    expected = actual_publish_at.isoformat()
    if metadata.get("draft") != "false":
        raise ReleaseError("generated production article must have draft: false")
    if metadata.get("date") != expected or metadata.get("lastmod") != expected:
        raise ReleaseError("generated production date/lastmod do not match the actual Eastern publication time")


def _set_production_timestamp(path: Path, actual_publish_at: datetime) -> None:
    """Update only production date/lastmod/draft while preserving the already-approved body."""
    text = path.read_text(encoding="utf-8")
    raw_fm, _, body = split_front_matter(text)
    output = update_front_matter(
        raw_fm,
        actual_publish_at.isoformat(),
        [],
        draft=False,
    ) + body.rstrip() + "\n"
    path.write_text(output, encoding="utf-8")
    _verify_generated_target(path, actual_publish_at)


def _publication_message(
    release: dict[str, object],
    *,
    target: Path,
    target_path: str,
    actual_publish_at: datetime,
    production_hash: str,
    changed_paths: list[str],
    mode: str,
) -> str:
    """Build one complete publication commit message for initial or amended pending commit."""
    title = _read_article_metadata(target).get("title", str(release["slug"]))
    message = build_publication_commit_message(
        title=title,
        doc_id=str(release["doc_id"]),
        slug=str(release["slug"]),
        target_path=target_path,
        publish_at=actual_publish_at.isoformat(),
        article_sha256=production_hash,
        mode=mode,
        changed_paths=changed_paths,
    )
    message += f"Publication-Approved-SHA256: {release['article_sha256']}\n"
    message += f"Publication-Scheduled-At: {release['publish_at']}\n"
    return message


def _changed_paths_after_import(target_path: str) -> list[str]:
    """Return import-created paths and reject changes outside the one-article publication envelope."""
    entries = _working_tree_changes()
    paths: list[str] = []
    for entry in entries:
        path = entry[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        allowed = (
            path == target_path
            or path.startswith("scripts/mermaid/")
            or path.startswith("static/mermaid/")
        )
        if not allowed:
            raise ReleaseError(f"publication import changed an unexpected path: {entry}")
        paths.append(path)
    if target_path not in paths:
        raise ReleaseError(f"publication import did not create expected article: {target_path}")
    return sorted(set(paths))


def _ensure_planned_paths_absent(paths: list[str]) -> None:
    """Prevent one article import from overwriting any pre-existing public or source asset."""
    for relative in paths:
        target = (REPO_ROOT / relative).resolve()
        try:
            target.relative_to(REPO_ROOT.resolve())
        except ValueError as exc:
            raise ReleaseError(f"planned publication path escapes repository: {relative}") from exc
        if target.exists():
            raise ReleaseError(f"planned publication path already exists: {relative}")


def _rollback_uncommitted_publication(paths: list[str]) -> None:
    """Remove only files known to be newly created by the current clean-start transaction."""
    if paths:
        _run(["git", "restore", "--staged", "--", *paths], check=False)
    for relative in paths:
        target = (REPO_ROOT / relative).resolve()
        try:
            target.relative_to(REPO_ROOT.resolve())
        except ValueError:
            continue
        if target.is_file() or target.is_symlink():
            target.unlink()


def _actual_eastern_now() -> datetime:
    """Return current production time with seconds, no microseconds."""
    return datetime.now(tz=EASTERN).replace(microsecond=0)


def _retry_push_pending(package: Path, release: dict[str, object]) -> bool:
    """Retry one pending publication transaction, amending its timestamp before a real re-push."""
    commit = str(release.get("production_commit") or "")
    if release.get("state") != "push-pending" or not commit:
        return False
    if _working_tree_changes():
        raise ReleaseError("cannot retry pending publication with a dirty working tree")
    if _git("branch", "--show-current") != EXPECTED_BRANCH:
        raise ReleaseError("pending publication retry requires branch main")
    if _git("remote", "get-url", "origin") != EXPECTED_REMOTE_URL:
        raise ReleaseError("pending publication retry origin URL mismatch")
    _ensure_identity()
    _git("fetch", "origin", EXPECTED_BRANCH)
    remote = _git("rev-parse", f"origin/{EXPECTED_BRANCH}")
    if remote == commit:
        release["state"] = "published"
        release["published_at"] = release.get("attempted_at")
        _write_release(package, release)
        return True
    local = _git("rev-parse", "HEAD")
    parent = str(release.get("production_parent") or _git("rev-parse", f"{commit}^"))
    if local != commit or remote != parent:
        raise ReleaseError(
            "pending publication cannot be retried automatically because local/remote history changed"
        )

    try:
        _validate_frozen_release(package, release)
    except ReleaseError as exc:
        _git("reset", "--hard", remote)
        release["state"] = "stale"
        release["stale_reason"] = str(exc)
        release["production_commit"] = None
        release["attempted_at"] = None
        _write_release(package, release)
        raise ReleaseError(
            "pending publication became stale before reaching production; local publication commit was discarded"
        ) from exc

    target_path = str(release.get("target_file") or "")
    if not target_path:
        raise ReleaseError("pending publication is missing target_file")
    target = REPO_ROOT / target_path
    if not target.is_file():
        raise ReleaseError(f"pending production article not found: {target_path}")

    changed_paths = [str(path) for path in release.get("publication_paths", [])]
    if not changed_paths:
        changed_paths = [target_path]
    mode = str(release.get("publication_mode") or "auto")
    actual_publish_at = _actual_eastern_now()

    try:
        _set_production_timestamp(target, actual_publish_at)
        _git("diff", "--check")
        _build_site(_resolve_hugo())
        production_hash = sha256_file(target)
        _git("add", "--", target_path)
        message = _publication_message(
            release,
            target=target,
            target_path=target_path,
            actual_publish_at=actual_publish_at,
            production_hash=production_hash,
            changed_paths=changed_paths,
            mode=mode,
        )
        _run(["git", "commit", "--amend", "-m", message])
    except Exception:
        _run(["git", "restore", "--staged", "--worktree", "--", target_path], check=False)
        raise

    new_commit = _git("rev-parse", "HEAD")
    release["production_commit"] = new_commit
    release["production_sha256"] = production_hash
    release["attempted_at"] = actual_publish_at.isoformat()
    _write_release(package, release)

    try:
        _git("push", "origin", "HEAD:main")
    except subprocess.CalledProcessError as exc:
        _git("fetch", "origin", EXPECTED_BRANCH, check=False)
        remote_now = _git("rev-parse", f"origin/{EXPECTED_BRANCH}", check=False)
        if remote_now != new_commit:
            raise ReleaseError(
                f"publication transaction remains push-pending at {new_commit}; remote is {remote_now or '<unknown>'}"
            ) from exc

    release["state"] = "published"
    release["published_at"] = actual_publish_at.isoformat()
    _write_release(package, release)
    return True


def publish_package(package: Path, *, mode: str) -> str:
    """Publish one approved package as one isolated production commit and push it."""
    if mode not in {"manual", "auto"}:
        raise ReleaseError("publication mode must be manual or auto")

    release_path = package / "release.json"
    if release_path.is_file():
        raw = json.loads(release_path.read_text(encoding="utf-8"))
        if raw.get("state") == "push-pending":
            if _retry_push_pending(package, raw):
                return str(raw.get("production_commit"))

    release = validate_approved_release(package)
    base_commit, _ = _ensure_clean_main_and_fetch()
    existing = _publication_commit_for_doc_id(str(release["doc_id"]))
    if existing:
        release["state"] = "published"
        release["production_commit"] = existing
        _write_release(package, release)
        return existing

    actual_publish_at = _actual_eastern_now()
    scheduled = datetime.fromisoformat(str(release["publish_at"]))
    if actual_publish_at < scheduled.astimezone(EASTERN):
        raise ReleaseError(f"release is not due until {release['publish_at']}")
    if has_publication_in_week(load_published_articles(), actual_publish_at):
        raise ReleaseError("the current America/New_York week already contains a published article")

    target_path = f"content/posts/{release['slug']}.en.md"
    target = REPO_ROOT / target_path
    if target.exists():
        raise ReleaseError(f"target article already exists without matching Publication-Doc-ID: {target_path}")
    source = package / str(release["article"])
    planned_paths = planned_publication_paths(source)
    if not planned_paths or planned_paths[0] != target_path:
        raise ReleaseError(
            f"approved slug/target does not match importer plan: expected {target_path}, got {planned_paths[:1]}"
        )
    _ensure_planned_paths_absent(planned_paths)

    committed = False
    try:
        import_result = _run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "publish_article.py"),
                "--source",
                str(source),
                "--date",
                actual_publish_at.isoformat(),
                "--draft",
                "false",
            ]
        ).stdout
        if f"target: {target}" not in import_result:
            raise ReleaseError("publish_article.py returned an unexpected target")

        _verify_generated_target(target, actual_publish_at)
        changed_paths = _changed_paths_after_import(target_path)
        unexpected = set(changed_paths) - set(planned_paths)
        if unexpected:
            raise ReleaseError(f"publication import produced unplanned paths: {sorted(unexpected)}")
        _git("diff", "--check")
        hugo = _resolve_hugo()
        _build_site(hugo)

        production_hash = sha256_file(target)
        for path in changed_paths:
            _git("add", "--", path)
        message = _publication_message(
            release,
            target=target,
            target_path=target_path,
            actual_publish_at=actual_publish_at,
            production_hash=production_hash,
            changed_paths=changed_paths,
            mode=mode,
        )
        _run(["git", "commit", "-m", message])
        committed = True
        commit = _git("rev-parse", "HEAD")
    except Exception:
        if not committed:
            _rollback_uncommitted_publication(planned_paths)
        raise

    release["state"] = "push-pending"
    release["production_commit"] = commit
    release["production_parent"] = base_commit
    release["attempted_at"] = actual_publish_at.isoformat()
    release["production_sha256"] = production_hash
    release["publication_mode"] = mode
    release["publication_paths"] = changed_paths
    _write_release(package, release)

    try:
        _git("push", "origin", "HEAD:main")
    except subprocess.CalledProcessError as exc:
        _git("fetch", "origin", EXPECTED_BRANCH, check=False)
        remote_now = _git("rev-parse", f"origin/{EXPECTED_BRANCH}", check=False)
        if remote_now != commit:
            raise ReleaseError(
                f"publication transaction is push-pending at {commit}; remote is {remote_now or '<unknown>'}"
            ) from exc

    release["state"] = "published"
    release["published_at"] = actual_publish_at.isoformat()
    _write_release(package, release)
    return commit


def safe_withdraw(*, filenames: list[str], dates: list[str]) -> str:
    """Delete selected current articles in a new audited commit and push normally."""
    _ensure_clean_main_and_fetch()
    articles = load_published_articles()
    selected = select_articles(articles, filenames=filenames, publication_dates=dates)
    if not selected:
        raise ReleaseError("no currently published articles matched the withdrawal selector")

    article_paths = [item["path"] for item in selected]
    paths_to_remove = set(article_paths)
    commit_records = publication_commits()
    by_file = {
        str(record["publication_file"]): record
        for record in commit_records
        if record.get("publication_file")
    }
    for article_path in article_paths:
        record = by_file.get(article_path)
        derived_candidates = article_mermaid_paths(REPO_ROOT, article_path)
        if record:
            derived_candidates.update(str(path) for path in record.get("publication_paths", []))
        for derived in derived_candidates:
            derived_path = str(derived)
            if derived_path == article_path:
                continue
            if derived_path.startswith("static/mermaid/"):
                if publication_asset_is_referenced(
                    REPO_ROOT,
                    derived_path,
                    excluding=set(article_paths),
                ):
                    continue
                paths_to_remove.add(derived_path)
            elif derived_path.startswith("scripts/mermaid/"):
                static_equivalent = f"static/mermaid/{Path(derived_path).stem}.svg"
                if publication_asset_is_referenced(
                    REPO_ROOT,
                    static_equivalent,
                    excluding=set(article_paths),
                ):
                    continue
                paths_to_remove.add(derived_path)

    removed_paths: list[str] = []
    committed = False
    try:
        for path in sorted(paths_to_remove):
            if (REPO_ROOT / path).exists():
                _git("rm", "--", path)
                removed_paths.append(path)
        _git("diff", "--check")
        _build_site(_resolve_hugo())
        withdrawn_at = _actual_eastern_now().isoformat()
        message = build_withdraw_commit_message(article_paths, withdrawn_at=withdrawn_at)
        for path in removed_paths:
            message += f"Withdrawn-Path: {path}\n"
        _run(["git", "commit", "-m", message])
        committed = True
        commit = _git("rev-parse", "HEAD")
    except Exception:
        if not committed and removed_paths:
            _run(
                ["git", "restore", "--staged", "--worktree", "--", *removed_paths],
                check=False,
            )
        raise

    try:
        _git("push", "origin", "HEAD:main")
    except subprocess.CalledProcessError as exc:
        _git("fetch", "origin", EXPECTED_BRANCH)
        remote_now = _git("rev-parse", f"origin/{EXPECTED_BRANCH}")
        if remote_now != commit:
            _git("reset", "--hard", remote_now)
            raise ReleaseError(
                f"withdraw push failed; local main restored to origin/main {remote_now}"
            ) from exc

    queue = _queue_root()
    for release_path in queue.glob("*/release.json") if queue.is_dir() else []:
        release = json.loads(release_path.read_text(encoding="utf-8"))
        if release.get("target_file") in article_paths:
            release["state"] = "withdrawn"
            release["withdrawn_at"] = withdrawn_at
            release["withdraw_commit"] = commit
            _write_release(release_path.parent, release)
    return commit


def publication_commits(limit: int = 500) -> list[dict[str, object]]:
    """Read first-parent main history with publication trailers for purge-tail validation."""
    raw = _git("log", "--first-parent", f"-n{limit}", "--format=%H%x1f%P%x1f%B%x1e")
    commits: list[dict[str, object]] = []
    for record in raw.split("\x1e"):
        record = record.strip()
        if not record:
            continue
        sha, parents, body = record.split("\x1f", 2)
        parent = parents.split()[0] if parents.strip() else None
        file_match = re.search(r"(?m)^Publication-File:\s*(.+?)\s*$", body)
        date_match = re.search(r"(?m)^Publication-Date:\s*(.+?)\s*$", body)
        publication_paths = re.findall(r"(?m)^Publication-Path:\s*(.+?)\s*$", body)
        commits.append(
            {
                "sha": sha.strip(),
                "parent": parent,
                "publication_file": file_match.group(1).strip() if file_match else None,
                "publication_date": date_match.group(1).strip() if date_match else None,
                "publication_paths": [path.strip() for path in publication_paths],
            }
        )
    return commits


def purge_publication_tail(*, filenames: list[str], dates: list[str]) -> tuple[str, str]:
    """Erase only selected publication commits that form the exact remote-main tail."""
    _, remote = _ensure_clean_main_and_fetch()
    commits = publication_commits()
    selected = select_publication_commits(commits, filenames=filenames, publication_dates=dates)
    if not selected:
        raise ReleaseError("no publication commits matched the purge selector")
    target_files = {str(item["publication_file"]) for item in selected if item.get("publication_file")}
    base = purge_tail_base(commits, target_files)

    backup = "backup/purge-" + _actual_eastern_now().strftime("%Y%m%d-%H%M%S")
    _git("branch", backup, remote)
    succeeded = False
    try:
        _git("reset", "--hard", base)
        _build_site(_resolve_hugo())
        _git("push", f"--force-with-lease=main:{remote}", "origin", "main")
        succeeded = True
    except Exception as exc:
        _git("fetch", "origin", EXPECTED_BRANCH, check=False)
        remote_now = _git("rev-parse", f"origin/{EXPECTED_BRANCH}", check=False)
        if remote_now == base:
            succeeded = True
        else:
            restore_to = remote_now or remote
            _git("reset", "--hard", restore_to, check=False)
    if not succeeded:
        raise ReleaseError(
            f"history rewrite failed; local main was restored and backup branch {backup} preserves previous HEAD {remote}"
        )

    queue = _queue_root()
    for release_path in queue.glob("*/release.json") if queue.is_dir() else []:
        release = json.loads(release_path.read_text(encoding="utf-8"))
        if release.get("target_file") in target_files:
            release["state"] = "purged"
            release["purged_at"] = _actual_eastern_now().isoformat()
            release["purge_backup_branch"] = backup
            _write_release(release_path.parent, release)
    return base, backup


def status_rows(queue_root: Path) -> list[dict[str, str]]:
    """Return concise local release-queue status rows."""
    rows: list[dict[str, str]] = []
    if not queue_root.is_dir():
        return rows
    for package in sorted(path for path in queue_root.iterdir() if path.is_dir()):
        release_path = package / "release.json"
        if release_path.is_file():
            release = json.loads(release_path.read_text(encoding="utf-8"))
            rows.append(
                {
                    "package": package.name,
                    "state": str(release.get("state", "unknown")),
                    "publish_at": str(release.get("publish_at", "")),
                    "doc_id": str(release.get("doc_id", "")),
                }
            )
        elif (package / "manifest.yaml").is_file():
            try:
                checked = validate_prepublish_package(package)
                rows.append(
                    {
                        "package": package.name,
                        "state": "ready-for-human-review",
                        "publish_at": "",
                        "doc_id": str(checked.get("doc_id", "")),
                    }
                )
            except ReleaseError as exc:
                rows.append(
                    {
                        "package": package.name,
                        "state": "machine-blocked",
                        "publish_at": "",
                        "doc_id": "",
                        "reason": str(exc),
                    }
                )
    return rows


def _print_status(queue_root: Path) -> None:
    """Print the queue without mutating anything."""
    rows = status_rows(queue_root)
    if not rows:
        print("release queue: empty")
        return
    for row in rows:
        print(
            f"{row['package']}: state={row['state']}"
            + (f" publish_at={row['publish_at']}" if row["publish_at"] else "")
            + (f" doc_id={row['doc_id']}" if row["doc_id"] else "")
            + (f" reason={row['reason']}" if row.get("reason") else "")
        )


def _require_flag(value: bool, message: str) -> None:
    if not value:
        raise ReleaseError(message)


def _dispatch_mutating(args: argparse.Namespace, queue_root: Path) -> int:
    """Execute one mutating CLI command while the caller holds the release lock."""
    if args.command == "schedule":
        _require_flag(args.confirm_human_gates, "schedule requires --confirm-human-gates")
        package = _resolve_package(args.package, queue_root)
        release = approve_release_package(package, publish_at_local=args.at)
        print(f"approved: {package.name}")
        print(f"publish_at: {release['publish_at']}")
        print("scheduler remains unchanged; enabling it is a separate command")
        return 0

    if args.command == "publish-now":
        _require_flag(args.confirm_human_gates, "publish-now requires --confirm-human-gates")
        _require_flag(args.confirm_production, "publish-now requires --confirm-production")
        package = _resolve_package(args.package, queue_root)
        now = _actual_eastern_now()
        _ensure_clean_main_and_fetch()
        _resolve_hugo()
        if has_publication_in_week(load_published_articles(), now):
            raise ReleaseError("the current America/New_York week already contains a published article")
        approve_release_package(
            package,
            publish_at_local=now.strftime("%Y-%m-%d %H:%M"),
            approved_at=now,
            auto_eligible=False,
        )
        commit = publish_package(package, mode="manual")
        print(f"published: {commit}")
        return 0

    if args.command == "run-due":
        if not args.ignore_switch and not autopublish_is_enabled():
            print("NO-OP: repository auto-publish switch is OFF")
            return 0
        # First reconcile/retry any commit that was created but could not be pushed.
        if queue_root.is_dir():
            for release_path in sorted(queue_root.glob("*/release.json")):
                raw = json.loads(release_path.read_text(encoding="utf-8"))
                if raw.get("state") == "push-pending":
                    _retry_push_pending(release_path.parent, raw)
                    print(f"retried pending push: {release_path.parent.name}")
                    return 0

        now = _actual_eastern_now()
        if has_publication_in_week(load_published_articles(), now):
            print("NO-OP: current America/New_York week already has a published article")
            return 0
        due = due_release_packages(queue_root, now=now)
        if not due:
            print("NO-OP: no approved release is due")
            return 0
        package, _ = due[0]
        commit = publish_package(package, mode="auto")
        print(f"auto-published: {package.name} commit={commit}")
        return 0

    if args.command == "withdraw":
        _require_flag(args.confirm_production, "withdraw requires --confirm-production")
        if not args.file and not args.date:
            raise ReleaseError("withdraw requires at least one --file or --date selector")
        commit = safe_withdraw(filenames=args.file, dates=args.date)
        print(f"withdrawn: {commit}")
        return 0

    if args.command == "purge-tail":
        _require_flag(
            args.confirm_history_rewrite,
            "purge-tail requires --confirm-history-rewrite",
        )
        if not args.file and not args.date:
            raise ReleaseError("purge-tail requires at least one --file or --date selector")
        base, backup = purge_publication_tail(filenames=args.file, dates=args.date)
        print(f"purged-to: {base}")
        print(f"local-backup-branch: {backup}")
        return 0

    raise ReleaseError(f"unsupported mutating command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point used by manual commands and the local scheduler."""
    parser = argparse.ArgumentParser(description="Jack Li blog release manager")
    parser.add_argument("--queue-root", help="private prepublication queue root")
    sub = parser.add_subparsers(dest="command", required=True)

    schedule = sub.add_parser("schedule", help="Human-approve one package for future publication")
    schedule.add_argument("--package", required=True)
    schedule.add_argument("--at", required=True, help="America/New_York local time: YYYY-MM-DD HH:MM")
    schedule.add_argument("--confirm-human-gates", action="store_true")

    publish_now = sub.add_parser("publish-now", help="Human-approve and publish one package immediately")
    publish_now.add_argument("--package", required=True)
    publish_now.add_argument("--confirm-human-gates", action="store_true")
    publish_now.add_argument("--confirm-production", action="store_true")

    run_due = sub.add_parser("run-due", help="publish at most one due approved package; intended for scheduler")
    run_due.add_argument(
        "--ignore-switch",
        action="store_true",
        help="manual one-shot due check even when scheduled auto-publish is disabled",
    )
    sub.add_parser("status", help="show local release queue")

    withdraw = sub.add_parser("withdraw", help="safe withdrawal: new commit, history preserved")
    withdraw.add_argument("--file", action="append", default=[])
    withdraw.add_argument("--date", action="append", default=[])
    withdraw.add_argument("--confirm-production", action="store_true")

    purge = sub.add_parser("purge-tail", help="erase only contiguous tail publication commits")
    purge.add_argument("--file", action="append", default=[])
    purge.add_argument("--date", action="append", default=[])
    purge.add_argument("--confirm-history-rewrite", action="store_true")

    args = parser.parse_args(argv)
    queue_root = _queue_root(args.queue_root)

    try:
        if args.command == "status":
            _print_status(queue_root)
            return 0
        with release_lock():
            return _dispatch_mutating(args, queue_root)

    except (ReleaseError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
