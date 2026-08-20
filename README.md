# bpmn-generator

Write a BPMN 2.0 diagram as one YAML description instead of dragging boxes around a modeler.

```bash
uv run bpmn-brief quy-trinh-brief.yaml -o quy-trinh.bpmn
```

You declare **what the steps are and how they connect**; where each element sits, how wide the columns are, how each edge runs, and the whole BPMNDI block are the computer's problem. The result opens in Camunda Modeler as an ordinary BPMN file.

## Why

A graphical modeler is good for one diagram and bad for twenty that have to agree with each other. Three things it cannot enforce:

- **Structural rules.** A modeler will happily let two flows run straight into one task, or an exclusive gateway have no default branch. It still draws nicely, but it reads wrongly: the token "escapes" the branch, or merges somewhere the reader cannot see. `bpmn-lint` catches those, and `bpmn-brief` repairs the ones that can be repaired without naming anything.
- **An id convention.** `Task_1` and `Gateway_3` are what a modeler produces. But an id is what somebody else has to type back in when they cut a slice of the diagram into a report. `task-user-lap-ke-hoach` says what it is. `bpmn-id` generates, checks, and renames in bulk.
- **A readable diff.** Two `.bpmn` files differing by a few coordinates make `git diff` useless. A brief file diffs exactly where you edited it.

## Five commands

