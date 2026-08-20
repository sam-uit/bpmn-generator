#!/usr/bin/env python3
"""Sinh BPMN 2.0 (kèm BPMNDI) từ một bản mô tả YAML không có toạ độ.

    python3 tools/brief.py content/processes/<ten>-brief.yaml \
        -o content/processes/<ten>.bpmn

Lược đồ của `-brief.yaml` chính là **dạng lưới** (grid form) trong `docs/schema.md`
của typst-bpmn: giống hệt file `.yaml` lưu trữ, chỉ khác là không có `bounds`/`waypoints`.
Nhờ vậy đọc một brief hay đọc một model đã chuyển đổi là cùng một thói quen.

Khác biệt duy nhất: brief cũng **không cần** `row`/`col`. Script tự tính:

  - Cột  = phân tầng theo đường dài nhất trên đồ thị dòng chảy (bỏ qua cạnh quay lui).
  - Dòng = kế thừa dòng của bước trước; nhánh thứ hai trở đi của một gateway tụt xuống
           dòng dưới; đụng chỗ thì đẩy tiếp xuống.

Người viết vẫn thắng máy: khai `row`/`col` cho node nào thì node đó giữ nguyên.

Trước khi bố cục, brief được `tools/rules.normalize()` sửa những vi phạm well-formed
mà máy sửa được mà không cần đặt tên: chèn cổng hợp lưu, đặt nhánh mặc định. Mọi thay đổi
đều được in ra. Tắt bằng `--no-fix`. Xem `docs/bpmn-rules.md`.

Toạ độ tuyệt đối, bề rộng cột, định tuyến cạnh và BPMNDI do `build.py` lo — script
này chỉ trả lời câu hỏi "cái gì nằm ở ô lưới nào".
"""

from __future__ import annotations

import argparse
import pathlib
import sys


from .build import LANE_LEFT_PAD, MARKER_ELEMENTS, POOL_HEADER, Model, build
from .rules import check, load_brief, normalize

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("cần PyYAML: pip install pyyaml --break-system-packages")


# --- dạng lưới (typst-bpmn) -> tên phần tử BPMN ---------------------------------------
TASK_KIND = {
    "none": "task",
    "user": "userTask",
    "service": "serviceTask",
    "send": "sendTask",
    "receive": "receiveTask",
    "manual": "manualTask",
    "script": "scriptTask",
    "rule": "businessRuleTask",
    "call": "callActivity",
}
GATEWAY_KIND = {
    "exclusive": "exclusiveGateway",
    "parallel": "parallelGateway",
    "inclusive": "inclusiveGateway",
    "event": "eventBasedGateway",
}
DATA_KIND = {
    "object": "dataObjectReference",
    "store": "dataStoreReference",
    "input": "dataObjectReference",
    "output": "dataObjectReference",
}

# Artifact = thứ được vẽ nhưng không nằm trên dòng chảy: không có token đi qua, không
# vào `flowNodeRef`, không tham gia phân tầng. Tách riêng ngay từ đầu thì phần bố cục
# không phải biết chúng tồn tại.
ARTIFACT_KINDS = ("data", "annotation")

# --- behaviour marker ------------------------------------------------------------------
# Ký hiệu BPMN vẽ dọc cạnh dưới một activity. Từ vựng lấy đúng theo `convert.markers_of`,
# vì hai đầu phải khớp nhau: `bpmn2yaml` ghi ra tên nào thì `bpmn-brief` phải đọc lại
# được đúng tên đó, nếu không thì vòng lặp yaml -> bpmn -> yaml mất marker ở vòng hai.
#
# Ba nhóm, và chúng khác nhau ở chỗ đi vào XML:
#   loop / mi-*   ->  một phần tử con `loopCharacteristics`
#   compensation  ->  thuộc tính `isForCompensation` trên chính activity
#   adhoc         ->  tên phần tử `adHocSubProcess`, tức là đổi cả loại phần tử
# `MARKER_ELEMENTS` nằm ở `build.py`: nó là chuỗi XML, mà XML là việc của tầng dựng.
# Ở đây chỉ cần biết *tên nào hợp lệ*, và tên nào sinh ra một `loopCharacteristics`.
MARKER_CANON = dict.fromkeys(list(MARKER_ELEMENTS) + ["compensation", "adhoc"])

