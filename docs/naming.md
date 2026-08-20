# The id convention for BPMN elements

The id of a BPMN element is not an internal detail of the model file: it is the thing **an author has to type back in by hand**.

```typ
#bpmn-span(M, from: "gateway-exclusive-triage-repair-route", to: "task-send-ship-unit-to-vendor",
           lane: "Technicians")
#bpmn-span(M, from: "task-user-check-parts-stock", to: "task-user-issue-parts")
```

```yaml
- ask: Why is the wait for parts so long?
  node: gateway-exclusive-parts-in-stock        # what the whywhy chain anchors to
```

Compared with the old `Gateway_1`, `Task_3`, `Gateway_7`, these are longer, but reading one tells you the type and the subtype without opening the model file to look them up.

So an id has to say what it is. Three goals, **in priority order**, and when two of them conflict the earlier one wins:

1. **Unique**: no two elements ever share an id.
2. **Consistent**: the same kind of element always has the same shape of id, with no exceptions.
3. **Explicit**: reading the id tells you the type, the subtype, and the name.

The tools: `bpmn-id` (check and bulk rename), and `bpmn-lint`, which calls it on every brief.

## The shape

```
<type>-<subtype>-<subsubtype>-<name>[-<hash>]
```

| Slot | Required | Contents |
| --- | --- | --- |
| `type` | yes | The element type, a closed set, see the table below |
| `subtype` | when the type has one | The subtype: `start`/`end`, `user`/`service`, `exclusive`/`parallel`, and so on |
| `subsubtype` | when there is one | For an event, what it catches or throws with (`message`, `timer`, `signal`, …) |
| `name` | yes | A slug taken from the label, at most **5 syllables** |
| `hash` | only on a collision | 6 hash characters, added to **both** of the colliding elements |

A slot with nothing in it is **left out entirely**, never filled with a placeholder:

```
task-lap-ke-hoach            ✓  an ordinary task
task-none-lap-ke-hoach       ✗  an empty slot is where a typo goes to be born
```

**The slug follows the label's language.** It is the label, lower case, diacritics removed, hyphenated. A model whose labels are Vietnamese therefore has Vietnamese slugs without diacritics, and one whose labels are English has English slugs. Nothing in the grammar is language-specific, and the examples below are in English because this document is.

Worked examples:

```
event-start-message-warranty-request     event · start · by message
event-intermediate-timer-window-expired  event · intermediate · timer
task-user-draft-the-plan                 task · a person working on the system
task-service-measure-kpi                 task · the system running by itself
gateway-exclusive-within-budget          gateway · exclusive
gateway-parallel-roll-out-together       gateway · parallel
participant-hong-ha-trading-jsc          pool
lane-marketing-department                lane
flow-gwy-tsk-within-budget               flow · from a gateway · to a task · branch label
message-tsk-prt-request-support          message flow · from a task · to a participant
definitions-l03-management-promotion-plan    file level: takes the file name
```

The three **file-level** ids (`definitions`, `collaboration`, `process`) take the *file name* as their name slot rather than the process title: they are never typed back into a function, the file name is already short and already unique within the repository, and opening the file confirms the match immediately.

For the same reason, the ids of **pools and lanes** are not capped at five syllables: a slice is requested by *display name* (`bpmn-figure(M, view: (lane: "Parts Store"))`), not by id. Only the ids that really do get typed again, tasks, events and gateways, have to be short.

## The keyword tables

### Slot 1: `type` (a closed set)

| Keyword | Short form | BPMN element |
| --- | --- | --- |
| `collaboration` | (none) | `<collaboration>`: the frame holding the pools |
| `definitions` | (none) | `<definitions>`: the root of the file |
| `event` | `evt` | `startEvent`, `intermediateCatch/ThrowEvent`, `endEvent`, `boundaryEvent` |
| `flow` | `flw` `seq` | `sequenceFlow` |
| `gateway` | `gwy` | every kind of gateway |
| `lane` | `lnn` | `<lane>` |
| `message` | `msg` | `messageFlow` |
| `participant` | `prt` `poo` | `<participant>`, a pool |
| `process` | `prc` | `<process>` |
| `subprocess` | `sub` | `subProcess` |
| `task` | `tsk` | every kind of task |

### Slot 2: `subtype`

**Events** (`event`)

| Keyword | Short form | Meaning |
| --- | --- | --- |
| `boundary` | `bdr` | A boundary event, attached to a task |
| `end` | `end` | End |
| `intermediate` | `int` | Intermediate, catching or throwing |
| `start` | `stt` | Start |

**Tasks** (`task`, `subprocess`)

| Keyword | Short form | Meaning |
| --- | --- | --- |
| `call` | `cal` | `callActivity`: calls another process |
| `manual` | `man` | Manual work, with no system support |
| `receive` | `rcv` | Waits to receive a message |
| `rule` | `rul` | `businessRuleTask`, a decision by rule or DMN |
| `script` | `scr` | A script run in the engine |
| `send` | `snd` | Sends a message |
| `service` | `svc` | The system performs it by itself |
| `user` | `usr` | A person working on the system |

An ordinary task (`task: none` in a brief) **has no slot 2**.

**Gateways** (`gateway`)

