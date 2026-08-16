#!/usr/bin/env python3
"""Sinh BPMN 2.0 XML (kèm BPMNDI) từ một đặc tả lưới cột/dòng.

Công cụ nháp: viết toạ độ DI bằng tay cho một collaboration ~25 node là việc
không thể kiểm soát. Ở đây mô tả bằng (lane, col, row) rồi để máy tính toạ độ.
File .bpmn sinh ra mới là nguồn sự thật và mở được trong Camunda Modeler.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

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

PALETTE = {
    "blue": ("#bbdefb", "#0d4372"),
    "orange": ("#ffe0b2", "#6b3c00"),
    "green": ("#c8e6c9", "#205022"),
    "red": ("#ffcdd2", "#831311"),
    "purple": ("#e1bee7", "#5b176d"),
}

EVENT_KINDS = {"startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent"}
GATEWAY_KINDS = {"exclusiveGateway", "parallelGateway", "inclusiveGateway", "eventBasedGateway"}


def size_of(kind: str) -> tuple[int, int]:
    if kind in EVENT_KINDS:
        return EV, EV
    if kind in GATEWAY_KINDS:
        return GW, GW
    return TASK_W, TASK_H


class Model:
    def __init__(self, spec: dict):
        self.spec = spec
        self.nodes = {n["id"]: dict(n) for n in spec["nodes"]}
        self.pools = spec["pools"]
        self.flows = spec.get("flows", [])
        self.messages = spec.get("messages", [])
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

    # -- định tuyến cạnh ------------------------------------------------------
    def route(self, flow: dict) -> list[tuple[float, float]]:
        if "waypoints" in flow:
            return flow["waypoints"]
        s, t = self.nodes[flow["src"]], self.nodes[flow["dst"]]
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
        """Nối một node với pool black box. `offset` đẩy đoạn dọc sang khoảng
        trống giữa hai cột để không cắt ngang shape của lane ở giữa."""
        pb = self.pool_bounds
        node_id = m["dst"] if m["src"] in pb else m["src"]
        pool_id = m["src"] if m["src"] in pb else m["dst"]
        n, p = self.nodes[node_id], pb[pool_id]
        off = m.get("offset", 0)
        stub = m.get("stub", 22)
        below = p["y"] > n["y"]                      # pool nằm phía dưới node
        y_node = n["y"] + n["h"] if below else n["y"]
        y_pool = p["y"] if below else p["y"] + p["h"]
        if off == 0:
            pts = [(n["cx"], y_node), (n["cx"], y_pool)]
        else:
            y_mid = y_node + stub if below else y_node - stub
            pts = [
                (n["cx"], y_node),
                (n["cx"], y_mid),
                (n["cx"] + off, y_mid),
                (n["cx"] + off, y_pool),
            ]
        return pts if m["src"] == node_id else list(reversed(pts))

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
            ' exporter="build.py" exporterVersion="0.1.0">'
        )

        # --- collaboration ---
        A(f'  <bpmn:collaboration id="{s["collaboration"]}">')
        for p in self.pools:
            if p.get("blackbox"):
                A(f'    <bpmn:participant id="{p["id"]}" name="{escape(p["name"])}" />')
            else:
                A(
                    f'    <bpmn:participant id="{p["id"]}" name="{escape(p["name"])}"'
                    f' processRef="{p["process"]}" />'
                )
        for i, m in enumerate(self.messages, 1):
            nm = f' name="{escape(m["name"])}"' if m.get("name") else ""
            A(
                f'    <bpmn:messageFlow id="MF_{i}"{nm} sourceRef="{m["src"]}"'
                f' targetRef="{m["dst"]}" />'
            )
        A("  </bpmn:collaboration>")

        # --- process ---
        for p in self.pools:
            if p.get("blackbox"):
                continue
            # Mô hình trong báo cáo là để đọc, không để chạy — nói rõ ra
            A(f'  <bpmn:process id="{p["process"]}" isExecutable="false">')
            A(f'    <bpmn:laneSet id="LaneSet_{p["process"]}">')
            for ln in p["lanes"]:
                A(f'      <bpmn:lane id="{ln["id"]}" name="{escape(ln["name"])}">')
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
                nm = f' name="{escape(n["name"])}"' if n.get("name") else ""
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
                extra = ""
                if n.get("default"):
                    extra = f' default="{n["default"]}"'
                if body:
                    A(f'    <bpmn:{kind} id="{n["id"]}"{nm}{extra}>')
                    L.extend(body)
                    A(f"    </bpmn:{kind}>")
                else:
                    A(f'    <bpmn:{kind} id="{n["id"]}"{nm}{extra} />')

            for f in self.flows:
                if self.nodes[f["src"]]["pool"] != p["id"]:
                    continue
                nm = f' name="{escape(f["name"])}"' if f.get("name") else ""
                A(
                    f'    <bpmn:sequenceFlow id="{self.flow_id(f)}"{nm}'
                    f' sourceRef="{f["src"]}" targetRef="{f["dst"]}" />'
                )
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
            if col:
                fill, stroke = PALETTE[col]
                attrs = (
                    f' bioc:stroke="{stroke}" bioc:fill="{fill}"'
                    f' color:background-color="{fill}" color:border-color="{stroke}"'
                )
            A(
                f'      <bpmndi:BPMNShape id="Shape_{n["id"]}" bpmnElement="{n["id"]}"{attrs}>'
            )
            A(self.bounds(node, 8))
            if n["kind"] in EVENT_KINDS or n["kind"] in GATEWAY_KINDS:
                if n.get("name"):
                    lw = 110
                    A("        <bpmndi:BPMNLabel>")
                    A(
                        f'          <dc:Bounds x="{node["cx"] - lw / 2:.0f}"'
                        f' y="{node["y"] + node["h"] + 6:.0f}" width="{lw}" height="27" />'
                    )
                    A("        </bpmndi:BPMNLabel>")
            A("      </bpmndi:BPMNShape>")
        for f in self.flows:
            wps = self.route(f)
            A(
                f'      <bpmndi:BPMNEdge id="Edge_{self.flow_id(f)}"'
                f' bpmnElement="{self.flow_id(f)}">'
            )
            for (x, y) in wps:
                A(f'        <di:waypoint x="{x:.0f}" y="{y:.0f}" />')
            if f.get("name"):
                lx, ly = self.edge_label(wps)
                A("        <bpmndi:BPMNLabel>")
                A(
                    f'          <dc:Bounds x="{lx:.0f}" y="{ly:.0f}"'
                    ' width="90" height="24" />'
                )
                A("        </bpmndi:BPMNLabel>")
            A("      </bpmndi:BPMNEdge>")
        for i, m in enumerate(self.messages, 1):
            wps = self.message_route(m)
            A(f'      <bpmndi:BPMNEdge id="Edge_MF_{i}" bpmnElement="MF_{i}">')
            for (x, y) in wps:
                A(f'        <di:waypoint x="{x:.0f}" y="{y:.0f}" />')
            if m.get("name"):
                lx = (wps[0][0] + wps[-1][0]) / 2
                ly = (wps[0][1] + wps[-1][1]) / 2
                A("        <bpmndi:BPMNLabel>")
                A(
                    f'          <dc:Bounds x="{lx + 6:.0f}" y="{ly - 10:.0f}"'
                    ' width="100" height="20" />'
                )
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
    def bounds(b: dict, indent: int) -> str:
        pad = " " * indent
        return (
            f'{pad}<dc:Bounds x="{b["x"]:.0f}" y="{b["y"]:.0f}"'
            f' width="{b["w"]:.0f}" height="{b["h"]:.0f}" />'
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
