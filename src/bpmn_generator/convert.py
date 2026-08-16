#!/usr/bin/env python3
"""Convert BPMN 2.0 XML (with BPMNDI) into the trimmed YAML consumed by bpmn.typ.

Deliberately drops everything with execution semantics: extensionElements,
zeebe:*/camunda:* namespaces, isExecutable, expressions, listeners, io mappings.
What survives is what you can *see* in a diagram.

    python3 convert.py model.bpmn -o model.yaml [--strict]
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from typing import Any

MODEL = "http://www.omg.org/spec/BPMN/20100524/MODEL"
DI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"
# NB: `di:waypoint` lives in the DD namespace, not the BPMN-DI one. Exporters
# differ here, so geometry lookups go through local-name matching instead.
BIOC = "http://bpmn.io/schema/bpmn/biocolor/1.0"
COLOR = "http://www.omg.org/spec/BPMN/non-normative/color/1.0"

# --- semantic element -> (family, subtype) -------------------------------------------------
EVENTS = {
    "startEvent": ("start", False),
    "intermediateCatchEvent": ("intermediate", False),
    "intermediateThrowEvent": ("intermediate", True),
    "boundaryEvent": ("boundary", False),
    "endEvent": ("end", True),
}
EVENT_DEFS = {
    "messageEventDefinition": "message",
    "timerEventDefinition": "timer",
    "errorEventDefinition": "error",
    "signalEventDefinition": "signal",
    "escalationEventDefinition": "escalation",
    "terminateEventDefinition": "terminate",
    "compensateEventDefinition": "compensate",
    "conditionalEventDefinition": "conditional",
    "linkEventDefinition": "link",
    "cancelEventDefinition": "cancel",
}
TASKS = {
    "task": "none",
    "userTask": "user",
    "serviceTask": "service",
    "sendTask": "send",
    "receiveTask": "receive",
    "manualTask": "manual",
    "scriptTask": "script",
    "businessRuleTask": "rule",
    "callActivity": "call",
}
GATEWAYS = {
    "exclusiveGateway": "exclusive",
    "parallelGateway": "parallel",
    "inclusiveGateway": "inclusive",
    "eventBasedGateway": "event",
    "complexGateway": "complex",
}
SUBPROCESS = {"subProcess", "transaction", "adHocSubProcess"}
GATEWAY_TAGS = set(GATEWAYS)


def markers_of(e: ET.Element) -> list[str]:
    """Behaviour markers BPMN draws along an activity's bottom edge."""
    out = []
    for c in e:
        t = local(c)
        if t == "standardLoopCharacteristics":
            out.append("loop")
        elif t == "multiInstanceLoopCharacteristics":
            out.append("mi-sequential" if c.get("isSequential") == "true" else "mi-parallel")
    if local(e) == "adHocSubProcess":
        out.append("adhoc")
    if e.get("isForCompensation") == "true":
        out.append("compensation")
    return out
DATA = {"dataObjectReference": "object", "dataStoreReference": "store", "dataInput": "input", "dataOutput": "output"}

# elements we knowingly ignore (structure, not drawn)
IGNORED = {
    "definitions", "collaboration", "process", "laneSet", "lane", "participant",
    "incoming", "outgoing", "flowNodeRef", "extensionElements", "documentation",
    "dataObject", "dataStore", "property", "category", "categoryValue",
    "conditionExpression", "text", "multiInstanceLoopCharacteristics",
    "standardLoopCharacteristics", "BPMNDiagram", "BPMNPlane", "BPMNShape",
    "BPMNEdge", "BPMNLabel", "Bounds", "waypoint", "message", "signal", "error",
    "escalation", "collaborationRef",
}


def local(e: ET.Element) -> str:
    return e.tag.split("}")[-1]


def kids(e: ET.Element, name: str) -> list[ET.Element]:
    """Direct children matching a local name, whatever namespace prefix the exporter used."""
    return [c for c in e if local(c) == name]


def kid(e: ET.Element | None, name: str) -> ET.Element | None:
    if e is None:
        return None
    for c in e:
        if local(c) == name:
            return c
    return None


def num(v: str | None, default: float = 0.0) -> float:
    try:
        f = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return round(f, 2)


def bounds_of(e: ET.Element | None) -> dict[str, float] | None:
    if e is None:
        return None
    b = kid(e, "Bounds")
    if b is None:
        return None
    return {"x": num(b.get("x")), "y": num(b.get("y")),
            "w": num(b.get("width")), "h": num(b.get("height"))}


