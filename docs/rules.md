# Well-formedness rules for a BPMN model

A structurally wrong model still draws a handsome picture, but it **reads wrongly**: the token escapes the branch, or merges implicitly somewhere the reader cannot see. A diagram in a report exists to be read by somebody else, so it has to be right even though nobody will ever execute it.

Check at any point:

```bash
bpmn-lint                                      # every model in content/processes/
bpmn-lint content/processes/<name>-brief.yaml  # from step 1, before generating
```

One set of rules guards both ends of the process: it runs on a `-brief.yaml` (step 1) and on a `.bpmn` (after step 3). `--strict` exits non-zero when there are errors.

## The rules

| Code | Level | Rule |
| --- | --- | --- |
| `E-MERGE` | error | No implicit merge: several incoming flows have to pass through a gateway |
| `E-DEFAULT` | error | An exclusive or inclusive gateway that splits needs a default branch |
| `E-SPLIT-JOIN` | error | Close with the gateway type you opened with |
| `E-MSG-GATEWAY` | error | A message flow must not touch a gateway |
| `E-START-IN` / `E-END-OUT` | error | A start event has no incoming flow; an end event has no outgoing flow |
| `E-DEAD-END` / `E-NO-IN` | error | A node with nothing on one end |
| `E-UNREACHABLE` | error | A node no start event can reach |
| `W-GW-NAME` | warning | A splitting gateway should be named as a question |
| `W-BRANCH-LABEL` | warning | A branch of a splitting gateway should be labelled as an answer |

## 1. No implicit merge, `E-MERGE`

**More than one flow running straight into an ordinary task, event or gateway is not allowed.** Every confluence has to pass through a gateway.

```
WRONG                              RIGHT
  A ─┐                               A ─┐
     ├──> Task                          ├─> (X) ──> Task
  B ─┘                               B ─┘
```

BPMN permits the wrong form and gives it a meaning: each arriving token is one activation of the task. The problem is that **the reader cannot see that**; the picture looks exactly like a merge. Requiring the gateway is requiring the intention to be stated: an exclusive merge, or a wait for all.

This applies to rework loops too: a *"failed, do it again"* branch coming back has to enter a gateway before the step being redone, rather than running straight into the task.

`bpmn-brief` **inserts this gateway for you** (see "What the machine repairs" below).

## 2. The default branch, `E-DEFAULT`

**An exclusive or inclusive gateway that splits always needs a default branch**, and that branch is the **happy path**.

Without one, when every condition is false the token is stuck at the gateway and the process dies where it stands, with nothing in the picture to show it. With one, there is always a way out.

In a `.bpmn` it is the `default="flow_..."` attribute on the gateway; Camunda Modeler draws a small slash at the start of that branch.

`bpmn-brief` **sets** the first branch declared as the default, the same convention the layout uses (the branch declared first keeps the main line), so the happy path only has to be stated once.

## 3. Close with the gateway you opened with, `E-SPLIT-JOIN`

| Opened with | Must close with | If it does not |
| --- | --- | --- |
| Parallel (`+`) | Parallel | Closing with exclusive means each branch carries on once, so everything after runs twice |
| Exclusive (`×`) | Exclusive | Closing with parallel means the gateway waits forever for a branch that never arrives |
| Event-based | Exclusive | (accepted: an event gateway has exactly one winning branch) |
| Inclusive (`○`) | Inclusive | |

Symmetric enclosure is the only way to keep tokens from escaping.

The rule does **not** apply to a loop-back branch: a rework loop has no closing point and does not need one. The checker detects back edges with a depth-first search and skips them.

## 4. A message flow must not touch a gateway, `E-MSG-GATEWAY`

A gateway only **routes**; it can neither receive nor send. To receive a message from another pool there has to be a **message catch event** first, and the gateway after it:

```
WRONG                                    RIGHT
  [Supplier] ─ ─ ─> (×) Accepted?         [Supplier] ─ ─ ─> (✉) Reply received ──> (×) Accepted?
```

This is the error that is **not** repaired automatically: repairing it means inserting an event, an event needs a name, and only the author knows what to call it. The checker reports it and suggests the shape of the fix.

## 5. Naming, `W-GW-NAME` and `W-BRANCH-LABEL`

A splitting gateway is named as a **question** (`Still under warranty?`) and its branches as **answers** (`Under warranty` / `Expired`, not `Yes` / `No`). A merging gateway needs no name, because it asks nothing.

## What the machine repairs, and what it leaves to you

`bpmn-brief` runs `rules.normalize()` before laying out, and prints every change it makes.

The boundary is sharp:

| Violation | Repaired? | Why |
| --- | --- | --- |
| `E-MERGE` | Yes, a merge gateway is inserted | A merge gateway **has no name**, so nobody has to be asked |
| `E-DEFAULT` | Yes, the first branch declared | Declaration order has already said which branch is the happy path |
| `E-MSG-GATEWAY` | No | It means inserting an event, and an event needs a name |
| `E-SPLIT-JOIN` | Partly | The inserted merge gateway's type is chosen to match the one that opened |
| Everything else | No | These are modelling mistakes, not mechanical ones |

The merge gateway's type is chosen by walking back from each incoming flow to the nearest splitting gateway: if every path points at the same parallel gateway, a parallel gateway is inserted; otherwise an exclusive one, which is right both for a rework loop and for exclusive branches.

## At step 3, refining in the modeler

Camunda Modeler does not prevent any of these, so after adjusting a diagram, **run it again**:

```bash
bpmn-lint content/processes/<name>.bpmn
```

Two things done in the modeler keep producing new violations:

- Drawing a second arrow into a task that already has one, giving `E-MERGE`.
- Running a message flow from an outside pool straight into a gateway, giving `E-MSG-GATEWAY`.

The report's own repository documents the full four-step working process.