| Command | Job |
| --- | --- |
| `bpmn-brief <name>-brief.yaml -o <name>.bpmn` | Generate: layer the graph, lay it out, repair the rules it can repair |
| `bpmn-lint <file>` | Structural rules plus the id convention. Takes `.bpmn` or `.yaml` |
| `bpmn-id <file> --rename --also <...>` | Rename ids in bulk to the convention, fixing every reference |
| `bpmn2yaml <file>.bpmn -o <file>.yaml` | Convert to the compact YAML [typst-bpmn](https://github.com/sam-uit/typst-bpmn) reads |
| `bpmn-rotate <file>.bpmn -o <file>-doc.bpmn` | Turn a finished diagram: horizontal to vertical, or back |

## Horizontal or vertical

`bpmn-rotate` changes how the diagram is *read*, it does not rotate a picture. Pools that were bands stacked down the page become columns standing side by side, the flow runs top to bottom instead of left to right, and the text stays upright.

The transform is a transpose, `(x, y) → (y, x)`, not a rotation: turning by 90 degrees either reverses the flow or drops the first lane to the end. The subtlety is that **containers swap their sides and glyphs do not**: a 3000×250 pool has to become 250×3000, while a task stays 100×80, because BPMN always draws a task wider than tall whichever way the diagram reads.

What comes out is a transposed horizontal layout rather than a vertical layout built from scratch, so every bend stays where it was. In exchange it works on any `.bpmn`, including files with subprocesses and groups.

Since v0.6.0 there is a second way, and the two are for different situations. `bpmn-rotate` turns a finished diagram, coordinates and all, and never asks what the shapes mean. `bpmn-brief` now **lays out** in whichever direction the `.yaml` states: set `horizontal: false` on a pool, drop the `bounds` and `waypoints` you want recomputed, and generate again. That is a layout in its own right rather than a turned one, which shows in the numbers: the same brief comes out 532×380 read across and 380×492 read down, not 380×532, because the pitch along the flow is measured from the height of a task when the flow runs down and from its width when it runs across.

Reach for `bpmn-rotate` to turn a diagram you have already arranged by hand, and for `horizontal:` to generate one in the direction you want from the start.

## The working loop

A brief is written **once**. After the first pass, the file you edit is the `.yaml` that `bpmn2yaml` produced, and it feeds straight back into `bpmn-brief`:

```
<name>-brief.yaml ──► [bpmn-brief] ──► <name>.bpmn ──► Camunda Modeler
   (the original,                                            │
    written once)                                      [bpmn2yaml]
                                                             │
                         ┌── not happy: edit <name>.yaml ────┤
                         │                                   │
                         └──────► [bpmn-brief] ◄─────────────┘
```

One pass preserves **every id** (node, sequence flow, message flow, data association), **every element** including data stores and annotations, the **default branch** of every gateway, **every coordinate you adjusted by hand in the modeler** (`bounds`, `waypoints`, label positions, colours), and the **reading direction** of each pool. Whatever the `.yaml` states explicitly beats the algorithm, the same rule as `row`/`col`. In full: [`docs/workflow.md`](docs/workflow.md).

As a library:

```python
from bpmn_generator import brief, ids, rules

g = rules.load_bpmn("quy-trinh.bpmn")
for f in rules.check(g):
    print(f.level, f.code, f.node, f.message)
```

## What a brief looks like

No coordinates, no `row`/`col`, just what connects to what:

```yaml
meta:
  id: definitions-xu-ly-bao-hanh
  title: Xử lý bảo hành

pools:
  - id: participant-trung-tam-dich-vu
    name: Trung Tâm Dịch Vụ
    process: process-xu-ly-bao-hanh
    lanes:
      - { id: lane-cskh, name: Tiếp Nhận }
      - { id: lane-ky-thuat, name: Kỹ Thuật Viên }

nodes:
  - { id: event-start-nhan-yeu-cau, name: Nhận yêu cầu bảo hành, kind: event, event: start, lane: lane-cskh }
  - { id: task-user-chan-doan-loi, name: Chẩn đoán lỗi thiết bị, kind: task, task: user, lane: lane-ky-thuat }
  - { id: gateway-exclusive-con-han, name: Còn hạn bảo hành?, kind: gateway, gateway: exclusive, lane: lane-cskh }
  - { id: task-user-goi-lai-khach, name: Gọi lại khách, kind: task, task: user, lane: lane-cskh, markers: [loop] }

flows:
  - { source: event-start-nhan-yeu-cau, target: gateway-exclusive-con-han }
  - { source: gateway-exclusive-con-han, target: task-user-chan-doan-loi, name: Còn hạn }
```

**Declaration order carries meaning.** Among the branches leaving a gateway, the one declared *first* keeps the main line through the layout, and is the default branch when the rules are repaired. The happy path only has to be stated once.

Declare `row`/`col` on a node and that node keeps them: **the author always beats the algorithm**.

`markers:` are the BPMN glyphs drawn along the bottom edge of an activity: `loop`, `mi-parallel`, `mi-sequential`, `compensation`. Full table in [`docs/workflow.md`](docs/workflow.md).

## The two places the machine stops

The boundary: *the machine repairs what needs no naming; anything that needs a name stops and reports.* Inserting a merge gateway is the machine's job, because a merge gateway has no label and so nobody has to be asked. A message flow touching a gateway is **not** repaired: fixing it properly means inserting a message catch event, an event needs a name, and only the author knows what to call it.

For the same reason `bpmn-id` will not shorten a ten-syllable label to three: choosing which three *is naming*. It reports `ID-LONG` and waits for you to declare a `slug:`.

## Documentation

- [`docs/workflow.md`](docs/workflow.md), the process: brief once, `.yaml` many times, what survives each pass and what does not
- [`docs/naming.md`](docs/naming.md), the id convention: the shape, the full keyword and abbreviation tables, and the bulk rename procedure
- [`docs/rules.md`](docs/rules.md), well-formedness: what is caught, what is repaired, and why
- [`CONTRIBUTING.md`](CONTRIBUTING.md), the repository's conventions: language, naming, changelog, dependencies, and what to run before committing

## Install and develop

```bash
uv sync                                                     # a development environment
uv run bpmn-lint <file>                                     # run straight from the repo
for t in tests/*.py; do PYTHONPATH=src python3 "$t"; done   # 125 assertions
```

The same tests run in CI on every push and pull request, on Python 3.11 and 3.12; see [`.github/workflows/check.yml`](.github/workflows/check.yml).

To use it from another project, declare a path dependency so that editing the library is visible immediately:

```toml
[tool.uv.sources]
bpmn-generator = { path = "../bpmn-generator", editable = true }
```

The path is relative *to the other project's `pyproject.toml`*, not to the directory you are standing in. A repository one level deeper needs `../../bpmn-generator`.

## Related

[typst-bpmn](https://github.com/sam-uit/typst-bpmn) renders these files as figures in a Typst document. The boundary between the two repositories is **the direction the data flows**:

```
brief.yaml ──► .bpmn         bpmn-generator   (authoring)
.bpmn ──► .yaml ──► figure    typst-bpmn      (rendering)
```

`bpmn2yaml` lives here even though it serves the rendering side, because it is a Python tool that manipulates BPMN files, and keeping them together means there is one place to fix when the schema changes.
