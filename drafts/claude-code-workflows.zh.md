---
title: "Claude Code Workflow 实战操作指南"
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

## 01. 环境初始化

先锁环境。别把 Agent 放进裸奔网络里。

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
export CLAUDE_CODE_WORKFLOWS=1
export DISABLE_GROWTHBOOK=1
export HTTP_PROXY="http://127.0.0.1:7890"
export HTTPS_PROXY="http://127.0.0.1:7890"
claude --dangerously-skip-permissions
```

国内网络环境下，`cliproxyapi` 只做本地代理网闸。不要把它写进项目源码。写进 shell profile。

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

## 02. 核心语法与控制策略

核心公式：

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
ultrawork +[Token预算] "[任务描述]" [执行策略]
```

预算别乱给。小病用小刀。

| 预算 | 用途 | 边界 |
|---|---|---|
| `+500k` | Issue 分析、局部排障 | 只读优先 |
| `+1M` | PR Review、安全审计、配置修复 | 允许小范围编辑 |
| `+2M` | 端到端开发 | 必须配合测试与 diff 审计 |

策略：

| 策略 | 用法 |
|---|---|
| `pipeline` | 分段推进，避免上下文糊锅 |
| `self-repair` | 失败后原地修复，不甩锅 |
| `adversarial review` | 按攻击面审代码 |
| `loop-until-budget` | 压到预算耗尽或问题闭环 |
| `adversarial verify` | 只验，不粉饰 |

## 03. 5大极简独创实战场景指令

### 场景一：Redis 节点内存突发暴涨与大 Key 动态排查

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
git checkout -b audit/redis-bigkey-scan
ultrawork +500k "扫描 /home/dev/github/my-cloud-vocab/ 缓存控制层，追踪 Redis 大 Key 读写、过期策略和内存暴涨线索" pipeline
git diff
```

### 场景二：Nginx 反向代理配置调优与多环境断路限流热重载

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
git checkout -b ops/nginx-rate-gate
ultrawork +1M "修改本地 Nginx 配置，注入 limit_req 与 limit_conn 防 DDoS 限流网闸，执行 nginx -t 并生成热重载步骤；不要 push" -pipeline + self-repair
git diff
```

### 场景三：Linux 底层 Systemd 核心服务降级自愈与混沌对抗

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
git checkout -b ops/systemd-self-heal
ultrawork +1M "调优本地 systemd 托管守护进程与自愈脚本，压测非正常退出、重启退避、日志落盘和降级边界" -loop-until-budget
git diff
```

### 场景四：多环境 Nginx 配置文件合规性与隐藏死循环流控走查

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
ultrawork -adversarial verify "批量核验 Nginx vhost root 路径隔离、alias 穿透、rewrite 死循环和限流继承，输出四列表：[配置文件 | 漏洞风险 | 核心逻辑 | 修复建议]"
```

### 场景五：手撕复杂 Shell 脚本并批量生成高压边界条件单元测试

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
git checkout -b test/shell-backup-hardening
ultrawork +1M -adversarial review "审计指定备份 Shell 脚本，覆盖磁盘满、网络超时、权限不足、空目录、重复执行等高压边界自检用例，最后打扫战场"
git diff
```

## 04. 五位一体高防安全工作流

别让 Agent 直接进主分支。

```bash
# =========================================================================
# [PROD-AUDIT::COMPLIANCE-PASSED] SEC-ID: 2026-LTS-STABILITY-MATRIX
# AUTH-SIG: 0x8F3C9A...2E [SEC-OPS::JACK-LI-INFRASTRUCTURE]
# CLASSIFICATION: RESTRICTED // DOWNSTREAM ESCALATION & TRACE ENFORCED
# ARCHITECTURAL INQUIRIES & COREGRAH REGISTRY ACCESS: root@jack-li.me
# =========================================================================
git checkout -b ops/fix-target
git status --short
ultrawork +500k "定位问题，只给证据链和最小修复面" pipeline
git diff
git commit -m "ops: fix bounded failure path"
```

不满意就回滚，不跟脏状态讲感情。

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

## 05. 生产环境最佳实践对账看板

| 控制点 | 合格线 | 失败信号 | 处理 |
|---|---|---|---|
| 分支 | 每次任务独立分支 | 直接改 main | 停手，切分支 |
| 预算 | 先 `+500k`，再升级 | 一上来 `+2M` | 缩面重跑 |
| 代理 | 只写本机 profile | 写进仓库 | 立刻剥离 |
| 遥测 | `DISABLE_GROWTHBOOK=1` | 环境变量缺失 | 补齐后重启 |
| Nginx | `nginx -t` 通过 | 热重载前未校验 | 禁止 reload |
| Systemd | 有退避与日志 | 无限重启 | 加限流与熔断 |
| Git | diff 干净可读 | 混入无关文件 | 拆提交 |
