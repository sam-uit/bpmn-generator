#!/usr/bin/env python3
"""Test `bpmn_generator.build` message flow routing, run: python3 tests/test_message_routes.py

Same style as `test_ids.py` and `test_rotate.py`: flat assertions, no pytest.

Routing is pure geometry over two boxes, so the tests build a `Model` without going
through `layout()`; they hand it the two dictionaries the routers actually read,
`nodes` and `pool_bounds`. That keeps each case readable as coordinates in, waypoints
out, and it is the only way to test the three routing shapes independently of whichever
layout happened to produce them.

The case that made this file exist: a message flow joining two nodes in two real pools
used to look up a node id in `pool_bounds` and die with a bare `KeyError`.
"""

from bpmn_generator.build import Model

CASES = []


def eq(got, want, why):
    CASES.append((got == want, why, got, want))


def node(x, y, w=100, h=80):
    return dict(x=x, y=y, w=w, h=h, cx=x + w / 2, cy=y + h / 2)


def band(x, y, w, h):
    return dict(x=x, y=y, w=w, h=h)


def model(nodes=None, bands=None):
    m = Model.__new__(Model)
    m.nodes = nodes or {}
    m.pool_bounds = bands or {}
    return m


def route(m, src, dst, **kw):
    return m.message_route(dict(src=src, dst=dst, **kw))


# --- an author's own waypoints always win --------------------------------------------
m = model({"a": node(0, 0)}, {"P": band(0, 300, 600, 60)})
eq(route(m, "a", "P", waypoints=[[1, 2], [3, 4]]), [(1.0, 2.0), (3.0, 4.0)],
   "explicit waypoints are returned untouched, the same rule as row and col")

# --- node to black box band ------------------------------------------------------------
m = model({"a": node(200, 100)}, {"P": band(160, 400, 800, 60)})
eq(route(m, "a", "P"), [(250.0, 180.0), (250.0, 400.0)],
   "band below: leaves the node's bottom edge at its centre x, stops at the band's top")
eq(route(m, "P", "a"), [(250.0, 400.0), (250.0, 180.0)],
   "same geometry reversed when the band is the source, so the arrow head lands right")
eq(route(m, "a", "P", offset=40),
   [(250.0, 180.0), (250.0, 202.0), (290.0, 202.0), (290.0, 400.0)],
   "offset jogs the vertical segment sideways after a stub of MESSAGE_STUB")
eq(route(m, "a", "P", offset=40, stub=10),
   [(250.0, 180.0), (250.0, 190.0), (290.0, 190.0), (290.0, 400.0)],
   "stub overrides the length of that first segment")

m = model({"a": node(200, 300)}, {"P": band(160, 60, 800, 60)})
eq(route(m, "a", "P"), [(250.0, 300.0), (250.0, 120.0)],
   "band above: leaves the node's top edge, stops at the band's bottom")

# --- node to node, two real pools ------------------------------------------------------
# Pools standing side by side leave a horizontal gap, so the message crosses horizontally.
m = model({"a": node(240, 260), "b": node(540, 260)})
eq(route(m, "a", "b"), [(340.0, 300.0), (540.0, 300.0)],
   "aligned centres across a horizontal gap: one straight segment, no elbow")
eq(route(m, "b", "a"), [(540.0, 300.0), (340.0, 300.0)],
   "the same pair the other way round is the same line reversed")

m = model({"a": node(240, 260), "b": node(540, 400)})
eq(route(m, "a", "b"),
   [(340.0, 300.0), (440.0, 300.0), (440.0, 440.0), (540.0, 440.0)],
   "misaligned centres: two turns in the middle of the gap, the shape drawn by hand")
eq(route(m, "a", "b", offset=20),
   [(340.0, 300.0), (460.0, 300.0), (460.0, 440.0), (540.0, 440.0)],
   "offset shifts the crossing segment so two message flows do not sit on each other")

# Pools stacked as horizontal bands leave a vertical gap, so the message crosses vertically.
m = model({"a": node(240, 100), "b": node(240, 400)})
eq(route(m, "a", "b"), [(290.0, 180.0), (290.0, 400.0)],
   "aligned centres across a vertical gap: one straight segment")

m = model({"a": node(240, 100), "b": node(400, 500)})
eq(route(m, "a", "b"),
   [(290.0, 180.0), (290.0, 340.0), (450.0, 340.0), (450.0, 500.0)],
   "misaligned across a vertical gap: turns at the middle of that gap")

m = model({"a": node(400, 500), "b": node(240, 100)})
eq(route(m, "a", "b"),
   [(450.0, 500.0), (450.0, 340.0), (290.0, 340.0), (290.0, 180.0)],
   "upward and leftward is the same route read backwards")

# The axis follows the wider gap, not the pool orientation flag, so a node pair that is
# far apart sideways and only slightly apart vertically still crosses sideways.
m = model({"a": node(240, 260), "b": node(760, 300)})
eq(route(m, "a", "b")[0], (340.0, 300.0),
   "wider horizontal gap wins: leaves the right edge, not the bottom")
eq(len(route(m, "a", "b")), 4,
   "and it needs the two turns, because the centres differ by 40")

# --- band to band -----------------------------------------------------------------------
m = model({}, {"P": band(160, 60, 800, 60), "Q": band(160, 400, 800, 60)})
eq(route(m, "P", "Q"), [(560.0, 120.0), (560.0, 400.0)],
   "two full width bands: one vertical segment at the centre of the shared span")
eq(route(m, "Q", "P"), [(560.0, 400.0), (560.0, 120.0)],
   "reversed source and target reverses the segment")

m = model({}, {"P": band(0, 60, 200, 60), "Q": band(600, 400, 200, 60)})
eq(route(m, "P", "Q"), [(400.0, 120.0), (400.0, 400.0)],
   "bands that do not overlap at all fall back to the midpoint of the two centres")

# --- an id that is neither a node nor a pool ---------------------------------------------
m = model({"a": node(200, 100)}, {"P": band(160, 400, 800, 60)})
try:
    route(m, "a", "typo-id")
    got = "no error"
except SystemExit as e:
    got = str(e)
eq(got.startswith("[error] message flow refers to `typo-id`"), True,
   "an unknown id is reported by name instead of dying with a bare KeyError")
eq("waypoints:" in got, True,
   "and the message says what the author can do about it")


def main() -> int:
    bad = [c for c in CASES if not c[0]]
    for ok, why, got, want in CASES:
        if not ok:
            print(f"  x {why}\n      got : {got!r}\n      want: {want!r}")
    print(f"bpmn_generator.build message routes: {len(CASES) - len(bad)}/{len(CASES)} passed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
