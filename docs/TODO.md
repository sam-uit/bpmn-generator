# TODO

Mục đã xong nằm ở [`changelogs.md`](changelogs.md).

- [ ] #feat #med `bpmn-brief` chế độ dọc. `build.py` đang hard-code `isHorizontal="true"` và chỉ biết bố cục ngang, còn `.yaml` thì đã mang sẵn khoá `horizontal: true|false` do `bpmn2yaml` ghi ra. Dạy `build.py` một chế độ dọc thì đổi phương chỉ còn là sửa một dòng trong `.yaml` rồi sinh lại, và khi đó là bố cục dọc thật: cạnh được định tuyến lại, nhãn đặt lại, lane có hình học đúng. Đây là nửa còn lại của `bpmn-rotate` (v0.4.0), vốn chỉ chuyển vị toạ độ của một bố cục ngang có sẵn.

- [ ] #bug #med `build.py` `message_route` giả định một đầu của message flow là pool black box: `pool_id = m["src"] if m["src"] in pb else m["dst"]`. Message flow nối *hai node ở hai pool thật* thì tra `pool_bounds` bằng id node và gãy với `KeyError`. Dựng lại: `tests/fixtures/vertical-pools.bpmn` bên typst-bpmn, qua `bpmn2yaml` rồi `bpmn-brief`.
