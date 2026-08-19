#!/usr/bin/env python3
"""Kiểm thử behaviour marker, chạy: python3 tests/test_markers.py

Cùng lối viết với `test_ids.py`: khẳng định phẳng, không pytest. Mỗi khẳng định ứng
với một quyết định trong `docs/workflow.md`, phần marker.

Điểm quan trọng nhất ở đây không phải "loop có sinh ra XML không" mà là **cái gì phải
gãy**: một marker gõ sai bị bỏ qua thì sơ đồ vẫn sinh ra, vẫn mở được, và thiếu đúng
cái vòng lặp người viết muốn nói. Nên quá nửa số ca dưới đây là ca lỗi.
"""

from bpmn_generator import brief as B
from bpmn_generator.build import MARKER_ELEMENTS

CASES = []


def eq(got, want, why):
    CASES.append((got == want, why, got, want))


def raises(fn, needle, why):
    try:
        fn()
    except SystemExit as e:
        CASES.append((needle in str(e), why, str(e), f"... {needle} ..."))
    else:
        CASES.append((False, why, "không lỗi", f"SystemExit chứa {needle!r}"))


def task(**kw):
    return dict(id="task-user-x", kind="task", task="user", **kw)


# --- từ vựng chuẩn ---
eq(B.markers_of(task(markers=["loop"])), ["loop"], "loop giữ nguyên")
eq(B.markers_of(task(markers=["mi-parallel"])), ["mi-parallel"], "mi-parallel giữ nguyên")
eq(B.markers_of(task(markers=["compensation"])), ["compensation"], "compensation giữ nguyên")

# --- tên viết tắt ---
eq(B.markers_of(task(markers=["parallel"])), ["mi-parallel"], "`parallel` -> mi-parallel")
eq(B.markers_of(task(markers=["sequential"])), ["mi-sequential"], "`sequential` -> mi-sequential")
eq(B.markers_of(task(markers=["LOOP"])), ["loop"], "không phân biệt hoa thường")
eq(B.markers_of(task(markers="loop")), ["loop"], "một chuỗi trần cũng nhận")

# --- rỗng là không làm gì, kể cả trên phần tử không mang được marker ---
eq(B.markers_of(task(markers=[])), [], "danh sách rỗng")
eq(B.markers_of(dict(id="e", kind="event", event="start", markers=[])), [],
   "`markers: []` trên sự kiện vẫn hợp lệ, không có gì để từ chối")

# --- trùng lặp ---
eq(B.markers_of(task(markers=["loop", "loop"])), ["loop"], "khai hai lần chỉ tính một")

# --- những thứ phải gãy ---
raises(lambda: B.markers_of(dict(id="gateway-parallel-x", kind="gateway", markers=["parallel"])),
       "gateway: parallel", "marker trên cổng: báo lỗi và chỉ đúng chỗ khai loại cổng")
raises(lambda: B.markers_of(dict(id="event-start-x", kind="event", markers=["loop"])),
       "sự kiện không mang marker", "marker trên sự kiện")
raises(lambda: B.markers_of(task(markers=["lopo"])), "marker không có",
       "tên gõ sai không được lặng lẽ bỏ qua")
raises(lambda: B.markers_of(task(markers=["loop", "mi-parallel"])), "một `loopCharacteristics`",
       "hai kiểu lặp cùng lúc: XML sẽ có hai phần tử con và Modeler chỉ đọc cái đầu")
raises(lambda: B.markers_of(task(markers=["adhoc"])), "adHocSubProcess",
       "adhoc cần một loại phần tử khác, chưa hỗ trợ")

# --- bảng XML khớp với từ vựng ---
eq(sorted(MARKER_ELEMENTS), ["loop", "mi-parallel", "mi-sequential"],
   "chỉ ba marker sinh ra `loopCharacteristics`; compensation là thuộc tính")
eq([m for m in B.MARKER_CANON if m not in MARKER_ELEMENTS], ["compensation", "adhoc"],
   "phần còn lại của từ vựng không đi qua bảng XML")


def main() -> int:
    bad = [c for c in CASES if not c[0]]
    for ok, why, got, want in CASES:
        if not ok:
            print(f"  ✗ {why}\n      nhận: {got!r}\n      cần : {want!r}")
    print(f"bpmn_generator.brief markers: {len(CASES) - len(bad)}/{len(CASES)} đạt")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
