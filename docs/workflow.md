# How a BPMN diagram gets built

This document describes **the modeller's working loop**, not the tool's internals. After reading it you know which command to run, at which step, and which file to edit.

The source diagram for this process is [`bpmnworkflow.bpmn`](bpmnworkflow.bpmn), which was itself built by this process. Running `bpmn-lint` on it reports nine errors, and all nine are *the same* limitation of the checker: it does not yet know that a `subProcess` is a scope of its own, so it treats the subprocess as an isolated node and the start and end events inside it as nodes of the outer scope. See "What does not survive the loop yet" at the end.

## The whole picture

```
                        ┌────────────────────────────────────────────────┐
                        │                                                │
  Write <name>-brief.yaml ┴─► feed the yaml ─► [bpmn-brief] ─► <name>.bpmn │
   (once, the original)                                     │             │
                                                            ▼             │
                                                 Adjust in Modeler        │
                                                            │             │
                                                            ▼             │
                                            [bpmn2yaml] ─> <name>.yaml    │
                                                            │             │
                                                 Happy? <x>─No────────────┘
                                                            │  (edit <name>.yaml)
                                                            └─Yes──► into the report
```

![BPMN Workflow](./bpmnworkflow.png)

Two files with two different roles, which is the most important thing on this page:

| File | Role | How often it is used |
| --- | --- | --- |
| `<name>-brief.yaml` | **The original.** The first description, usually only the happy path | **Once.** Write it, generate the first `.bpmn`, then leave it alone |
| `<name>.yaml` | **The continuously improved copy.** Produced by `bpmn2yaml`, edited from then on | Many times, once per pass |

Put another way: **the brief is a launchpad, not a lasting source of truth.** After the first pass, the file you edit is `<name>.yaml`. It already carries the coordinates, it already carries everything added in the modeler, and it feeds straight back into `bpmn-brief`.

## The loop

### 1. Write `<name>-brief.yaml`, once

No coordinates, no `row`/`col`: just what the steps are and how they connect. The happy path is enough; branches and waiting events can be added on later passes.

```bash
bpmn-brief content/processes/<name>-brief.yaml -o content/processes/<name>.bpmn
```

**Declaration order carries meaning.** Among the branches leaving a gateway, the one declared *first* keeps the main line through the layout and is the default branch when the rules are repaired.

### 2. Feed the yaml, get the bpmn

One command, for both kinds of input:

```bash
bpmn-brief <name>-brief.yaml -o <name>.bpmn   # the first pass
bpmn-brief <name>.yaml       -o <name>.bpmn   # every pass after that
```

`bpmn-brief` prints everything it repaired (`[sửa] …`) and everything it refused to repair (`✗ …`). [`rules.md`](rules.md) explains the boundary between the two.

### 3. Adjust it in Camunda Modeler

Automatic layout gets the *structure* right, what comes before what and where a branch splits, and it does not get the *aesthetics* right: labels crowding each other, an arc swinging too wide, two events that should swap places. That is five minutes of dragging, not a few hundred more lines of algorithm.

This is also where things the brief cannot describe get added: data stores, annotations, analytic colour.

### 4. Convert back to yaml

```bash
bpmn2yaml <name>.bpmn -o <name>.yaml --strict
```

`--strict` exits with an error code if the file contains a drawable element the converter does not understand. **Do not drop that flag**: it is the only thing that tells you whether the diagram lost an element.

### 5. Happy with the bpmn?

- **Yes** $\rightarrow$ `<name>.yaml` is what goes into the report; typst-bpmn reads it.
- **No** $\rightarrow$ edit `<name>.yaml` and go back to step 2.

Edit `<name>.yaml`, and do **not** go back to the brief. The brief did its job on the first pass; returning to it throws away everything added in the modeler.

## What the loop preserves

One pass of `<name>.yaml` $\rightarrow$ `.bpmn` $\rightarrow$ `<name>.yaml` preserves:

