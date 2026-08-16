#!/usr/bin/env python3
"""Luật well-formed cho mô hình BPMN — kiểm tra và sửa tự động.

Tách riêng khỏi `build.py` (toạ độ) và `brief.py` (bố cục) vì đây là chuyện
**cấu trúc**, không liên quan gì tới chỗ đặt phần tử. Trộn vào sẽ làm cả ba khó đọc.

Module này làm việc trên một *đồ thị chuẩn hoá* nên nạp được từ cả hai phía:

    load_brief(dict)   ->  Graph      # trước khi sinh, ở bước 1
    load_bpmn(path)    ->  Graph      # sau khi refine trong Modeler, ở bước 3

Hai việc:

    check(graph)       -> [Finding]   # lint.py dùng
    normalize(brief)   -> (brief, [Change])   # brief.py dùng

Vì sao có luật? Một mô hình sai cấu trúc vẫn vẽ ra hình đẹp, nhưng đọc sai: token
"thoát" ra khỏi nhánh, hoặc gộp ngầm ở chỗ người đọc không nhìn thấy. Sơ đồ trong báo
cáo là để người khác đọc, nên phải đúng ngay cả khi không ai chạy nó.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field

# --- mô hình đồ thị chuẩn hoá ----------------------------------------------------------
GATEWAYS = {"exclusive", "parallel", "inclusive", "event"}
# Cổng "rẽ theo điều kiện" — chỉ những loại này mới cần nhánh mặc định
CONDITIONAL_GATEWAYS = {"exclusive", "inclusive"}


@dataclass
class Node:
    id: str
    kind: str = "task"          # task | gateway | event
    gateway: str = ""           # exclusive | parallel | inclusive | event
    event: str = ""             # start | intermediate | end
    name: str = ""
    default: str = ""
    lane: str = ""


@dataclass
class Graph:
    nodes: dict[str, Node] = field(default_factory=dict)
    # (id, source, target, name)
    flows: list[tuple[str, str, str, str]] = field(default_factory=list)
    messages: list[tuple[str, str, str]] = field(default_factory=list)
    pools: set[str] = field(default_factory=set)

    def out(self, nid: str) -> list[tuple[str, str, str, str]]:
        return [f for f in self.flows if f[1] == nid]

    def inc(self, nid: str) -> list[tuple[str, str, str, str]]:
        return [f for f in self.flows if f[2] == nid]

    def is_gateway(self, nid: str) -> bool:
        n = self.nodes.get(nid)
        return n is not None and n.kind == "gateway"


@dataclass
class Finding:
    code: str
    level: str        # error | warn
    node: str
    message: str
    hint: str = ""


# --- nạp từ brief YAML -----------------------------------------------------------------
def load_brief(brief: dict) -> Graph:
    g = Graph()
    for p in brief.get("pools", []):
        g.pools.add(p["id"])
    for n in brief.get("nodes", []):
        # Artifact (kho dữ liệu, ghi chú) được vẽ nhưng không nằm trên dòng chảy: không
        # có token đi qua. Đưa vào đồ thị thì mọi luật "phải có luồng vào/ra" đều báo
        # nhầm — `load_bpmn` cũng bỏ qua chúng, hai bên phải nói cùng một thứ.
        if n.get("kind") in ("data", "annotation", "group"):
            continue
        g.nodes[n["id"]] = Node(
            id=n["id"],
            kind=n.get("kind", "task"),
            gateway=n.get("gateway", "exclusive") if n.get("kind") == "gateway" else "",
            event=n.get("event", "start") if n.get("kind") == "event" else "",
            name=n.get("name", ""),
            default=n.get("default", ""),
            lane=n.get("lane", ""),
        )
    # `bpmn2yaml` đánh dấu nhánh mặc định ở *cạnh* (`default: true`), còn BPMN khai nó ở
    # *cổng* (`default="Flow_x"`). Dịch lại ở đây thì một model chuyển đổi ngược không bị
    # `normalize` chọn lại nhánh mặc định lần nữa.
    for f in brief.get("flows", []):
        if f.get("default") is True and f.get("source") in g.nodes:
            g.nodes[f["source"]].default = f.get(
                "id", f"Flow_{f['source']}__{f['target']}")

    for i, f in enumerate(brief.get("flows", [])):
        if f.get("kind") in ("data", "association"):
            continue
        if f.get("kind") == "message":
            g.messages.append((f.get("id", f"MF_{i}"), f["source"], f["target"]))
        else:
            fid = f.get("id", f"Flow_{f['source']}__{f['target']}")
            g.flows.append((fid, f["source"], f["target"], f.get("name", "")))
    return g


# --- nạp từ .bpmn ----------------------------------------------------------------------
_XML_GATEWAY = {
    "exclusiveGateway": "exclusive",
    "parallelGateway": "parallel",
    "inclusiveGateway": "inclusive",
    "eventBasedGateway": "event",
    "complexGateway": "complex",
}
_XML_EVENT = {
    "startEvent": "start",
    "endEvent": "end",
    "intermediateCatchEvent": "intermediate",
    "intermediateThrowEvent": "intermediate",
    "boundaryEvent": "boundary",
}


def load_bpmn(path: str) -> Graph:
    root = ET.parse(path).getroot()
    loc = lambda e: e.tag.split("}")[-1]
    g = Graph()
    for e in root.iter():
        t = loc(e)
        nid = e.get("id")
        if not nid:
            continue
        if t == "participant":
            g.pools.add(nid)
        elif t == "sequenceFlow":
            g.flows.append((nid, e.get("sourceRef"), e.get("targetRef"), e.get("name") or ""))
        elif t == "messageFlow":
            g.messages.append((nid, e.get("sourceRef"), e.get("targetRef")))
        elif t in _XML_GATEWAY:
            g.nodes[nid] = Node(nid, "gateway", _XML_GATEWAY[t], "",
                                e.get("name") or "", e.get("default") or "")
        elif t in _XML_EVENT:
            g.nodes[nid] = Node(nid, "event", "", _XML_EVENT[t], e.get("name") or "")
        elif t.endswith("Task") or t in ("task", "subProcess", "callActivity"):
            g.nodes[nid] = Node(nid, "task", "", "", e.get("name") or "")
    # lane -> node
    for e in root.iter():
        if loc(e) == "lane":
            for c in e:
                if loc(c) == "flowNodeRef" and c.text and c.text in g.nodes:
                    g.nodes[c.text].lane = e.get("id")
    return g


# --- tìm điểm hợp lưu của một cổng rẽ ---------------------------------------------------
def back_edges(g: Graph) -> set[str]:
    """Cạnh quay lui = cạnh trỏ về một node đang nằm trên ngăn xếp DFS (vòng rework)."""
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in g.nodes}
    back: set[str] = set()

    def visit(u: str) -> None:
        color[u] = GREY
        for fid, s, t, _ in g.out(u):
            c = color.get(t, BLACK)
            if c == GREY:
                back.add(fid)
            elif c == WHITE:
                visit(t)
        color[u] = BLACK

    for n in list(g.nodes):
        if color.get(n) == WHITE:
            visit(n)
    return back


def reconvergence(g: Graph, split: str, back: set[str] | None = None) -> str | None:
    """Node đầu tiên mà MỌI nhánh của `split` đều đi qua.

    Dùng để kiểm tra "mở bằng cổng nào thì đóng bằng cổng đó".

    **Không đi qua cạnh quay lui.** Một nhánh rework quay về đầu quy trình thì rồi cũng
    tới được mọi thứ phía sau; tính vào sẽ báo nhầm một cổng bất kỳ ở xa là "điểm đóng".
    Nhánh nào chỉ vòng lại thì coi như không có điểm hợp lưu — và đúng là nó không có.
    """
    if back is None:
        back = back_edges(g)
    branches = [f[2] for f in g.out(split) if f[0] not in back]
    if len(branches) < 2:
        return None
    reach = []
    dist_all: list[dict[str, int]] = []
    for b in branches:
        seen = {b: 0}
        q = deque([(b, 0)])
        while q:
            u, d = q.popleft()
            if d > len(g.nodes):
                continue
            for f in g.out(u):
                if f[0] in back:
                    continue
                v = f[2]
                if v not in seen:
                    seen[v] = d + 1
                    q.append((v, d + 1))
        reach.append(set(seen))
        dist_all.append(seen)
    common = set.intersection(*reach)
    common.discard(split)
    if not common:
        return None
    return min(common, key=lambda n: max(d.get(n, 10**6) for d in dist_all))


# --- kiểm tra --------------------------------------------------------------------------
def check(g: Graph) -> list[Finding]:
    out: list[Finding] = []
    back = back_edges(g)

    for nid, n in g.nodes.items():
        inc, outs = g.inc(nid), g.out(nid)

        # R1 — không cho gộp ngầm: nhiều luồng vào phải đi qua một cổng
        if len(inc) > 1 and n.kind != "gateway":
            out.append(Finding(
                "E-MERGE", "error", nid,
                f"{_label(n)} có {len(inc)} luồng vào nhưng không phải cổng",
                "Chèn một cổng hợp lưu trước nó; `just bpmn-brief` tự làm việc này.",
            ))

        # R2 — cổng rẽ theo điều kiện phải có nhánh mặc định (happy path)
        if n.kind == "gateway" and n.gateway in CONDITIONAL_GATEWAYS and len(outs) > 1:
            if not n.default:
                out.append(Finding(
                    "E-DEFAULT", "error", nid,
                    f"Cổng {n.gateway} {_label(n)} có {len(outs)} nhánh ra nhưng không có nhánh mặc định",
                    "Nhánh mặc định là happy path; thiếu nó thì token kẹt khi mọi điều kiện đều sai.",
                ))
            elif n.default not in {f[0] for f in outs}:
                out.append(Finding(
                    "E-DEFAULT", "error", nid,
                    f"Nhánh mặc định `{n.default}` không phải là một nhánh ra của cổng này", ""))

        # R3 — mở bằng cổng nào thì đóng bằng cổng đó
        if n.kind == "gateway" and len(outs) > 1:
            join = reconvergence(g, nid, back)
            if join and g.is_gateway(join):
                jk = g.nodes[join].gateway
                if jk != n.gateway and not (n.gateway == "event" and jk == "exclusive"):
                    out.append(Finding(
                        "E-SPLIT-JOIN", "error", nid,
                        f"Cổng {n.gateway} đóng lại bằng cổng {jk} tại `{join}`",
                        "Mở bằng cổng nào thì đóng bằng cổng đó, nếu không token sẽ kẹt "
                        "(parallel đóng bằng exclusive) hoặc nhân bản (ngược lại).",
                    ))

        # R4 — nhánh ra của cổng rẽ điều kiện phải có nhãn là câu trả lời
        if n.kind == "gateway" and n.gateway in CONDITIONAL_GATEWAYS and len(outs) > 1:
            for f in outs:
                if not f[3]:
                    out.append(Finding(
                        "W-BRANCH-LABEL", "warn", nid,
                        f"Nhánh `{f[0]}` không có nhãn",
                        "Nhãn nhánh phải là câu trả lời cho câu hỏi ở cổng.",
                    ))
            if not n.name:
                out.append(Finding(
                    "W-GW-NAME", "warn", nid,
                    "Cổng rẽ nhánh không có tên",
                    "Đặt tên cổng là một câu hỏi, ví dụ `Còn hạn bảo hành?`.",
                ))

        # R5 — sự kiện đầu/cuối và node cụt
        if n.kind == "event" and n.event == "start" and inc:
            out.append(Finding("E-START-IN", "error", nid, "Sự kiện bắt đầu có luồng vào", ""))
        if n.kind == "event" and n.event == "end" and outs:
            out.append(Finding("E-END-OUT", "error", nid, "Sự kiện kết thúc có luồng ra", ""))
        if not outs and not (n.kind == "event" and n.event == "end"):
            out.append(Finding(
                "E-DEAD-END", "error", nid,
                f"{_label(n)} không có luồng ra",
                "Mọi nhánh phải kết thúc bằng một sự kiện kết thúc.",
            ))
        if not inc and not (n.kind == "event" and n.event == "start"):
            out.append(Finding(
                "E-NO-IN", "error", nid, f"{_label(n)} không có luồng vào", ""))

    # R6 — message flow phải chạm vào task hoặc sự kiện, không chạm vào cổng
    for mid, s, t in g.messages:
        for end in (s, t):
            if g.is_gateway(end):
                out.append(Finding(
                    "E-MSG-GATEWAY", "error", end,
                    f"Message flow `{mid}` nối thẳng vào một cổng",
                    "Chèn một sự kiện bắt thông điệp (`definition: message`) trước cổng — "
                    "cổng chỉ định tuyến, nó không nhận được thông điệp.",
                ))

    # R7 — mọi node phải tới được từ một sự kiện bắt đầu
    starts = [i for i, n in g.nodes.items() if n.kind == "event" and n.event == "start"]
    if starts:
        seen = set(starts)
        q = deque(starts)
        while q:
            u = q.popleft()
            for f in g.out(u):
                if f[2] not in seen:
                    seen.add(f[2])
                    q.append(f[2])
        for nid in g.nodes:
            if nid not in seen:
                out.append(Finding("E-UNREACHABLE", "error", nid,
                                   "Không đi tới được từ sự kiện bắt đầu nào", ""))
    else:
        out.append(Finding("E-NO-START", "error", "-", "Mô hình không có sự kiện bắt đầu", ""))

    return out


def _label(n: Node) -> str:
    return f"`{n.id}`" + (f" ({n.name})" if n.name else "")


# --- sửa tự động trên brief -------------------------------------------------------------
@dataclass
class Change:
    kind: str
    detail: str


def normalize(brief: dict) -> tuple[dict, list[Change]]:
    """Sửa những vi phạm **máy sửa được mà không cần người đặt tên**.

    Cụ thể: chèn cổng hợp lưu (cổng hợp lưu không có tên nên không cần hỏi ai), và đặt
    nhánh mặc định cho cổng rẽ điều kiện.

    Không tự sửa: message flow chạm vào cổng — sửa đúng phải chèn một sự kiện bắt thông
    điệp, mà sự kiện thì cần một cái tên, và chỉ người viết mới biết đặt tên gì.
    """
    changes: list[Change] = []
    nodes = brief.setdefault("nodes", [])
    flows = brief.setdefault("flows", [])

    # Nhánh mặc định của một model chuyển đổi ngược nằm ở cạnh; kéo về cổng trước khi
    # kiểm, nếu không R2 sẽ "sửa" lại đúng cái đã đúng và in ra một dòng thay đổi giả.
    by_id_pre = {n["id"]: n for n in nodes}
    for f in flows:
        if f.get("default") is True and f.get("source") in by_id_pre:
            by_id_pre[f["source"]].setdefault(
                "default", f.get("id", f"Flow_{f['source']}__{f['target']}"))

    g = load_brief(brief)

    # --- R1: chèn cổng hợp lưu trước mỗi node không phải cổng mà có nhiều luồng vào ---
    for nid in list(g.nodes):
        n = g.nodes[nid]
        inc = g.inc(nid)
        if len(inc) < 2 or n.kind == "gateway":
            continue

        # Loại cổng hợp lưu phải khớp với cổng đã mở ra các nhánh này (R3).
        kind = _closing_kind(g, [f[1] for f in inc])
        # id của cổng chèn thêm cũng phải theo quy ước (docs/bpmn-naming.md). Cổng hợp
        # lưu không có nhãn, nên ô tên lấy theo *node nó đứng trước* — đó đúng là cách
        # người đọc gọi nó: "cổng hợp lưu trước bước X".
        from . import ids  # cục bộ: rules là tầng dưới, không nên phụ thuộc vòng
        base = (ids.parse(nid) or {}).get("name", "") or nid.split("_", 1)[-1]
        gid = ids.make_id("gateway", "", kind, slug=f"hop-{base}")
        idx = next((k for k, x in enumerate(nodes) if x["id"] == nid), len(nodes))
        nodes.insert(idx, dict(id=gid, kind="gateway", gateway=kind, lane=n.lane))
        for f in flows:
            if f.get("kind") in ("message", "data", "association"):
                continue
            if f.get("target") == nid:
                f["target"] = gid
        flows.append(dict(source=gid, target=nid))
        changes.append(Change(
            "merge-gateway",
            f"chèn cổng {kind} `{gid}` trước `{nid}` ({len(inc)} luồng vào)",
        ))
        g = load_brief(brief)

    # --- R2: nhánh đầu tiên của cổng rẽ điều kiện là nhánh mặc định ---
    by_id = {n["id"]: n for n in nodes}
    for nid, n in g.nodes.items():
        if n.kind != "gateway" or n.gateway not in CONDITIONAL_GATEWAYS:
            continue
        outs = g.out(nid)
        if len(outs) < 2 or by_id[nid].get("default"):
            continue
        first = outs[0]
        by_id[nid]["default"] = first[0]
        changes.append(Change(
            "default-flow",
            f"cổng `{nid}`: nhánh mặc định = `{first[0]}`"
            + (f" ({first[3]})" if first[3] else ""),
        ))

    return brief, changes


def _closing_kind(g: Graph, sources: list[str]) -> str:
    """Cổng hợp lưu nên cùng loại với cổng đã mở ra các nhánh này.

    Đi ngược từ mỗi nguồn tới cổng rẽ gần nhất; nếu tất cả cùng chỉ về một cổng thì lấy
    loại của cổng đó (song song đóng bằng song song). Không xác định được thì dùng
    exclusive — đúng cho vòng rework và cho các nhánh loại trừ.
    """
    kinds = set()
    for s in sources:
        u, hops = s, 0
        while hops < len(g.nodes):
            if g.is_gateway(u) and len(g.out(u)) > 1:
                kinds.add(g.nodes[u].gateway)
                break
            preds = g.inc(u)
            if len(preds) != 1:
                break
            u = preds[0][1]
            hops += 1
    if kinds == {"parallel"}:
        return "parallel"
    return "exclusive"