# Tên viết tắt cho cùng một marker. `parallel`/`sequential` có ở đây vì đó là chữ người
# viết gõ ra trước tiên, và vì trong ngữ cảnh của một activity thì không còn nghĩa nào
# khác để nhầm. Trên một *cổng* thì có, nên chỗ đó vẫn phải báo lỗi.
MARKER_ALIASES = {
    "parallel": "mi-parallel",
    "sequential": "mi-sequential",
    "mi_parallel": "mi-parallel",
    "mi_sequential": "mi-sequential",
    "multi-instance": "mi-parallel",
    "multiinstance": "mi-parallel",
    "compensate": "compensation",
    "ad-hoc": "adhoc",
}

# Chỉ activity mang được marker. Cái này không phải giới hạn của script mà là của BPMN:
# `loopCharacteristics` là thuộc tính của `tActivity`, sự kiện và cổng không có chỗ đặt.
MARKER_KINDS = ("task", "subprocess")


def markers_of(n: dict) -> list[str]:
    """Đọc `markers:` của một node, chuẩn hoá tên, và dừng lại khi nó vô nghĩa.

    Dừng chứ không bỏ qua: một marker gõ sai mà bị lặng lẽ bỏ thì sơ đồ vẫn sinh ra,
    vẫn mở được, và thiếu đúng cái vòng lặp mà người viết muốn nói. Lỗi im lặng ở đây
    đắt hơn hẳn một dòng báo lỗi.
    """
    raw = n.get("markers") or []
    if isinstance(raw, str):
        raw = [raw]
    if not raw:
        return []

    nid = n.get("id", "?")
    kind = n.get("kind", "task")
    if kind not in MARKER_KINDS:
        hint = ""
        if kind == "gateway":
            hint = ("\n  cổng không mang marker; loại cổng khai bằng "
                    "`gateway: parallel|exclusive|inclusive|event`")
        elif kind == "event":
            hint = "\n  sự kiện không mang marker; loại sự kiện khai bằng `definition:`"
        raise SystemExit(f"bpmn-brief: `markers` chỉ dùng được cho activity, "
                         f"không cho kind '{kind}' (node {nid}){hint}")

    out: list[str] = []
    for m in raw:
        key = MARKER_ALIASES.get(str(m).strip().lower(), str(m).strip().lower())
        if key not in MARKER_CANON:
            raise SystemExit(
                f"bpmn-brief: marker không có: '{m}' (node {nid})\n"
                f"  hợp lệ: {', '.join(MARKER_CANON)}"
            )
        if key == "adhoc":
            raise SystemExit(
                f"bpmn-brief: marker 'adhoc' cần phần tử adHocSubProcess (node {nid})\n"
                "  subprocess chưa hỗ trợ, giữ file .bpmn làm nguồn sự thật cho mô hình này"
            )
        if key not in out:
            out.append(key)

    # Một activity có **một** `loopCharacteristics`, không phải nhiều. Khai cả `loop` lẫn
    # `mi-parallel` thì XML sinh ra sẽ có hai phần tử con và Modeler chỉ đọc cái đầu:
    # sai âm thầm, đúng loại lỗi cần bắt sớm.
    repeat = [m for m in out if m in MARKER_ELEMENTS]
    if len(repeat) > 1:
        raise SystemExit(
            f"bpmn-brief: node {nid} khai {len(repeat)} kiểu lặp cùng lúc "
            f"({', '.join(repeat)})\n  một activity chỉ mang được một `loopCharacteristics`"
        )
    return out


def element_of(n: dict) -> str:
    kind = n.get("kind", "task")
    if kind == "task":
        return TASK_KIND.get(n.get("task", "none"), "task")
    if kind == "gateway":
        return GATEWAY_KIND.get(n.get("gateway", "exclusive"), "exclusiveGateway")
    if kind == "event":
        ev = n.get("event", "start")
        if ev == "start":
            return "startEvent"
        if ev == "end":
            return "endEvent"
        return "intermediateThrowEvent" if n.get("throw") else "intermediateCatchEvent"
    if kind == "data":
        return DATA_KIND.get(n.get("data", "object"), "dataObjectReference")
    if kind == "annotation":
        return "textAnnotation"
    hint = {
        "subprocess": "gỡ subprocess ra thành một mô hình riêng, hoặc giữ file .bpmn "
                      "làm nguồn sự thật cho mô hình này",
        "group": "bỏ group khỏi .yaml — group chỉ là khung trang trí, vẽ lại trong Modeler",
    }.get(kind)
    tail = f"\n  {hint}" if hint else ""
    raise SystemExit(f"bpmn-brief: chưa hỗ trợ kind '{kind}' (node {n.get('id')}){tail}")


