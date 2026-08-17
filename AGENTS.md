# AGENTS.md

## CRITICAL Production Push Identity Gate

After every push to the production repository, run the three identity checks below before claiming completion.

Public identity boundary:

```text
GitHub public profile email: jack@jack-li.me
Git commit email: 16163394+jack-li-dev@users.noreply.github.com
```

The public GitHub profile may show `jack@jack-li.me`. Git commit metadata must never use that address. Commits must use only the GitHub anonymous noreply alias.

### Check 1: Local Repository Identity Scope

From the repository root:

```bash
git config user.name "Jack Li"
git config user.email "16163394+jack-li-dev@users.noreply.github.com"
git config user.name
git config user.email
git config --list --show-origin | grep -E "user\\.(name|email)"
```

Required output for the first two readbacks:

```text
Jack Li
16163394+jack-li-dev@users.noreply.github.com
```

Required source check:

```text
file:.git/config user.email=16163394+jack-li-dev@users.noreply.github.com
```

The local `.git/config` entry must override any global identity. This keeps the anonymous email scoped to this project and avoids contaminating other repositories.

### Check 2: Full Local Branch Metadata

From the repository root:

```bash
git log main --pretty=format:"Commit: %h | Author: %an | Email: <%ae> | Committer: %cn | CommitterEmail: <%ce> | Date: %ad%n"
```

Every displayed commit on `main` must show:

```text
Author: Jack Li
Email: <16163394+jack-li-dev@users.noreply.github.com>
Committer: Jack Li
CommitterEmail: <16163394+jack-li-dev@users.noreply.github.com>
```

Hard fail if any displayed commit uses a real email in either author or committer metadata, such as:

```text
Email: <jack@jack-li.me>
CommitterEmail: <huaijiu888@gmail.com>
```

If the check fails, stop. Fix the current repository identity with:

```bash
git config user.name "Jack Li"
git config user.email "16163394+jack-li-dev@users.noreply.github.com"
```

Then amend or rewrite the affected commit metadata before any further production push. A new masking commit is not enough. If any historical commit leaks a real email, rewrite the reachable production history and push with `--force-with-lease`.

### Check 3: Full Production Clone Metadata

After pushing to production, verify the real production clone as well:

```bash
cd /home/dev/github/jack-li-dev.github.io
git fetch origin main
git pull --ff-only origin main
git log main --pretty=format:"Commit: %h | Author: %an | Email: <%ae> | Committer: %cn | CommitterEmail: <%ce> | Date: %ad%n"
```

Every displayed production commit must show:

```text
Author: Jack Li
Email: <16163394+jack-li-dev@users.noreply.github.com>
Committer: Jack Li
CommitterEmail: <16163394+jack-li-dev@users.noreply.github.com>
```

This is an all-history gate. If even one production commit fails, the production repository is not compliant.

## Project Boundary

This repository is the Hugo source workspace for Jack Li's site customization.

Shadow sandbox / staging remote:

```text
git@github.com:jack-li-dev/my_hugo.git
```

Production/GitHub Pages source remote:

```text
git@github.com:jack-li-dev/jack-li-dev.github.io.git
```

`my_hugo` is the test/staging shadow sandbox. `jack-li-dev.github.io` is the formal production repository for the public site.

Do not push to `jack-li-dev.github.io` unless the user explicitly authorizes a production/main-site push in the current task. For normal development notes, handoff docs, rules, and staging work, push only to `my_hugo`.

## Git Rules

- Before large refactors, run the requested pull/sync command first and report the result.
- Never use `git add .`.
- Stage source files explicitly.
- Do not stage or commit ignored build outputs:
  - `public/`
  - `.hugo_build.lock`
  - `resources/_generated/`
- When the user says to push to `git@github.com:jack-li-dev/my_hugo.git`, add/use the sandbox remote and push there only.
- Keep the production remote untouched unless the user explicitly names `git@github.com:jack-li-dev/jack-li-dev.github.io.git`, `https://github.com/jack-li-dev/jack-li-dev.github.io`, or clearly requests production/GitHub Pages push.

## Hugo Local Preview Rules

Always start local preview with an explicit localhost baseURL:

```bash
./.bin/hugo server --bind 127.0.0.1 --baseURL http://127.0.0.1:1313/ --disableFastRender
```

For background preview, use the verified detached command:

```bash
setsid ./.bin/hugo server --bind 127.0.0.1 --baseURL http://127.0.0.1:1313/ --disableFastRender > /tmp/jack-li-me-hugo.log 2>&1 < /dev/null & echo $! > /tmp/jack-li-me-hugo.pid
```

