# AGENTS.md

## Project Boundary

This repository is the Hugo source workspace for Jack Li's site customization.

Primary development remote:

```text
git@github.com:jack-li-dev/my_hugo.git
```

Production/GitHub Pages source remote may exist as `origin`:

```text
git@github.com:jack-li-dev/jack-li-dev.github.io.git
```

Do not push to `origin` unless the user explicitly asks for production/main-site push. For normal development notes, handoff docs, rules, and staging work, push only to `my_hugo`.

## Git Rules

- Before large refactors, run the requested pull/sync command first and report the result.
- Never use `git add .`.
- Stage source files explicitly.
- Do not stage or commit ignored build outputs:
  - `public/`
  - `.hugo_build.lock`
  - `resources/_generated/`
- When the user says to push to `git@github.com:jack-li-dev/my_hugo.git`, add/use remote name `my_hugo` and push there only.
- Keep `origin` untouched unless the user explicitly names `git@github.com:jack-li-dev/jack-li-dev.github.io.git` or clearly requests production/GitHub Pages push.

## Hugo Local Preview Rules

Always start local preview with an explicit localhost baseURL:

```bash
../.bin/hugo server --bind 127.0.0.1 --baseURL http://127.0.0.1:1313/ --disableFastRender
```

For background preview, use the verified detached command:

```bash
setsid ../.bin/hugo server --bind 127.0.0.1 --baseURL http://127.0.0.1:1313/ --disableFastRender > /tmp/jack-li-me-hugo.log 2>&1 < /dev/null & echo $! > /tmp/jack-li-me-hugo.pid
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
../.bin/hugo --gc --minify
```

A clean build should have no errors and no Hugo deprecation warnings.

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

- Scenario: During the sovereign site cleanup from multilingual i18n to English-only, the pipeline also introduced a hybrid static/dynamic LTS marker. Local Hugo must keep `lts_string: "[LTS: 2026.05.26]"` as a static baseline, while GitHub Actions mutates that value only inside the ephemeral Ubuntu build sandbox using `TZ="America/New_York"` and `date -d "+365 days"`.
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
- Required CI mutation primitive:

```bash
FUTURE_LTS="$(TZ="America/New_York" date -d "+365 days" "+%Y.%m.%d")"
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
