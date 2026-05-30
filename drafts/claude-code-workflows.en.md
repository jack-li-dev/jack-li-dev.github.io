---
title: "Claude Code Workflow Field Guide"
date: 2026-05-28T00:00:00+08:00
lastmod: 2026-05-28T00:00:00+08:00
draft: false
categories: ["AI-Vibe-Coding", "Sovereign-Fortress"]
tags: ["Claude-Code", "ultrawork", "workflow", "linux", "redis", "nginx", "systemd"]
---

```text
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
```

## 01. Environment Bootstrap

Start with a locked boundary. An agent without an egress policy is just a process with expensive hands.

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
export CLAUDE_CODE_WORKFLOWS=1
export DISABLE_GROWTHBOOK=1
claude --dangerously-skip-permissions
```

For air-gapped or highly secured corporate infrastructure, pin agent traffic through pre-approved local network gateways. Block telemetry-linked growth hooks at process start. Do not bake site-specific gateways into repository code.

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
cat >> ~/.zshrc <<'EOF'
export CLAUDE_CODE_WORKFLOWS=1
export DISABLE_GROWTHBOOK=1
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"
EOF

cat >> ~/.bashrc <<'EOF'
export CLAUDE_CODE_WORKFLOWS=1
export DISABLE_GROWTHBOOK=1
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"
EOF
```

## 02. Core Syntax And Control Policy

The control line is small. The blast radius is not.

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
ultrawork +[token-budget] "[task]" [execution-policy]
```

| Budget | Use | Boundary |
|---|---|---|
| `+500k` | Issue triage, local failure analysis | Read first |
| `+1M` | PR review, security audit, bounded repair | Small edits allowed |
| `+2M` | End-to-end development | Tests and diff review required |

| Policy | Job |
|---|---|
| `pipeline` | Split the work before context turns soft |
| `self-repair` | Repair failed attempts in place |
| `adversarial review` | Read the code like it owes you money |
| `loop-until-budget` | Keep pressure until budget or closure |
| `adversarial verify` | Verify only. No decoration |

## 03. Five Minimal Field Scenarios

### Scenario 1: Redis Memory Spike And Big-Key Trace

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
git checkout -b audit/redis-bigkey-scan
ultrawork +500k "scan /home/dev/github/my-cloud-vocab/ cache-control logic for Redis big-key reads, writes, expiry drift, and memory spike evidence" pipeline
git diff
```

### Scenario 2: Nginx Reverse Proxy Rate Gate And Hot Reload

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
git checkout -b ops/nginx-rate-gate
ultrawork +1M "edit local Nginx config to add limit_req and limit_conn gates, run nginx -t, and produce the reload path; do not push" -pipeline + self-repair
git diff
```

### Scenario 3: Systemd Degrade-And-Heal Boundary Test

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
git checkout -b ops/systemd-self-heal
ultrawork +1M "tune a local systemd-managed daemon and self-heal script under abnormal exit, restart backoff, log persistence, and degraded-mode pressure" -loop-until-budget
git diff
```

### Scenario 4: Multi-Environment Nginx Compliance Walk

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
ultrawork -adversarial verify "verify Nginx vhost root isolation, alias traversal, rewrite loops, and inherited throttling; output four columns: [config file | risk | core logic | fix]"
```

### Scenario 5: Shell Backup Script Boundary Tests

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
git checkout -b test/shell-backup-hardening
ultrawork +1M -adversarial review "review the target backup shell script, generate boundary tests for full disk, network timeout, permission denial, empty source, and repeated execution, then clean the workspace"
git diff
```

## 04. Five-Part Hardened Workflow

Do not let an agent touch the main branch raw.

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
git checkout -b ops/fix-target
git status --short
ultrawork +500k "find the failure, show evidence, and keep the repair surface small" pipeline
git diff
git commit -m "ops: fix bounded failure path"
```

If the diff smells wrong, kill it. No ceremony.

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
git status --short
git diff
git restore --staged <file>
git restore <file>
```

## 05. Production Practice Ledger

| Control | Pass Line | Failure Signal | Move |
|---|---|---|---|
| Branch | One task, one branch | Direct edits on main | Stop and branch |
| Budget | Start at `+500k` | Blind `+2M` | Shrink scope |
| Gateway | Local profile only | Gateway config in repo | Strip it |
| Telemetry | `DISABLE_GROWTHBOOK=1` | Missing env guard | Set it and restart |
| Nginx | `nginx -t` passes | Reload before test | Block reload |
| Systemd | Backoff and logs exist | Infinite restart loop | Add throttle and fuse |
| Git | Diff is readable | Mixed unrelated files | Split commits |
