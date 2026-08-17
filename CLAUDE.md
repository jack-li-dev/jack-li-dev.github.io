# CLAUDE.md

`AGENTS.md` is the canonical repository rule file. This file is only a thin Claude-specific adapter and must not become a second publication rule set.

Before any blog task, read `AGENTS.md` in full. In particular:

- Blog work may read or execute evidence from `Knowledge` / `my_technology`, but must not mutate those repositories or interfere with active RBAC/flywheel work.
- Check the current repository worktree before editing and preserve unrelated changes.
- Keep unpublished bilingual drafts local/private. Only a frozen English release candidate may be imported uncommitted for the real production Hugo preview loop.
- Front matter is always first. A private pre-publication draft may omit `date` / `lastmod`; the frozen production candidate must use the real `America/New_York` release time and its actual DST offset.
- Every article retains the provenance fingerprint and release hash/Git/time evidence defined in `AGENTS.md`.
- Match the established published-site voice before polishing a new article: concrete engineering setup, unresolved technical tension, natural section handoffs, and an ending that returns to the opening. External engineering blogs are structural references only, not voices to imitate.
- Put provenance in valid comments inside a real code/config example when available; do not append a standalone fingerprint footer.
- Never invent commands, output, test results, versions, citations, runtime behavior, or personal experience.
- When reader-facing runnable code or lock/config files are presented as the executed reproduction, deterministically compare them with the actual executed files before release; formatting-only normalization is allowed, semantic drift is not.
- Scheduled/release Hugo builds use a verified pinned version; never silently convert the CI back to a floating `latest` version.
- English copy: `stop-slop -> humanizer -> semantic diff -> claim revalidation`.
- Simplified Chinese copy: `deslop-zh -> qu-ai-wei -> semantic diff`, with factual preservation above style cleanup.
- Follow the review order and the three independent release rounds defined in `AGENTS.md`.
- One weekly release window is a ceiling, not a quota; `NO-OP` is acceptable.
- Production commit/push always remains behind explicit Human approval and the existing production identity gates.
- Manual and scheduled publication share `scripts/blog_release.py`; scheduler runs are deterministic and must never write/rewrite content with an LLM at due time.
- A failed push stays one `push-pending` publication transaction; retry may amend that one local commit to the new actual Eastern attempt time, but must never append a second publication commit for the same approved DOC-ID.
- Auto-publish is OFF by default. Human approval freezes the exact article SHA plus an America/New_York not-before time; missed offline schedules use the actual later production time.
- Approval also freezes the prepublication package and Canonical Wiki SHA; scheduled publication must stop when either changed after review.
- Scheduled publication also requires the ignored `.bin/autopublish.enabled` repository kill switch; a leftover Windows task alone must never be sufficient to publish.
- Default unpublish is `withdraw` (new commit). `purge-tail` may rewrite history only for the exact contiguous publication tail, with a recovery branch and `--force-with-lease`; never provide a plain-force bypass.

If this adapter conflicts with `AGENTS.md`, `AGENTS.md` wins and this file must be corrected narrowly.