# --- phân tầng ------------------------------------------------------------------------
def back_edges(nodes: list[str], edges: list[tuple[str, str]]) -> set[int]:
    """Cạnh quay lui = cạnh trỏ về một node đang nằm trên ngăn xếp DFS.

    Vòng lặp rework là chuyện thường trong quy trình thật; nếu đem nó vào phân tầng thì
    không còn thứ tự nào hợp lệ. Nên tách ra, xếp chỗ theo phần còn lại, rồi vẽ nó bằng
    cung quay lui phía dưới.
    """
    out: dict[str, list[tuple[int, str]]] = {n: [] for n in nodes}
    for i, (s, t) in enumerate(edges):
        if s in out:
            out[s].append((i, t))

    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in nodes}
    back: set[int] = set()

    def visit(u: str) -> None:
        color[u] = GREY
        for i, v in out.get(u, ()):
            if color.get(v, BLACK) == GREY:
                back.add(i)
            elif color.get(v, BLACK) == WHITE:
                visit(v)
        color[u] = BLACK

    sys.setrecursionlimit(10000)
    for n in nodes:
        if color[n] == WHITE:
            visit(n)
    return back


def layer(nodes: list[dict], edges: list[tuple[str, str]], back: set[int]) -> dict[str, int]:
    """Cột = đường dài nhất tính từ một node nguồn. Node khai sẵn `col` thì giữ nguyên."""
    ids = [n["id"] for n in nodes]
    fixed = {n["id"]: n["col"] - 1 for n in nodes if "col" in n}
    fwd = [(s, t) for i, (s, t) in enumerate(edges) if i not in back]
    preds: dict[str, list[str]] = {i: [] for i in ids}
    for s, t in fwd:
        if t in preds and s in preds:
            preds[t].append(s)

    col: dict[str, int] = {}

    def solve(u: str, seen: frozenset[str]) -> int:
        if u in col:
            return col[u]
        if u in fixed:
            col[u] = fixed[u]
            return col[u]
        if u in seen:
            return 0
        ps = preds.get(u, [])
        c = 0 if not ps else max(solve(p, seen | {u}) for p in ps) + 1
        col[u] = c
        return c

    for i in ids:
        solve(i, frozenset())
    return col


def assign_rows(nodes: list[dict], edges: list[tuple[str, str]], back: set[int],
                col: dict[str, int]) -> dict[str, int]:
    """Dòng = kế thừa bước trước; nhánh thứ hai trở đi tụt xuống; đụng thì đẩy tiếp.

    Thứ tự khai báo trong YAML quyết định nhánh nào giữ được dòng chính — đó là chỗ
    người viết nói "nhánh này mới là dòng chảy chính", và máy phải nghe theo.
    """
    by_id = {n["id"]: n for n in nodes}
    fwd = [(s, t) for i, (s, t) in enumerate(edges) if i not in back]

    rank: dict[tuple[str, str], int] = {}
    seen_src: dict[str, int] = {}
    for s, t in fwd:
        rank[(s, t)] = seen_src.get(s, 0)
        seen_src[s] = rank[(s, t)] + 1

    preds: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for s, t in fwd:
        if t in preds:
            preds[t].append(s)

    row: dict[str, int] = {}
    taken: set[tuple[str, int, int]] = set()
    order = sorted(nodes, key=lambda n: (col[n["id"]], nodes.index(n)))

    for n in order:
        nid = n["id"]
        lane = n.get("lane", "")
        if "row" in n:
            row[nid] = n["row"] - 1
            taken.add((lane, col[nid], row[nid]))
            continue
        ps = [p for p in preds[nid] if p in row]
        if not ps:
            want = 0
        elif len(ps) > 1:
            # Điểm hợp lưu kéo về dòng chính
            want = min(row[p] for p in ps)
        else:
            p = ps[0]
            want = row[p] + rank.get((p, nid), 0)
        while (lane, col[nid], want) in taken:
            want += 1
        row[nid] = want
        taken.add((lane, col[nid], want))
    return row


