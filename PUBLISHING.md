# Blog 发布 / 自动周发使用手册

本仓库只发布已经完成机器审核并由 Human 最终批准的 Publication Copy（发布副本）。定时任务只执行确定性 Gate（门禁）与 Git/Hugo 操作，不调用 LLM，也不在到点后修改文章。

## 1. Mental Model

```text
private prepublish package
→ machine gates PASS
→ Human mastery + final approval
→ freeze SHA + Eastern not-before time
→ manual publish / scheduler due-check
→ Git + Hugo preflight
→ 1 article = 1 publication commit
→ origin/main
```

自动发布默认 **OFF**。默认私有队列是：

```text
drafts/prepublish/<package>/
```

该目录已被 `.gitignore` 排除。未来迁到独立私有 staging repository（预发布仓库）时，只需设置：

```bash
export BLOG_RELEASE_QUEUE=/path/to/private/release-queue
```

Canonical Knowledge 默认位置是 `/home/dev/github/Knowledge`。如果以后移动仓库：

```bash
export KNOWLEDGE_REPO=/new/path/Knowledge
```

## 2. 命令速查

| 目标 | 命令 |
|---|---|
| 查看队列 | `bash scripts/blog-release.sh status` |
| 立即发布 | `bash scripts/blog-release.sh publish-now --package <package> --confirm-human-gates --confirm-production` |
| 预约发布 | `bash scripts/blog-release.sh schedule --package <package> --at "YYYY-MM-DD HH:MM" --confirm-human-gates` |
| 手工跑一次到期检查 | `bash scripts/autopublish-scheduler.sh run-once` |
| 查看自动任务 | `bash scripts/autopublish-scheduler.sh status` |
| 开启自动任务 | `bash scripts/autopublish-scheduler.sh enable` |
| 暂停自动任务 | `bash scripts/autopublish-scheduler.sh disable` |
| 删除自动任务 | `bash scripts/autopublish-scheduler.sh remove` |
| 安全撤回 | `bash scripts/blog-release.sh withdraw ... --confirm-production` |
| 擦除连续尾部发布历史 | `bash scripts/blog-release.sh purge-tail ... --confirm-history-rewrite` |

## 3. Human Approval（人工批准）解决什么

`schedule` / `publish-now` 只接受：

```text
manifest.state = ready-for-human-review
```

同时要求 manifest 中：

```text
所有 Machine Gate = PASS
所有额外专项 Machine Gate = PASS
不存在非 Human blocker
```

`human_mastery`、`human_final` 由你判断。`--confirm-human-gates` 表示：

> 我已完成 mastery 和最终审稿，并批准当前文章 SHA。

批准会生成 Git ignored（Git 忽略）的 `release.json`，冻结：

```text
DOC-ID
slug
article SHA-256
whole prepublish package SHA-256
Canonical path + SHA-256
publish_at
approved_at
approved_by = human
```

批准后只要文章、evidence/repro/manifest package 或 Canonical Wiki 任一发生变化，旧 approval（批准）就失效。

## 4. 手动一键发布

例如：

```bash
bash scripts/blog-release.sh publish-now \
  --package drafts/prepublish/zap-sync-vs-close \
  --confirm-human-gates \
  --confirm-production
```

发布事务：

```text
production preflight
→ Human approval freeze
→ actual America/New_York timestamp
→ date == lastmod
→ draft: false
→ import exactly one article
→ git diff --check
→ Hugo production build
→ isolated publication commit
→ push origin/main
```

Production preflight（生产预检）要求：

```text
branch = main
working tree = clean
HEAD = origin/main
origin = git@github.com:jack-li-dev/jack-li-dev.github.io.git
Git identity = Jack Li / noreply GitHub email
Hugo = v0.164.0+extended
```

脚本不会自动 stash、reset、merge、rebase 或升级 Hugo。

## 5. 预约未来发布

例如美东 2026-08-25 09:00：

