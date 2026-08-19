#!/usr/bin/env python3
"""Kiểm thử `bpmn_generator.rotate`, chạy: python3 tests/test_rotate.py

Cùng lối viết với `test_ids.py`: khẳng định phẳng, không pytest.

Hai khẳng định quan trọng nhất ở cuối: khung hoán kích thước còn ký hiệu thì không, và
xoay hai lần thì mọi hộp trở về đúng chỗ cũ. Cái thứ hai là lưới an toàn rẻ nhất cho một
phép biến đổi hình học: chuyển vị là phép đối hợp, nên bất kỳ chỗ nào tính sai một chiều
đều lộ ra khi đi ngược lại.
"""

import io
import xml.etree.ElementTree as ET

from bpmn_generator import rotate as R

CASES = []


def eq(got, want, why):
    CASES.append((got == want, why, got, want))


def bounds(x, y, w, h):
    e = ET.Element("Bounds")
    e.set("x", str(x)); e.set("y", str(y))
    e.set("width", str(w)); e.set("height", str(h))
    return e


def rect(e):
    return tuple(R.num(e.get(k)) for k in ("x", "y", "width", "height"))


# --- chuyển vị một hộp ---
b = bounds(300, 100, 100, 80)
R.transpose_box(b, swap=False)
eq(rect(b), (90.0, 310.0, 100.0, 80.0),
   "ký hiệu: giữ 100x80, tâm (350,140) thành (140,350), nên góc là (90,310)")

b = bounds(160, 60, 3000, 250)
R.transpose_box(b, swap=True)
eq(rect(b), (60.0, 160.0, 250.0, 3000.0), "khung: hoán luôn w/h, góc chuyển vị thẳng")

b = bounds(200, 200, 36, 36)
R.transpose_box(b, swap=False)
eq(rect(b), (200.0, 200.0, 36.0, 36.0), "hình vuông: chuyển vị không đổi gì")

# --- neo vào viền ---
box = (100.0, 100.0, 100.0, 80.0)          # x, y, w, h; tâm (150, 140)
eq(R.dock(box, (150, 300)), (150.0, 180.0), "điểm kề ở dưới: neo cạnh dưới, giữ hoành độ")
eq(R.dock(box, (150, 10)), (150.0, 100.0), "điểm kề ở trên: neo cạnh trên")
eq(R.dock(box, (400, 140)), (200.0, 140.0), "điểm kề bên phải: neo cạnh phải")
eq(R.dock(box, (120, 400)), (120.0, 180.0),
   "hoành độ của điểm kề được giữ, nên đoạn vẫn thẳng đứng sau khi neo")
eq(R.dock(box, (101, 400)), (106.0, 180.0),
   "sát mép thì bị kẹp vào trong DOCK_MARGIN, mũi tên chạm viền chứ không chạm góc")