# --- dựng spec cho bpmnbuild -----------------------------------------------------------
def to_spec(brief: dict, source: str) -> dict:
    meta = brief.get("meta", {})
    pools_in = brief.get("pools", [])
    all_nodes = brief.get("nodes", [])
    flows_in = brief.get("flows", [])

    # Artifact ra một rổ riêng: chúng được vẽ nhưng không nằm trên dòng chảy.
    nodes_in = [n for n in all_nodes if n.get("kind") not in ARTIFACT_KINDS]
    artifacts_in = [n for n in all_nodes if n.get("kind") in ARTIFACT_KINDS]

    pools = []
    lane_of_pool = {}
    for p in pools_in:
        pid = p["id"]
        # Một participant không có lane và không chứa node nào là black box — dù file
        # nguồn không nói thẳng. Đây là chỗ `.yaml` chuyển đổi ngược quay lại được:
        # `bpmn2yaml` không ghi `blackbox`, nó chỉ đơn giản không ghi `lanes`.
        if p.get("blackbox") or not p.get("lanes"):
            bb = dict(id=pid, name=p.get("name", pid), blackbox=True)
            if p.get("bounds"):
                bb["bounds"] = p["bounds"]
            pools.append(bb)
            continue
        lanes = []
        for l in p.get("lanes", []):
            l = dict(id=l, name=l) if isinstance(l, str) else dict(l)
            ln = dict(id=l["id"], name=l.get("name", l["id"]), rows=1)
            if l.get("bounds"):
                ln["bounds"] = l["bounds"]
            lanes.append(ln)
            lane_of_pool[l["id"]] = pid
        entry = dict(
            id=pid,
            name=p.get("name", pid),
            process=p.get("process", "Process_" + pid),
            lanes=lanes,
        )
        if p.get("bounds"):
            entry["bounds"] = p["bounds"]
        pools.append(entry)

    # Lane mặc định khi node không khai: lane đầu tiên
    first_lane = next((l["id"] for p in pools for l in p.get("lanes", [])), None)
    for n in nodes_in:
        n.setdefault("lane", first_lane)

    ids = [n["id"] for n in nodes_in]
    seq = [f for f in flows_in if f.get("kind", "sequence") == "sequence"]
    edges = [(f["source"], f["target"]) for f in seq]
    back = back_edges(ids, edges)
    col = layer(nodes_in, edges, back)
    row = assign_rows(nodes_in, edges, back, col)

    # Số dòng thật của mỗi lane
    rows_per_lane: dict[str, int] = {}
    for n in nodes_in:
        lane = n["lane"]
        rows_per_lane[lane] = max(rows_per_lane.get(lane, 1), row[n["id"]] + 1)
    # Artifact treo dưới phần tử chủ, nên lane phải chừa thêm một dòng cho nó — nếu
    # không thì cái kho dữ liệu rơi ra ngoài khung lane.
    hosts_with_art = {f["target"] if f["source"] in {a["id"] for a in artifacts_in} else f["source"]
                      for f in flows_in if f.get("kind") in ("data", "association")}
    for n in nodes_in:
        if n["id"] in hosts_with_art:
            lane = n["lane"]
            rows_per_lane[lane] = max(rows_per_lane.get(lane, 1), row[n["id"]] + 2)
    for p in pools:
        for l in p.get("lanes", []):
            l["rows"] = rows_per_lane.get(l["id"], 1)

    nodes = []
    for n in nodes_in:
        out = dict(
            id=n["id"],
            name=n.get("name", ""),
            kind=element_of(n),
            lane=n["lane"],
            col=col[n["id"]],
            row=row[n["id"]],
        )
        if n.get("definition") and n.get("definition") != "none":
            out["definition"] = n["definition"]
        if n.get("color"):
            out["color"] = n["color"]
        for k in ("fill", "stroke"):
            if n.get(k):
                out[k] = n[k]
        if n.get("default"):
            out["default"] = n["default"]
        ms = markers_of(n)
        if ms:
            out["markers"] = ms
        # Toạ độ có sẵn thì đi thẳng vào `build.py` và thắng bố cục tự động. Một `.yaml`
        # do `bpmn2yaml` sinh ra sau khi chỉnh tay trong Modeler luôn mang theo chúng.
        # `isMarkerVisible` của cổng loại trừ: Modeler cho bật/tắt dấu X, và đó là lựa
        # chọn trình bày của người vẽ chứ không suy ra được từ cấu trúc.
        if n.get("marker") and n.get("kind") == "gateway":
            out["marker"] = True
        if n.get("bounds"):
            out["bounds"] = n["bounds"]
        if n.get("label"):
            out["label"] = n["label"]
        nodes.append(out)

    flows = []
    for i, f in enumerate(seq):
        d = dict(src=f["source"], dst=f["target"])
        # Giữ id cạnh nếu file nguồn đã có: cổng rẽ trỏ tới nhánh mặc định *bằng id*,
        # nên sinh lại id mới sẽ làm `default=` trỏ vào hư không.
        if f.get("id"):
            d["id"] = f["id"]
        if f.get("name"):
            d["name"] = f["name"]
        for k in ("label", "fill", "stroke"):
            if f.get(k):
                d[k] = f[k]
        if f.get("waypoints"):
            d["waypoints"] = f["waypoints"]
        elif f.get("route"):
            d["route"] = f["route"]
        elif edges[i] and i in back:
            # Cung quay lui: vòng xuống dưới rồi trở về, đúng cách một modeler vẽ
            d["route"] = "loop"
            d["dy"] = 45
        flows.append(d)

    messages = []
    for f in flows_in:
        if f.get("kind") == "message":
            m = dict(src=f["source"], dst=f["target"])
            if f.get("id"):
                m["id"] = f["id"]
            if f.get("name"):
                m["name"] = f["name"]
            if f.get("offset"):
                m["offset"] = f["offset"]
            for k in ("waypoints", "label", "fill", "stroke"):
                if f.get(k):
                    m[k] = f[k]
            messages.append(m)

    # --- artifact và dây nối của chúng ---------------------------------------------
    # Artifact không tự biết mình treo vào đâu; chỗ duy nhất nói điều đó là cạnh
    # `data`/`association`. Nên đọc cạnh trước, rồi mới đặt được artifact.
    art_ids = {a["id"] for a in artifacts_in}
    node_ids = {n["id"] for n in nodes_in}
    links = []
    for f in flows_in:
        if f.get("kind") not in ("data", "association"):
            continue
        s, t = f["source"], f["target"]
        if s in art_ids and t in node_ids:
            art, host, direction = s, t, "input"
        elif t in art_ids and s in node_ids:
            art, host, direction = t, s, "output"
        else:
            continue
        lk = dict(id=f.get("id"), art=art, host=host,
                  direction=direction, kind=f.get("kind"))
        if f.get("waypoints"):
            lk["waypoints"] = f["waypoints"]
        links.append(lk)

    host_of = {l["art"]: l["host"] for l in links}
    artifacts = []
    for a in artifacts_in:
        out = dict(
            id=a["id"],
            name=a.get("name", "") or a.get("text", ""),
            kind=element_of(a),
            host=host_of.get(a["id"]),
        )
        if a.get("lane"):
            out["lane"] = a["lane"]
        for k in ("bounds", "label", "fill", "stroke"):
            if a.get(k):
                out[k] = a[k]
        artifacts.append(out)

    orphan = [a["id"] for a in artifacts if a["host"] is None]
    if orphan:
        print(f"  [chú ý] {len(orphan)} artifact không nối vào phần tử nào, bị bỏ qua: "
              + ", ".join(orphan))
        artifacts = [a for a in artifacts if a["host"] is not None]
        links = [l for l in links if l["art"] not in orphan]

    return dict(
        id=meta.get("id", "Definitions_" + pathlib.Path(source).stem.replace("-", "_")),
        collaboration=meta.get("collaboration", "Collaboration_1"),
        pools=pools,
        nodes=nodes,
        flows=flows,
        messages=messages,
        artifacts=artifacts,
        links=links,
    )