- **every id**: node, sequence flow, message flow, data association;
- **every element**, including data stores and annotations, which are re-hung under their host;
- **the default branch** of every conditional gateway;
- **the behaviour markers** of an activity: `loop`, `mi-parallel`, `mi-sequential`, `compensation`;
- **every coordinate**: `bounds` on every shape, `waypoints` on every edge, node and edge `label` boxes, and the `fill`/`stroke` hex;
- **the reading direction**, `horizontal:` on each pool. Until v0.6.0 this was the one thing the `.yaml` stated and `bpmn-brief` ignored, so a vertical model came back horizontal and the author lost the single largest decision made about the page.

A second pass over the same file produces an **identical** `.yaml`. If it does not, that is a bug.

To lay a model out in the other direction, set `horizontal: false` on its pools, delete the `bounds` and `waypoints` you want recomputed, and generate again. What comes out is a vertical layout rather than a horizontal one turned on its side: the pitch along the flow is measured from the height of a task rather than its width, and the lanes are as thick as the shapes are wide. `bpmn-rotate` is still the tool for turning a diagram that is already arranged the way you want; this is the tool for generating one that way from the start.

Coordinates are **computed** only when the file does not already carry them, which is to say on the first pass from a brief. From the second pass on, the `.yaml` that `bpmn2yaml` produced carries `bounds` and `waypoints`, and whatever it carries goes straight into the result: the same rule as `row`/`col`, the author always beats the algorithm. To throw the coordinates away and lay the model out afresh, delete the `bounds` and `waypoints` keys from the `.yaml`.

Pin half of them and `bpmn-brief` prints `[chú ý]`: the pinned part sits where the modeler put it and the rest sits where the grid computed it, and those two coordinate systems know nothing about each other, so shapes can overlap.

What is **not** preserved, deliberately:

- **The id of `<bpmn:process>`.** It never appears on the diagram, so `bpmn2yaml` does not record it and the next pass generates `Process_<participant-id>`. Nothing references it.

## What does not survive the loop yet

`bpmn-brief` stops and says so when it meets:

| `kind` | Why | What to do |
| --- | --- | --- |
| `subprocess` | It needs a drawing plane of its own, which does not exist yet | Split it into a model of its own, or keep the `.bpmn` as the source of truth for that model |
| `group` | A decorative frame with no flow semantics | Drop it from the `.yaml` and redraw it in the modeler on the last pass |

Two shapes that used to fail and now do not, worth knowing because they change what the output looks like. An annotation survives whether it hangs off a node or off a sequence flow; a flow-level one is written into the collaboration, which is where Camunda Modeler puts it. A model with no pool at all, a plain process with no collaboration, comes out as a bare `<bpmn:process>` with the diagram plane pointing at the process rather than at a collaboration, which is the shape it went in as.

The `adhoc` marker stops as well, because it is not an attribute but a different element type (`adHocSubProcess`), which puts it in the same place as `subprocess`.

## Behaviour markers

The BPMN glyphs drawn along the bottom edge of an activity. Declared with `markers:` on a node, and only on an activity: `loopCharacteristics` is an attribute of `tActivity`, so events and gateways have nowhere to put it.

```yaml
  - { id: task-user-call-back, name: Call the customer back, kind: task, task: user, markers: [loop] }
```

| Name | Draws | In the XML |
| --- | --- | --- |
| `loop` | a circular arrow | `<bpmn:standardLoopCharacteristics />` |
| `mi-parallel` (`parallel`) | three vertical bars | `<bpmn:multiInstanceLoopCharacteristics isSequential="false" />` |
| `mi-sequential` (`sequential`) | three horizontal bars | `<bpmn:multiInstanceLoopCharacteristics isSequential="true" />` |
| `compensation` | a rewind arrow | the `isForCompensation="true"` attribute |

`bpmn-brief` stops and reports when a marker name is not in the table, when a marker is put on a gateway or an event, and when one activity declares two kinds of repetition at once (`loop` together with `mi-*`), because the XML then has two child elements and the modeler reads only the first. `markers: []` is valid everywhere; there is nothing in it to refuse.

An artifact attached to nothing is dropped as well, and reported (`[chú ý] …`) rather than vanishing in silence.

## See also

- [`naming.md`](naming.md), the id convention, the keyword tables, and bulk renaming
- [`rules.md`](rules.md), well-formedness: what is caught, what is repaired, and why
