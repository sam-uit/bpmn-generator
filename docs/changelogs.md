# Changelogs

Every tagged version gets an entry here. A completed item moves out of [`TODO.md`](TODO.md) and into the entry for the version that shipped it.

## v0.6.3

**`docs/` in English, and the sample data with it**

`workflow.md`, `rules.md`, `naming.md` and the remaining Vietnamese entries of this changelog, translated whole files at a time. Example step names, labels and ids moved with the prose, so each document now reads in one language throughout.

**This reverses one decision from v0.6.2.** That entry kept the README's sample brief in Vietnamese, on the grounds that `task-user-chan-doan-loi` is the name of a real step rather than English prose left untranslated. The counter-argument won: a document's examples teach a grammar, they are not a citation of the model files, and a reader meeting Vietnamese labels in an English README has to work out which parts are the convention and which are the domain. The README sample and every example in `naming.md` are now English.

What survives that is the rule underneath, stated once instead of being implied by the examples: **a slug follows the language of the label it is made from.** The slug is the label, lower case, diacritics removed, hyphenated, so a Vietnamese-labelled model has Vietnamese slugs and an English-labelled one has English slugs. Nothing in the grammar is language-specific. `CONTRIBUTING.md` said the narrower version of this ("id slugs are Vietnamese") and now says the general one.

What Vietnamese remains in `docs/` is quotation, and each piece of it is needed for the sentence around it to be true: the `[sửa]` and `[chú ý]` markers this tool actually prints, the `name="Phân loại\nhướng xử lý"` attribute from the newline bug in v0.5.0, and the ids quoted in the v0.6.2 entry below, which is a record of a decision this entry reverses. Changing the first two means changing strings in `src/`, which is a behaviour change rather than a documentation one, so the docs will follow the code there rather than lead it.

That leaves the source comments and the user-facing strings in `src/` as the whole of the remaining backlog.

## v0.6.2

**README in English**

The first file anybody reads was the last one still in Vietnamese. Translated whole rather than in pieces, which is the unit the language rule asks for: a half-translated file costs a reader more than a consistently Vietnamese one, and a README is where a stranger decides whether to keep reading.

Nothing was dropped and nothing was smoothed over in the move. Every backticked identifier, command, key and file name is character-for-character what it was, checked by comparing the two sets, so the document still says exactly what the code is called. The sample data stays Vietnamese, because `task-user-chan-doan-loi` and `Chẩn đoán lỗi thiết bị` are the names of real steps in the report this was built for, not English prose left untranslated.

Two things were brought up to date while passing through. The list of what one pass preserves now includes the reading direction, which v0.6.0 added and the README had not caught up with. The install section now says the tests also run in CI, which v0.6.1 added.

That leaves `docs/` as the remaining Vietnamese, and it is a larger and more careful job: `workflow.md`, `naming.md` and `rules.md` carry the reference tables, so a translation pass there has to be checked against the code rather than read for sense.

## v0.6.1

**A licence, a check gate, and an ignore file that is about this repository**

Three gaps found by reading the repository as a stranger would, before packing it up.

**LICENSE.** `pyproject.toml` has declared `license = { text = "MIT" }` since the package was first published, and there was no licence file to point at. A declaration without the text is not a licence; anybody who wanted to use this had nothing to read and nothing to comply with.

**A check gate of its own.** typst-bpmn installs this package from a git tag and calls `bpmn2yaml` inside its own gate, so a tag that nothing had ever tested was what another repository pinned itself to. `.github/workflows/check.yml` runs the six test scripts on every push and pull request, on Python 3.11 and 3.12: the floor stated in `pyproject.toml` and the version typst-bpmn's CI runs on, because a syntax feature added after 3.11 would otherwise pass here and fail for the one consumer that matters. It also checks that the package imports, that all five console scripts resolve after an install, and that `pyproject.toml` and `_version.py` state the same version. The tests run against the working tree rather than an installed copy, which is what a pull request needs to check.

**`.gitignore`.** Half of it was about the other repository: `samples/`, `models/`, `plan.md`, `out2/`, `*.whl`, `*.ttf`, copied across when the tools were split out and never read again. What is left is what this repository actually produces, and each rule now says why it is there. Two are load-bearing and easy to delete by accident: `!docs/*.png`, which keeps the one committed picture out of the `*.png` sweep, and `uv.lock`, which is deliberately not committed because a lock file belongs to an application and this is a library.

