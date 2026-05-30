---
title: "Claude Code Dynamic Workflows Field Guide"
date: 2026-05-30T04:00:00Z
lastmod: 2026-05-30T04:00:00Z
draft: false
slug: claude-code-dynamic-workflows-field-guide
description: "Use Claude Code Dynamic Workflows to run large agent jobs, keep intermediate results out of the main context, verify runs, and save reusable workflow scripts."
mermaid: true
categories: ["AI-Coding"]
tags: ["Claude-Code", "Workflow", "JavaScript", "Troubleshooting"]
translationKey: claude-code-dynamic-workflows
---

## 01. What Dynamic Workflows Are

This article covers Claude Code Dynamic Workflows.
They fit tasks with many agents and many results.
They also fit one chat window that can fill up fast.

Say production Nginx suddenly reports a large number of 502 errors.
You need to check logs, configs, and upstream service status across 100 machines.
One Claude Code chat window usually cannot hold that scale,
because every call consumes context and the context fills up in the end.

Dynamic Workflows are JavaScript execution scripts written by Claude Code.
They run in the background, schedule dozens or hundreds of subagents,
and keep intermediate results in JavaScript variables.
They do not add those intermediate results to the current chat context.
Only the final answer returns to the chat, so context pressure stays much lower.

Normal subagent results all enter Claude Code context.
The more agents you run, the easier the context gets stuffed with intermediate output.
Dynamic Workflows keep intermediate results in JavaScript variables.
The Claude Code context mainly keeps the final answer.

### When It Fits

Full-codebase bug checks, large config migrations, cross-source validation,
and load-test plan generation all fit this pattern.
For example: scanning 500+ files, changing 200+ config files,
checking 10 APIs against each other, or generating 20 attack paths in parallel.
These tasks share the same shape: large scale, many branches,
and intermediate results that need to stay in the script while the work runs.

## 02. Skill vs Subagent vs Workflow

Many people think a Skill can replace a Workflow.
That judgment is probably a bit off.
Skill, Subagent, and Workflow are different things.

[![](/mermaid/claude-code-dynamic-workflows-en.svg)](/mermaid/claude-code-dynamic-workflows-en.svg)

Here is the difference:

| Item | Skill | Subagent | Workflow |
| ---- | ---- | ---- | ---- |
| Type | Claude Code instructions | Claude Code worker | Runtime script |
| Next step | Claude Code follows prompt | Claude Code logic | Script itself |
| Storage | Claude Code context | Claude Code context | Script variables |
| Reuse | Instruction set | Worker definition | The orchestration |
| Scale | Same as subagent | A few agents per round | Dozens to hundreds |
| Interrupted | Restart that round | Restart that round | Continue in session |

- Skill/Subagent: all results enter Claude Code context, so the context
  fills up and wastes a lot of tokens.
- Workflow: loops, branches, and intermediate results stay in the
  JavaScript script, so Claude Code context keeps only the final answer.

## 03. Three Ways to Start a Workflow

There are three ways to start a Workflow:
write `workflow` directly in the prompt,
enable `/effort ultracode` and let Claude Code decide,
or call built-in and saved workflow commands.

### Method A: Trigger It Directly in the Chat

In the chat, say "use workflow to help me check Redis slow queries".
Claude Code recognizes the keyword and generates a script.

Use this form:

```text
Use workflow to check production Redis slow queries.
Keep the budget within 150k tokens.
Scan the AOF logs from the last 2 hours.
Find every command slower than 10ms.

Environment:
- Redis 6.2 cluster, 3 masters and 3 replicas
- AOF log path: /var/lib/redis/appendonly.aof
```

After triggering, check these two places:

- The `workflow` keyword in the input box gets highlighted with color.
- If you do not want to trigger it, you can press `Alt+W` to cancel.

### Method B: Smart Mode, Let Claude Code Decide

Set `/effort ultracode`.
Claude Code decides whether to enable workflow based on task complexity.

This fits cases like these:

- You are not sure whether the task needs workflow.
- You want Claude Code to choose the right approach.
- You want higher output quality and do not care much about cost.

Keep two points in mind:

