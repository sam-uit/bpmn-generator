#!/usr/bin/env python3
"""Sinh BPMN 2.0 XML (kèm BPMNDI) từ một đặc tả lưới cột/dòng.

Công cụ nháp: viết toạ độ DI bằng tay cho một collaboration ~25 node là việc
không thể kiểm soát. Ở đây mô tả bằng (lane, col, row) rồi để máy tính toạ độ.
File .bpmn sinh ra mới là nguồn sự thật và mở được trong Camunda Modeler.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from ._version import __version__ as VERSION


def edge_colors(f: dict) -> str:
    """Thuộc tính màu cho một cạnh. Modeler tô màu được cả cạnh, không chỉ shape, và một
    cung rework tô đỏ là thông tin thật chứ không phải trang trí."""
    if not (f.get("fill") or f.get("stroke")):
        return ""
    stroke = f.get("stroke") or f.get("fill")
    return f' bioc:stroke="{stroke}" color:border-color="{stroke}"'


def edge_label_box(flow: dict, auto: dict) -> dict:
    """Hộp nhãn của một cạnh: lấy cái người vẽ đặt nếu có, còn không thì lấy cái tự tính.

    Nhãn cạnh là chỗ chỉnh tay nhiều thứ hai sau đường đi, vì bộ tính tự động luôn đặt
    nó ở giữa cạnh, mà giữa cạnh thì hay đè lên một shape khác.
    """
    lab = flow.get("label")
    if not lab:
        return auto
    return dict(x=float(lab["x"]), y=float(lab["y"]),
                w=float(lab["w"]), h=float(lab["h"]))


def coord(v: float) -> str:
    """Toạ độ: số nguyên in không có phần lẻ, số lẻ thì giữ nguyên.

    Trước đây mọi toạ độ đều `:.0f`, hợp lý khi mọi toạ độ đều do lưới sinh ra. Nhưng
    Modeler đặt nhãn ở nửa đơn vị (`x="903.5"`), nên khi `bounds` đi thẳng từ file vào
    thì làm tròn là *sửa* dữ liệu của người vẽ, và vòng lặp không còn bất biến.
    """
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:g}"


def attr(text: str) -> str:
    """Giá trị thuộc tính XML.

    Xuống dòng phải mã hoá thành `&#10;`. Ký tự xuống dòng đặt trần trong một thuộc tính
    là hợp lệ về cú pháp, nhưng bộ phân tích XML *chuẩn hoá giá trị thuộc tính* và biến
    nó thành dấu cách, nên `name="Phân loại\nhướng xử lý"` đọc lại thành một dòng và
    ngắt dòng người vẽ đặt biến mất sau mỗi vòng.
    """
    return escape(text).replace("\r\n", "&#10;").replace("\n", "&#10;").replace("\r", "&#10;")

# --- kích thước chuẩn của BPMN (đơn vị BPMN, giống Camunda Modeler) ---
TASK_W, TASK_H = 100, 80
GW = 50
EV = 36
GAP = 50            # khoảng trống giữa hai cột
ROW_BAND = 80       # chiều cao vùng chứa một dòng
ROW_PITCH = 110     # khoảng cách giữa hai dòng
LANE_PAD_TOP = 20
LANE_PAD_BOT = 10
POOL_HEADER = 30
LANE_LEFT_PAD = 40
LANE_RIGHT_PAD = 40
BLACKBOX_H = 60
POOL_X = 160
MESSAGE_STUB = 22   # stub a message flow runs before it turns into the free corridor

PALETTE = {
    "blue": ("#bbdefb", "#0d4372"),
    "orange": ("#ffe0b2", "#6b3c00"),
    "green": ("#c8e6c9", "#205022"),
    "red": ("#ffcdd2", "#831311"),
    "purple": ("#e1bee7", "#5b176d"),
}

# Ký hiệu lặp vẽ dọc cạnh dưới activity, dưới dạng phần tử con của activity đó. Bảng
# nằm ở đây vì nó là XML; từ vựng và phần kiểm tra thì ở `brief.py`.
MARKER_ELEMENTS = {
    "loop": "<bpmn:standardLoopCharacteristics />",
    # `isSequential` mặc định là false, nên Camunda ghi thẻ trần. Ghi giống hệt thì
    # `git diff` giữa file mình sinh và file Modeler lưu lại chỉ còn phần thật sự đổi.
    "mi-parallel": "<bpmn:multiInstanceLoopCharacteristics />",
    "mi-sequential": '<bpmn:multiInstanceLoopCharacteristics isSequential="true" />',
}

EVENT_KINDS = {"startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent"}
GATEWAY_KINDS = {"exclusiveGateway", "parallelGateway", "inclusiveGateway", "eventBasedGateway"}
DATA_KINDS = {"dataObjectReference", "dataStoreReference"}

DATA_W, DATA_H = 50, 50
NOTE_W, NOTE_H = 100, 30
ARTIFACT_GAP = 45   # khoảng hở giữa đáy phần tử chủ và đỉnh artifact
ARTIFACT_PITCH = 62  # hai artifact cùng một chủ thì xếp cạnh nhau


def size_of(kind: str) -> tuple[int, int]:
    if kind in EVENT_KINDS:
        return EV, EV
    if kind in GATEWAY_KINDS:
        return GW, GW
    if kind in DATA_KINDS:
        return DATA_W, DATA_H
    if kind == "textAnnotation":
        return NOTE_W, NOTE_H
    return TASK_W, TASK_H


def polyline_midpoint(wps: list[tuple[float, float]]) -> tuple[float, float]:
    """The point half way along a polyline, measured by length rather than by count.

    Measured rather than counted because an orthogonal route is mostly short jogs and one
    long run; taking the middle *vertex* would put the anchor in a corner, while the middle
    of the *length* lands on the long run, which is the part a reader sees as the line.
    """
    if not wps:
        return (0.0, 0.0)
    if len(wps) == 1:
        return wps[0]
    spans = []
    total = 0.0
    for (x0, y0), (x1, y1) in zip(wps, wps[1:]):
        d = abs(x1 - x0) + abs(y1 - y0)
        spans.append(d)
        total += d
    half = total / 2
    for i, d in enumerate(spans):
        if half <= d or i == len(spans) - 1:
            (x0, y0), (x1, y1) = wps[i], wps[i + 1]
            t = half / d if d else 0.0
            return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
        half -= d
    return wps[len(wps) // 2]


def _pin(node: dict, b: dict | None) -> None:
    """Đặt một phần tử vào đúng hộp đã cho, và tính lại tâm theo hộp đó."""
    if not b:
        return
    node["x"], node["y"] = float(b["x"]), float(b["y"])
    node["w"], node["h"] = float(b["w"]), float(b["h"])
    node["cx"] = node["x"] + node["w"] / 2
    node["cy"] = node["y"] + node["h"] / 2


class Model:
    def __init__(self, spec: dict):
        self.spec = spec
        self.nodes = {n["id"]: dict(n) for n in spec["nodes"]}
        self.pools = spec["pools"]
        self.flows = spec.get("flows", [])
        self.messages = spec.get("messages", [])
        self.artifacts = {a["id"]: dict(a) for a in spec.get("artifacts", [])}
        self.links = spec.get("links", [])
        self.lane_of_pool: dict[str, str] = {}
        for p in self.pools:
            for ln in p.get("lanes", []):
                self.lane_of_pool[ln["id"]] = p["id"]
        self.layout()

    # -- bố cục ---------------------------------------------------------------
    def layout(self) -> None:
        cols = sorted({n["col"] for n in self.nodes.values()})
        widths = {}
        for c in cols:
            widths[c] = max(size_of(n["kind"])[0] for n in self.nodes.values() if n["col"] == c)

        x = POOL_X + POOL_HEADER + LANE_LEFT_PAD
        col_x = {}
        for c in cols:
            col_x[c] = x
            x += widths[c] + GAP
        content_w = x - GAP - (POOL_X + POOL_HEADER + LANE_LEFT_PAD)
        self.col_x = col_x
        self.col_w = widths
        self.lane_w = POOL_HEADER + LANE_LEFT_PAD + content_w + LANE_RIGHT_PAD
        self.pool_w = self.lane_w

        # trục dọc: pool black box trên, pool chính, pool black box dưới
        y = 60
        self.pool_bounds: dict[str, dict] = {}
        self.lane_bounds: dict[str, dict] = {}
        for p in self.pools:
            if p.get("blackbox"):
                self.pool_bounds[p["id"]] = dict(x=POOL_X, y=y, w=self.pool_w, h=BLACKBOX_H)
                y += BLACKBOX_H + 40
                continue
            pool_y = y
            for ln in p["lanes"]:
                h = LANE_PAD_TOP + ln["rows"] * ROW_PITCH + LANE_PAD_BOT
                self.lane_bounds[ln["id"]] = dict(
                    x=POOL_X + POOL_HEADER, y=y, w=self.lane_w - POOL_HEADER, h=h
                )
                y += h
            self.pool_bounds[p["id"]] = dict(x=POOL_X, y=pool_y, w=self.pool_w, h=y - pool_y)
            y += 40

        for n in self.nodes.values():
            w, h = size_of(n["kind"])
            lb = self.lane_bounds[n["lane"]]
            band_top = lb["y"] + LANE_PAD_TOP + n["row"] * ROW_PITCH
            cw = widths[n["col"]]
            n["w"], n["h"] = w, h
            n["x"] = col_x[n["col"]] + (cw - w) // 2
            n["y"] = band_top + (ROW_BAND - h) // 2
            n["cx"] = n["x"] + w / 2
            n["cy"] = n["y"] + h / 2
            n["pool"] = self.lane_of_pool[n["lane"]]

        self.pin_given_bounds()
        self.place_artifacts()
        self.pin_given_bounds(artifacts=True)

    # -- toạ độ do người viết đưa vào -----------------------------------------
    def pin_given_bounds(self, artifacts: bool = False) -> None:
        """Ghi đè bố cục vừa tính bằng `bounds` có sẵn trong đặc tả.

        Chạy *sau* khi tính, không phải thay cho việc tính: một file chỉ ghim vài phần
        tử thì phần còn lại vẫn cần lưới, và làm theo thứ tự này thì đường không ghim gì
        cho ra kết quả y hệt như trước.
        """
        if artifacts:
            for a in self.artifacts.values():
                _pin(a, a.get("bounds"))
            return
        for p in self.pools:
            b = p.get("bounds")
            if b:
                self.pool_bounds[p["id"]] = dict(
                    x=float(b["x"]), y=float(b["y"]), w=float(b["w"]), h=float(b["h"]))
            for ln in p.get("lanes", []):
                lb = ln.get("bounds")
                if lb:
                    self.lane_bounds[ln["id"]] = dict(
                        x=float(lb["x"]), y=float(lb["y"]), w=float(lb["w"]), h=float(lb["h"]))
                elif ln.get("implicit") and b:
                    # An implicit band has no bounds of its own to pin, and leaving it on
                    # the computed grid while its pool moved to pinned coordinates would
                    # place every unpinned node in the wrong place. It is the pool minus
                    # the header strip, which is exactly what a lane rectangle is.
                    pb = self.pool_bounds[p["id"]]
                    self.lane_bounds[ln["id"]] = dict(
                        x=pb["x"] + POOL_HEADER, y=pb["y"],
                        w=pb["w"] - POOL_HEADER, h=pb["h"])
        for n in self.nodes.values():
            _pin(n, n.get("bounds"))

    def host_box(self, host_id: str) -> dict | None:
        """The box an artifact hangs from, whether that is a node or a sequence flow.

        A node is its own box. A sequence flow is not a box at all, so it stands in as a
        zero-sized point at the middle of its own route, which puts the annotation below
        the line exactly where a modeler drops it. Pool and lane come from the flow's
        source node, because an association has to be written inside the process that owns
        the flow it annotates.
        """
        node = self.nodes.get(host_id)
        if node is not None:
            return node
        for f in self.flows:
            if self.flow_id(f) != host_id:
                continue
            mx, my = polyline_midpoint(self.route(f))
            src = self.nodes[f["src"]]
            return dict(id=host_id, x=mx, y=my, w=0.0, h=0.0, cx=mx, cy=my,
                        pool=src["pool"], lane=src["lane"])
        return None

    def place_artifacts(self) -> None:
        """Artifact treo dưới phần tử chủ của nó.

        Không đưa artifact vào lưới: chúng không có `col`/`row`, và ép chúng vào lưới
        sẽ đẩy cả một cột ra chỗ khác chỉ vì một cái kho dữ liệu. Dưới-chủ-thể là chỗ
        Modeler cũng đặt, và là chỗ mắt người tìm đến.
        """
        per_host: dict[str, int] = {}
        for a in self.artifacts.values():
            host = self.host_box(a.get("host") or "")
            if host is None:
                continue
            w, h = size_of(a["kind"])
            k = per_host.get(host["id"], 0)
            per_host[host["id"]] = k + 1
            a["w"], a["h"] = w, h
            a["x"] = host["cx"] - w / 2 + k * ARTIFACT_PITCH
            a["y"] = host["y"] + host["h"] + ARTIFACT_GAP
            a["cx"] = a["x"] + w / 2
            a["cy"] = a["y"] + h / 2
            # A node lends its pool to whatever hangs off it. A sequence flow does not:
            # an annotation on a flow is written at collaboration level, outside every
            # process, which is where Camunda Modeler puts it and therefore where a file
            # that came from Modeler expects to find it again.
            host_is_node = a.get("host") in self.nodes
            a["pool"] = a.get("pool") or (host["pool"] if host_is_node else None)
            a["lane"] = a.get("lane") or (host["lane"] if host_is_node else None)

    # -- định tuyến cạnh ------------------------------------------------------
    def route(self, flow: dict) -> list[tuple[float, float]]:
        if "waypoints" in flow:
            return flow["waypoints"]
        s, t = self.nodes[flow["src"]], self.nodes[flow["dst"]]
        # Waypoint do người viết đưa vào thì thắng bộ định tuyến, không bàn. Đây là cùng
        # một luật với `row`/`col`: cái gì tác giả nói tường minh thì máy không đoán lại.
        # Đường đi của một cạnh là chỗ chỉnh tay nhiều nhất trong Modeler, mà trước đây
        # `bpmn-brief` vẽ lại từ đầu, nên mỗi vòng lặp lại xoá đúng phần vừa chỉnh.
        given = flow.get("waypoints")
        if given:
            return [(float(x), float(y)) for x, y in given]

        mode = flow.get("route", "auto")
        sc, tc = (s["cx"], s["cy"]), (t["cx"], t["cy"])

        def right(n):
            return (n["x"] + n["w"], n["cy"])

        def left(n):
            return (n["x"], n["cy"])

        def top(n):
            return (n["cx"], n["y"])

        def bottom(n):
            return (n["cx"], n["y"] + n["h"])

        if mode == "loop":  # quay lui: đi vòng xuống dưới
            dy = flow.get("dy", 60)
            yl = max(s["y"] + s["h"], t["y"] + t["h"]) + dy
            return [bottom(s), (s["cx"], yl), (t["cx"], yl), bottom(t)]
        if mode == "loop-up":
            dy = flow.get("dy", 60)
            yl = min(s["y"], t["y"]) - dy
            return [top(s), (s["cx"], yl), (t["cx"], yl), top(t)]
        if mode == "bus":  # đi vòng qua một đường ngang phía dưới/trên
            dy = flow.get("dy", 45)
            if t["cy"] > s["cy"]:
                yb = s["y"] + s["h"] + dy
                return [bottom(s), (s["cx"], yb), (t["cx"], yb), top(t)]
            yb = s["y"] - dy
            return [top(s), (s["cx"], yb), (t["cx"], yb), bottom(t)]
        if mode == "vh":  # xuống trước, sang ngang sau
            return [bottom(s) if tc[1] > sc[1] else top(s), (s["cx"], t["cy"]), left(t)]
        if mode == "hv":  # sang ngang trước, xuống sau
            return [right(s), (t["cx"], s["cy"]), top(t) if tc[1] > sc[1] else bottom(t)]
        if mode == "h":
            return [right(s), left(t)]
        if mode == "detour":  # né qua dòng phía dưới rồi quay lên
            yl = flow["y"]
            return [right(s), (s["x"] + s["w"] + 20, yl), (t["x"] - 20, yl), left(t)]

        # auto
        if abs(s["cy"] - t["cy"]) < 4:
            return [right(s), left(t)] if t["cx"] > s["cx"] else [left(s), right(t)]
        if t["cx"] > s["cx"] + s["w"] / 2 + t["w"] / 2:
            # Nhiều nhánh cùng rời một gateway sang cùng một cột sẽ trùng đoạn dọc;
            # đẩy mỗi nhánh lệch đi một chút để đọc được.
            sib = [f for f in self.flows if f["src"] == flow["src"]]
            k = sib.index(flow) if len(sib) > 1 else 0
            mx = (s["x"] + s["w"] + t["x"]) / 2 + k * 16 - (len(sib) - 1) * 8
            return [right(s), (mx, s["cy"]), (mx, t["cy"]), left(t)]
        # gần như thẳng đứng
        return [bottom(s), top(t)] if t["cy"] > s["cy"] else [top(s), bottom(t)]

    def message_route(self, m: dict) -> list[tuple[float, float]]:
        """Route a message flow the author gave no explicit waypoints for.

        Three shapes of message flow exist and each needs its own geometry, so this
        method only picks between them:

        - **node to black box band**, the common case in a sliced model, where one end
          is a collapsed participant drawn as a full-width band;
        - **node to node**, where both ends are real activities or events sitting in two
          different real pools;
        - **band to band**, two collapsed participants exchanging a message directly.

        Before v0.5.3 only the first was handled: the endpoint that was not a pool was
        assumed to be a node and the other was looked up in `pool_bounds`. A message flow
        between two real pools therefore looked up a *node* id in `pool_bounds` and died
        with a bare `KeyError`, which said nothing about what was wrong.
        """
        given = m.get("waypoints")
        if given:
            return [(float(x), float(y)) for x, y in given]
        pool_bounds = self.pool_bounds
        src_is_band = m["src"] in pool_bounds
        dst_is_band = m["dst"] in pool_bounds
        for end in ("src", "dst"):
            if m[end] not in pool_bounds and m[end] not in self.nodes:
                raise SystemExit(
                    f"[error] message flow refers to `{m[end]}`, which is neither a"
                    " node nor a pool in this model.\n"
                    "        A message flow has to join two elements that exist; check the"
                    " id for a typo, or give `waypoints:` if you want to route it yourself."
                )
        if src_is_band != dst_is_band:
            return self.message_route_node_to_band(m, pool_bounds)
        if not src_is_band:
            return self.message_route_node_to_node(m)
        return self.message_route_band_to_band(m, pool_bounds)

    def message_route_node_to_band(
        self, m: dict, pool_bounds: dict
    ) -> list[tuple[float, float]]:
        """Join a node to a collapsed participant band above or below it.

        The band spans the full width of the diagram, so the flow drops straight out of
        the node at the node's own centre x; the band contributes only the y of its near
        edge. `offset` pushes the vertical segment sideways into the empty corridor
        between two columns so it does not cut across the shapes of an intervening lane.
        """
        node_id = m["dst"] if m["src"] in pool_bounds else m["src"]
        pool_id = m["src"] if m["src"] in pool_bounds else m["dst"]
        n, p = self.nodes[node_id], pool_bounds[pool_id]
        off = m.get("offset", 0)
        stub = m.get("stub", MESSAGE_STUB)
        band_is_below = p["y"] > n["y"]
        y_node = n["y"] + n["h"] if band_is_below else n["y"]
        y_pool = p["y"] if band_is_below else p["y"] + p["h"]
        if off == 0:
            pts = [(n["cx"], y_node), (n["cx"], y_pool)]
        else:
            y_mid = y_node + stub if band_is_below else y_node - stub
            pts = [
                (n["cx"], y_node),
                (n["cx"], y_mid),
                (n["cx"] + off, y_mid),
                (n["cx"] + off, y_pool),
            ]
        return pts if m["src"] == node_id else list(reversed(pts))

    def message_route_node_to_node(self, m: dict) -> list[tuple[float, float]]:
        """Join two nodes sitting in two different real pools.

        The axis is chosen from the gap that actually exists between the two boxes rather
        than from the pool orientation flag, because that keeps working for a diagram the
        author laid out by hand: pools stacked as horizontal bands leave a vertical gap,
        pools standing side by side leave a horizontal one, and whichever gap is wider is
        the direction the message has to cross.

        The flow leaves the facing edge of each box at that box's own centre, and when the
        two centres do not line up it turns twice in the middle of the gap, the shape a
        modeler draws by hand. `offset` shifts that middle segment along the crossing axis
        when two message flows would otherwise land on top of each other.
        """
        s, t = self.nodes[m["src"]], self.nodes[m["dst"]]
        off = m.get("offset", 0)
        gap_x = max(t["x"] - (s["x"] + s["w"]), s["x"] - (t["x"] + t["w"]))
        gap_y = max(t["y"] - (s["y"] + s["h"]), s["y"] - (t["y"] + t["h"]))
        if gap_x > gap_y:
            rightward = t["cx"] > s["cx"]
            x0 = s["x"] + s["w"] if rightward else s["x"]
            x1 = t["x"] if rightward else t["x"] + t["w"]
            if s["cy"] == t["cy"]:
                return [(x0, s["cy"]), (x1, t["cy"])]
            x_mid = (x0 + x1) / 2 + off
            return [(x0, s["cy"]), (x_mid, s["cy"]), (x_mid, t["cy"]), (x1, t["cy"])]
        downward = t["cy"] > s["cy"]
        y0 = s["y"] + s["h"] if downward else s["y"]
        y1 = t["y"] if downward else t["y"] + t["h"]
        if s["cx"] == t["cx"]:
            return [(s["cx"], y0), (t["cx"], y1)]
        y_mid = (y0 + y1) / 2 + off
        return [(s["cx"], y0), (s["cx"], y_mid), (t["cx"], y_mid), (t["cx"], y1)]

    def message_route_band_to_band(
        self, m: dict, pool_bounds: dict
    ) -> list[tuple[float, float]]:
        """Join two collapsed participant bands directly to each other.

        Two bands are stacked, so the flow is a single vertical segment between their
        facing edges. It is placed at the centre of the horizontal span the two bands
        share, which for the usual full-width bands is the middle of the diagram, and
        falls back to the midpoint of the two centres when they do not overlap at all.
        """
        a, b = pool_bounds[m["src"]], pool_bounds[m["dst"]]
        lo = max(a["x"], b["x"])
        hi = min(a["x"] + a["w"], b["x"] + b["w"])
        x = (lo + hi) / 2 if hi > lo else (a["x"] + a["w"] / 2 + b["x"] + b["w"] / 2) / 2
        x += m.get("offset", 0)
        b_is_below = b["y"] > a["y"]
        y0 = a["y"] + a["h"] if b_is_below else a["y"]
        y1 = b["y"] if b_is_below else b["y"] + b["h"]
        return [(x, y0), (x, y1)]

    # -- xuất XML -------------------------------------------------------------
    def xml(self) -> str:
        s = self.spec
        L = []
        A = L.append
        A('<?xml version="1.0" encoding="UTF-8"?>')
        A(
            '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"'
            ' xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"'
            ' xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"'
            ' xmlns:di="http://www.omg.org/spec/DD/20100524/DI"'
            ' xmlns:bioc="http://bpmn.io/schema/bpmn/biocolor/1.0"'
            ' xmlns:color="http://www.omg.org/spec/BPMN/non-normative/color/1.0"'
            f' id="{s["id"]}" targetNamespace="http://bpmn.io/schema/bpmn"'
            f' exporter="bpmn-generator" exporterVersion="{VERSION}">'
        )

        # --- collaboration ---
        A(f'  <bpmn:collaboration id="{s["collaboration"]}">')
        for p in self.pools:
            if p.get("blackbox"):
                A(f'    <bpmn:participant id="{p["id"]}" name="{attr(p["name"])}" />')
            else:
                A(
                    f'    <bpmn:participant id="{p["id"]}" name="{attr(p["name"])}"'
                    f' processRef="{p["process"]}" />'
                )
        for i, m in enumerate(self.messages, 1):
            nm = f' name="{attr(m["name"])}"' if m.get("name") else ""
            A(
                f'    <bpmn:messageFlow id="{self.msg_id(m, i)}"{nm}'
                f' sourceRef="{m["src"]}" targetRef="{m["dst"]}" />'
            )
        # An artifact that belongs to no pool lives in the collaboration, next to the
        # message flows. That is the case for an annotation hanging off a sequence flow:
        # it comments on the flow, not on either process, and it has no process to live in.
        loose = [a for a in self.artifacts.values() if not a.get("pool")]
        for a in loose:
            L.extend(self.artifact_lines(a, 4))
        loose_ids = {a["id"] for a in loose}
        for lk in self.links:
            if lk.get("kind") != "association" or lk["art"] not in loose_ids:
                continue
            L.extend(self.association_lines(lk, 4))
        A("  </bpmn:collaboration>")

        # --- process ---
        for p in self.pools:
            if p.get("blackbox"):
                continue
            # Mô hình trong báo cáo là để đọc, không để chạy, nói rõ ra
            A(f'  <bpmn:process id="{p["process"]}" isExecutable="false">')
            # An implicit band is a placeholder the layout needs, not a lane the author
            # drew, so it is never written out. A pool whose only band is implicit gets no
            # laneSet at all, which is both legal BPMN and what the source file said.
            drawn_lanes = [ln for ln in p["lanes"] if not ln.get("implicit")]
            if drawn_lanes:
                A(f'    <bpmn:laneSet id="LaneSet_{p["process"]}">')
                for ln in drawn_lanes:
                    A(f'      <bpmn:lane id="{ln["id"]}" name="{attr(ln["name"])}">')
                    for n in self.spec["nodes"]:
                        if n["lane"] == ln["id"]:
                            A(f'        <bpmn:flowNodeRef>{n["id"]}</bpmn:flowNodeRef>')
                    A("      </bpmn:lane>")
                A("    </bpmn:laneSet>")

            own = {n["id"] for n in self.nodes.values() if n["pool"] == p["id"]}
            for n in self.spec["nodes"]:
                if n["id"] not in own:
                    continue
                node = self.nodes[n["id"]]
                kind = n["kind"]
                nm = f' name="{attr(n["name"])}"' if n.get("name") else ""
                inc = [f["src"] for f in self.flows if f["dst"] == n["id"]]
                out = [f["dst"] for f in self.flows if f["src"] == n["id"]]
                inc_ids = [self.flow_id(f) for f in self.flows if f["dst"] == n["id"]]
                out_ids = [self.flow_id(f) for f in self.flows if f["src"] == n["id"]]
                body = []
                for fid in inc_ids:
                    body.append(f"      <bpmn:incoming>{fid}</bpmn:incoming>")
                for fid in out_ids:
                    body.append(f"      <bpmn:outgoing>{fid}</bpmn:outgoing>")
                if n.get("definition"):
                    d = n["definition"]
                    body.append(f'      <bpmn:{d}EventDefinition id="Def_{n["id"]}" />')
                # Data association là con của chính activity, không phải của process,
                # đó là lý do nó phải chèn ở đây chứ không ở vòng lặp cạnh phía dưới.
                for lk in self.links:
                    if lk["host"] != n["id"] or lk.get("kind") != "data":
                        continue
                    tag = ("dataOutputAssociation" if lk["direction"] == "output"
                           else "dataInputAssociation")
                    ref = "targetRef" if lk["direction"] == "output" else "sourceRef"
                    body.append(f'      <bpmn:{tag} id="{self.link_id(lk)}">')
                    body.append(f"        <bpmn:{ref}>{lk['art']}</bpmn:{ref}>")
                    body.append(f"      </bpmn:{tag}>")
                # `loopCharacteristics` đứng **cuối** thân activity theo XSD của BPMN
                # (tActivity: incoming, outgoing, ..., dataOutputAssociation,
                # loopCharacteristics), nên chèn sau data association chứ không trước.
                for m in n.get("markers", ()):
                    el = MARKER_ELEMENTS.get(m)
                    if el:
                        body.append(f"      {el}")
                extra = ""
                if n.get("default"):
                    extra = f' default="{n["default"]}"'
                # compensation không phải phần tử con mà là một thuộc tính của activity.
                if "compensation" in n.get("markers", ()):
                    extra += ' isForCompensation="true"'
                if body:
                    A(f'    <bpmn:{kind} id="{n["id"]}"{nm}{extra}>')
                    L.extend(body)
                    A(f"    </bpmn:{kind}>")
                else:
                    A(f'    <bpmn:{kind} id="{n["id"]}"{nm}{extra} />')

            for a in self.artifacts.values():
                if a.get("pool") != p["id"]:
                    continue
                L.extend(self.artifact_lines(a, 4))

            for f in self.flows:
                if self.nodes[f["src"]]["pool"] != p["id"]:
                    continue
                nm = f' name="{attr(f["name"])}"' if f.get("name") else ""
                A(
                    f'    <bpmn:sequenceFlow id="{self.flow_id(f)}"{nm}'
                    f' sourceRef="{f["src"]}" targetRef="{f["dst"]}" />'
                )
            for lk in self.links:
                if lk.get("kind") != "association":
                    continue
                if self.artifacts[lk["art"]].get("pool") != p["id"]:
                    continue
                L.extend(self.association_lines(lk, 4))
            A("  </bpmn:process>")

        # --- diagram ---
        A(f'  <bpmndi:BPMNDiagram id="BPMNDiagram_1">')
        A(f'    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="{s["collaboration"]}">')
        for p in self.pools:
            b = self.pool_bounds[p["id"]]
            A(
                f'      <bpmndi:BPMNShape id="Shape_{p["id"]}" bpmnElement="{p["id"]}"'
                f' isHorizontal="true">'
            )
            A(self.bounds(b, 8))
            A("      </bpmndi:BPMNShape>")
            for ln in p.get("lanes", []):
                if ln.get("implicit"):
                    continue
                lb = self.lane_bounds[ln["id"]]
                A(
                    f'      <bpmndi:BPMNShape id="Shape_{ln["id"]}" bpmnElement="{ln["id"]}"'
                    f' isHorizontal="true">'
                )
                A(self.bounds(lb, 8))
                A("      </bpmndi:BPMNShape>")
        for n in self.spec["nodes"]:
            node = self.nodes[n["id"]]
            col = n.get("color")
            attrs = ""
            # Màu hex tường minh (do Modeler đặt) thắng tên trong bảng màu: bảng chỉ là
            # lối viết tắt cho vài màu quen, còn người vẽ thì chọn được bất kỳ màu nào.
            if n.get("fill") or n.get("stroke"):
                fill = n.get("fill", "#ffffff")
                stroke = n.get("stroke", "#22242A")
                attrs = (
                    f' bioc:stroke="{stroke}" bioc:fill="{fill}"'
                    f' color:background-color="{fill}" color:border-color="{stroke}"'
                )
            elif col:
                fill, stroke = PALETTE[col]
                attrs = (
                    f' bioc:stroke="{stroke}" bioc:fill="{fill}"'
                    f' color:background-color="{fill}" color:border-color="{stroke}"'
                )
            if n.get("marker") and n["kind"] == "exclusiveGateway":
                attrs += ' isMarkerVisible="true"'
            A(
                f'      <bpmndi:BPMNShape id="Shape_{n["id"]}" bpmnElement="{n["id"]}"{attrs}>'
            )
            A(self.bounds(node, 8))
            lab = n.get("label")
            if lab:
                A("        <bpmndi:BPMNLabel>")
                A(
                    f'          <dc:Bounds x="{coord(float(lab["x"]))}"'
                    f' y="{coord(float(lab["y"]))}" width="{coord(float(lab["w"]))}"'
                    f' height="{coord(float(lab["h"]))}" />'
                )
                A("        </bpmndi:BPMNLabel>")
            elif n["kind"] in EVENT_KINDS or n["kind"] in GATEWAY_KINDS:
                if n.get("name"):
                    lw = 110
                    A("        <bpmndi:BPMNLabel>")
                    A(
                        f'          <dc:Bounds x="{node["cx"] - lw / 2:.0f}"'
                        f' y="{node["y"] + node["h"] + 6:.0f}" width="{lw}" height="27" />'
                    )
                    A("        </bpmndi:BPMNLabel>")
            A("      </bpmndi:BPMNShape>")
        for a in self.artifacts.values():
            at = ""
            if a.get("fill") or a.get("stroke"):
                fill = a.get("fill", "#ffffff")
                stroke = a.get("stroke", "#22242A")
                at = (f' bioc:stroke="{stroke}" bioc:fill="{fill}"'
                      f' color:background-color="{fill}" color:border-color="{stroke}"')
            A(f'      <bpmndi:BPMNShape id="Shape_{a["id"]}" bpmnElement="{a["id"]}"{at}>')
            A(self.bounds(a, 8))
            if a.get("label") or (a["kind"] in DATA_KINDS and a.get("name")):
                auto = dict(x=a["cx"] - 45, y=a["y"] + a["h"] + 6, w=90, h=14)
                A("        <bpmndi:BPMNLabel>")
                A(self.bounds(edge_label_box(a, auto), 10))
                A("        </bpmndi:BPMNLabel>")
            A("      </bpmndi:BPMNShape>")
        for lk in self.links:
            a, host = self.artifacts[lk["art"]], self.host_box(lk["host"])
            if host is None:
                continue
            # Artifact luôn nằm dưới chủ của nó, nên hai điểm là đủ: đáy chủ, đỉnh artifact.
            given = lk.get("waypoints")
            if given:
                wps = [(float(x), float(y)) for x, y in given]
            else:
                near = (host["cx"], host["y"] + host["h"])
                far = (a["cx"], a["y"])
                wps = [near, far] if lk["direction"] == "output" else [far, near]
            A(
                f'      <bpmndi:BPMNEdge id="Edge_{self.link_id(lk)}"'
                f' bpmnElement="{self.link_id(lk)}">'
            )
            for (x, y) in wps:
                A(f'        <di:waypoint x="{coord(x)}" y="{coord(y)}" />')
            A("      </bpmndi:BPMNEdge>")
        for f in self.flows:
            wps = self.route(f)
            A(
                f'      <bpmndi:BPMNEdge id="Edge_{self.flow_id(f)}"'
                f' bpmnElement="{self.flow_id(f)}"{edge_colors(f)}>'
            )
            for (x, y) in wps:
                A(f'        <di:waypoint x="{coord(x)}" y="{coord(y)}" />')
            if f.get("label") or f.get("name"):
                A("        <bpmndi:BPMNLabel>")
                lx, ly = self.edge_label(wps)
                auto = dict(x=lx, y=ly, w=90, h=24)
                A(self.bounds(edge_label_box(f, auto), 10))
                A("        </bpmndi:BPMNLabel>")
            A("      </bpmndi:BPMNEdge>")
        for i, m in enumerate(self.messages, 1):
            wps = self.message_route(m)
            mid = self.msg_id(m, i)
            A(f'      <bpmndi:BPMNEdge id="Edge_{mid}" bpmnElement="{mid}"{edge_colors(m)}>')
            for (x, y) in wps:
                A(f'        <di:waypoint x="{coord(x)}" y="{coord(y)}" />')
            if m.get("label") or m.get("name"):
                lx = (wps[0][0] + wps[-1][0]) / 2
                ly = (wps[0][1] + wps[-1][1]) / 2
                auto = dict(x=lx + 6, y=ly - 10, w=100, h=20)
                A("        <bpmndi:BPMNLabel>")
                A(self.bounds(edge_label_box(m, auto), 10))
                A("        </bpmndi:BPMNLabel>")
            A("      </bpmndi:BPMNEdge>")
        A("    </bpmndi:BPMNPlane>")
        A("  </bpmndi:BPMNDiagram>")
        A("</bpmn:definitions>")
        return "\n".join(L) + "\n"

    @staticmethod
    def edge_label(wps: list[tuple[float, float]]) -> tuple[float, float]:
        """Đặt nhãn cạnh trên đoạn dài nhất: ngang thì kê phía trên, dọc thì kê bên phải.
        Đoạn dài nhất là đoạn ít có nguy cơ đè lên shape nhất."""
        best, blen = 0, -1.0
        for i in range(len(wps) - 1):
            (x0, y0), (x1, y1) = wps[i], wps[i + 1]
            d = abs(x1 - x0) + abs(y1 - y0)
            if d > blen:
                best, blen = i, d
        (x0, y0), (x1, y1) = wps[best], wps[best + 1]
        if abs(x1 - x0) >= abs(y1 - y0):  # đoạn ngang
            return (x0 + x1) / 2 - 45, min(y0, y1) - 26
        return max(x0, x1) + 6, (y0 + y1) / 2 - 12

    def flow_id(self, f: dict) -> str:
        return f.get("id") or f"Flow_{f['src']}__{f['dst']}"

    @staticmethod
    def msg_id(m: dict, i: int) -> str:
        return m.get("id") or f"MF_{i}"

    @staticmethod
    def artifact_lines(a: dict, indent: int) -> list[str]:
        """The XML element for one artifact, written the same whether it sits in a process
        or in the collaboration."""
        pad = " " * indent
        if a["kind"] == "textAnnotation":
            return [
                f'{pad}<bpmn:textAnnotation id="{a["id"]}">',
                f"{pad}  <bpmn:text>{escape(a.get('name', ''))}</bpmn:text>",
                f"{pad}</bpmn:textAnnotation>",
            ]
        nm = f' name="{escape(a["name"])}"' if a.get("name") else ""
        return [f'{pad}<bpmn:{a["kind"]} id="{a["id"]}"{nm} />']

    @classmethod
    def association_lines(cls, lk: dict, indent: int) -> list[str]:
        """The XML element for one association.

        Which end is the source is the author's choice, not ours: an association can be
        drawn from the annotation to the thing or the other way about, and `direction` is
        the only record of which way it was drawn.
        """
        if lk.get("direction") == "input":
            src, dst = lk["art"], lk["host"]
        else:
            src, dst = lk["host"], lk["art"]
        pad = " " * indent
        return [f'{pad}<bpmn:association id="{cls.link_id(lk)}"'
                f' sourceRef="{src}" targetRef="{dst}" />']

    @staticmethod
    def link_id(lk: dict) -> str:
        return lk.get("id") or f"Link_{lk['host']}__{lk['art']}"

    @staticmethod
    def bounds(b: dict, indent: int) -> str:
        pad = " " * indent
        return (
            f'{pad}<dc:Bounds x="{coord(b["x"])}" y="{coord(b["y"])}"'
            f' width="{coord(b["w"])}" height="{coord(b["h"])}" />'
        )


def build(spec: dict, path: str) -> None:
    m = Model(spec)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(m.xml())
    ext = m.pool_bounds
    xs = [b["x"] for b in ext.values()]
    ws = [b["x"] + b["w"] for b in ext.values()]
    ys = [b["y"] for b in ext.values()]
    hs = [b["y"] + b["h"] for b in ext.values()]
    print(
        f"{path}: {len(m.nodes)} node, extent "
        f"{min(xs):.0f},{min(ys):.0f} -> {max(ws):.0f},{max(hs):.0f} "
        f"({max(ws) - min(xs):.0f} x {max(hs) - min(ys):.0f})"
    )