| Keyword | Short form | Meaning |
| --- | --- | --- |
| `complex` | `cmx` | A complex merge condition, better avoided |
| `event` | `evt` | `eventBasedGateway`: branches on whichever event arrives first |
| `exclusive` | `exc` | Exactly one branch |
| `inclusive` | `inc` | One or more branches |
| `parallel` | `par` | Every branch |

For **flows** (`flow`, `message`), slots 2 and 3 are **the types of the two ends**, in short form:

```
flow-gwy-tsk-...     from a gateway to a task
flow-evt-gwy-...     from an event to a gateway
message-tsk-prt-...  from a task to a participant
```

### Slot 3: `subsubtype` (events only)

| Keyword | Short form | Meaning |
| --- | --- | --- |
| `compensation` | `cmp` | Compensation |
| `conditional` | `cnd` | A data condition becoming true |
| `error` | `err` | A business error |
| `escalation` | `esc` | Escalation |
| `link` | `lnk` | Joins two points in the same process |
| `message` | `msg` | Receiving or sending a message |
| `signal` | `sgn` | A broadcast signal |
| `terminate` | `trm` | Ends the whole process at once |
| `timer` | `tmr` | A timer or a cycle |

### Where the short forms appear

**Only in the two type slots of a flow id.** Everywhere else the word is written out: an id is read far more often than it is typed, and `flow-gateway-task-du-ngan-sach` is longer than `flow-gwy-tsk-du-ngan-sach` without saying anything more.

The short forms are still **accepted as input**: writing `kind: evt` in a brief expands to `event`. Convenient while typing, and it has no effect on the id that comes out.

## The two places the machine stops

The repository's automation boundary: *the machine repairs what needs no naming; anything that needs a name stops and reports.* For ids there are exactly two of those.

**`ID-NONAME`: an element with no `name`.** There is nothing to put in the name slot, and the machine is not allowed to invent one. The commonest case is an unlabelled merge gateway:

```
? Gateway_1f3a9c
```

What to do: give it a name (`name: Roll-out merge`), or, if the label is deliberately empty on the drawing, declare `slug: roll-out-merge`. A label and an id are two different things.

**`ID-LONG`: a label longer than 5 syllables.** Choosing which three syllables stand for a ten-syllable label *is naming*. A mechanical truncation produces something worse than the old id:

```
"Draft the plan and estimate the budget for it"
  -> task-user-draft-the-plan-and-estimate   ✗ cut off mid-phrase
```

What to do: declare `slug:` in the brief. The author always beats the machine, the same principle as `row`/`col`:

```yaml
- id: task-user-draft-the-plan
  name: Draft the plan and estimate the budget for it
  slug: draft-the-plan
```

### A model with no brief: `<model>-slugs.yaml`

Two of the report's three models were built from a Python spec, and a `.bpmn` has nowhere to declare `slug:`. Their slug table sits beside the model:

```
content/processes/l03-core-warranty-handling.bpmn
content/processes/l03-core-warranty-handling-slugs.yaml    <- {id: the chosen name slot}
```

`bpmn-id` and `bpmn-lint` **find this file by name**, with no flag needed. The reason it has to live on rather than exist only during a migration: if the table lived only inside one command run, the next lint would report `ID-LONG` for exactly the ids that were deliberately shortened, and a false warning that keeps coming back is the fastest way to teach somebody to stop reading warnings.

Generate the initial template with `--propose-slugs`. The machine only copies the labels down; shortening them is still a person's job:

```bash
bpmn-id content/processes/<name>.bpmn --propose-slugs /tmp/slugs.yaml
```

### Merge gateways inserted by the machine

`rules.normalize()` inserts a merge gateway when several flows run into one task. That gateway has no label, which is correct BPMN, so its id takes the name of the **step it stands in front of**, `gateway-exclusive-merge-draft-the-plan`, because that is exactly what a reader calls it: "the merge gateway before Draft the plan".

## Using the tool

```bash
# 1. See what is out of line (writes nothing)
bpmn-id content/processes/<name>-brief.yaml

# 2. Declare `slug:` for the long labels, name the unnamed elements, run it again

# 3. Rename, listing EVERY file that mentions an id
bpmn-id content/processes/<name>-brief.yaml --rename \
    --also content/processes/<name>.bpmn \
           content/processes/<name>.yaml \
           content/chapter03.md \
           content/analysis/wh-ch03-warranty.yaml

# 4. Regenerate and compile, to be sure no reference was missed
bpmn-brief <name> && just report
```

`--also` is the easiest thing to get wrong: miss a file and that file keeps the old id, and Typst **reports no error**, because `bpmn-span` given an id that does not exist simply skips that element. After a rename, always open the PDF and check the figure still has all its elements.

## Where it is tested

```bash
PYTHONPATH=src python3 tests/test_ids.py      # the tool itself, 24 assertions
```

Each assertion in that file corresponds to one design decision in this document. Changing the convention means changing them too, and that is the point: a convention with no safety net drifts.

`bpmn-lint` on a `-brief.yaml` reports both the structural rules and the ids that break the convention.

On a `.bpmn` it does **not** check ids: a file that has been through Camunda Modeler may contain ids the modeler generated for newly added elements, and that belongs to step 3 of the working loop rather than being a fault in the model. The source of truth for ids is the brief; fix it there and regenerate.

See also: [`rules.md`](rules.md) for the structural rules, and `README.md` for the file naming convention.
