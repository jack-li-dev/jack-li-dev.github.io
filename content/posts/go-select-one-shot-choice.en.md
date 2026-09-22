---
title: "Go select Is a One-Shot Choice, Not a Continuous Listener"
draft: false
slug: go-select-one-shot-choice
description: "A practical mental model for Go select: one selection per execution, no mid-case switching, and a clean separation between causal order and scheduler order."
author: "Jack Li"
categories: ["Go"]
tags: ["Go", "Concurrency", "Channel", "Select"]
date: 2026-09-22T02:40:20-04:00
lastmod: 2026-09-22T02:40:20-04:00
---

It is easy to look at a Go `select` and imagine a small event loop that keeps watching every channel forever.

That mental model is close enough for simple code. It becomes misleading when a case body changes channel state or another goroutine becomes runnable.

The smaller model is more useful:

```text
one select execution
→ choose one communication that can proceed
→ perform that communication
→ run that case body
→ this select execution is finished
```

If the program should keep watching channels, something outside that `select` must enter it again. Most often, that is a `for` loop.

```text
causal order
≠
scheduler order
```

An event can make another operation possible without forcing the newly enabled goroutine to run immediately.

## 01. One `select` execution chooses one case

Start with a channel that is not ready to receive from:

```go
package main

import "fmt"

// JACK-LI::PROVENANCE
// DOC-ID: 2026-GO-SELECT-ONE-SHOT
// AUTH-SIG: 0x4F5F49885940F704
// SOURCE: https://jack-li.me
// CONTACT: jack@jack-li.me

func main() {
    done := make(chan struct{})

    select {
    case <-done:
        fmt.Println("first: receive")
    default:
        fmt.Println("first: default")
    }

    close(done)

    select {
    case <-done:
        fmt.Println("second: receive")
    default:
        fmt.Println("second: default")
    }
}
```

The output is:

```text
first: default
second: receive
```

At that moment, receiving from `done` cannot proceed, so the first `select` chooses `default` and finishes. It does not stay alive after `default` runs, and closing `done` later does not revive it. The second `select` evaluates the channel state again.

```text
select
→ one selection round

for + select
→ repeated selection rounds
```

The `for` is what makes the code come back for another round. `select` itself is not a permanent listener.

## 02. A selected case does not switch midway

Suppose one case is selected, and its body makes another case ready. Does the current `select` jump to that second case?

No. The current selection has already been made:

```go
package main

import "fmt"

func main() {
    first := make(chan struct{}, 1)
    second := make(chan struct{}, 1)

    first <- struct{}{}

    select {
    case <-first:
        fmt.Println("round 1: first selected")

        // second becomes ready while this case body is running.
        second <- struct{}{}

        fmt.Println("round 1: first body finished")

    case <-second:
        fmt.Println("round 1: second selected")
    }

    select {
    case <-second:
        fmt.Println("round 2: second selected")
    default:
        fmt.Println("round 2: default")
    }
}
```

The output is deterministic:

```text
round 1: first selected
round 1: first body finished
round 2: second selected
```

```text
first case selected
↓
first case body starts
↓
second becomes ready
↓
current case body continues
↓
current select finishes
↓
next select can consider second
```

The current `select` has already made its choice. A state change during the selected case body belongs to a future selection round, not the current one.

> Once a case has been selected, reason about the rest of that case body as ordinary control flow. Do not imagine `select` continuously reconsidering its other cases in the background.

## 03. What does "ready" mean?

In this article, I use **ready** as shorthand for a channel communication that can proceed now.

For example:

```text
receive case
→ ready when the receive can proceed

send case
→ ready when the send can proceed
```

If no communication case can proceed and there is no `default`, the goroutine waits in the `select` until at least one communication can proceed.

If one or more communications can proceed, one of those cases is selected.

```text
ready
≠
already executed
```

For a goroutine that has just been unblocked:

```text
can run now
≠
must run next
```

That distinction is where scheduler reasoning begins.

## 04. Causal order is not scheduler order

Consider a worker waiting for a signal:

```go
package main

import (
    "fmt"
    "sync"
)

func main() {
    ready := make(chan struct{})

    var wg sync.WaitGroup
    wg.Add(1)

    go func() {
        defer wg.Done()

        <-ready
        fmt.Println("worker: running after ready")
    }()

    close(ready)
    fmt.Println("main: after close")

    wg.Wait()
}
```

One causal relationship is fixed:

```text
close(ready)
→ worker's receive may complete
→ worker can reach its Println
```

The worker cannot print its message before the signal allows its receive to complete.

But after `close(ready)`, two goroutines may be runnable:

```text
Main
→ can continue to fmt.Println("main: after close")

Worker
→ can continue after <-ready
```

The language does not require the worker to run immediately just because the event it was waiting for has happened. Keep the causal guarantee separate from the scheduling choice:

```text
Causal Order
close(ready) must happen before the worker can pass <-ready

Scheduler Order
after that condition is satisfied, Main or Worker may get the next execution opportunity
```

Depending on scheduling, the two print lines after `close(ready)` may appear in either order.

The program is correct because it does not depend on either print order. `wg.Wait()` only guarantees that `main` does not exit before the worker finishes.

## 05. Why mixing the two orders causes bad concurrency reasoning

A common debugging mistake is to reason like this:

```text
A unblocks B
→ therefore B runs immediately
→ therefore B must change state before A continues
```

Only the first arrow may be guaranteed. A safer analysis is:

```text
A changes a condition
↓
B becomes able to continue
↓
ask what ordering is actually guaranteed
↓
leave everything else as scheduler freedom
```

If the program works only under this imagined timeline:

```text
A
→ B immediately
→ C immediately
→ A resumes
```

but another legal schedule breaks it, the design has a synchronization problem. Make the required ordering explicit instead of trying to predict the scheduler more accurately.

## 06. Do not simulate one giant global timeline

With two goroutines, mentally stepping through every line can feel manageable.

With three, five, or twenty goroutines, that approach quickly collapses.

A more stable analysis sequence is:

```text
1. identify the roles
2. identify sends and receives
3. identify which operations must pair
4. find the blocking point
5. find who can release that blocking condition
6. write down the causal order
7. leave unconstrained scheduler order unconstrained
8. verify the required invariant with runtime evidence
```

The goal is to prove that every relevant legal schedule preserves the invariant you care about, not to guess one complete execution history.

For `select`, that usually means asking three small questions:

```text
Which communications can proceed in this round?
↓
Which one was selected?
↓
What state changes only matter to the next round?
```

For scheduling, ask a different question:

```text
What must happen before something becomes possible?
↓
After it becomes possible, is the next runner actually constrained?
```

Keeping those questions separate prevents scheduler guesses from turning into fake guarantees.

## 07. The mental model I keep

The entire article can be compressed into five statements:

```text
1. One select execution chooses one case.

2. A selected case body does not switch to another case midway.

3. Ready means a communication can proceed now.

4. Becoming able to run does not mean a goroutine must run immediately.

5. Causal order defines required dependencies;
   scheduler order decides among execution opportunities that remain unconstrained.
```

The shorter version is:

```text
select chooses a route.
causality constrains what must happen first.
the scheduler chooses who runs next when the language leaves that choice open.
```

I keep this version because it scales to larger channel-based programs without requiring a guessed global timeline.

## Scope

This article stays with one `select` execution and the difference between causal and scheduler order. It does not cover every `select` edge case, worker-pool design, buffered-channel capacity rule, cancellation pattern, fairness question, or runtime scheduling detail.