Stop background preview with:

```bash
kill "$(cat /tmp/jack-li-me-hugo.pid)" && rm -f /tmp/jack-li-me-hugo.pid
```

Do not rely on plain `nohup ... &` in this environment; it was observed to exit immediately. Use `setsid` as above.

If local links unexpectedly point to `https://jack-li.me/`, restart the Hugo server with the explicit `--baseURL http://127.0.0.1:1313/`. Otherwise the browser may leave localhost and hit undeployed production URLs, creating false 404 reports.

## Hugo Build Verification

Run before claiming completion:

```bash
./.bin/hugo --gc --minify
```

A clean build should have no errors and no Hugo deprecation warnings.

## Publication Release Governance

Blog publication work must stay isolated from concurrent Knowledge and experiment work.

- `Knowledge` and `my_technology` may be read or executed for evidence, but blog tasks must not edit, stage, commit, reset, stash, rebase, clean, or otherwise mutate those repositories.
- Active RBAC work and its flywheel remain out of publication scope until separately completed and selected.
- Before editing this repository, run `git status --short --branch`. Preserve unrelated work and stop if the task would overlap it.
- Unpublished Chinese/English drafts remain local/private. A frozen English release candidate may enter this production working tree uncommitted for Hugo build/render review. Production commit/push still requires explicit Human approval.

### Release cadence

- One weekly release window is the default, not a quota. `NO-OP` is valid when no article is release-ready.
- Publish at most one new technical article per week. Prefer roughly 2-4 high-quality releases per month while the site is still building its technical reputation.
- Never weaken a gate or create filler to preserve cadence.

### Front matter and time authority

- Front matter must be the first bytes of an article. Nothing may appear before the opening `---`.
- Pre-publication drafts may intentionally omit `date` and `lastmod` so a draft-creation time cannot be mistaken for the first publication time.
- A frozen production candidate must include accurate `title`, `date`, `lastmod`, `draft`, `slug`, `description`, `categories`, and `tags` values appropriate to that article.
- Production publication time authority is `America/New_York`. Never derive formal release timestamps from the operator's local timezone.
- Generate real Eastern timestamps with `TZ="America/New_York" date --iso-8601=seconds`; preserve the DST offset returned by the timezone database.
- `date` becomes immutable after the first production release. `lastmod` initially equals `date` and changes only for substantive article edits.
- If a draft does carry timestamps, treat them as provisional. When the article is frozen for production, replace them with the real Eastern release timestamp.

### Provenance fingerprint

Every formal article must carry the established Jack Li provenance marker:

```text
JACK-LI::PROVENANCE
DOC-ID: <stable unique article id>
AUTH-SIG: <stable unique non-secret marker>
SOURCE: https://jack-li.me
CONTACT: jack@jack-li.me
```

- Embed the marker as valid comments inside a real reader-facing code or configuration example when the article contains one, matching the established published-site pattern. Do not append the fingerprint as a standalone footer HTML comment merely because it is easy to hide there.
- The fingerprint must not distort executable meaning. Prefer comment syntax native to the displayed artifact (`//`, `#`, YAML comments, and similar). If no honest code/config artifact exists, stop and choose an article-appropriate provenance placement during review instead of inventing fake code just to carry the marker.
- `DOC-ID` and `AUTH-SIG` must not silently change after publication.
- Treat the marker as provenance evidence, not DRM or a cryptographic signature.
- Release evidence must also retain the final article SHA-256, relevant source/runtime Git commits, production commit, and Eastern publication time.

### Evidence and runtime truth

- Never write `tested`, `verified`, `works`, benchmark numbers, supported versions, command output, or runtime behavior from memory.
- For executable claims, run the smallest sufficient real check and retain command, working directory, relevant versions, source Git commit, timestamp, exit code, and unedited output.
- If an article says a displayed test, source file, `go.mod`, `go.sum`, config, or other runnable artifact is the exact reproduction that was executed, compare the reader-facing block deterministically with the executed source before release. Normalize only syntax-preserving formatting such as `gofmt`; do not rely on visual review for code fidelity.
- Keep environment scope accurate. Evidence from WSL2/Linux or one dependency version must not be generalized beyond what sources and tests support.
- Runtime checks stay article-scoped. Do not rerun unrelated JWT, RBAC, GORM, or other suites for ceremony.
- Pin the Hugo version used by CI/release automation. Do not use a floating `latest` version for scheduled publication. Treat a Hugo version upgrade as a separate infrastructure change: verify a real build/render first, then update the pin.

