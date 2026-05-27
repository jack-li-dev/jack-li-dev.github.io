# jack-li-dev.github.io (Source Ledger)

> Persistent focus. Low noise. 

This repository contains the immutable markdown source code and corporate-grade deployment runbooks for `https://jack-li.me`. 

- **Engine:** Hugo (Extended v0.145.0+)
- **Theme:** PaperMod (Customized Architecture)
- **CI/CD:** GitHub Actions Automation Pipelines
- **Infrastructure Security:** Cloudflare Edge Protections & WAF Interceptors

## Local Runbook

Run all commands from the repository root:

```bash
cd /home/dev/github/my_hugo/jack-li-me
```

Start the local Hugo preview server:

```bash
../.bin/hugo server --bind 127.0.0.1 --baseURL http://127.0.0.1:1313/ --disableFastRender
```

Open:

```text
http://127.0.0.1:1313/
http://127.0.0.1:1313/about/
http://127.0.0.1:1313/zh/about/
```

Stop the foreground server:

```text
Ctrl+C
```

Start in the background and write logs locally:

```bash
setsid ../.bin/hugo server --bind 127.0.0.1 --baseURL http://127.0.0.1:1313/ --disableFastRender > /tmp/jack-li-me-hugo.log 2>&1 < /dev/null & echo $! > /tmp/jack-li-me-hugo.pid
```

Stop the background server:

```bash
kill "$(cat /tmp/jack-li-me-hugo.pid)" && rm -f /tmp/jack-li-me-hugo.pid
```

Build the static site:

```bash
../.bin/hugo --gc --minify
```

Ignored build outputs must stay out of Git:

```text
public/
.hugo_build.lock
resources/_generated/
```

---
*Telemetry from true production battlefields. Managed and maintained under static air-gapped logic for 2026 LTS stability.*