# --- một sơ đồ nhỏ, đủ để chạy hết đường ---
DOC = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
    xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
    xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
    xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="D_1">
  <bpmn:collaboration id="C_1">
    <bpmn:participant id="P_1" name="Pool" processRef="Proc_1" />
  </bpmn:collaboration>
  <bpmn:process id="Proc_1">
    <bpmn:laneSet id="LS_1">
      <bpmn:lane id="L_1" name="Lane">
        <bpmn:flowNodeRef>E_1</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>T_1</bpmn:flowNodeRef>
      </bpmn:lane>
    </bpmn:laneSet>
    <bpmn:startEvent id="E_1" name="Bắt đầu"><bpmn:outgoing>F_1</bpmn:outgoing></bpmn:startEvent>
    <bpmn:userTask id="T_1" name="Việc"><bpmn:incoming>F_1</bpmn:incoming></bpmn:userTask>
    <bpmn:sequenceFlow id="F_1" sourceRef="E_1" targetRef="T_1" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="Dia_1">
    <bpmndi:BPMNPlane id="Pl_1" bpmnElement="C_1">
      <bpmndi:BPMNShape id="S_P1" bpmnElement="P_1" isHorizontal="true">
        <dc:Bounds x="160" y="60" width="600" height="200" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="S_L1" bpmnElement="L_1" isHorizontal="true">
        <dc:Bounds x="190" y="60" width="570" height="200" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="S_E1" bpmnElement="E_1">
        <dc:Bounds x="242" y="142" width="36" height="36" />
        <bpmndi:BPMNLabel><dc:Bounds x="235" y="185" width="50" height="14" /></bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="S_T1" bpmnElement="T_1">
        <dc:Bounds x="340" y="120" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Ed_F1" bpmnElement="F_1">
        <di:waypoint x="278" y="160" />
        <di:waypoint x="340" y="160" />
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
"""


def parse(text):
    return ET.fromstring(text)


def shapes(root):
    out = {}
    for s in root.iter():
        if R.local(s) != "BPMNShape":
            continue
        b = R.bounds_of(s)
        if b is not None:
            out[s.get("bpmnElement")] = rect(b)
    return out


root = parse(DOC)
eq(R.orientation(root), "horizontal", "đọc phương từ isHorizontal của pool")

before = shapes(root)
R.rotate(root)
after = shapes(root)

eq(R.orientation(root), "vertical", "sau khi xoay thì pool thành dọc")
eq((after["P_1"][2], after["P_1"][3]), (200.0, 600.0), "pool hoán w/h thành 200x600")
eq((after["T_1"][2], after["T_1"][3]), (100.0, 80.0), "task vẫn 100x80, không bị dựng đứng")
eq((after["E_1"][2], after["E_1"][3]), (36.0, 36.0), "event vẫn 36x36")

# Tâm của task phải chuyển vị đúng, dù hộp không đổi kích thước. Đo **so với gốc bản
# vẽ**, vì sau khi chuyển vị cả hình được dịch lại để gốc nằm nguyên chỗ cũ.
ox = min(v[0] for v in before.values())
oy = min(v[1] for v in before.values())
cx, cy = before["T_1"][0] + 50 - ox, before["T_1"][1] + 40 - oy
eq((after["T_1"][0] + 50 - ox, after["T_1"][1] + 40 - oy), (cy, cx),
   "tâm task chuyển vị đúng, tính từ gốc bản vẽ")

# Góc trên trái của cả bản vẽ giữ nguyên, không nhảy đi đâu.
eq((min(v[0] for v in after.values()), min(v[1] for v in after.values())),
   (min(v[0] for v in before.values()), min(v[1] for v in before.values())),
   "gốc bản vẽ giữ nguyên sau khi xoay")

# Cạnh được neo lại vào viền: sau khi xoay, F_1 đi từ đáy event xuống đỉnh task.
wps = [(R.num(p.get("x")), R.num(p.get("y")))
       for e in root.iter() if R.local(e) == "BPMNEdge"
       for p in e if R.local(p) == "waypoint"]
ev = after["E_1"]
tk = after["T_1"]
eq(wps[0][1], ev[1] + ev[3], "đầu cạnh neo đúng vào cạnh dưới của event")
eq(wps[-1][1], tk[1], "cuối cạnh neo đúng vào cạnh trên của task")

# --- xoay hai lần là phép đồng nhất ---
root2 = parse(DOC)
R.rotate(root2)
R.rotate(root2)
eq(shapes(root2), shapes(parse(DOC)), "xoay hai lần: mọi hộp về đúng chỗ cũ")
eq(R.orientation(root2), "horizontal", "xoay hai lần: phương về như cũ")


def main() -> int:
    bad = [c for c in CASES if not c[0]]
    for ok, why, got, want in CASES:
        if not ok:
            print(f"  ✗ {why}\n      nhận: {got!r}\n      cần : {want!r}")
    print(f"bpmn_generator.rotate: {len(CASES) - len(bad)}/{len(CASES)} đạt")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
