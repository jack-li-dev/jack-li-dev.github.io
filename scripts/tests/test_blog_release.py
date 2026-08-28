import hashlib
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo


from scripts.blog_release import (
    ReleaseError,
    approve_release_package,
    article_mermaid_paths,
    autopublish_is_enabled,
    build_withdraw_commit_message,
    build_publication_commit_message,
    due_release_packages,
    eastern_week_key,
    has_publication_in_week,
    publication_asset_is_referenced,
    release_lock,
    select_publication_commits,
    sha256_package,
    parse_eastern_local_time,
    purge_tail_base,
    select_articles,
    validate_prepublish_package,
    validate_approved_release,
)
from scripts.publish_article import planned_publication_paths, update_front_matter


class BlogReleaseTests(unittest.TestCase):
    """Validate the high-risk publication and withdrawal guardrails."""

    def test_parse_eastern_local_time_uses_dst_offset(self):
        """Summer and winter schedules must use New York DST rules, not a fixed offset."""
        summer = parse_eastern_local_time("2026-08-25 09:00")
        winter = parse_eastern_local_time("2026-12-15 09:00")

        self.assertEqual(summer.isoformat(), "2026-08-25T09:00:00-04:00")
        self.assertEqual(winter.isoformat(), "2026-12-15T09:00:00-05:00")

    def test_parse_eastern_local_time_rejects_dst_gap_and_ambiguous_hour(self):
        """Scheduling must never guess through New York's nonexistent or repeated DST wall-clock hour."""
        with self.assertRaisesRegex(ReleaseError, "does not exist"):
            parse_eastern_local_time("2026-03-08 02:30")

        with self.assertRaisesRegex(ReleaseError, "ambiguous"):
            parse_eastern_local_time("2026-11-01 01:30")

    def test_eastern_week_key_treats_same_local_week_as_one_release_window(self):
        """Weekly publication limits are based on America/New_York calendar weeks."""
        first = datetime.fromisoformat("2026-08-17T23:30:00-04:00")
        second = datetime.fromisoformat("2026-08-23T08:00:00-04:00")
        next_week = datetime.fromisoformat("2026-08-24T08:00:00-04:00")

        self.assertEqual(eastern_week_key(first), eastern_week_key(second))
        self.assertNotEqual(eastern_week_key(first), eastern_week_key(next_week))

    def test_validate_approved_release_rejects_changed_article_hash(self):
        """A scheduled release must stop if the approved article changes by one byte."""
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            article = package / "article.en.md"
            article.write_text("---\ntitle: test\n---\nbody\n", encoding="utf-8")
            approved_hash = hashlib.sha256(article.read_bytes()).hexdigest()
            release = {
                "schema_version": 1,
                "state": "approved",
                "article": "article.en.md",
                "article_sha256": approved_hash,
                "package_sha256": sha256_package(package),
                "slug": "test",
                "doc_id": "DOC-1",
                "publish_at": "2026-08-25T09:00:00-04:00",
                "timezone": "America/New_York",
                "approved_by": "human",
            }
            (package / "release.json").write_text(json.dumps(release), encoding="utf-8")

            article.write_text("---\ntitle: test\n---\nchanged\n", encoding="utf-8")

            with self.assertRaisesRegex(ReleaseError, "SHA-256"):
                validate_approved_release(package)

    def test_validate_approved_release_rejects_changed_evidence_tree(self):
        """Approval freezes the whole prepublish evidence package, not only reader-facing prose."""
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            article = package / "article.en.md"
            evidence = package / "factcheck.md"
            article.write_text("article\n", encoding="utf-8")
            evidence.write_text("factcheck v1\n", encoding="utf-8")
            release = {
                "schema_version": 1,
                "state": "approved",
                "article": "article.en.md",
                "article_sha256": hashlib.sha256(article.read_bytes()).hexdigest(),
                "package_sha256": sha256_package(package),
                "slug": "test",
                "doc_id": "DOC-1",
                "publish_at": "2026-08-25T09:00:00-04:00",
                "timezone": "America/New_York",
                "approved_by": "human",
                "auto_eligible": True,
            }
            (package / "release.json").write_text(json.dumps(release), encoding="utf-8")

            evidence.write_text("factcheck v2\n", encoding="utf-8")

            with self.assertRaisesRegex(ReleaseError, "package SHA-256"):
                validate_approved_release(package)

    def test_validate_approved_release_rejects_changed_canonical_knowledge(self):
        """A frozen release must stop when its load-bearing Canonical Wiki changes after approval."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            knowledge = root / "Knowledge"
            wiki = knowledge / "10-Wiki" / "Go - Zap Structured Logging.md"
            wiki.parent.mkdir(parents=True)
            wiki.write_text("canonical v1\n", encoding="utf-8")

            package = root / "package"
            package.mkdir()
            article = package / "article.en.md"
            article.write_text("article\n", encoding="utf-8")
            release = {
                "schema_version": 1,
                "state": "approved",
                "article": "article.en.md",
                "article_sha256": hashlib.sha256(article.read_bytes()).hexdigest(),
                "package_sha256": sha256_package(package),
                "slug": "test",
                "doc_id": "DOC-1",
                "publish_at": "2026-08-25T09:00:00-04:00",
                "timezone": "America/New_York",
                "approved_by": "human",
                "auto_eligible": True,
                "canonical": {
                    "repository": "Knowledge",
                    "path": "10-Wiki/Go - Zap Structured Logging.md",
                    "sha256": hashlib.sha256(wiki.read_bytes()).hexdigest(),
                },
            }
            (package / "release.json").write_text(json.dumps(release), encoding="utf-8")

            wiki.write_text("canonical v2\n", encoding="utf-8")

            with mock.patch.dict("os.environ", {"KNOWLEDGE_REPO": str(knowledge)}):
                with self.assertRaisesRegex(ReleaseError, "Canonical SHA-256 changed"):
                    validate_approved_release(package)

    def test_select_articles_supports_filename_and_eastern_publication_date(self):
        """Batch withdrawal can select published posts by filename or Eastern publication date."""
        articles = [
            {
                "path": "content/posts/a.en.md",
                "date": "2026-08-25T09:00:00-04:00",
            },
            {
                "path": "content/posts/b.en.md",
                "date": "2026-08-26T01:00:00+00:00",
            },
            {
                "path": "content/posts/c.en.md",
                "date": "2026-08-26T09:00:00-04:00",
            },
        ]

        selected = select_articles(
            articles,
            filenames=["b.en.md"],
            publication_dates=["2026-08-25"],
        )

        self.assertEqual(
            [item["path"] for item in selected],
            ["content/posts/a.en.md", "content/posts/b.en.md"],
        )

    def test_purge_tail_requires_selected_publication_commits_to_be_exact_head_suffix(self):
        """History erasure must refuse targets that are not the contiguous publication tail."""
        commits = [
            {"sha": "c3", "publication_file": "content/posts/c.en.md", "parent": "c2"},
            {"sha": "c2", "publication_file": "content/posts/b.en.md", "parent": "c1"},
            {"sha": "c1", "publication_file": None, "parent": "c0"},
        ]

        self.assertEqual(
            purge_tail_base(commits, {"content/posts/c.en.md", "content/posts/b.en.md"}),
            "c1",
        )

        with self.assertRaisesRegex(ReleaseError, "contiguous tail"):
            purge_tail_base(commits, {"content/posts/b.en.md"})

    def test_publication_commit_message_contains_machine_readable_trailers(self):
        """Each article commit must carry stable metadata used by withdrawal and audit commands."""
        message = build_publication_commit_message(
            title="Example",
            doc_id="DOC-1",
            slug="example",
            target_path="content/posts/example.en.md",
            publish_at="2026-08-25T09:00:00-04:00",
            article_sha256="abc123",
            mode="auto",
            changed_paths=[
                "content/posts/example.en.md",
                "static/mermaid/example.svg",
            ],
        )

        self.assertIn("Publication-Doc-ID: DOC-1", message)
        self.assertIn("Publication-File: content/posts/example.en.md", message)
        self.assertIn("Publication-Date: 2026-08-25T09:00:00-04:00", message)
        self.assertIn("Publication-Mode: auto", message)
        self.assertIn("Publication-Path: content/posts/example.en.md", message)
        self.assertIn("Publication-Path: static/mermaid/example.svg", message)

    def test_update_front_matter_can_freeze_release_date_and_publish_draft(self):
        """Production import must set date/lastmod together and turn draft off explicitly."""
        raw = 'title: "Example"\ndraft: true\nslug: example'

        output = update_front_matter(
            raw,
            "2026-08-25T09:00:00-04:00",
            [],
            draft=False,
        )

        self.assertIn("date: 2026-08-25T09:00:00-04:00", output)
        self.assertIn("lastmod: 2026-08-25T09:00:00-04:00", output)
        self.assertIn("draft: false", output)
        self.assertNotIn("draft: true", output)

    def test_planned_publication_paths_predicts_article_and_mermaid_artifacts(self):
        """Release rollback must know every file the importer may create before mutation starts."""
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "article.en.md"
            source.write_text(
                "---\n"
                'title: "Example"\n'
                "slug: example\n"
                "---\n"
                "```mermaid\nflowchart LR\nA --> B\n```\n"
                "```mermaid\nflowchart LR\nC --> D\n```\n",
                encoding="utf-8",
            )

            self.assertEqual(
                planned_publication_paths(source),
                [
                    "content/posts/example.en.md",
                    "scripts/mermaid/example-1.mmd",
                    "scripts/mermaid/example-2.mmd",
                    "static/mermaid/example-1.svg",
                    "static/mermaid/example-2.svg",
                ],
            )

    def test_validate_prepublish_package_requires_ready_state_and_machine_gates(self):
        """Human approval is only available after the machine-owned publication gates pass."""
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            article = package / "article.en.md"
            article.write_text("---\ntitle: test\ndraft: true\nslug: test\n---\nbody\n", encoding="utf-8")
            digest = hashlib.sha256(article.read_bytes()).hexdigest()
            (package / "manifest.yaml").write_text(
                "\n".join(
                    [
                        "content_id: DOC-1",
                        "state: ready-for-human-review",
                        "publication:",
                        "  slug: test",
                        f"  article_en_sha256: {digest}",
                        "gates:",
                        "  publish_value: pass",
                        "  canonical_alignment: pass",
                        "  primary_source_factcheck: pass",
                        "  runtime_verification: pass",
                        "  bilingual_alignment: pass",
                        "  links: pass",
                        "  hugo_build: pass-hugo-0.164.0-extended",
                        "  hugo_version_pin: pass-pinned-0.164.0",
                        "  render: pass-desktop-mobile-console-clean",
                        "  rights_security: pass",
                        "  creation_proof: pass-prepublish",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = validate_prepublish_package(package)

            self.assertEqual(result["doc_id"], "DOC-1")
            self.assertEqual(result["slug"], "test")
            self.assertEqual(result["article_sha256"], digest)

    def test_validate_prepublish_package_rejects_reader_facing_obsidian_wikilink(self):
        """Publication must fail closed when renderer-specific Wiki syntax leaks into article prose."""
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            article = package / "article.en.md"
            article.write_text(
                "---\ntitle: test\ndraft: true\nslug: test\n---\n"
                "See [[Go - Zap Structured Logging|Zap logging]].\n",
                encoding="utf-8",
            )
            digest = hashlib.sha256(article.read_bytes()).hexdigest()
            (package / "manifest.yaml").write_text(
                "\n".join(
                    [
                        "content_id: DOC-1",
                        "state: ready-for-human-review",
                        "publication:",
                        "  slug: test",
                        f"  article_en_sha256: {digest}",
                        "gates:",
                        "  publish_value: pass",
                        "  canonical_alignment: pass",
                        "  primary_source_factcheck: pass",
                        "  runtime_verification: pass",
                        "  bilingual_alignment: pass",
                        "  links: pass",
                        "  hugo_build: pass-hugo-0.164.0-extended",
                        "  hugo_version_pin: pass-pinned-0.164.0",
                        "  render: pass-desktop-mobile-console-clean",
                        "  rights_security: pass",
                        "  creation_proof: pass-prepublish",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ReleaseError, "Obsidian Wiki link residue"):
                validate_prepublish_package(package)

    def test_validate_prepublish_package_rejects_any_extra_nonhuman_blocked_gate(self):
        """Topic-specific machine gates must block approval even when base gates all pass."""
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            article = package / "article.en.md"
            article.write_text("---\ntitle: test\ndraft: true\nslug: test\n---\nbody\n", encoding="utf-8")
            digest = hashlib.sha256(article.read_bytes()).hexdigest()
            (package / "manifest.yaml").write_text(
                "\n".join(
                    [
                        "content_id: DOC-1",
                        "state: ready-for-human-review",
                        "publication:",
                        "  slug: test",
                        f"  article_en_sha256: {digest}",
                        "gates:",
                        "  publish_value: pass",
                        "  canonical_alignment: pass",
                        "  primary_source_factcheck: pass",
                        "  runtime_verification: pass",
                        "  bilingual_alignment: pass",
                        "  links: pass",
                        "  hugo_build: pass-hugo-0.164.0-extended",
                        "  hugo_version_pin: pass-pinned-0.164.0",
                        "  render: pass-desktop-mobile-console-clean",
                        "  rights_security: pass",
                        "  creation_proof: pass-prepublish",
                        "  topic_specific_contract: blocked",
                        "  human_mastery: pending-human",
                        "  human_final: pending-human",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ReleaseError, "topic_specific_contract"):
                validate_prepublish_package(package)

    def test_validate_prepublish_package_rejects_nonhuman_blocker_record(self):
        """A remaining machine blocker must reject approval even if gate values were accidentally marked pass."""
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            article = package / "article.en.md"
            article.write_text("---\ntitle: test\ndraft: true\nslug: test\n---\nbody\n", encoding="utf-8")
            digest = hashlib.sha256(article.read_bytes()).hexdigest()
            (package / "manifest.yaml").write_text(
                "\n".join(
                    [
                        "content_id: DOC-1",
                        "state: ready-for-human-review",
                        "publication:",
                        "  slug: test",
                        f"  article_en_sha256: {digest}",
                        "gates:",
                        "  publish_value: pass",
                        "  canonical_alignment: pass",
                        "  primary_source_factcheck: pass",
                        "  runtime_verification: pass",
                        "  bilingual_alignment: pass",
                        "  links: pass",
                        "  hugo_build: pass-hugo-0.164.0-extended",
                        "  hugo_version_pin: pass-pinned-0.164.0",
                        "  render: pass-desktop-mobile-console-clean",
                        "  rights_security: pass",
                        "  creation_proof: pass-prepublish",
                        "  human_mastery: pending-human",
                        "  human_final: pending-human",
                        "blockers:",
                        "  - id: stale-runtime-evidence",
                        "    status: blocked-runtime",
                        "    reason: test",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ReleaseError, "stale-runtime-evidence"):
                validate_prepublish_package(package)

    def test_approve_release_package_freezes_hash_and_eastern_schedule(self):
        """Approval writes a local release record bound to one exact article and Eastern time."""
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            article = package / "article.en.md"
            article.write_text("---\ntitle: test\ndraft: true\nslug: test\n---\nbody\n", encoding="utf-8")
            digest = hashlib.sha256(article.read_bytes()).hexdigest()
            (package / "manifest.yaml").write_text(
                "\n".join(
                    [
                        "content_id: DOC-1",
                        "state: ready-for-human-review",
                        "publication:",
                        "  slug: test",
                        f"  article_en_sha256: {digest}",
                        "gates:",
                        "  publish_value: pass",
                        "  canonical_alignment: pass",
                        "  primary_source_factcheck: pass",
                        "  runtime_verification: pass",
                        "  bilingual_alignment: pass",
                        "  links: pass",
                        "  hugo_build: pass-hugo-0.164.0-extended",
                        "  hugo_version_pin: pass-pinned-0.164.0",
                        "  render: pass-desktop-mobile-console-clean",
                        "  rights_security: pass",
                        "  creation_proof: pass-prepublish",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            release = approve_release_package(
                package,
                publish_at_local="2026-08-25 09:00",
                approved_at=datetime(2026, 8, 17, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
            )

            self.assertEqual(release["state"], "approved")
            self.assertEqual(release["publish_at"], "2026-08-25T09:00:00-04:00")
            self.assertEqual(release["article_sha256"], digest)
            self.assertTrue((package / "release.json").is_file())

    def test_due_release_packages_returns_only_due_approved_packages_in_order(self):
        """Scheduler ignores future/unapproved packages and publishes oldest due item first."""
        with tempfile.TemporaryDirectory() as tmp:
            queue = Path(tmp)
            for name, state, publish_at in [
                ("later", "approved", "2026-08-18T09:00:00-04:00"),
                ("first", "approved", "2026-08-17T08:00:00-04:00"),
                ("future", "approved", "2026-08-19T09:00:00-04:00"),
                ("draft", "draft", "2026-08-16T09:00:00-04:00"),
            ]:
                package = queue / name
                package.mkdir()
                article = package / "article.en.md"
                article.write_text(name, encoding="utf-8")
                (package / "release.json").write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "state": state,
                            "article": "article.en.md",
                            "article_sha256": hashlib.sha256(article.read_bytes()).hexdigest(),
                            "package_sha256": sha256_package(package),
                            "slug": name,
                            "doc_id": name,
                            "publish_at": publish_at,
                            "timezone": "America/New_York",
                            "approved_by": "human",
                            "auto_eligible": state == "approved",
                        }
                    ),
                    encoding="utf-8",
                )

            due = due_release_packages(
                queue,
                now=datetime.fromisoformat("2026-08-18T10:00:00-04:00"),
            )

            self.assertEqual([item[0].name for item in due], ["first", "later"])

    def test_due_release_packages_ignores_manual_only_approval(self):
        """A failed or unfinished publish-now approval must never be consumed by the scheduler."""
        with tempfile.TemporaryDirectory() as tmp:
            queue = Path(tmp)
            package = queue / "manual"
            package.mkdir()
            article = package / "article.en.md"
            article.write_text("manual", encoding="utf-8")
            (package / "release.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "state": "approved",
                        "article": "article.en.md",
                        "article_sha256": hashlib.sha256(article.read_bytes()).hexdigest(),
                        "package_sha256": sha256_package(package),
                        "slug": "manual",
                        "doc_id": "manual",
                        "publish_at": "2026-08-17T08:00:00-04:00",
                        "timezone": "America/New_York",
                        "approved_by": "human",
                        "auto_eligible": False,
                    }
                ),
                encoding="utf-8",
            )

            due = due_release_packages(
                queue,
                now=datetime.fromisoformat("2026-08-18T10:00:00-04:00"),
            )

            self.assertEqual(due, [])

    def test_has_publication_in_week_uses_actual_article_dates(self):
        """A legacy or automated article already published this Eastern week consumes the weekly slot."""
        articles = [
            {"path": "content/posts/a.en.md", "date": "2026-08-18T01:00:00+00:00"},
        ]

        self.assertTrue(
            has_publication_in_week(
                articles,
                datetime.fromisoformat("2026-08-23T12:00:00-04:00"),
            )
        )
        self.assertFalse(
            has_publication_in_week(
                articles,
                datetime.fromisoformat("2026-08-24T12:00:00-04:00"),
            )
        )

    def test_select_publication_commits_supports_filename_and_eastern_date(self):
        """History-purge selection uses publication trailers and Eastern local dates."""
        commits = [
            {
                "sha": "c3",
                "publication_file": "content/posts/c.en.md",
                "publication_date": "2026-08-26T09:00:00-04:00",
                "parent": "c2",
            },
            {
                "sha": "c2",
                "publication_file": "content/posts/b.en.md",
                "publication_date": "2026-08-26T01:00:00+00:00",
                "parent": "c1",
            },
        ]

        selected = select_publication_commits(
            commits,
            filenames=["c.en.md"],
            publication_dates=["2026-08-25"],
        )

        self.assertEqual(
            {item["publication_file"] for item in selected},
            {"content/posts/b.en.md", "content/posts/c.en.md"},
        )

    def test_withdraw_commit_message_records_every_removed_file(self):
        """Safe withdrawal commits retain a machine-readable list of removed articles."""
        message = build_withdraw_commit_message(
            ["content/posts/a.en.md", "content/posts/b.en.md"],
            withdrawn_at="2026-08-25T10:00:00-04:00",
        )

        self.assertIn("post: withdraw 2 articles", message)
        self.assertIn("Withdrawn-File: content/posts/a.en.md", message)
        self.assertIn("Withdrawn-File: content/posts/b.en.md", message)
        self.assertIn("Withdrawn-Mode: safe", message)

    def test_autopublish_switch_is_off_until_flag_exists(self):
        """A leftover Windows task must not publish unless the repository-local kill switch is enabled."""
        with tempfile.TemporaryDirectory() as tmp:
            flag = Path(tmp) / "autopublish.enabled"

            self.assertFalse(autopublish_is_enabled(flag))

            flag.write_text("enabled\n", encoding="utf-8")
            self.assertTrue(autopublish_is_enabled(flag))

    def test_release_lock_rejects_second_concurrent_transaction(self):
        """Manual and scheduled release commands must not mutate production concurrently."""
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "release.lock"

            with release_lock(lock_path):
                with self.assertRaisesRegex(ReleaseError, "another release transaction"):
                    with release_lock(lock_path):
                        self.fail("second transaction unexpectedly acquired the lock")

    def test_publication_asset_reference_check_ignores_articles_being_withdrawn(self):
        """Derived Mermaid assets may be removed only when no remaining article references them."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            posts = repo / "content" / "posts"
            posts.mkdir(parents=True)
            withdrawing = posts / "a.en.md"
            other = posts / "b.en.md"
            withdrawing.write_text("![](/mermaid/shared.svg)\n", encoding="utf-8")
            other.write_text("unrelated\n", encoding="utf-8")

            self.assertFalse(
                publication_asset_is_referenced(
                    repo,
                    "static/mermaid/shared.svg",
                    excluding={"content/posts/a.en.md"},
                )
            )

            other.write_text("![](/mermaid/shared.svg)\n", encoding="utf-8")
            self.assertTrue(
                publication_asset_is_referenced(
                    repo,
                    "static/mermaid/shared.svg",
                    excluding={"content/posts/a.en.md"},
                )
            )

    def test_article_mermaid_paths_supports_legacy_posts_without_publication_trailers(self):
        """Safe withdrawal can discover a legacy article's Mermaid source/export pair from body links."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            article = repo / "content" / "posts" / "legacy.en.md"
            article.parent.mkdir(parents=True)
            article.write_text(
                "[![](/mermaid/legacy.svg)](/mermaid/legacy.svg)\n",
                encoding="utf-8",
            )

            self.assertEqual(
                article_mermaid_paths(repo, "content/posts/legacy.en.md"),
                {"static/mermaid/legacy.svg", "scripts/mermaid/legacy.mmd"},
            )


if __name__ == "__main__":
    unittest.main()