def colors_of(e: ET.Element) -> dict[str, str]:
    """bpmn.io / OMG non-normative colour extensions."""
    out = {}
    fill = e.get(f"{{{COLOR}}}background-color") or e.get(f"{{{BIOC}}}fill")
    stroke = e.get(f"{{{COLOR}}}border-color") or e.get(f"{{{BIOC}}}stroke")
    if fill:
        out["fill"] = fill
    if stroke:
        out["stroke"] = stroke
    return out


class Converter:
    def __init__(self, root: ET.Element):
        self.root = root
        self.unsupported: list[str] = []
        self.shapes: dict[str, ET.Element] = {}
        self.edges: dict[str, ET.Element] = {}
        self.sem: dict[str, ET.Element] = {}
        self.node_pool: dict[str, str] = {}
        self.node_lane: dict[str, str] = {}
        self.default_flows: set[str] = set()
        self.category: dict[str, str] = {}
        self.parent: dict[ET.Element, ET.Element] = {}

    # -- indexing ---------------------------------------------------------------------------
    def index(self) -> None:
        for parent in self.root.iter():
            for child in parent:
                self.parent[child] = parent
        for e in self.root.iter():
            t = local(e)
            if t == "BPMNShape":
                self.shapes[e.get("bpmnElement", "")] = e
            elif t == "BPMNEdge":
                self.edges[e.get("bpmnElement", "")] = e
            elif t == "categoryValue":
                self.category[e.get("id", "")] = e.get("value", "")
            elif e.get("id"):
                self.sem.setdefault(e.get("id"), e)
            if e.get("default"):
                self.default_flows.add(e.get("default"))

        # process -> participant, and lane membership
        proc_pool = {}
        for p in self.root.iter(f"{{{MODEL}}}participant"):
            if p.get("processRef"):
                proc_pool[p.get("processRef")] = p.get("id")
        for proc in self.root.iter(f"{{{MODEL}}}process"):
            pool = proc_pool.get(proc.get("id"), "")
            for child in proc.iter():
                if child.get("id") and local(child) not in IGNORED:
                    self.node_pool.setdefault(child.get("id"), pool)
            for lane in proc.iter(f"{{{MODEL}}}lane"):
                for ref in lane.findall(f"{{{MODEL}}}flowNodeRef"):
                    if ref.text:
                        self.node_lane[ref.text.strip()] = lane.get("id", "")

    # -- pools ------------------------------------------------------------------------------
    def pools(self) -> list[dict[str, Any]]:
        out = []
        for p in self.root.iter(f"{{{MODEL}}}participant"):
            pid = p.get("id", "")
            shape = self.shapes.get(pid)
            if shape is None:
                continue
            entry: dict[str, Any] = {"id": pid, "name": p.get("name", "") or ""}
            entry["horizontal"] = shape.get("isHorizontal", "true") != "false"
            entry["bounds"] = bounds_of(shape)
            entry.update(colors_of(shape))
            lanes = []
            proc = self.sem.get(p.get("processRef", ""))
            if proc is not None:
                for lane in proc.iter(f"{{{MODEL}}}lane"):
                    lshape = self.shapes.get(lane.get("id", ""))
                    if lshape is None:
                        continue
                    lanes.append({"id": lane.get("id"), "name": lane.get("name", "") or "",
                                  "bounds": bounds_of(lshape)})
            # reading order: top-to-bottom in a horizontal pool, left-to-right
            # in a vertical one
            if entry["horizontal"]:
                lanes.sort(key=lambda l: (l["bounds"]["y"], l["bounds"]["x"]))
            else:
                lanes.sort(key=lambda l: (l["bounds"]["x"], l["bounds"]["y"]))
            if lanes:
                entry["lanes"] = lanes
            out.append(entry)
        out.sort(key=lambda p: (p["bounds"]["y"], p["bounds"]["x"]))
        return out  # y then x covers both orientations

    # -- flow nodes -------------------------------------------------------------------------
    def node(self, e: ET.Element) -> dict[str, Any] | None:
        t = local(e)
        nid = e.get("id", "")
        shape = self.shapes.get(nid)
        if shape is None:
            return None
        n: dict[str, Any] = {"id": nid, "name": (e.get("name") or "").strip()}

        if t in EVENTS:
            family, throw = EVENTS[t]
            n["kind"] = "event"
            n["event"] = family
            defs = "none"
            for child in e:
                if local(child) in EVENT_DEFS:
                    defs = EVENT_DEFS[local(child)]
                    break
            n["definition"] = defs
            n["throw"] = throw or defs in ("terminate",)
            if family == "boundary":
                n["attached-to"] = e.get("attachedToRef", "")
                n["interrupting"] = e.get("cancelActivity", "true") != "false"
        elif t in TASKS:
            n["kind"] = "task"
            n["task"] = TASKS[t]
            m = markers_of(e)
            if m:
                n["markers"] = m
        elif t in SUBPROCESS:
            n["kind"] = "subprocess"
            n["expanded"] = shape.get("isExpanded", "false") != "false"
            n["triggered-by-event"] = e.get("triggeredByEvent", "false") != "false"
            if t == "transaction":
                n["transaction"] = True
            m = markers_of(e)
            if m:
                n["markers"] = m
        elif t in GATEWAYS:
            n["kind"] = "gateway"
            n["gateway"] = GATEWAYS[t]
            if GATEWAYS[t] == "exclusive":
                n["marker"] = shape.get("isMarkerVisible", "false") != "false"
            if GATEWAYS[t] == "event":
                # BPMN distinguishes the three event-gateway renderings by these
                # two attributes rather than by element name
                n["event-type"] = e.get("eventGatewayType", "Exclusive").lower()
                n["instantiate"] = e.get("instantiate", "false") != "false"
        elif t in DATA:
            n["kind"] = "data"
            n["data"] = DATA[t]
            if t in ("dataInput", "dataOutput"):
                n["direction"] = "input" if t == "dataInput" else "output"
            # isCollection lives on the referenced dataObject, not the reference
            ref = self.sem.get(e.get("dataObjectRef", ""))
            if (ref is not None and ref.get("isCollection") == "true") or \
                    e.get("isCollection") == "true":
                n["collection"] = True
        elif t == "textAnnotation":
            n["kind"] = "annotation"
            txt = kid(e, "text")
            n["text"] = (txt.text or "").strip() if txt is not None else ""
            n.pop("name", None)
        elif t == "group":
            n["kind"] = "group"
            n["name"] = self.category.get(e.get("categoryValueRef", ""), "")
        else:
            return None

        n["bounds"] = bounds_of(shape)
        lb = bounds_of(kid(shape, "BPMNLabel"))
        if lb and lb["w"]:
            n["label"] = lb
        n.update(colors_of(shape))
        pool = self.node_pool.get(nid)
        if pool:
            n["pool"] = pool
        lane = self.node_lane.get(nid)
        if lane:
            n["lane"] = lane
        return n

    def nodes(self) -> list[dict[str, Any]]:
        out = []
        for e in self.root.iter():
            t = local(e)
            if t.startswith("BPMN") or t in ("Bounds", "waypoint"):
                continue
            if t in IGNORED or t in ("sequenceFlow", "messageFlow", "association", "dataAssociation",
                                     "dataInputAssociation", "dataOutputAssociation"):
                continue
            n = self.node(e)
            if n:
                out.append(n)
            elif e.get("id") and e.get("id") in self.shapes:
                self.unsupported.append(f"{t}#{e.get('id')}")
        # deterministic paint order: containers first, then nodes
        order = {"group": 0, "annotation": 3, "data": 2}
        out.sort(key=lambda n: (order.get(n["kind"], 1), n["bounds"]["y"], n["bounds"]["x"]))
        return out

    # -- connections ------------------------------------------------------------------------
    def flows(self) -> list[dict[str, Any]]:
        out = []
        kinds = {"sequenceFlow": "sequence", "messageFlow": "message", "association": "association",
                 "dataInputAssociation": "data", "dataOutputAssociation": "data"}
        for e in self.root.iter():
            t = local(e)
            if t not in kinds:
                continue
            fid = e.get("id", "")
            edge = self.edges.get(fid)
            if edge is None:
                continue
            # Data associations name their far end in a *child element*, and take
            # their near end from the activity they are declared inside.
            if t in ("dataInputAssociation", "dataOutputAssociation"):
                host = self.parent.get(e)
                host_id = host.get("id", "") if host is not None else ""
                ref = kid(e, "targetRef" if t == "dataOutputAssociation" else "sourceRef")
                far = (ref.text or "").strip() if ref is not None else ""
                src, tgt = ((host_id, far) if t == "dataOutputAssociation" else (far, host_id))
            else:
                src, tgt = e.get("sourceRef", ""), e.get("targetRef", "")
            f: dict[str, Any] = {"id": fid, "kind": kinds[t], "source": src, "target": tgt}
            name = (e.get("name") or "").strip()
            if name:
                f["name"] = name
            f["waypoints"] = [[num(w.get("x")), num(w.get("y"))]
                              for w in kids(edge, "waypoint")]
            lb = bounds_of(kid(edge, "BPMNLabel"))
            if lb and lb["w"]:
                f["label"] = lb
            if fid in self.default_flows:
                f["default"] = True
            # the conditional-flow diamond is drawn only when the source is an
            # activity; a gateway's branches carry the condition implicitly
            if kid(e, "conditionExpression") is not None:
                src = self.sem.get(e.get("sourceRef", ""))
                if src is None or local(src) not in GATEWAY_TAGS:
                    f["conditional"] = True
            if t == "association":
                f["direction"] = e.get("associationDirection", "None").lower()
            f.update(colors_of(edge))
            out.append(f)
        return out

    # -- assembly ---------------------------------------------------------------------------
    def run(self, source: str) -> dict[str, Any]:
        self.index()
        pools = self.pools()
        nodes = self.nodes()
        flows = self.flows()

        xs, ys = [], []
        for b in [p["bounds"] for p in pools] + [n["bounds"] for n in nodes]:
            xs += [b["x"], b["x"] + b["w"]]
            ys += [b["y"], b["y"] + b["h"]]
        for n in nodes:
            if "label" in n:
                lb = n["label"]
                xs += [lb["x"], lb["x"] + lb["w"]]
                ys += [lb["y"], lb["y"] + lb["h"]]
        for f in flows:
            for x, y in f["waypoints"]:
                xs.append(x)
                ys.append(y)
            if "label" in f:
                lb = f["label"]
                xs += [lb["x"], lb["x"] + lb["w"]]
                ys += [lb["y"], lb["y"] + lb["h"]]
        pad = 10
        extent = {"x": min(xs) - pad, "y": min(ys) - pad,
                  "w": max(xs) - min(xs) + 2 * pad, "h": max(ys) - min(ys) + 2 * pad}

        title = ""
        for n in nodes:
            if n["kind"] == "group" and n.get("name"):
                title = n["name"]
                break

        return {
            "meta": {"id": self.root.get("id", ""), "source": source,
                     "title": title, "extent": extent, "layout": "di"},
            "pools": pools,
            "nodes": nodes,
            "flows": flows,
        }