## v0.6.0

**The vertical layout mode, and the last thing the `.yaml` said that `build.py` ignored**

`bpmn2yaml` has always written `horizontal:` on every pool, because that is where BPMN keeps the reading direction, on each participant's shape. `build.py` hard-coded `isHorizontal="true"` and knew one layout. A vertical model therefore went in vertical and came back horizontal, which broke the improvement loop on the single largest decision an author makes about a page, and did it silently.

**It is a layout, not a transpose.** That distinction is the whole reason this was a feature rather than four lines calling into `bpmn-rotate`. A transposed horizontal layout spaces its columns by the *width* of a task, because that is what the columns were spaced by before they were turned. A diagram that reads downwards should space them by a task's *height*, since that is the extent a task actually occupies along the flow. The same brief now comes out 532×380 read across and 380×492 read down; a transpose would have given 380×532.

The mechanism is one idea applied everywhere: **lay out and route in the flow's own frame, and map to the page once, at the end.**

- `xy(main, cross)` maps a point from that frame to the page, and `frame(box)` reads a page rectangle back into it. `main` runs along the flow, `cross` runs across the lanes.
- `node_extent(kind)` gives a shape's extent along and across the flow. A task is 100 by 80 whichever way the process reads, so reading down it occupies 80 along the flow and 100 across it, and that swap is where the tighter geometry comes from.
- `layout()` is written entirely in that frame. Columns advance along `main`, lanes stack along `cross`, and the pool header always runs along the start of the flow, which is down the left side of a pool that reads across and along the top of one that reads down.
- `route()` splits into a mapping shell and `route_frame()`, which is the old router unchanged. Inside it "right" means forward and "down" means towards the next lane, so every mode keeps the meaning it had when the only direction was left to right. There is no second copy of the routing logic to disagree with the first.
- The message routers moved into the same frame. A black box band lies across the flow whichever way the diagram reads, so in that frame it is always the band above or below, and there is still only one geometry to write.

Two things are placed rather than mapped, because they do not turn with the diagram. A label box is wide either way, so an event's name goes under the shape when the flow runs across and beside it when the flow runs down; mapping would have put it where the next shape goes. An artifact hangs across the flow for the same reason.

`isHorizontal` is now written from the model instead of being asserted, on the pool shape and on every lane shape, which also means a modeler can no longer be handed a pool turned one way with its lanes turned the other.

Measured, not asserted. Every horizontal model in the fixtures rebuilds **byte-identical** to v0.5.6, so nothing about the existing behaviour moved. `tests/fixtures/vertical-pools.bpmn` now round-trips byte-identical for the first time: `horizontal` was the last key that differed after v0.5.4 closed the pool bug. A generated vertical model is a fixed point after one pass.

**`tests/test_vertical.py`**, 21 assertions, written to tell a layout from a transpose: the pool is *not* the horizontal pool with its sides swapped, a task is still 100 by 80, lanes stand side by side starting at the same height, every sequence flow ends lower down the page than it starts, the black box is a column beside the pool, the message flow crosses at a constant height between the two facing edges, and the event label sits beside its shape rather than under it.

With this the open list is empty. Everything `bpmn2yaml` writes into a `.yaml` is now something `bpmn-brief` reads back.

`CONTRIBUTING.md` also spells out that the English-only rule covers commit messages. It was already in the list and was still the part that got missed, because a commit message is not in any file anybody reopens.

## v0.5.6

**A model with no pool is a model**

A plain process with no collaboration is legitimate BPMN and it is what a modeler writes for a diagram with no pool drawn on it. `bpmn2yaml` converted one happily, writing `pools: []`, and then `bpmn-brief` left every node with no lane and `layout()` died on `KeyError: None`. A crash on valid input, with a message about a missing dictionary key, on the simplest kind of diagram there is.

The fix reuses the implicit band from v0.5.4 one level up: a model with no real pool gets **one implicit pool holding one implicit band**. Layout, routing and the process body then work unchanged, because from their point of view there is a pool like any other. Neither is written to XML.

What comes out is the shape that went in: no `<bpmn:collaboration>` at all, one bare `<bpmn:process>`, and the `BPMNPlane` pointing at that process rather than at a collaboration. An empty collaboration would have been legal and one line cheaper, but reading it back would invent a participant the author never drew, and inventing elements is the thing the whole round trip exists to prevent.