# --- báo cáo kích thước ----------------------------------------------------------------
def report_fit(spec: dict, text_width_mm: float = 174.0, font_units: float = 11.0) -> None:
    """Kích thước "đủ nhìn" là một quyết định, nên phải nói ra bằng số.

    Không cố ép sơ đồ nhỏ nhất hay to nhất — chỉ báo cỡ chữ sẽ in ra và gợi ý lát cắt
    khi nó rơi xuống dưới ngưỡng đọc được (6pt).
    """
    m = Model(spec)
    xs = [b["x"] for b in m.pool_bounds.values()]
    x1 = [b["x"] + b["w"] for b in m.pool_bounds.values()]
    ys = [b["y"] for b in m.pool_bounds.values()]
    y1 = [b["y"] + b["h"] for b in m.pool_bounds.values()]
    w = max(x1) - min(xs)
    h = max(y1) - min(ys)
    pt = font_units * (text_width_mm / w) * 72 / 25.4
    size_at = lambda width: font_units * (text_width_mm / width) * 72 / 25.4
    budget = font_units * (text_width_mm / 6) * 72 / 25.4  # bề rộng tối đa để còn 6pt

    def verdict(width):
        s = size_at(width)
        return f"{s:4.1f}pt  {'đọc được' if s >= 6 else 'quá nhỏ'}"

    print(f"  extent {w:.0f} x {h:.0f} (tỉ lệ {w / h:.2f})")
    print(f"  Ở bề rộng chữ {text_width_mm:.0f}mm, ngưỡng đọc được là 6pt "
          f"(tương ứng mô hình rộng tối đa ~{budget:.0f} đơn vị):")
    print(f"    toàn cảnh          {w:7.0f} đv   {verdict(w)}")

    # Từng lane: bề rộng thật của phần có node, chưa tính `compact` nén dải trống
    BANDS = POOL_HEADER + 30 + 2 * LANE_LEFT_PAD
    lanes = {}
    for n in m.nodes.values():
        e = lanes.setdefault(n["lane"], [1e9, -1e9, 0])
        e[0] = min(e[0], n["x"])
        e[1] = max(e[1], n["x"] + n["w"])
        e[2] += 1
    names = {l["id"]: l["name"] for p in spec["pools"] for l in p.get("lanes", [])}
    for lane, (x0, x1, cnt) in lanes.items():
        lw = x1 - x0 + BANDS
        nm = names.get(lane, lane)
        print(f"    lane {nm:<18.18} {lw:7.0f} đv   {verdict(lw)}   ({cnt} node)")

    print("  (số của lane là cận trên — `compact: true` còn nén được các dải trống)")
    if pt < 6:
        print("  Gợi ý: cắt bằng bpmn-lane(M, \"<tên lane>\"), hoặc hẹp hơn nữa bằng")
        print("         bpmn-part(M, (<id>, ..), lane: \"<tên lane>\") — xem docs/bpmn-workflow.md")