```bash
bash scripts/blog-release.sh schedule \
  --package drafts/prepublish/zap-sync-vs-close \
  --at "2026-08-25 09:00" \
  --confirm-human-gates
```

`--at` 永远解释为 `America/New_York`，使用 IANA timezone database（IANA 时区数据库）自动处理 EST / EDT。

DST 切换当天如果输入不存在的本地时间（春季跳时）或重复的歧义时间（秋季回拨），脚本会直接拒绝，让你换一个明确时间，不猜 offset。

`publish_at` 是 not-before time（不得早于时间），不是秒级 realtime deadline（实时截止点）。`schedule` 只冻结批准记录，不会立即发布，也不会自动开启 Windows Scheduler（Windows 计划任务）。

## 6. 开启 / 关闭本机自动发布

当前默认 OFF。自动发布采用双钥匙：

```text
Windows Task enabled
AND
.bin/autopublish.enabled exists
```

任何一把关闭，周期 `run-due` 都不会自动发布。

查看：

```bash
bash scripts/autopublish-scheduler.sh status
```

开启，默认每 5 分钟检查一次：

```bash
bash scripts/autopublish-scheduler.sh enable
```

指定 10 分钟：

```bash
bash scripts/autopublish-scheduler.sh enable 10
```

暂停 / 删除：

```bash
bash scripts/autopublish-scheduler.sh disable
bash scripts/autopublish-scheduler.sh remove
```

Windows Task 名：

```text
JackLiBlog-AutoPublish
```

任务显式绑定当前 Windows 登录用户，使用 Interactive logon type（交互式登录类型），不保存密码、不要求用管理员账户运行。

日志：

```text
.bin/autopublish.log
```

任务本身只负责唤醒 WSL 并运行：

```bash
python3 scripts/blog_release.py run-due
```

真正的时间、SHA、周频、Git、Hugo Gate 全部在 release manager（发布管理器）中判断。

## 7. 电脑关机后如何补发

Scheduler 使用登录触发 + 周期触发：

```text
planned 09:00
→ PC powered off
→ schedule missed
→ next Windows logon
→ run-due
→ if gates still PASS: publish
```

此时正式 `date` / `lastmod` 使用**实际执行发布事务时的美东时间**，不会伪造为关机期间的原计划时间。

默认 5 分钟检查意味着正常情况是 `publish_at` 之后的第一个成功检查周期上线，而不是承诺精确到秒。

## 8. 每周最多一篇

`run-due` 按 `America/New_York` 的 ISO week（ISO 周）检查现有正式文章：

```text
current Eastern week already has an article?
├─ yes → NO-OP
└─ no  → publish oldest due package only
```

因此电脑离线积压多篇后，也不会开机一次全发。

## 9. Queue 状态

```bash
bash scripts/blog-release.sh status
```

| 状态 | 含义 |
|---|---|
| `not-approved` | 只有 prepublish package，尚未 Human approve |
| `approved` | 已批准，等待 `publish_at` |
| `push-pending` | 一个 publication transaction 已有本地 pending commit，但尚未确认进入远端 |
| `published` | 已发布 |
| `stale` | pending/approved 内容或 Canonical 已变化，旧批准失效，必须重新审核 |
| `withdrawn` | 已安全撤回 |
| `purged` | 已擦除连续尾部 publication commits |

`push-pending` 始终保持**一个发布 commit**，不会为同一 DOC-ID 追加第二个发布提交。如果远端确认没有收到旧 commit，重试前会把真实美东 `date/lastmod` 更新为新的上线尝试时间并 `commit --amend`，所以 pending commit SHA 允许变化。

## 10. 安全撤回：日常默认

按文件：

```bash
bash scripts/blog-release.sh withdraw \
  --file article-a.en.md \
  --confirm-production
```

批量文件：

```bash
bash scripts/blog-release.sh withdraw \
  --file article-a.en.md \
  --file article-b.en.md \
  --confirm-production
```

按**美东发布日期**：

