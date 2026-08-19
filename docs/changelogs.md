# Changelogs

Mỗi version được tag ghi một mục ở đây. Mục TODO nào hoàn thành thì chuyển từ [`TODO.md`](TODO.md) sang đây, ở version phát hành nó.

## v0.3.0

**`markers` trong brief** `#feat` `#high`

`bpmn-brief` đọc được `markers:` trên activity và sinh ra phần tử BPMN tương ứng. Trước đó khoá này bị bỏ qua trong im lặng: `bpmn2yaml` ghi nó ra, nhưng đưa file `.yaml` đó ngược lại vào `bpmn-brief` thì marker biến mất, nên vòng lặp `yaml` → `bpmn` → `yaml` không bất biến với những mô hình có vòng lặp hoặc đa thể hiện.

```yaml
  - id: task-empty-with-loop
    name: Loop
    kind: task
    task: user
    lane: lane1
    markers: [loop]
```

Từ vựng lấy đúng theo `convert.markers_of`, vì hai đầu phải khớp nhau: `loop`, `mi-parallel`, `mi-sequential`, `compensation`, `adhoc`. Kèm tên viết tắt cho những chữ người viết gõ ra trước tiên: `parallel` và `sequential` quy về `mi-parallel` và `mi-sequential`.

Ba nhóm marker khác nhau ở chỗ chúng đi vào XML: `loop` và `mi-*` thành một phần tử con `loopCharacteristics` (đặt cuối thân activity theo XSD, sau `dataOutputAssociation`); `compensation` thành thuộc tính `isForCompensation` trên chính activity; `adhoc` thì phải đổi cả tên phần tử thành `adHocSubProcess`, nên hiện chưa hỗ trợ và báo rõ.

Phần lớn công sức nằm ở việc quyết định **cái gì phải gãy**. Một marker gõ sai mà bị lặng lẽ bỏ thì sơ đồ vẫn sinh ra, vẫn mở được, và thiếu đúng cái vòng lặp người viết muốn nói, nên bốn trường hợp dừng lại và báo lỗi: tên không có trong từ vựng; marker đặt trên cổng hoặc sự kiện (BPMN chỉ cho `tActivity` mang `loopCharacteristics`); hai kiểu lặp khai cùng lúc, vì XML sẽ có hai phần tử con mà Modeler chỉ đọc cái đầu; và `adhoc`. Riêng `markers: []` là hợp lệ ở mọi nơi, kể cả trên sự kiện, vì không có gì để từ chối.

Lỗi trên cổng chỉ thẳng chỗ đúng, `gateway: parallel|exclusive|inclusive|event`, vì đó gần như chắc chắn là điều người viết định nói khi gõ `markers: [parallel]` cho một cổng.

Thêm `tests/test_markers.py`, 17 khẳng định, quá nửa là ca lỗi.

## v0.2.0

**Vòng lặp `yaml` → `bpmn` → `yaml` chạy được và bất biến**

`bpmn-brief` nhận luôn file `.yaml` do `bpmn2yaml` sinh ra làm đầu vào, nên brief chỉ dùng một lần ở vòng đầu; từ vòng hai trở đi thứ được sửa là `.yaml`. Một vòng giữ nguyên mọi id (node, sequence flow, message flow, data association), mọi phần tử kể cả kho dữ liệu và ghi chú, và nhánh mặc định của mọi cổng rẽ điều kiện. Toạ độ cố ý không giữ, vì mỗi lần sinh là bố cục lại, và đó là lý do bước chỉnh tay trên Modeler nằm *trong* vòng lặp chứ không nằm sau nó.

Tài liệu vòng làm việc: [`workflow.md`](workflow.md).

## v0.1.0

**Package Python đầu tiên**

Sáu script rời trong `report/tools/` của repo báo cáo chuyển thành một package cài được, với bốn console script: `bpmn-brief`, `bpmn-lint`, `bpmn-id`, `bpmn2yaml`. Lý do tách ra: khi công cụ nằm chung với nội dung thì không phân biệt được commit nào sửa báo cáo, commit nào sửa công cụ, mà hai thứ đó có nhịp thay đổi và người đọc hoàn toàn khác nhau.

`convert.py` (`bpmn2yaml`) nằm ở repo này dù nó phục vụ phía kết xuất, vì nó là công cụ Python thao tác trên file BPMN. Ranh giới giữa hai repo là chiều đi của dữ liệu, không phải ai dùng.

Kèm `docs/naming.md`, `docs/rules.md`, và `tests/test_ids.py` với 24 khẳng định.