### Chinese and English publication copies

- Canonical Knowledge remains upstream authority. Publication drafts are derived views.
- When a Chinese control draft exists, use it to preserve the technical meaning. The English article is an audience-native adaptation rather than a line-by-line translation.
- Before release, compare Chinese, English, and Canonical Knowledge for load-bearing facts, versions, numbers, conditions, limitations, causal relations, code behavior, and verification statements.

### Publication voice and narrative

- Existing formal articles on `jack-li.me` are the first voice calibration source. Before rewriting or creating a release candidate, compare the draft against at least one published article for heading style, sentence register, opening pace, transitions, ending shape, and provenance placement. Do not let every new article invent a new site persona.
- Chinese copies must read as native Chinese engineering prose, not as an English article translated sentence by sentence. Treat the English copy as a fact/scope constraint, not a wording template. Rebuild Chinese headings, paragraph rhythm, transitions, and conclusion shape when literal structural mirroring would sound like a course outline or translation.
- Native-Chinese review is a mandatory per-release gate for every reader-facing Chinese article, and it must be rerun after every material Chinese rewrite; it is not a one-time cleanup step. Review sentence-level grammar, not only anti-slop vocabulary: aspect/particle choices such as `了 / 着 / 过`, natural use of `把` and `被` constructions, Chinese word order, and whether causal, concessive, contrastive, progressive, and parallel connectors express the real relation between clauses. Do not mechanically inject particles or passive/`把` constructions just to make prose look more human; use them only where normal Chinese information structure calls for them.
- Native Chinese technical prose may naturally mix Chinese with established English technical terms, API names, runtime terms, and operation words when that is how engineers normally write them. After the required first-use Chinese gloss has been satisfied where applicable, prefer the natural technical token (`reload`, `logger`, `buffer`, `wrapper`, `stdout`, API names, etc.) over repeatedly translating it into stilted Chinese merely for language purity. Mixed-language usage must remain readable and consistent; do not scatter gratuitous English where a normal Chinese term is more natural.
- Native-Chinese review must also include a mandatory verbosity/information-density pass. Technical prose should say each fact once, with the shortest natural wording that preserves causality, scope, evidence strength, and necessary teaching context. Remove repeated premises, duplicate explanations, synonym stacking, editor narration, and obvious consequences the reader can already infer. For every paragraph, ask whether a materially shorter version carries the same technical meaning; if yes, prefer the shorter version. Do not chase an arbitrary word-count target or delete qualifiers/evidence merely to look concise.
- Reader-facing layout review is a separate mandatory gate after Chinese prose stabilizes. Inspect paragraph density on both desktop and mobile: one prose paragraph should normally carry one main idea or one tightly coupled cause/effect unit, not background + branch + conclusion + next action in one block. Split at real semantic boundaries with blank Markdown lines; a soft source line break is not a rendered paragraph break. Treat long visual text walls as a defect even when every sentence is individually correct. Do not enforce a rigid character/line quota, and do not fragment tightly coupled reasoning into choppy one-sentence bullets merely to shorten boxes. Code, ASCII diagrams, tables, lists, and quotations are exempt from prose-paragraph density heuristics.
- When calibrating Chinese prose, compare several strong Chinese technical writers/sites with different registers and extract only reusable techniques such as concrete problem entry, short explanatory paragraphs, direct examples, and restrained conclusions. Do not copy a named writer's personal tone, jokes, catchphrases, or argumentative persona.
- Avoid editorial/course scaffolding in Chinese reader-facing headings when normal prose works better. Labels such as `零件 1`, `Part 1`, `最后留下 Mental Model`, `先看一张总图`, or `这篇到底解决什么` should be treated as candidates for rewrite unless the document is intentionally a lesson/reference outline.
- In narrative/explanatory posts, keep reader-facing titles and H2 headings out of the editor's control plane. Avoid scaffolding labels such as `Start With the Map`, `What This Article Solves`, `Overview`, or their Chinese equivalents when the heading can instead name the state, object, or phenomenon the reader is looking at. A diagram may still appear immediately; the heading does not need to announce the teaching device.
- If a post is structured as discovery/debugging, the title may identify the problem domain but should not reveal the root cause or final fix before the reader reaches the evidence. Answer-first/reference posts are exempt.
- For explanatory engineering posts, do not open by dumping the final conclusion unless the article is intentionally a reference entry. Prefer a concrete engineering scene, anomaly, failed assumption, or small question that gives the reader a reason to continue before introducing the abstraction.
- The introduction should establish three things quickly: the situation, the unresolved tension, and what will be tested or explained. Do not manufacture personal incidents; hypothetical scenes must be clearly hypothetical.
- For novice-oriented explanatory/debugging posts, prefer a learning ladder over an encyclopedia outline: minimum `what`/`why` context -> one macro map when it reduces orientation cost -> smallest runnable current/broken case -> observable symptom/impact -> only the prerequisite parts needed to explain that symptom -> runnable minimal examples -> reassemble the original case -> root cause -> smallest fix -> rerun/verify -> reusable mental model. Compress or skip any stage that does not earn its place for that topic.
- For production-facing engineering posts, continue the learning ladder into operations when the topic has real runtime failure modes: name the production symptom, show the smallest useful diagnostic command/metric/state check, connect it back to the resource/call path, give the narrow fix, and state the prevention rule. Keep diagnosis evidence-driven; do not invent an outage story just to make the article feel practical.
- Explicitly separate development convenience from production deployment choices. Do not turn one deployment pattern into a universal rule (for example, do not claim production logging must use application-managed files when container platforms commonly collect stdout/stderr). If a recommendation depends on environment, name the environment that makes it apply.
- Reader-facing production snippets must not silently demonstrate the failure mode the prose warns against. If the article says a cleanup error matters, the production-shaped example must preserve or report that error rather than discarding it with `_ =`, unless the omission is explicitly scoped as a teaching simplification.
- Use `trace down, learn up` as a default debugging-learning shape when appropriate: first trace the real feature/resource path from the outside without overexplaining internals, then learn the smallest inner components independently, and finally climb back up to the original program. Do not front-load deep internals before the reader has seen the behavior they explain.
- Runnable examples are for behavior-bearing claims, not a quota. A pure interface/schema/source-contract step may stay as a read-only contract inspection when a synthetic `main()` would demonstrate no new behavior; state that choice explicitly and run the neighboring behavior-bearing parts instead.
- Diagrams are evidence-bearing teaching aids, not decoration or a quota. Prefer one early macro ASCII/Markdown diagram when the system has multiple ownership/data-flow boundaries; add a micro diagram only at a genuine abstraction boundary such as an interface contract, lifecycle transfer, or causal bug mechanism. Do not add Mermaid/static assets when text diagrams communicate the mechanism more clearly.
- Do not reveal the final patch while the article is still establishing prerequisite mechanics unless the topic is intentionally answer-first. Background sections should explain only enough to unlock the next question; the repair should appear after the reader has enough evidence to predict it.
- Each major section should answer a question raised earlier and naturally expose the next question. Avoid outline-like sections that read as independent encyclopedia fragments with no narrative handoff.
- Keep suspense technical, not theatrical. Withhold only the amount of answer needed to create curiosity; never hide a safety-critical fact or fake uncertainty after the evidence is already known.
- End by returning to the opening problem and compressing the article into one reusable engineering model or decision rule. References may appear before this closing section so the final reader impression is the resolved idea, not a bibliography or provenance footer.
- External high-quality engineering blogs may be used as structural calibration references for scene-setting, pacing, transitions, and closure. Extract techniques; do not imitate an individual author's characteristic wording, jokes, personal history, or verbal tics.