def report_pinning(spec: dict) -> None:
    """Nói ra khi toạ độ trong file chỉ có một nửa.

    Ghim toàn bộ thì đúng, không ghim gì cũng đúng. Ghim một nửa thì phần được ghim nằm
    ở chỗ Modeler đặt, phần còn lại nằm ở chỗ lưới tính, và hai hệ toạ độ đó không biết
    nhau: kết quả là hình chồng lấn mà không có gì báo. Đây đúng là loại lỗi im lặng mà
    tài liệu của repo nói phải dừng lại và báo.
    """
    nodes = spec["nodes"]
    pinned = [n for n in nodes if n.get("bounds")]
    if pinned and len(pinned) != len(nodes):
        loose = [n["id"] for n in nodes if not n.get("bounds")]
        print(f"  [chú ý] {len(pinned)}/{len(nodes)} node có `bounds`, số còn lại được bố "
              f"cục lại nên có thể chồng lên nhau: {', '.join(loose[:5])}"
              + (" ..." if len(loose) > 5 else ""))
    flows = spec.get("flows", [])
    routed = [f for f in flows if f.get("waypoints")]
    if routed and len(routed) != len(flows):
        print(f"  [chú ý] {len(routed)}/{len(flows)} luồng có `waypoints`, số còn lại "
              "được định tuyến lại")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief", help="file <ten>-brief.yaml")
    ap.add_argument("-o", "--out", help="file .bpmn xuất ra (mặc định: bỏ hậu tố -brief)")
    ap.add_argument("--width", type=float, default=174.0, help="bề rộng chữ (mm) để báo cỡ chữ")
    ap.add_argument("--no-fix", action="store_true",
                    help="không tự chèn cổng hợp lưu / đặt nhánh mặc định")
    args = ap.parse_args()

    src = pathlib.Path(args.brief)
    brief = yaml.safe_load(src.read_text(encoding="utf-8"))
    out = args.out or str(src).replace("-brief.yaml", ".bpmn").replace("-brief.yml", ".bpmn")
    if out == str(src):
        return print("bpmnbrief: cần -o, tên file không có hậu tố -brief") or 1

    # Sửa những vi phạm máy sửa được, trước khi bố cục — chèn cổng làm đổi đồ thị nên
    # phải xong trước khi phân tầng.
    if not args.no_fix:
        brief, changes = normalize(brief)
        for c in changes:
            print(f"  [sửa] {c.detail}")

    spec = to_spec(brief, src.name)
    report_pinning(spec)
    build(spec, out)
    report_fit(spec, text_width_mm=args.width)

    # Những gì còn lại là lỗi mô hình hoá, người phải sửa
    rest = [f for f in check(load_brief(brief)) if f.level == "error"]
    if rest:
        print(f"  {len(rest)} lỗi còn lại (xem docs/bpmn-rules.md):")
        for f in rest:
            print(f"    ✗ [{f.code}] {f.node}: {f.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