```bash
bash scripts/blog-release.sh withdraw \
  --date 2026-08-25 \
  --confirm-production
```

文件与日期可以同时使用，匹配结果取并集。

`withdraw` 新建删除 commit，不改写已有历史：

```text
publication commit
...
withdraw commit
```

新式 publication commit 会从 `Publication-Path` 找文章专属 Mermaid SVG/MMD；旧文章没有这些 trailers 时，`withdraw` 会从正文 `/mermaid/*.svg` 链接反查对应 SVG/MMD。两种情况都只删除未被其他现存文章引用的资产，共享资产保留。

## 11. purge-tail：仅限刚发布的连续尾巴

`purge-tail` 只自动处理带 `Publication-*` trailer、由新 release manager 生成的单文章独立提交。历史遗留文章如果发布 commit 混有 workflow、模板、脚本或其他文章变更，必须使用 `withdraw`；脚本不会为了擦一篇文章顺带抹掉那些无关历史。

只有下面这种情况才允许历史擦除：

```text
HEAD
├─ publication C  target
├─ publication B  target
└─ safe base
```

如果目标后面已经有无关提交：

```text
HEAD
├─ infrastructure fix   unrelated
├─ publication C        target
└─ ...
```

脚本直接拒绝。

按文件：

```bash
bash scripts/blog-release.sh purge-tail \
  --file article-a.en.md \
  --confirm-history-rewrite
```

按发布日期：

```bash
bash scripts/blog-release.sh purge-tail \
  --date 2026-08-25 \
  --confirm-history-rewrite
```

通过时固定执行：

```text
create local backup/purge-YYYYMMDD-HHMMSS
→ reset to safe base
→ Hugo build
→ git push --force-with-lease
```

没有普通 `--force` fallback（后备开关）。

中间历史删除会改写其后提交的 SHA，所以日常撤回不要用它。如果因为 Secret、法律或严重隐私问题必须深度擦除历史，应停止常规发布流程，单独做 incident procedure（事件处置流程）。

即使 Git branch history（分支历史）已改写，也不能保证第三方 clone、fork、搜索引擎或 CDN 缓存中的旧副本消失。

## 12. Publication Commit 协议

手动与自动发布共享同一核心，并要求：

```text
1 article = 1 isolated publication commit
```

基础设施、规则、Hugo 配置等修改必须单独提交，不能混进文章发布 commit。

新式 publication commit 使用 `Publication-*` trailer（提交尾注）记录 DOC-ID、文件、实际发布日期、批准 SHA、生产 SHA、发布模式和派生产物，用于幂等、审计、撤回和 `purge-tail`。

## 13. 常见阻塞

| 报错 / 状态 | 怎么处理 |
|---|---|
| `production working tree is not clean` | `git status --short --branch`，人工处理，不让自动任务 stash/reset |
| `local main must exactly match origin/main` | 人工同步/判断 Git；发布器不会 merge/rebase |
| `approved article SHA-256 changed` | 旧 approval 失效，重跑受影响 Gate + Human Review |
| 本美东周已有文章 | 正常 `NO-OP`，等下一周 |
| Hugo 不是 `v0.164.0+extended` | 单独验证新 Hugo 后再升级 pin |
| `push-pending` | 后续 due-check 继续同一个 publication transaction；必要时 amend 单个 pending commit 后重试 |

## 14. 推荐日常流程

```text
Canonical / evidence
→ prepublish
→ machine review
→ Human Review
→ publish-now       # 立即发
   or
→ schedule          # 以后发
→ enable scheduler only when needed
```

撤回：

```text
normal case → withdraw
exact publication tail + truly need history erasure → purge-tail
```

最终安全底线：

```text
no Human approval → no publish
SHA changed → no publish
Canonical changed → no publish
machine blocker exists → no approval
dirty Git → no publish
wrong Hugo → no publish
already published this week → NO-OP
scheduler OFF → never auto-publish
```