### Anti-slop and humanization

Do not stack every available humanizer as consecutive rewrite passes. Extra rewriting can erase technical qualifiers.

English release copy:

```text
stop-slop
-> humanizer
-> semantic diff against pre-edit copy and Canonical Knowledge
-> load-bearing claim revalidation
```

- `deslop-en`, `avoid-ai-writing`, `anti-ai-slop-writing`, and `slopbuster` are optional adversarial audits. Use them only for incremental findings; do not automatically rewrite every flag.

Simplified Chinese release copy:

```text
deslop-zh
-> qu-ai-wei (minimal technical-prose pass)
-> semantic diff against Canonical Knowledge
```

- Chinese-specific rules outrank English-only punctuation, passive-voice, or vocabulary heuristics.
- After Chinese humanization, perform a native-Chinese cold read without looking at the English copy. If the paragraph order only makes sense because the editor remembers the English source, rewrite the Chinese transitions before bilingual fact alignment.
- Preserve technical terms, evidence strength, causality, responsibility, numbers, and version scope.
- Never invent personal anecdotes or "human" details to satisfy a style detector.

### Review order and release rounds

Review publication material in this order:

```text
alignment
-> layout/render
-> factual/technical errors
-> logic
-> control-plane leakage
-> links
-> tags/front matter/metadata
-> line count and split pressure
-> causality
-> instant mental-model clarity
-> closure
-> prerequisites
-> human prose / concision / truth / repetition
```

