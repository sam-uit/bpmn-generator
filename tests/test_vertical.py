#!/usr/bin/env python3
"""Test the vertical layout mode, run: python3 tests/test_vertical.py

Same style as the other test files: flat assertions, no pytest.

`horizontal: false` on a pool used to be carried all the way from the DI into the `.yaml`
and then ignored, so a vertical model came back horizontal and the improvement loop lost
the one thing the author had chosen about the whole page. The mode added in v0.6.0 is a
real layout rather than a transposed one, and these tests are written to tell the two
apart: a transpose would give a column pitch measured from task *widths*, and lane
thickness measured from task heights. Native layout is the other way round.
"""

import pathlib
import tempfile
import xml.etree.ElementTree as ET

import yaml

from bpmn_generator.brief import to_spec
from bpmn_generator.build import build
from bpmn_generator.convert import Converter
from bpmn_generator.rules import normalize

CASES = []

DI = "{http://www.omg.org/spec/BPMN/20100524/DI}"
DC = "{http://www.omg.org/spec/DD/20100524/DC}"


def eq(got, want, why):
    CASES.append((got == want, why, got, want))


BRIEF = """\
meta:
  id: definitions-vertical-test

pools:
  - id: participant-noi-bo
    name: Noi Bo
    horizontal: false
    lanes:
      - { id: lane-mot, name: Mot }
      - { id: lane-hai, name: Hai }
  - id: participant-doi-tac
    name: Doi Tac
    horizontal: false
    blackbox: true

nodes:
  - { id: event-start-a, name: Bat dau, kind: event, event: start, lane: lane-mot }
  - { id: task-send-gui, name: Gui ho so, kind: task, task: send, lane: lane-mot }
  - { id: task-user-nhan, name: Nhan ket qua, kind: task, task: user, lane: lane-hai }
  - { id: event-end-b, name: Xong, kind: event, event: end, lane: lane-hai }

flows:
  - { source: event-start-a, target: task-send-gui }
  - { source: task-send-gui, target: task-user-nhan }
  - { source: task-user-nhan, target: event-end-b }
  - { kind: message, source: task-send-gui, target: participant-doi-tac }
"""


def render(text: str, name: str) -> tuple[str, dict, dict]:
    """Build the brief and hand back the XML plus the shapes and edges by element id."""
    brief, _ = normalize(yaml.safe_load(text))
    with tempfile.TemporaryDirectory() as d:
        out = pathlib.Path(d) / (name + ".bpmn")
        build(to_spec(brief, name + ".yaml"), str(out))
        xml = out.read_text(encoding="utf-8")
        root = ET.parse(str(out)).getroot()
    shapes, edges = {}, {}
    for e in root.iter(f"{DI}BPMNShape"):
        b = e.find(f"{DC}Bounds")
        shapes[e.get("bpmnElement")] = dict(
            x=float(b.get("x")), y=float(b.get("y")),
            w=float(b.get("width")), h=float(b.get("height")),
            horizontal=e.get("isHorizontal"),
            label=[el for el in e.iter(f"{DI}BPMNLabel")],
        )
    for e in root.iter(f"{DI}BPMNEdge"):
        edges[e.get("bpmnElement")] = [
            (float(w.get("x")), float(w.get("y")))
            for w in e.iter("{http://www.omg.org/spec/DD/20100524/DI}waypoint")
        ]
    return xml, shapes, edges


vx, vs, ve = render(BRIEF, "vertical")
hx, hs, he = render(BRIEF.replace("horizontal: false", "horizontal: true"), "horizontal")

# --- the DI says which way it is turned -------------------------------------------------
eq(vs["participant-noi-bo"]["horizontal"], "false",
   "the pool shape states the reading direction: that is where BPMN keeps it")
eq(vs["lane-mot"]["horizontal"], "false",
   "and every lane inside it agrees, or a modeler draws the pool one way and its lanes another")
eq(hs["participant-noi-bo"]["horizontal"], "true",
   "the same brief with the flag flipped comes out horizontal, one line apart")