# --- minimal YAML writer (stable key order, no dependency) --------------------------------
def dump(v: Any, indent: int = 0) -> str:
    sp = "  " * indent
    if isinstance(v, dict):
        if all(not isinstance(x, (dict, list)) for x in v.values()) and len(v) <= 4:
            return "{ " + ", ".join(f"{k}: {scalar(x)}" for k, x in v.items()) + " }"
        out = []
        for k, x in v.items():
            if isinstance(x, (dict, list)) and x and not is_inline(x):
                out.append(f"{sp}{k}:\n{dump(x, indent + 1)}")
            else:
                out.append(f"{sp}{k}: {dump(x, indent + 1) if isinstance(x, (dict, list)) else scalar(x)}")
        return "\n".join(out)
    if isinstance(v, list):
        if is_inline(v):
            return "[" + ", ".join(scalar(x) if not isinstance(x, list) else
                                   "[" + ", ".join(scalar(y) for y in x) + "]" for x in v) + "]"
        out = []
        for x in v:
            body = dump(x, indent + 1)
            out.append(f"{sp}- " + body.lstrip()[: len(body.lstrip())] if not isinstance(x, dict)
                       else f"{sp}- " + dump(x, indent + 1).lstrip())
        return "\n".join(out)
    return scalar(v)