One consequence had to be handled rather than inherited: an artifact with no pool is normally written in the collaboration, and with no collaboration there is nowhere for it to go. In a poolless model those artifacts join the one process.

Checked on `tests/fixtures/leading-comment.bpmn` from typst-bpmn, which is exactly this shape: it now builds, and every bound and waypoint comes back identical. The only additions are label boxes for the two named events, which the emitter has always written when a file arrives without them.

**`tests/test_roundtrip.py`** gains five assertions: no collaboration is written, exactly one process is, the plane points at it, the model comes back with no pool, and every node keeps its coordinates.

With this the open list is down to one item, the vertical layout mode, and it is the only thing left that `bpmn2yaml` states in the `.yaml` and `bpmn-brief` still ignores.

## v0.5.5

**An annotation can hang off a sequence flow again**

`brief.py` built a link only when one end of an `association` was a node. An association whose other end was a *flow* was skipped, the annotation was then left with no host, and the orphan sweep deleted it together with both of its associations. Annotating one branch of a gateway is the main thing annotations are for, so the case that silently lost data was the common one, and it lost it quietly: the only trace was one `[chú ý]` line counting orphans.

A data association still has to end on a node, because it moves data between an activity and a data object. Only a plain `association` may now name a flow.

Three things follow from letting a flow be a host, and each is a place where a flow is not a box:

- **Where the annotation sits.** A sequence flow has no bounds, so it stands in as a zero-sized point at the middle of its own route, and the annotation hangs below that point the way it hangs below a task. The midpoint is measured by length rather than by vertex count, because an orthogonal route is mostly short jogs plus one long run and the middle vertex is usually a corner.
- **Which process owns it.** Neither, and that is not a gap in the model. Camunda Modeler writes a flow-level annotation into the `<bpmn:collaboration>`, next to the message flows, and so does this now: an artifact with no pool is written there along with its associations. A node still lends its pool to whatever hangs off it, so nothing changes for an annotation on a task.
- **Which end is the source.** An association can be drawn from the annotation to the thing or from the thing to the annotation, and `direction` was the only record of which. The emitter used to write `sourceRef="host"` unconditionally and flipped every annotation-first association on the way through. It now follows what the file said.

Measured on `samples/b04-btvn01.bpmn`, the model that has one of these: every node, every flow, the annotation and both associations now survive a full round trip with identical coordinates, and the emitted `<bpmn:collaboration>` block matches Camunda Modeler's own element for element. The only remaining differences are the exclusive gateway `bpmn-brief` deliberately inserts to fix a merge into an event, and the two flows retargeted onto it.

**`tests/test_roundtrip.py`** gains five assertions on a document whose annotation hangs off a sequence flow: it survives, its association survives with the same two ends, it is written at collaboration level, and both come back with the same bounds and waypoints.

## v0.5.4

**A pool without a lane is a pool, not a black box**

`bpmn2yaml` wrote neither `process:` nor `blackbox:`, so `bpmn-brief` had to guess which participants were collapsed, and it guessed from the absence of `lanes:`. A participant that owns a process and declares no lane set is ordinary BPMN and the usual shape of a single-role pool. Every one of them was read as a black box: the pool lost its process, and every node it owned was moved into the first lane of whichever pool happened to be listed first.

The damage was not subtle and it was sitting in this repository's own fixtures. `samples/b04-btvn01.bpmn` has two real participants; it came back out with one, and half the model relocated. `tests/fixtures/two-blackboxes.bpmn` did not come back out at all, it crashed with `KeyError: None`, because the nodes of the flattened pool ended up with no lane to be placed in.

The fix is the same principle the coordinates already follow: **what the file states wins over what the algorithm infers.**

- `convert.py` states the kind. A participant with a `processRef` gets `process: <id>`, one without gets `blackbox: true`. Nothing is left to be deduced downstream.
- `brief.py` trusts the statement. `blackbox:` decides if present, `process:` decides next, and the lane heuristic survives only for a hand-written brief that says neither.
- A real pool with no lane set gets **one implicit band**, keyed by the pool's own id so no invented id can collide, purely so the layout has a rectangle to place nodes in. It is marked `implicit` and never written to XML, so a file that arrived with no laneSet leaves with no laneSet. When the pool's bounds are pinned, the band follows them rather than staying on the computed grid.

