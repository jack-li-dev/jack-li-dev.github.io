# Handoff

Date: 2026-05-26

## Repository

Current local path:

```bash
/home/dev/github/my_hugo/jack-li-me
```

Primary development remote:

```bash
git@github.com:jack-li-dev/my_hugo.git
```

Current pushed commit:

```text
91673ca docs: add development handoff
```

The old GitHub Pages source remote is still present as `origin`:

```bash
git@github.com:jack-li-dev/jack-li-dev.github.io.git
```

Do normal development against `my_hugo/main`.

## Fresh Machine Bootstrap

```bash
git clone git@github.com:jack-li-dev/my_hugo.git
cd my_hugo
git submodule update --init --depth 1 --recursive
```

Hugo binary expected by this repo:

```bash
../.bin/hugo
```

Current verified Hugo version:

```text
hugo v0.161.1 extended linux/amd64
```

If `../.bin/hugo` is missing on the new machine, install Hugo Extended there before building.

## Local Preview

Start foreground server:

```bash
../.bin/hugo server --bind 127.0.0.1 --baseURL http://127.0.0.1:1313/ --disableFastRender
```

Start background server:

```bash
setsid ../.bin/hugo server --bind 127.0.0.1 --baseURL http://127.0.0.1:1313/ --disableFastRender > /tmp/jack-li-me-hugo.log 2>&1 < /dev/null & echo $! > /tmp/jack-li-me-hugo.pid
```

Stop background server:

```bash
kill "$(cat /tmp/jack-li-me-hugo.pid)" && rm -f /tmp/jack-li-me-hugo.pid
```

Preview URLs:

```text
http://127.0.0.1:1313/
http://127.0.0.1:1313/zh/
http://127.0.0.1:1313/about/
http://127.0.0.1:1313/zh/about/
http://127.0.0.1:1313/posts/
http://127.0.0.1:1313/zh/posts/
```

## Build Check

```bash
../.bin/hugo --gc --minify
```

Last verified result:

```text
EN pages: 19
ZH pages: 17
No build errors
No Hugo deprecation warnings
```

## Completed Work

- PaperMod dark-only configuration in `hugo.yaml`.
- English and Chinese language configuration.
- Per-language menu and profile subtitle.
- OLED black custom CSS in `assets/css/extended/custom.css`.
- Profile telemetry bar in `layouts/_partials/index_profile.html`.
- Clean custom footer with per-language zero-comment notice.
- English and Chinese About pages.
- English and Chinese archive/search pages.
- Chinese translation for the existing Kind high-availability post.
- Local runbook added to `README.md`.

## Verified Routes

```text
200 /
200 /posts/
200 /about/
200 /archives/
200 /search/
200 /zh/
200 /zh/posts/
200 /zh/about/
200 /zh/archives/
200 /zh/search/
200 /zh/posts/kind-high-availability-2026/
```

## Important Notes

- Do not commit `public/`, `.hugo_build.lock`, or `resources/_generated/`.
- Do not use `git add .`; stage source files explicitly.
- Local preview must use `--baseURL http://127.0.0.1:1313/`, otherwise generated links may point to `https://jack-li.me/`.
- The wallet address is still a placeholder: `[Your-Wallet-Address-Placeholder]`.