A frozen release candidate requires at least three different review rounds:

1. Evidence/technical: canonical alignment, primary sources, runtime evidence, versions, code/command truth, logic, causality, security, and rights.
2. Post-edit semantic: after humanization/deslop, re-check Chinese-English-Canonical parity and every changed load-bearing claim.
3. Release: front matter, Eastern timestamp, provenance fingerprint, links, metadata/SEO, Hugo build, real render, final diff, hashes, and production identity.

Repeatedly rereading prose without a different review responsibility does not count as an independent round. A material edit invalidates affected downstream gates.

Production publication is blocked until all applicable gates pass and the Human explicitly approves the frozen artifact.

### Manual / scheduled release automation

- `scripts/blog_release.py` / `scripts/blog-release.sh` are the canonical production release manager. Manual and scheduled publication must share this core rather than maintain separate push logic.
- Automation is OFF by default. Repository setup, clone, build, and test operations must never enable a Windows scheduled task implicitly.
- Scheduled publication requires both the Windows task and the ignored repository-local `.bin/autopublish.enabled` kill switch. Either one being OFF must prevent scheduler-driven publication; manual `run-once` may explicitly bypass only this switch for diagnosis.
- A scheduled release requires a private/local `release.json` created only after explicit Human mastery + final editorial approval. The approval binds the exact English article SHA-256 and an `America/New_York` not-before time.
- Approval also freezes the full prepublication package digest and the load-bearing Canonical Wiki path/SHA when present. Due-time publication must re-check them read-only; any change invalidates approval and returns the article to review.
- Scheduler execution is deterministic only: validate approved SHA, publication cadence, Git state/identity/remote, pinned Hugo, build, commit, and push. Do not invoke an LLM, humanizer, fact-check rewrite, or automatic dependency/tool upgrade at due time.
- Missed schedules caused by an offline/powered-off workstation are catch-up events. Use the actual later Eastern production transaction time for first `date` / `lastmod`; never backdate the article to the missed schedule.
- Publish at most one due article per America/New_York ISO week. Backlog must remain queued rather than burst-publishing after downtime.
- Every production article release must be an isolated single-article commit with `Publication-*` trailers. Infrastructure/rule/config changes must be committed separately before release automation runs.
- A failed production push may remain as one `push-pending` publication transaction. Never append a second publication commit for the same approved DOC-ID. If the remote confirms the pending commit was not received, retry may amend that single local commit to the new actual Eastern production-attempt time before pushing again.
- The Windows Task Scheduler adapter is only a wake-up mechanism. It may trigger at logon and periodically, but release eligibility remains entirely inside the repository release manager.

### Withdrawal and history rewrite

- `withdraw` is the default safe unpublish operation: remove selected current article files in a new commit and push normally. It may select multiple articles by filename and/or Eastern publication date.
- `purge-tail` is a separate high-risk operation. It may rewrite production history only when all selected publication commits form the exact contiguous tail of `origin/main` and there are no later/unrelated commits to replay.
- `purge-tail` must create a local recovery branch before reset and must push with an exact `--force-with-lease`; never fall back to plain `--force`.
- Do not automate arbitrary middle-of-history deletion for routine content withdrawal. If legal/secret/privacy remediation requires deeper history rewriting, stop the normal publication workflow and perform a separately reviewed incident procedure.
- Rewritten Git branch history cannot guarantee removal from third-party clones, forks, search caches, or CDNs; never claim otherwise.

## Article Ordering Consistency

When an article compares the same group of concepts across headings, prose, Mermaid diagrams, tables, lists, or captions, keep the order identical everywhere.

- For timeline-shaped technical concepts, use chronological order by default.
- Example canonical order for Claude Code evolution/comparison content:

```text
Skill -> Subagent -> Workflow
```

- After generating or importing an article, run a final consistency audit over every repeated group such as `A vs B vs C`, Mermaid subgraphs, table columns, list items, and nearby prose.
- If any order differs, fix the heading, diagram, and table/list order together before publishing.

## Mermaid Static Image Rules

If an article uses Mermaid and the publish decision is to ship a rendered image instead of browser-side Mermaid JS, use this repository as the asset source of truth.

- Store generated Mermaid images under:

```text
/home/dev/github/my_hugo/static/mermaid/
```

- Do not put published Mermaid images under `content/`, `assets/`, or `public/`.
- In Markdown, reference them with root-relative paths only:

```markdown
![](/mermaid/<file>.svg)
```

- Do not write `static/mermaid/<file>.svg`.
- Do not write relative paths such as `../mermaid/<file>.svg`.

### Mermaid Render Toolchain

- Prefer the fixed local CLI from the writing workspace:

```text
/home/dev/.skills-manager/skills/my-skills/skills/write-skill/.tools/mermaid-cli/node_modules/.bin/mmdc
```

- Prefer system Chromium:

```text
/usr/bin/chromium-browser
```

- If the local Mermaid CLI is missing, install it in the writing workspace with:

```bash
PUPPETEER_SKIP_DOWNLOAD=1 npm install @mermaid-js/mermaid-cli@11.15.0 --prefix /home/dev/.skills-manager/skills/my-skills/skills/write-skill/.tools/mermaid-cli --no-audit --no-fund
```

- If `npx @mermaid-js/mermaid-cli` times out or throws `ENOTEMPTY`, do not keep retrying `npx`. Clean the damaged `~/.npm/_npx/` temp directory and run `npm cache verify`, or use the fixed local CLI above.

### Mermaid Publish Verification Loop

Before claiming a Mermaid image is ready for publish, verify this exact loop:

1. The source image exists in `static/mermaid/`.
2. Run Hugo build or local preview:

```bash
./.bin/hugo --gc --minify
```

or

```bash
./.bin/hugo server --bind 127.0.0.1 --baseURL http://127.0.0.1:1313/ --disableFastRender
```

3. Confirm the built file exists in:

```text
/home/dev/github/my_hugo/public/mermaid/
```

4. Open both:

```text
http://127.0.0.1:1313/mermaid/<file>.svg
```

and the article page that references it.

If either path fails, do not claim the Mermaid asset is ready.

For i18n/navigation changes, verify these routes:

```text
/
/posts/
/about/
/archives/
/search/
/zh/
/zh/posts/
/zh/about/
/zh/archives/
/zh/search/
/zh/posts/kind-high-availability-2026/
```

Use `curl` or browser checks against `http://127.0.0.1:1313`, not `https://jack-li.me`, unless explicitly validating production.

## Internationalization Rules

Do not treat i18n as only adding translated Markdown pages. For this site, a complete i18n change must cover:

- `languages.en` and `languages.zh` configuration in `hugo.yaml`.
- Per-language `params.profileMode` subtitle.
- Per-language `menu.main` labels.
- Per-language footer/zero-comment notice.
- Translated content pages where menu items point:
  - About
  - Posts section index
  - Archives
  - Search
  - Existing posts that should appear in `/zh/posts/`
- Route validation for both English and Chinese URLs.

Avoid fixed front matter `url` values on translated `archives`/`search` pages unless the language prefix behavior is explicitly verified. Fixed URLs can prevent Hugo from generating `/zh/...` routes.

## PaperMod Override Rules

This PaperMod version uses `layouts/_partials/`.

For local theme overrides, prefer:

```text
layouts/_partials/
```

Only mirror to `layouts/partials/` when compatibility is required, and never create wrapper partials that call the same partial name recursively.

Do not edit files inside `themes/PaperMod` directly unless the user explicitly asks for vendored theme changes.

## Infrastructure & CI/CD Guardrails

### CRITICAL ANTI-DRIFT GUARDRAIL: GITHUB ACTIONS ENVIRONMENT-AGNOSTIC DUAL-LOOP DEADLOCK

Incident profile:

- Scenario: During the sovereign site cleanup from multilingual i18n to English-only, the pipeline also introduced a hybrid static/dynamic LTS marker. Local Hugo must keep `lts_string: "[LTS: 2026.05.26]"` as a static baseline, while GitHub Actions mutates that value only inside the ephemeral Ubuntu build sandbox using the current `America/New_York` date.
- Shadow loop: The private `my_hugo` repository was used as the blue/green validation loop before production Pages rollout.
- Deadlock: After changing repository visibility from Private to Public through Danger Zone, GitHub Pages routing and repository policy state did not fully converge immediately. The default `GITHUB_TOKEN` remained effectively read-only for Pages deployment.
- Physical result: The build job passed, but the deploy job was skipped or blocked because the workflow did not have effective high-privilege Pages write authority. The Settings/Pages screen did not produce a usable Pages URL.

Actionable immunity:

- Do not rely on manual Pages branch toggles in the GitHub UI to repair this state.
- The workflow must declare global Pages deployment permissions explicitly:

```yaml
permissions:
  contents: read
  pages: write
  id-token: write
```

- The deploy job must bind the official Pages environment explicitly:

```yaml
environment:
  name: github-pages
  url: ${{ steps.deployment.outputs.page_url }}
```

- Keep the LTS mutation inside the CI sandbox only. Never commit the computed date back into `hugo.yaml`.
- The LTS date must use `TZ="America/New_York"` and the current day. Do not use `+365 days`, `tomorrow`, or any other future offset.
- Required CI mutation primitive:

```bash
FUTURE_LTS="$(TZ="America/New_York" date "+%Y.%m.%d")"
sed -i "s|\[LTS: 2026\.05\.26\]|[LTS: ${FUTURE_LTS}]|g" hugo.yaml
```

- If the source tree is clean but the Pages pipeline must be re-triggered, do not inject garbage source changes. Use an empty trigger commit:

```bash
git commit --allow-empty -m "build: force trigger"
```

## Identity & Privacy Firewalls

### CRITICAL IDENTITY FIREWALL: GITHUB MULTI-IDENTITY BOUNDARY & METADATA PURGE PROTOCOL

#### 1. The Public Identity Disconnect

- Fact: The public commercial profile identity is `Jack Li`, and the public Web contact channel is `jack@jack-li.me`.
- Web profile rule: In `https://github.com/settings/emails`, the account may need `Keep my email addresses private` unchecked so the profile email selector can expose the custom-domain contact address.
- Commit identity rule: This Web profile setting is fully decoupled from terminal Git identity. All local Git commits must still use the GitHub masked noreply alias:

```bash
git config --local user.name "Jack Li"
git config --local user.email "16163394+jack-li-dev@users.noreply.github.com"
```

- Required boundary: Public Web profile may show the commercial domain. Cryptographic commit metadata must show only the GitHub noreply protection alias.

#### 2. The Legacy Metadata Collision Leakage

- Fact: If any public commit leaks a legacy email such as `huaijiu888@gmail.com` or an old identity such as `lixiao888`, GitHub's global metadata index can map those commit nodes to the legacy account identity and pollute the public professional profile.
- Recovery rule: Do not add trash masking commits. Rewrite the affected timeline immediately.
- Local identity lock before rewrite:

```bash
git config --local user.name "Jack Li"
git config --local user.email "16163394+jack-li-dev@users.noreply.github.com"
```

- Modern tip-only rewrite primitive:

```bash
GIT_COMMITTER_NAME="Jack Li" \
GIT_COMMITTER_EMAIL="16163394+jack-li-dev@users.noreply.github.com" \
git commit --amend --no-edit --author="Jack Li <16163394+jack-li-dev@users.noreply.github.com>"
```

- Historical rewrite primitive when older commits are contaminated:

```bash
git filter-branch --force --env-filter '
if [ "$GIT_AUTHOR_EMAIL" = "OLD_EMAIL" ] || [ "$GIT_AUTHOR_NAME" = "OLD_NAME" ] || [ "$GIT_COMMITTER_EMAIL" = "OLD_EMAIL" ] || [ "$GIT_COMMITTER_NAME" = "OLD_NAME" ]; then
  export GIT_AUTHOR_NAME="Jack Li"
  export GIT_AUTHOR_EMAIL="16163394+jack-li-dev@users.noreply.github.com"
  export GIT_COMMITTER_NAME="Jack Li"
  export GIT_COMMITTER_EMAIL="16163394+jack-li-dev@users.noreply.github.com"
fi
' -- main
```

- Force-push gateway after verification:

```bash
git push origin main --force
```

- Truth check before any deployment:

```bash
git log -n 3 --pretty=format:"Commit: %h | Author: %an | Email: <%ae> | Committer: %cn | CommitterEmail: <%ce> | Date: %ad%n"
```

#### 3. The Private Repository Cold Storage Strategy

- Mandatory rule: Do not touch legacy private repositories for cosmetic identity cleanup.
- Do not mass-update private repositories with API scripts.
- Do not run bulk `--force` push sequences across private repositories.
- Rationale: Private repositories are not public internet surface area. Bulk history rewriting across many old private repositories creates unnecessary account-risk telemetry and can trigger anti-abuse review. Long-lived private histories can also serve as organic account continuity signals. Leave them in frozen cold storage unless there is a concrete security incident requiring targeted action.

#### 4. The New Repository Enlistment Law

- Every new repository initialized with `git init` must receive local scoped identity before the first commit.
- The `--global` flag is forbidden for identity changes in this workspace because it can contaminate unrelated repositories.
- Required first-command block:

```bash
git config --local user.name "Jack Li"
git config --local user.email "16163394+jack-li-dev@users.noreply.github.com"
```

### CROSS-MACHINE MIGRATION GUARDRAIL: MULTI-ENV IDEMPOTENT POST-CLONE PROTOCOL

#### 1. The New Environment Identity Hazard

- Risk fact: When cloning either `jack-li-dev.github.io` as the production sovereign repository or `my_hugo` as the shadow sandbox onto a new workstation, or after reinstalling the WSL runtime, the hidden `.git/config` local identity block is not preserved by standard Git cloning.
- Consequence: The new machine's generic or domestic `git config --global` identity can take over. The first unguarded `git commit` can inject leaked personal email metadata such as `huaijiu888@gmail.com` back into public history and re-open the identity exposure chain.

#### 2. The Post-Clone Enlistment Drill

- Rule: After every fresh clone of either repository, enforce the local identity seal before any build, code edit, commit, amend, rebase, or push sequence.
- Required command flow from the repository root:

```bash
# Step 1: Step into the cloned repository root.
cd /path/to/repository-root

# Step 2: Apply the local cryptographic identity seal. Local scope only.
git config --local user.name "Jack Li"
git config --local user.email "16163394+jack-li-dev@users.noreply.github.com"

# Step 3: Verify the local identity matrix.
git config --local --list | grep -E "user\\.(name|email)"
```

- Compliance output:

```text
user.name=Jack Li
user.email=16163394+jack-li-dev@users.noreply.github.com
```

#### 3. The Safety Trap Net Trigger

- Action: Keep GitHub's centralized command-line email privacy block enabled.
- Verification line: In `https://github.com/settings/emails`, ensure `Block command line pushes that expose my email` is checked.
- Expected behavior: If an unconfigured fresh workstation creates a commit with a personal email and attempts to push, GitHub must reject the push at the API gateway with a non-zero exit code before public cloud indexing.

#### 4. The Re-Run Independent Audit Protocol

- For `my_hugo` as the private shadow testbed, run a local identity audit before merging or promoting code toward `jack-li-dev.github.io`.
- Required pre-flight scan:

```bash
git log -n 5 --pretty=format:"Commit: %h | Author: %an | Email: <%ae> | Committer: %cn | CommitterEmail: <%ce> | Date: %ad%n"
```

- Hard fail the promotion if any author or committer field contains a legacy username or personal email.

### WHITELIST EXEMPTION SCOPES: APPROVED OPEN-SOURCE FINGERPRINTS

The following repositories represent the core infrastructure, AI engineering, and multi-identity edge blueprints of `jack-li-dev`. They are fully exempt from automated cleanup scripts, purge matrices, fork pruning, and reputation-noise reduction jobs.

- Cloud-native infrastructure:
  - `kubernetes/kubernetes`
  - `kubernetes-sigs/kind`
  - `helm/helm`
  - `prometheus/prometheus`
  - `hashicorp/terraform`
  - `harbor/harbor`
  - `aws/aws-cli`
  - `localstack/localstack`
- AI agent and MCP ecosystem:
  - `open-webui/open-webui`
  - `langchain-ai/langchain`
  - `mem0ai/mem0`
  - `modelcontextprotocol/fastmcp`
  - `claude-code-proxy`
  - `cursor-memory-bank`
  - `chatbot-ui`
- System engineering:
  - `denoland/deno`
  - `tauri-apps/tauri`
  - `rockylinux/rocky`

Any cleanup automation touching public forks must implement a local-name exemption list for these repositories before applying deletion logic.

### FRONT-END UI MASK: REPOSITORY FOOTER SOCIAL DECOUPLING PROHIBITION

- Fact: To ensure zero physical trace leakage and support targeted manual application workflows, all public-facing portfolio social indices, specifically LinkedIn, X/Twitter, and WeChat, must be neutralized at the Hugo architecture layer.
- Mandatory boundary: The config parameters `[[params.social]]`, `params.socialIcons`, `params.socialButtons`, or equivalent theme variables for external identity vectors are permanently banned for LinkedIn, X/Twitter, and WeChat.
- Allowed web UI contact surface: The only legitimate communication channel on the public web UI is the domain email `jack@jack-li.me`.
- Allowed root asset surface: The canonical root asset link remains `https://jack-li.me`.

## Current Known Placeholders

The Web3 wallet address is still a placeholder:

```text
[Your-Wallet-Address-Placeholder]
```

Do not replace it with a guessed address.