# --- containers turn, glyphs do not -----------------------------------------------------
pool_v, pool_h = vs["participant-noi-bo"], hs["participant-noi-bo"]
eq((pool_v["w"], pool_v["h"]) == (pool_h["h"], pool_h["w"]), False,
   "the pool is not the horizontal pool with its sides swapped: a native vertical layout"
   " measures the flow along task heights and the lanes across task widths")
eq(pool_v["h"] > pool_v["w"], True, "a vertical pool is taller than it is wide")
eq(pool_h["w"] > pool_h["h"], True, "a horizontal pool is wider than it is tall")
eq((vs["task-send-gui"]["w"], vs["task-send-gui"]["h"]), (100.0, 80.0),
   "a task is 100 by 80 whichever way the process reads: the glyph does not turn")
eq((vs["event-start-a"]["w"], vs["event-start-a"]["h"]), (36.0, 36.0),
   "and an event stays a circle, which is the case that would hide a swapped size")

# --- lanes stand side by side ------------------------------------------------------------
one, two = vs["lane-mot"], vs["lane-hai"]
eq(one["y"] == two["y"], True, "vertical lanes start at the same height")
eq(two["x"] >= one["x"] + one["w"], True,
   "and follow each other across the page, first lane leftmost, in declaration order")
eq(one["h"] > one["w"], True, "each lane is a column, not a band")
eq(one["y"] > pool_v["y"], True,
   "the lanes start below the pool's own edge: the title strip runs along the top of a"
   " vertical pool, not down its side")

# --- the flow runs downwards --------------------------------------------------------------
chain = ["Flow_event-start-a__task-send-gui",
         "Flow_task-send-gui__task-user-nhan",
         "Flow_task-user-nhan__event-end-b"]
eq([ve[f][-1][1] > ve[f][0][1] for f in chain], [True, True, True],
   "every sequence flow ends lower down the page than it starts")
eq(ve[chain[0]][0][0] == ve[chain[0]][-1][0], True,
   "two shapes in the same track are joined by one straight segment along the flow")

# --- the black box is a column, and the message crosses sideways ---------------------------
band = vs["participant-doi-tac"]
eq(band["h"] > band["w"], True,
   "a collapsed participant is a column too, beside the pool rather than under it")
eq(band["x"] >= pool_v["x"] + pool_v["w"], True, "and it stands clear of the pool")
msg = ve["MF_1"]
eq(msg[0][1] == msg[-1][1], True,
   "the message flow crosses the page at a constant height: across the flow, not along it")
eq((msg[0][0], msg[-1][0]),
   (vs["task-send-gui"]["x"] + vs["task-send-gui"]["w"], band["x"]),
   "leaving the task's near face and landing on the band's near face")

# --- labels move out of the way of the flow -------------------------------------------------
start = vs["event-start-a"]
lab = start["label"][0].find(f"{DC}Bounds")
eq(float(lab.get("x")) >= start["x"] + start["w"], True,
   "an event label sits beside the shape when the process reads downwards; underneath it"
   " would be where the next shape goes")

# --- and the whole thing survives the loop ---------------------------------------------------
brief, _ = normalize(yaml.safe_load(BRIEF))
with tempfile.TemporaryDirectory() as d:
    first = pathlib.Path(d) / "v1.bpmn"
    build(to_spec(brief, "v1.yaml"), str(first))
    model = Converter(ET.parse(str(first)).getroot()).run("v1.bpmn")
    second = pathlib.Path(d) / "v2.bpmn"
    b2, _ = normalize(model)
    build(to_spec(b2, "v2.yaml"), str(second))
    eq(second.read_text(encoding="utf-8"), first.read_text(encoding="utf-8"),
       "a second pass changes nothing: the direction survives the loop like any coordinate")
eq([p.get("horizontal") for p in model["pools"]], [False, False],
   "and it comes back stated, not inferred from the shape of the bounds")


def main() -> int:
    bad = [c for c in CASES if not c[0]]
    for ok, why, got, want in CASES:
        if not ok:
            print(f"  x {why}\n      got : {got!r}\n      want: {want!r}")
    print(f"bpmn_generator vertical mode: {len(CASES) - len(bad)}/{len(CASES)} passed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