Two smaller faults surfaced on the way and both are the same shape, an inference beating a statement:

**The default band ignored the node's own pool.** A node in a laneless pool names a `pool:` and no `lane:`, and `brief.py` reached straight for the first band in the model. It now takes the first band *of the pool the node names*, and only then falls back. This is what let nodes migrate between pools on a round trip.

**An artifact could not stay in its own pool.** `place_artifacts` gave every artifact its host's pool. A data object shared by two tasks in two different pools therefore followed whichever host was recorded, not the pool it was declared in. An artifact that states `pool:` now keeps it, exactly as `bounds` and `waypoints` do.

Measured on the fixtures rather than asserted: `b04-btvn01` now round-trips with no node moving pool, and the only remaining differences are the gateway `bpmn-brief` deliberately inserts to fix a rule violation, and one known limitation filed below. `vertical-pools` differs by exactly one key, `horizontal`, which is the open vertical-mode item.

**`tests/test_roundtrip.py`** gains six assertions on a two-pool document where one pool declares no lane: the process survives, both processes are written, no laneSet is invented, no node changes pool, and the pool comes back byte-identical.

**Filed, not fixed**, both found by running the fixtures through: a text annotation attached to a *sequence flow* is dropped along with its associations, and a model with no pool at all still crashes. Both are in [`TODO.md`](TODO.md) with a reproducer.

