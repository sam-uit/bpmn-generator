#!/usr/bin/env python3
"""Kiểm thử vòng lặp `.yaml` -> `.bpmn` -> `.yaml`, chạy: python3 tests/test_roundtrip.py

Khẳng định trung tâm: một file `.yaml` do `bpmn2yaml` sinh ra, đưa lại vào `bpmn-brief`
rồi chuyển ngược, phải cho ra **đúng file cũ**, trừ dòng `source` vốn ghi tên file nguồn.

Vì sao đây là bài kiểm quan trọng nhất của repo: vòng lặp cải tiến nằm ở chỗ người vẽ
chỉnh tay trong Modeler rồi quay lại sửa `.yaml`. Nếu vòng lặp không bất biến thì mỗi
lần sinh lại xoá đúng phần vừa chỉnh, và công cụ chống lại chính quy trình nó phục vụ.
"""

import pathlib
import tempfile
import xml.etree.ElementTree as ET

import yaml

from bpmn_generator.brief import to_spec
from bpmn_generator.build import build
from bpmn_generator.convert import Converter, to_yaml
from bpmn_generator.rules import normalize

CASES = []


def eq(got, want, why):
    CASES.append((got == want, why, got, want))


SRC = """\
meta:
  id: rt-test
  source: rt.bpmn
  title: ""
  layout: di

pools:
  - id: pool1
    name: Test
    horizontal: true
    bounds: { x: 160, y: 60, w: 732, h: 250 }
    lanes:
      - id: lane1
        name: Lane
        bounds: { x: 190, y: 60, w: 702, h: 250 }

nodes:
  - id: event-start-x
    name: Start
    kind: event
    event: start
    definition: none
    throw: false
    bounds: { x: 230, y: 102, w: 36, h: 36 }
    label: { x: 193, y: 144, w: 110, h: 27 }
    pool: pool1
    lane: lane1
  - id: gateway-exclusive-x
    name: Cong
    kind: gateway
    gateway: exclusive
    marker: true
    bounds: { x: 466, y: 95, w: 50, h: 50 }
    label: { x: 469, y: 151, w: 44, h: 14 }
    pool: pool1
    lane: lane1
  - id: task-user-a
    name: A
    kind: task
    task: user
    markers: [loop]
    bounds: { x: 566, y: 80, w: 100, h: 80 }
    pool: pool1
    lane: lane1
  - id: task-user-b
    name: "B hai\ndòng"
    kind: task
    task: user
    markers: [mi-parallel]
    bounds: { x: 566, y: 190, w: 100, h: 80 }
    fill: "#ffcdd2"
    stroke: "#831311"
    pool: pool1
    lane: lane1

flows:
  - id: f1
    kind: sequence
    source: event-start-x
    target: gateway-exclusive-x
    waypoints: [[266, 120], [466, 120]]
  - id: f2
    kind: sequence
    source: gateway-exclusive-x
    target: task-user-a
    waypoints: [[516, 120], [566, 120]]
    default: true
  - id: f3
    kind: sequence
    source: gateway-exclusive-x
    target: task-user-b
    name: Nhánh phụ
    waypoints: [[491, 145], [491, 230], [566, 230]]
    label: { x: 497.5, y: 186, w: 51, h: 27 }
    stroke: "#831311"
"""


def cycle(text: str, name: str) -> dict:
    """Một vòng đúng như `main()` chạy: chuẩn hoá, dựng spec, ghi .bpmn, đọc ngược."""
    brief, _ = normalize(yaml.safe_load(text))
    with tempfile.TemporaryDirectory() as d:
        out = pathlib.Path(d) / (name + ".bpmn")
        build(to_spec(brief, name + ".yaml"), str(out))
        model = Converter(ET.parse(str(out)).getroot()).run(name + ".bpmn")
    return model


src_model = yaml.safe_load(SRC)
back = cycle(SRC, "rt")

# `source` ghi tên file vừa đọc, nên nó *phải* khác. Mọi thứ khác thì không được khác.
for d in (src_model, back):
    d["meta"].pop("source", None)
    d["meta"].pop("extent", None)

eq(back["pools"], src_model["pools"], "pool và lane giữ nguyên bounds")

# So bằng *văn bản YAML* chứ không bằng dict: `to_yaml` mới là thứ người dùng nhìn thấy,
# và nó in 266 chứ không phải 266.0, nên so dict sẽ vướng chuyện int/float vô nghĩa.
def flow_text(model):
    m = dict(model, pools=[], nodes=[])
    m["meta"] = dict(m["meta"], source="x")
    return to_yaml(m).split("flows:", 1)[-1]

eq(flow_text(back), flow_text(src_model), "mọi waypoint quay lại đúng như cũ")

by_src = {n["id"]: n for n in src_model["nodes"]}
by_back = {n["id"]: n for n in back["nodes"]}
eq(sorted(by_back), sorted(by_src), "không mất node nào")
for nid in sorted(by_src):
    eq(by_back.get(nid), by_src[nid], f"node {nid} quay lại nguyên vẹn")

# Chạy vòng thứ hai: đã bất biến ở vòng một thì vòng hai phải giống hệt vòng một.
back2 = cycle(yaml.safe_dump(back, allow_unicode=True, sort_keys=False), "rt2")
back2["meta"].pop("source", None)
back2["meta"].pop("extent", None)
eq(back2, back, "vòng thứ hai không đổi thêm gì nữa")


def main() -> int:
    bad = [c for c in CASES if not c[0]]
    for ok, why, got, want in CASES:
        if not ok:
            print(f"  ✗ {why}\n      nhận: {got!r}\n      cần : {want!r}")
    print(f"bpmn_generator vòng lặp: {len(CASES) - len(bad)}/{len(CASES)} đạt")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