- ultracode mode only applies to the current session.
- For daily development, `/effort high` is usually better value.

### Method C: Command Call, Reuse a Saved Script

Call a built-in command or a workflow script you saved.

Built-in command:

```bash
/deep-research research a technical topic in depth
```

Custom commands:

```bash
/nginx-502-debug
/redis-bigkey-scan
```

The two commands above call your saved Nginx 502 debug script
and Redis BigKey scan script.

Keep the script paths separate:

- Session internal record: `~/.claude/projects/{PROJECT_NAME}/{SESSION_ID}/workflows`
- Reusable command save path: project-level `.claude/commands/`, user-level `~/.claude/commands/`

### Verify That It Is Actually Enabled

After enabling it, do not use it blind.
First check whether the switch is really on in the current Claude Code version.
Open `/config`, press Enter, find `dynamic workflows`,
and check that its value is `true`.
That means the current session supports Dynamic Workflows.

Then type `workflow` in the input box.
If the keyword turns colored, Claude Code has recognized the workflow trigger.
If it does not change color, or `/workflows` shows no running task,
do not treat it as enabled yet.

Run a low-risk test first:

```text
workflow 20K list the heading structure of the first 3 Markdown files in this repository.
Only output the heading tree for each file. Do not modify files.
```

After it starts, type `/workflows`.
Normally you can see phases, agents, run status, and progress.
Open one agent detail view, and you can see its status, model,
token usage, prompt, output, or tool calls.
After the task finishes, the final output should show agent count,
total elapsed time, and token usage.

If all of these match, you have run one workflow end to end.

## 04. Common Workflow Shortcuts

When workflow is running, you can press `/workflows` to view live status.

Common shortcuts:

| Shortcut | Function | Notes |
| ---- | ---- | ---- |
| `↑` / `↓` | Select phase or agent | Move in `/workflows` |
| `Enter` / `→` | Enter detail view | View prompt, tool calls, result |
| `Esc` | Go back one level | Return from agent detail to phase or list |
| `j` / `k` | Scroll detail view | Use when agent output is long |
| `p` | Pause or resume workflow | Resume in the same session |
| `x` | Stop workflow or agent | On run focus, stops whole workflow |
| `r` | Restart the running agent | Restarts only the selected agent |
| `s` | Save workflow script | Saves it as a command for later use |

Use the table above for the `/workflows` view.
Startup confirmations and running shortcuts are easier to read separately.

Before startup, you will see a few confirmation items:

1. `Yes, run it`: start this workflow run.
2. `Yes, and don't ask again`: do not repeat the same confirmation in this project.
3. `View raw script`: view the JavaScript script generated by Claude Code first.
4. `No`: cancel this workflow run.

## 05. Hard Limits

Dynamic Workflows are not unlimited.
There are two hard limits.

### Limit 1: No User Input While Running

Only permission escalation requests pause workflow.
Otherwise it runs automatically.

- The workflow script schedules agents.
  During the run, only agent permission requests can interrupt it.
- If every phase needs manual confirmation,
  split the job into several workflow runs.

### Limit 2: The Script Cannot Access the File System

The workflow script runs in a sandbox.
It cannot directly operate on the file system or call Node.js APIs.

There are two limits for concurrency and total count:

- 16 concurrent agents: at most 16 agents run at the same time.
- 1000 total agents: one workflow run can start at most 1000 agents in total.
- These limits prevent infinite loops from blowing up token usage.

## 06. Production Nginx 502 Troubleshooting

Say production Nginx breaks at 3 a.m. and reports a large number of 502 errors.
You need to find what failed fast.
The machine count and token usage below are a troubleshooting sample.
They show how to split workflow phases, and they are not real incident data.

### Nginx Scenario

- Environment: 100 Nginx machines, 50 backend Spring Boot services
- Symptom: 502 error rate jumps from 0.1% to 15%
- Time window: only 30 minutes, then SLA compensation is triggered

Sample troubleshooting environment:

```text
OS: Rocky Linux 9.4
Entry node: nginx-01 / 10.20.1.11 / 80, 443
Backend node: app-03 / 10.20.2.23 / 8080
Log paths: /var/log/nginx/error.log, /var/log/spring-boot/app.log
Connectivity: nginx-01 -> app-03:8080 sometimes times out
```

