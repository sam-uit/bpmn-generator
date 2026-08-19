#!/usr/bin/env python3
"""Đổi phương của một sơ đồ BPMN: ngang thành dọc, hoặc ngược lại.

    bpmn-rotate quy-trinh.bpmn -o quy-trinh-doc.bpmn

Không phải xoay hình. Xoay hình là việc của phía kết xuất (typst-bpmn quay cả bản vẽ
một góc để nó vừa trang giấy, chữ quay theo). Ở đây là đổi *cách đọc* sơ đồ: pool đang
là dải ngang xếp chồng, dòng chảy trái sang phải, thì thành cột dọc đứng cạnh nhau,
dòng chảy trên xuống dưới. Chữ vẫn nằm ngang, vẫn đọc bình thường.

## Phép biến đổi là chuyển vị, không phải phép quay

Quay 90 độ thì hoặc dòng chảy chạy ngược, hoặc lane đầu tiên rơi xuống cuối. Cái đúng
là **chuyển vị**, `(x, y) -> (y, x)`, tức là lật qua đường chéo chính:

    ngang:  dòng chảy theo +x, lane xếp theo +y
    dọc:    dòng chảy theo +y, lane xếp theo +x

Chuyển vị giữ được cả hai thứ tự: điểm bắt đầu vẫn ở góc trên trái, lane khai trước vẫn
đứng trước. Về hình học nó là một phép phản chiếu (định thức âm), nhưng với một bản vẽ
toàn hình chữ nhật thẳng trục thì không ai nhận ra, và cái người đọc thật sự nhìn thấy,
"dòng chảy đi xuống, lane trải ngang", thì đúng.

## Khung thì hoán kích thước, ký hiệu thì không

Đây là chỗ một phép nhân ma trận thuần tuý làm sai. Chuyển vị nguyên xi cả `width` lẫn
`height` sẽ biến task 100x80 thành 80x100, tức là cao hơn rộng, mà BPMN thì luôn vẽ task
rộng hơn cao bất kể sơ đồ đi theo phương nào. Ngược lại, một pool 3000x250 thì *phải*
thành 250x3000, nếu không thì không còn là cột.

Ranh giới đúng là **khung thì hoán, ký hiệu thì không**:

  - hoán `w`/`h`: participant, lane, subprocess đã mở, group. Chúng là vùng chứa, và
    thứ chúng chứa vừa đổi phương.
  - giữ nguyên `w`/`h`: task, event, gateway, data object, ghi chú. Chúng là ký hiệu có
    hình dạng cố định trong đặc tả.

Ký hiệu giữ kích thước thì không chuyển vị được góc trên trái nữa, phải chuyển vị **tâm**
rồi đặt lại hộp quanh tâm đó.

## Cạnh phải neo lại

Chuyển vị waypoint xong thì đầu và cuối mỗi cạnh không còn nằm trên viền của ký hiệu,
đúng vì ký hiệu không đổi kích thước. Nên hai đầu được neo lại vào viền theo hướng của
đoạn kề nó. Các điểm gãy ở giữa thì giữ nguyên: định tuyến lại cho một bố cục dọc là
việc của `build.py` ở chế độ dọc, không phải của một bộ lọc toạ độ. Xem `docs/TODO.md`.

Vì vậy kết quả của lệnh này là *bố cục ngang đã chuyển vị*, không phải một bố cục dọc
được sinh ra từ đầu. Nó dùng được ngay, kể cả với file có subprocess hay group mà
`bpmn-brief` chưa dựng lại được, và đó là lý do nó tồn tại.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET

MODEL = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"
DI = "http://www.omg.org/spec/DD/20100524/DI"

# Giữ tiền tố quen thuộc khi ghi lại, nếu không thì ElementTree đặt `ns0:`, `ns1:` và
# file mở ra trong Modeler vẫn đúng nhưng không ai đọc được diff.
NAMESPACES = {
    "bpmn": MODEL,
    "bpmndi": BPMNDI,
    "dc": DC,
    "di": DI,
    "bioc": "http://bpmn.io/schema/bpmn/biocolor/1.0",
    "color": "http://www.omg.org/spec/BPMN/non-normative/color/1.0",
    "modeler": "http://camunda.org/schema/modeler/1.0",
    "zeebe": "http://camunda.org/schema/zeebe/1.0",
    "camunda": "http://camunda.org/schema/1.0/bpmn",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

# Vùng chứa: hoán `w`/`h` khi đổi phương. Danh sách theo *tên phần tử ngữ nghĩa* mà
# BPMNShape trỏ tới, không theo tên của chính BPMNShape.
CONTAINERS = {"participant", "lane", "subProcess", "transaction", "adHocSubProcess", "group"}

# Neo cách viền một chút, giống cách Modeler vẽ: mũi tên chạm viền chứ không chạm góc.
DOCK_MARGIN = 6


def local(e: ET.Element) -> str:
    return e.tag.rsplit("}", 1)[-1]


def num(v: str | None, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def fmt(v: float) -> str:
    """Số nguyên thì in không có phần thập phân, giống hệt cách Modeler ghi."""
    return str(int(round(v))) if abs(v - round(v)) < 1e-9 else f"{v:g}"


# --- đọc cấu trúc ----------------------------------------------------------------------
def semantic_kinds(root: ET.Element) -> dict[str, str]:
    """id phần tử ngữ nghĩa -> tên phần tử. BPMNShape chỉ mang `bpmnElement`, nên muốn
    biết một shape là pool hay là task thì phải tra ngược sang phần thân của file."""
    out: dict[str, str] = {}
    for e in root.iter():
        eid = e.get("id")
        if eid and local(e) not in ("BPMNShape", "BPMNEdge", "BPMNLabel", "BPMNPlane",
                                    "BPMNDiagram", "Bounds"):
            out[eid] = local(e)
    return out


def bounds_of(shape: ET.Element) -> ET.Element | None:
    for c in shape:
        if local(c) == "Bounds":
            return c
    return None


def rect(b: ET.Element) -> tuple[float, float, float, float]:
    return num(b.get("x")), num(b.get("y")), num(b.get("width")), num(b.get("height"))


# --- phép biến đổi ---------------------------------------------------------------------
def transpose_box(b: ET.Element, swap: bool) -> None:
    """Chuyển vị một `dc:Bounds` tại chỗ.

    `swap=True` cho vùng chứa: hoán luôn `w`/`h`, và khi đó góc trên trái chuyển vị thẳng.
    `swap=False` cho ký hiệu: giữ `w`/`h`, chuyển vị **tâm** rồi đặt lại hộp quanh tâm.
    """
    x, y, w, h = rect(b)
    if swap:
        b.set("x", fmt(y))
        b.set("y", fmt(x))
        b.set("width", fmt(h))
        b.set("height", fmt(w))
    else:
        cx, cy = x + w / 2, y + h / 2
        b.set("x", fmt(cy - w / 2))
        b.set("y", fmt(cx - h / 2))


def dock(box: tuple[float, float, float, float],
         inner: tuple[float, float]) -> tuple[float, float]:
    """Điểm neo trên viền `box`, nhìn từ điểm `inner` kề nó.

    Chọn cạnh theo trục mà điểm kề lệch xa hơn, rồi kẹp toạ độ còn lại vào trong cạnh đó.
    Kẹp chứ không lấy tâm: nếu đoạn kề đang thẳng đứng thì giữ nguyên hoành độ của nó,
    cạnh vẫn thẳng đứng sau khi neo.
    """
    x, y, w, h = box
    cx, cy = x + w / 2, y + h / 2
    px, py = inner
    dx, dy = px - cx, py - cy
    # Không có cạnh nào rõ ràng (điểm kề nằm ngay tâm): neo xuống dưới cho có định hướng.
    if dx == 0 and dy == 0:
        return cx, y + h
    if abs(dx) * h >= abs(dy) * w:
        edge_x = x + w if dx > 0 else x
        return edge_x, min(max(py, y + DOCK_MARGIN), y + h - DOCK_MARGIN)
    edge_y = y + h if dy > 0 else y
    return min(max(px, x + DOCK_MARGIN), x + w - DOCK_MARGIN), edge_y


def rotate(root: ET.Element) -> dict[str, int]:
    kinds = semantic_kinds(root)
    stat = {"shape": 0, "container": 0, "edge": 0, "label": 0, "flip": 0}

    boxes: dict[str, tuple[float, float, float, float]] = {}
    origin: list[tuple[float, float]] = []

    for shape in root.iter():
        if local(shape) != "BPMNShape":
            continue
        b = bounds_of(shape)
        if b is None:
            continue
        x, y, w, h = rect(b)
        origin.append((x, y))
        ref = shape.get("bpmnElement", "")
        kind = kinds.get(ref, "")
        # Một subprocess thu gọn được vẽ đúng bằng ký hiệu task, nên nó không phải vùng
        # chứa dù tên phần tử nói vậy. `isExpanded` là chỗ duy nhất phân biệt hai cái.
        expanded = shape.get("isExpanded", "true") != "false"
        swap = kind in CONTAINERS and (expanded or kind in ("participant", "lane", "group"))
        transpose_box(b, swap)
        stat["container" if swap else "shape"] += 1

        if shape.get("isHorizontal") is not None:
            shape.set("isHorizontal", "false" if shape.get("isHorizontal") != "false" else "true")
            stat["flip"] += 1

        boxes[ref] = rect(b)

        # Nhãn của event và gateway **chuyển vị theo**, tức là từ dưới ký hiệu chuyển sang
        # bên phải nó. Nghe như mất quy ước, nhưng quy ước thật không phải "nhãn nằm dưới"
        # mà là "nhãn nằm vuông góc với dòng chảy": dòng chảy ngang thì nhãn xuống dưới,
        # dòng chảy dọc thì nhãn ra bên cạnh. Đã thử giữ nguyên độ lệch và dựng thử: nhãn
        # nằm dưới thì cạnh đi xuống cắt ngang qua chữ.
        for c in shape:
            if local(c) == "BPMNLabel":
                lb = bounds_of(c)
                if lb is not None:
                    transpose_box(lb, False)
                    stat["label"] += 1

    for edge in root.iter():
        if local(edge) != "BPMNEdge":
            continue
        pts = [c for c in edge if local(c) == "waypoint"]
        for p in pts:
            x, y = num(p.get("x")), num(p.get("y"))
            p.set("x", fmt(y))
            p.set("y", fmt(x))
        # Neo lại hai đầu: ký hiệu giữ nguyên kích thước nên waypoint đã chuyển vị không
        # còn nằm trên viền của chúng.
        if len(pts) >= 2:
            for end, nxt, ref in ((pts[0], pts[1], edge.get("sourceElement")),
                                  (pts[-1], pts[-2], edge.get("targetElement"))):
                box = _box_for(edge, ref, boxes, end is pts[0], root)
                if box is None:
                    continue
                nx, ny = dock(box, (num(nxt.get("x")), num(nxt.get("y"))))
                end.set("x", fmt(nx))
                end.set("y", fmt(ny))
        for c in edge:
            if local(c) == "BPMNLabel":
                lb = bounds_of(c)
                if lb is not None:
                    transpose_box(lb, False)
                    stat["label"] += 1
        stat["edge"] += 1

    # Giữ nguyên góc trên trái của cả bản vẽ. Chuyển vị đổi chỗ hai toạ độ của gốc, nên
    # không dịch lại thì sơ đồ nhảy sang một chỗ khác trên mặt phẳng mà không vì lý do gì.
    if origin:
        want_x = min(p[0] for p in origin)
        want_y = min(p[1] for p in origin)
        got_x, got_y = want_y, want_x
        translate(root, want_x - got_x, want_y - got_y)
    return stat


def _box_for(edge: ET.Element, ref: str | None, boxes: dict, is_source: bool,
             root: ET.Element) -> tuple[float, float, float, float] | None:
    """Hộp của đầu cạnh. `sourceElement`/`targetElement` là tuỳ chọn trong DI, nhiều bộ
    xuất không ghi, nên phải lần ngược qua phần thân bằng `bpmnElement` của chính cạnh."""
    if ref and ref in boxes:
        return boxes[ref]
    fid = edge.get("bpmnElement")
    if not fid:
        return None
    for e in root.iter():
        if e.get("id") != fid:
            continue
        end = e.get("sourceRef") if is_source else e.get("targetRef")
        if end in boxes:
            return boxes[end]
    return None


def translate(root: ET.Element, dx: float, dy: float) -> None:
    if dx == 0 and dy == 0:
        return
    for e in root.iter():
        t = local(e)
        if t == "Bounds":
            e.set("x", fmt(num(e.get("x")) + dx))
            e.set("y", fmt(num(e.get("y")) + dy))
        elif t == "waypoint":
            e.set("x", fmt(num(e.get("x")) + dx))
            e.set("y", fmt(num(e.get("y")) + dy))


def orientation(root: ET.Element) -> str:
    """Phương hiện tại, đọc từ các pool. Không có pool nào thì coi như ngang."""
    vals = [s.get("isHorizontal") for s in root.iter()
            if local(s) == "BPMNShape" and s.get("isHorizontal") is not None]
    if not vals:
        return "horizontal"
    return "vertical" if all(v == "false" for v in vals) else "horizontal"


# --- CLI --------------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="bpmn-rotate",
        description="Đổi phương của sơ đồ BPMN: ngang thành dọc, hoặc ngược lại.")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", help="mặc định ghi đè file vào")
    ap.add_argument("--to", choices=("horizontal", "vertical", "flip"), default="flip",
                    help="phương đích; `flip` (mặc định) là đảo phương hiện tại")
    a = ap.parse_args(argv)

    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)

    tree = ET.parse(a.input)
    root = tree.getroot()
    now = orientation(root)
    if a.to != "flip" and a.to == now:
        print(f"bpmn-rotate: {a.input} đã là {now}, không đổi gì")
        return 0

    stat = rotate(root)
    out = a.output or a.input
    ET.indent(tree, space="  ")
    tree.write(out, encoding="UTF-8", xml_declaration=True)
    print(f"{out}: {now} -> {orientation(root)}, "
          f"{stat['container']} khung, {stat['shape']} ký hiệu, {stat['edge']} cạnh, "
          f"{stat['label']} nhãn")
    return 0


if __name__ == "__main__":
    sys.exit(main())