def is_inline(v: Any) -> bool:
    if isinstance(v, list):
        return all(not isinstance(x, dict) for x in v)
    if isinstance(v, dict):
        return all(not isinstance(x, (dict, list)) for x in v.values()) and len(v) <= 4
    return True


def scalar(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return f"{v:g}"
    s = str(v)
    if s == "":
        return '""'
    if any(c in s for c in ':#{}[]&*!|>%@`"\'\n') or s.strip() != s or s.lower() in ("yes", "no", "true", "false", "null"):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    return s


def to_yaml(doc: dict[str, Any]) -> str:
    lines = ["# Generated by convert.py - do not edit by hand unless you drop `layout: di`.",
             f"# source: {doc['meta']['source']}", ""]
    for section in ("meta", "pools", "nodes", "flows"):
        val = doc[section]
        if not val:
            # keep the key: a process with no pools is legitimate, and a reader
            # should not have to tell "absent" from "empty"
            lines.append(f"{section}: []")
            lines.append("")
            continue
        lines.append(f"{section}:")
        lines.append(dump(val, 1))
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("-o", "--output")
    ap.add_argument("--strict", action="store_true", help="fail if any drawable element is unsupported")
    a = ap.parse_args()

    root = ET.parse(a.input).getroot()
    conv = Converter(root)
    doc = conv.run(a.input.split("/")[-1])

    if conv.unsupported:
        for u in sorted(set(conv.unsupported)):
            print(f"unsupported: {u}", file=sys.stderr)
        if a.strict:
            return 1

    text = to_yaml(doc)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"{a.output}: {len(doc['pools'])} pools, {len(doc['nodes'])} nodes, {len(doc['flows'])} flows")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