Tips:
SLA compensation means the service provider pays compensation
when the service misses the time or quality promised in the service-level agreement.
It is usually credits, extra service time, or fee reduction.

### Traditional Troubleshooting, 2 Hours

1. SSH into each machine and read Nginx error.log.
2. Check upstream config and confirm backend service status.
3. Read backend service logs and look for timeouts or connection refusal.
4. Compare timelines and find the failure propagation path.

### Use Workflow to Troubleshoot One Nginx 502 Incident, 8 Minutes

```text
workflow +230k use Haiku for parallel scans and Opus for combined analysis.
Production Nginx has many 502 errors. Find what failed:

1. Use 20 Haiku agents to scan error.log on 100 Nginx machines.
   Scan the last 1 hour in parallel.
   - Extract every 502-related error.
   - Count 502 errors per machine and their time distribution.
   - Find the upstream address with the most 502 errors.

2. Use 10 Haiku agents to check backend service status in parallel.
   - SSH into backend servers and read Spring Boot logs.
   - Check JVM heap memory and GC logs.
   - Check database connection pool status.

3. Use 5 Haiku agents for cross-checks.
   - Compare Nginx 502 timestamps with backend exception timestamps.
   - Check network jitter and DNS resolution errors.
   - Read load balancer config change records.

4. Use Opus to combine all evidence and output the failure reason and fix plan.

Environment:
- Nginx config path: /etc/nginx/nginx.conf
- Backend service log: /var/log/spring-boot/app.log
- Database connection pool: HikariCP
```

### Nginx Output

```text
Failure reason analysis:
1. Backend service spring-boot-api-03 triggered Full GC at 02:47:23.
2. Full GC paused the service for 8 seconds, and all requests timed out.
3. Nginx upstream timeout was set to 5 seconds, so it returned 502.
4. The load balancer did not remove the bad node in time, so 502 errors spread.

Fix plan:
1. Restart spring-boot-api-03 immediately to clear heap memory.
2. Change Nginx upstream timeout to 10 seconds.
3. Set load balancer health check interval to 3 seconds.
4. Tune JVM parameters to avoid Full GC.

Token usage:
- 20 Haiku agents, Phase 1: 120k tokens
- 10 Haiku agents, Phase 2: 60k tokens
- 5 Haiku agents, Phase 3: 30k tokens
- 1 Opus agent, Phase 4: 15k tokens
- Total: 225k tokens, within budget
```

## 07. Redis BigKey Check and Fix

Say a production Redis cluster suddenly has slow queries.
You suspect a BigKey is blocking Redis.
The QPS, latency, and token usage below only show the troubleshooting format.
They are not real incident data.

### Redis Scenario

- Environment: Redis 6.2 cluster, 3 masters and 3 replicas, 100k QPS
- Symptom: slow query logs spike, P99 latency jumps from 5ms to 200ms
- Impact: user login times out, order payment fails

Sample troubleshooting environment:

```text
OS: Ubuntu Server 22.04
Master node: redis-master-01 / 10.30.1.10 / 6379
Replica node: redis-replica-01 / 10.30.1.11 / 6379
Application node: api-02 / 10.30.2.12
Log paths: /var/log/redis/redis-server.log, /var/lib/redis/appendonly.aof
Connectivity:
  api-02 -> redis-master-01:6379 normal
  slow queries concentrate on HGETALL
```

P99 latency means you sort requests in a time window from fastest to slowest,
then read the latency at the 99% position.
If P99 jumps from 5ms to 200ms, the slowest tail of requests is already much slower.
Login and payment paths feel it first.
At that point, keep checking BigKey, slow queries, lock waits, or network jitter.
You need to confirm what is dragging the Redis main thread.

HGETALL reads all fields in a Hash in one operation.
If the key is large, it can occupy the Redis main thread for a long time.
HSCAN scans in batches with a cursor and reads only a small slice each time.
Replacing HGETALL with HSCAN reduces the blocking time of one operation.