**Downstream**: this changes what `bpmn2yaml` writes, so it was checked against [typst-bpmn](https://github.com/sam-uit/typst-bpmn) rather than assumed. Its three YAML-fed golden cases (`b04-btvn01`, `vertical-pools`, `leading-comment`) gain only `process:` keys, which the Typst side ignores, and no `blackbox: true` at all, because every participant in them owns a process. No golden number moves. The one case that does hold black boxes, `two-blackboxes`, is loaded through the XML parser, which has always set that flag itself. Where a black box *does* reach the Typst side through YAML from now on, the two parsers agree where they used to differ: the XML reader marked it collapsed and the YAML path drew it as an ordinary empty pool.

## v0.5.3

**Message flow routing: three shapes instead of one, and the `KeyError` that hid behind explicit waypoints**

`message_route` assumed every message flow had a collapsed participant at one end. It picked the endpoint that was not in `pool_bounds`, called it the node, and looked the *other* one up as a pool. A message flow joining two nodes therefore looked up a node id in `pool_bounds` and died with a bare `KeyError: 'Event_19kg7ym'`, a message that names the victim and says nothing about the cause.

How this survived so long is the interesting part. The first line of the function returns the author's own `waypoints` untouched, and since v0.5.0 every `.yaml` that came back from a modeler carries waypoints for every edge. The crash was therefore invisible on the improvement loop and only reachable from a hand-written brief, which is exactly the path a new user takes first. Strip the message waypoints from this repository's own sample, `samples/b04-btvn01.bpmn` converted and fed back, and the old code dies on it.

The routing is now three named methods, because there are three geometries and one of them cannot stand in for the others:

- `message_route_node_to_band`, unchanged behaviour, kept byte-identical output. The band spans the whole width so the flow drops at the node's centre x and the band contributes only a y.
- `message_route_node_to_node`, new. It picks the axis from the gap that actually exists between the two boxes rather than from the `isHorizontal` flag, which matters because that flag is still hard-coded and because a hand-placed diagram can disagree with it. Pools side by side leave a horizontal gap, pools stacked leave a vertical one, and the wider gap is the direction the message has to cross. With centres aligned it is one straight segment; otherwise it turns twice in the middle of the gap, the shape a modeler draws by hand.
- `message_route_band_to_band`, new. Two collapsed participants exchanging a message directly, one vertical segment at the centre of the span the two bands share.

Checked against the modeler rather than against itself: on `tests/fixtures/vertical-pools.bpmn` with its message waypoints removed, `MF_request` comes back as `340,300 -> 540,300`, which is what Camunda Modeler drew before the waypoints were stripped.

An id that is neither a node nor a pool now raises a message that names the id and says what to do about it, instead of a `KeyError`. That is also the first user-facing string written under the new English-only rule.

**`tests/test_message_routes.py`**, 20 assertions covering all three shapes, both directions, `offset` and `stub`, and the unknown-id message. It builds a `Model` without going through `layout()` and hands it only the two dictionaries the routers read, so each case reads as coordinates in and waypoints out.

**Found while fixing this, filed rather than fixed**: a real pool that declares no lane is read as a black box, because `bpmn2yaml` writes neither `blackbox:` nor `process:` and `brief.py` falls back to "no lanes means collapsed". It loses the process and moves the pool's nodes into another pool's first lane. That is a three-file change across `convert.py`, `brief.py` and `build.py`, and mixing it into a routing fix would make both unreviewable, so it is now the open `#bug #med` in [`TODO.md`](TODO.md).

## v0.5.2

**CONTRIBUTING.md, and English as a rule**

The conventions this repository follows were, until now, held in one person's head and in a memory file outside the repository. A clone did not carry them. [`CONTRIBUTING.md`](../CONTRIBUTING.md) writes them down: language, naming, punctuation, Markdown source, changelog, dependencies, and what to run before committing. Each rule carries the reason it is a rule, because a convention with no stated reason reads as taste, and taste is negotiable at three in the morning when something needs to ship.

**English only**, from 2026-08-20, for documentation, comments, docstrings, argparse help, and every string this package prints to a user. Existing Vietnamese prose is a scheduled backlog, translated in one planned pass rather than piecemeal, because a half-translated file costs the reader more than a consistently Vietnamese one.

One exception is written into the rule: **id slugs stay Vietnamese without diacritics**. `task-user-lap-ke-hoach` is not English prose that was left untranslated, it is the name of a real process step, and translating it would break every `bpmn-span` reference in the consuming report. The grammar that produces those slugs is [`docs/naming.md`](naming.md) and it is unaffected.

The **dependency** section states the two things that are invisible from inside any single file here. The version number lives only in `src/bpmn_generator/_version.py`, which both `__init__` and `build` import, so the `exporterVersion` stamped into a generated `.bpmn` cannot drift from the installed package; `pyproject.toml` carries the same number and is the one copy updated by hand. And typst-bpmn's CI installs this package from GitHub pinned to a **tag**, so a release is invisible downstream until it is pushed and tagged, and a change to `bpmn2yaml`'s output can move typst-bpmn's golden manifest. The pin is a tag rather than a branch precisely so that move is a decision somebody made.

The **before committing** section also corrects the README, which still named one test file from the days when there was one. There are four now, 68 assertions, and they are plain scripts: `PYTHONPATH=src python3 tests/<file>.py` runs them with no test-runner dependency.

## v0.5.1

**The writing conventions applied to the code base, and four dead references**

62 uses of the em-dash across docstrings, comments and **strings printed to the user**. Replaced by meaning rather than mechanically turned into commas: a semicolon where it joins two independent clauses, a colon where it attaches a label or opens an explanation.

Four dead references surfaced during the sweep, and all four were in text a user reads and then types out:

- `bpmn-brief` printed the hint "slice with `bpmn-lane(M, ..)`, or narrower still with `bpmn-part(M, ..)`". **Neither function exists** in typst-bpmn. The right names are `bpmn-figure(M, view: (lane: ..))` and `bpmn-span(M, from:, to:)`.
- The same line pointed at `docs/bpmn-workflow.md`, which does not exist either. Three old documentation paths (`bpmn-rules.md`, `bpmn-naming.md`, `bpmn-workflow.md`) were still scattered through `brief.py`, `ids.py`, `rules.py`, `test_ids.py` and `docs/naming.md`, left over from splitting this repository out of the report. They now point at `docs/rules.md`, `docs/naming.md` and `docs/workflow.md`.

All four test files green, with no behaviour changed.

## v0.5.0

**The improvement loop keeps what the author adjusted** `#bug` `#high`

`bpmn-brief` discarded every coordinate the `.yaml` already carried and drew from scratch. With `bounds` that usually went unnoticed, because the layout is deterministic and a rerun puts things back where they were; with `waypoints` it was obvious immediately, because an edge's path is the thing most often adjusted by hand in the modeler. An arc leaving a gateway from the *bottom* edge and swinging down came back leaving from the *right* edge with a dogleg in it.

This is not a matter of taste. The improvement loop of this toolchain is exactly that the author adjusts the diagram in the modeler and then goes back to editing the `.yaml`, so every regeneration deleted precisely what had just been adjusted, and the tool worked against the process it exists to serve. The documentation did say "coordinates are deliberately not kept", but that sentence was only true for the first pass, when the `.yaml` has no coordinates at all.

Now everything the author puts in beats the algorithm, under the same rule as `row`/`col`. Specifically, what used to be redrawn and now passes straight through:

| | Before | Now |
| --- | --- | --- |
| `waypoints` on a sequence flow | re-routed | used as given |
| `waypoints` on a message flow | re-routed | used as given |
| `waypoints` on a data association | a straight line from host to artifact | used as given |
| `bounds` on a node, pool, lane, black box or artifact | computed from the grid | used as given |
| `label` on a node, edge or artifact | computed from the centre | used as given |
| `fill` / `stroke` hex | only palette names were understood | used as given, and beats the palette |
| `marker` on an exclusive gateway (`isMarkerVisible`) | lost | kept |

Pin half of them and the pinned part sits where the modeler put it while the rest sits where the grid computed it, two coordinate systems that know nothing about each other. `bpmn-brief` now prints `[chú ý]` in that case rather than quietly producing a diagram with overlapping shapes.

Three smaller bugs surfaced while measuring:

**A line break inside a name was swallowed.** `name="Phân loại\nhướng xử lý"` writes a bare newline into an XML attribute. Syntactically legal, but a parser *normalises attribute values* and turns it into a space, so the line break the author placed disappeared on every pass. It is now encoded as `&#10;`.

**Half-unit coordinates were rounded.** Every coordinate was printed with `%.0f`, which is reasonable when the grid generates all of them. But the modeler places labels on half units (`x="903.5"`), so once `bounds` pass straight through from the file, rounding them is editing the author's data.

**`exporterVersion` had stood at "0.1.0"** across three releases, which means it was stating something false rather than merely saying nothing. The version number moved into `_version.py`, one place for both `__init__` and `build`.

Measured on the five L3 models in the report: a `yaml → bpmn → yaml` pass now loses **not one line of content**. What still differs is the order of data associations within the `flows` list, because BPMN requires them to sit inside the activity rather than beside the sequence flows. The sixth model (the promotion plan) still stops at `group`, exactly as the "does not survive the loop" table says.

Added `tests/test_roundtrip.py`, 8 assertions, including a second pass to be sure the invariance is not luck.

## v0.4.0

**`bpmn-rotate`, changing a diagram's direction** `#feat` `#high`

A fifth command: `bpmn-rotate process.bpmn -o process-vertical.bpmn` turns a horizontal diagram into a vertical one, or back. This is not rotating a picture. Rotating a picture is the rendering side's job, where typst-bpmn turns the whole drawing to fit the page and the text turns with it. This changes how the diagram is *read*: pools that were bands stacked down the page become columns standing side by side, the flow runs top to bottom instead of left to right, and the text stays upright.

The transform is a **transpose**, `(x, y) → (y, x)`, not a rotation. Rotating by 90 degrees either reverses the flow or drops the first lane to the end. A transpose keeps both orders: the start stays at the top left, and the lane declared first stays first. Geometrically it is a reflection rather than a rotation, but on a drawing made entirely of axis-aligned rectangles nobody can tell.

Three places where a pure matrix multiplication gets it wrong, and they are most of what this release is:

**Containers swap their sides and glyphs do not.** Transposing `width` and `height` alike would turn a 100×80 task into 80×100, taller than it is wide, when BPMN always draws a task wider than tall whichever way the diagram reads. A 3000×250 pool, on the other hand, has to become 250×3000 or it is no longer a column. The right boundary is that containers (participant, lane, expanded subprocess, group) swap, and glyphs (task, event, gateway, data object, annotation) do not. A glyph that keeps its size has to have its **centre** transposed and its box rebuilt around that centre, rather than having its top-left corner transposed.

**Edges have to be re-anchored.** Because glyphs do not change size, a transposed waypoint no longer lies on their border. Both ends of every edge are re-anchored to the border along the direction of the adjacent segment, with the other coordinate clamped inside that border, so a vertical segment is still vertical after anchoring. The bends in between are left alone: re-routing for a vertical layout is `build.py`'s job in vertical mode, and it was recorded in [`TODO.md`](TODO.md).

**Labels transpose with their glyph.** Keeping the label's offset from the glyph's centre was tried first, so that an event's label would stay underneath as it is in the horizontal version, and then rendered: the downward edge cut straight through the text. The real convention is not "the label goes underneath" but "the label goes perpendicular to the flow", so labels transpose too and move from below to beside.

The drawing's origin is preserved: a transpose swaps the two coordinates of the top-left corner, and without translating back the diagram jumps somewhere else on the plane for no reason.

What comes out is *a transposed horizontal layout*, not a vertical layout built from scratch. It works immediately on any `.bpmn`, including files with subprocesses or groups that `bpmn-brief` cannot yet rebuild, and that is why it exists as a separate filter rather than a flag on `bpmn-brief`.

Added `tests/test_rotate.py`, 19 assertions. The most valuable one is "rotate twice and every box is back where it started": a transpose is an involution, so anywhere one direction is computed wrongly shows up on the way back. Checked on the B2B tender-assessment model, 39 shapes and 42 edges, with zero drift.

## v0.3.0

**`markers` in a brief** `#feat` `#high`

`bpmn-brief` reads `markers:` on an activity and generates the corresponding BPMN element. Until now the key was ignored in silence: `bpmn2yaml` wrote it out, but feeding that `.yaml` back into `bpmn-brief` lost the marker, so the `yaml` → `bpmn` → `yaml` loop was not invariant for any model with a loop or a multi-instance activity.

```yaml
  - id: task-empty-with-loop
    name: Loop
    kind: task
    task: user
    lane: lane1
    markers: [loop]
```

The vocabulary is taken from `convert.markers_of`, because the two ends have to agree: `loop`, `mi-parallel`, `mi-sequential`, `compensation`, `adhoc`. Plus short forms for what an author types first: `parallel` and `sequential` resolve to `mi-parallel` and `mi-sequential`.

The three groups of marker differ in how they reach the XML: `loop` and `mi-*` become a `loopCharacteristics` child element (placed last in the activity body per the XSD, after `dataOutputAssociation`); `compensation` becomes the `isForCompensation` attribute on the activity itself; and `adhoc` would require changing the element's name to `adHocSubProcess`, so it is not supported and says so.

Most of the effort went into deciding **what has to break**. A mistyped marker that is quietly dropped still produces a diagram that still opens and is missing exactly the loop the author meant to state, so four cases stop with an error: a name not in the vocabulary; a marker on a gateway or an event (BPMN only lets `tActivity` carry `loopCharacteristics`); two kinds of repetition declared at once, because the XML would then have two child elements and the modeler reads only the first; and `adhoc`. `markers: []` alone is valid everywhere, including on an event, because there is nothing in it to refuse.

The error on a gateway points straight at the right place, `gateway: parallel|exclusive|inclusive|event`, because that is almost certainly what the author meant when typing `markers: [parallel]` on a gateway.

Added `tests/test_markers.py`, 17 assertions, more than half of them error cases.

## v0.2.0

**The `yaml` → `bpmn` → `yaml` loop works and is invariant**

`bpmn-brief` accepts the `.yaml` that `bpmn2yaml` produced as input, so the brief is used once on the first pass and from the second pass on the file being edited is the `.yaml`. One pass keeps every id (node, sequence flow, message flow, data association), every element including data stores and annotations, and the default branch of every conditional gateway. Coordinates were deliberately not kept, because every generation re-laid the diagram out, and that is why the manual step in the modeler sits *inside* the loop rather than after it.

The working loop is documented in [`workflow.md`](workflow.md).

## v0.1.0

**The first Python package**

Six loose scripts in the report repository's `report/tools/` became one installable package with four console scripts: `bpmn-brief`, `bpmn-lint`, `bpmn-id`, `bpmn2yaml`. The reason for splitting them out: while the tools sat beside the content there was no telling which commit changed the report and which changed the tools, and those two things have entirely different rhythms and entirely different readers.

`convert.py` (`bpmn2yaml`) lives in this repository even though it serves the rendering side, because it is a Python tool that manipulates BPMN files. The boundary between the two repositories is the direction the data flows, not who uses it.

With `docs/naming.md`, `docs/rules.md`, and `tests/test_ids.py` with its 24 assertions.