### Use Workflow to Check It

```text
workflow +150k use Haiku for parallel scans and Opus for combined analysis.
Production Redis cluster has slow queries. Help me check BigKey:

1. Use 10 Haiku agents to scan AOF logs in parallel, last 1 hour.
   - Extract HGETALL, SMEMBERS, ZRANGE, and other commands that may trigger BigKey.
   - Count access frequency and data size for each key.
   - Find the top 20 suspected BigKeys.

2. Use 6 Haiku agents for cross-checks, 3 agents per suspected BigKey.
   - Agent 1: use MEMORY USAGE to query key memory usage.
   - Agent 2: use SLOWLOG GET to query slow query records for the key.
   - Agent 3: use CLIENT LIST to query client connection count for the key.
   - Cross-check the three agent results and confirm whether it is a real BigKey.

3. Use Opus to combine all evidence and output the failure reason and fix plan.

Environment:
- Redis version: 6.2.6
- AOF log path: /var/lib/redis/appendonly.aof
- Slow query threshold: 10ms
```

### Redis Output

```text
Failure reason analysis:
1. key "user:session:active" is a Hash with 500,000 fields.
2. Each HGETALL operation takes 180ms and triggers slow query.
3. The key is accessed 200 times per second during peak hours,
   blocking the Redis main thread.

Fix plan:
1. Split the BigKey immediately:
   shard "user:session:active" into 100 keys by user_id hash.
2. Change business code:
   replace HGETALL with HSCAN and avoid reading all fields at once.
3. Configure Redis slow query alert: slowlog-log-slower-than 5000, 5ms.
4. Scan BigKeys regularly: run redis-cli --bigkeys once every day before dawn.

Token usage:
- 10 Haiku agents, Phase 1: 80k tokens
- 6 Haiku agents, Phase 2: 48k tokens
- 1 Opus agent, Phase 3: 12k tokens
- Total: 140k tokens, within budget
```

## 08. Save It as a Reusable Command

When workflow is running, you can enter the `/workflows` view,
select a run, and press `s` to save the script.

Save paths:

- Project-level: `.claude/commands/`
- User-level: `~/.claude/commands/`

`~/.claude/projects/{PROJECT_NAME}/{SESSION_ID}/workflows`
is the session internal record path.
It is not the right save path for reusable commands.

Recommended command form:

```bash
/<workflow-name>
/nginx-502-debug
/redis-bigkey-scan
```

Reference script:

```javascript
// JACK-LI::PROVENANCE
// DOC-ID: 2026-CLAUDE-CODE-DYNAMIC-WORKFLOWS
// AUTH-SIG: 0x4E70186531BF792E
// SOURCE: https://jack-li.me
// CONTACT: jack@jack-li.me

export const meta = {
  name: 'nginx-502-debug',
  description: 'Nginx 502 troubleshooting workflow',
  phases: [
    { title: 'Scan', detail: 'Scan Nginx logs' },
    { title: 'Check', detail: 'Check backend services' },
    { title: 'Verify', detail: 'Cross-check evidence' },
    { title: 'Report', detail: 'Combined analysis' },
  ],
}

phase('Scan')
const logs = await parallel(
  nginxServers.map(server => () =>
    agent(`Scan error.log on ${server}`, { model: 'haiku' })
  )
)

phase('Check')
const services = await parallel(
  backendServices.map(svc => () =>
    agent(`Check status of ${svc}`, { model: 'haiku' })
  )
)

phase('Verify')
const timeline = await agent('Cross-check timeline', { model: 'haiku' })

phase('Report')
const report = await agent('Analyze failure reason', { model: 'opus' })

return { logs, services, timeline, report }
```

## 09. Small Summary

Dynamic Workflows are how Claude Code schedules many subagents.
They fit large scans, migrations, and cross-checks.

1. Scale: one workflow run can schedule dozens or hundreds of agents.
2. Context saving: intermediate results stay in JavaScript variables
   and do not occupy the chat window.
3. Reuse: after saving the script, call it directly next time
   and avoid extra token waste.
4. Cost control: use Haiku for parallel scans and Opus for analysis,
   so token usage is predictable.
