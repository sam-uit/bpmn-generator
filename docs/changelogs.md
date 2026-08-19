# Changelogs

Mỗi version được tag ghi một mục ở đây. Mục TODO nào hoàn thành thì chuyển từ [`TODO.md`](TODO.md) sang đây, ở version phát hành nó.

## v0.4.0

**`bpmn-rotate`, đổi phương của sơ đồ** `#feat` `#high`

Lệnh thứ năm: `bpmn-rotate quy-trinh.bpmn -o quy-trinh-doc.bpmn` đổi một sơ đồ ngang thành dọc, hoặc ngược lại. Không phải xoay hình. Xoay hình là việc của phía kết xuất, typst-bpmn quay cả bản vẽ để nó vừa trang giấy và chữ quay theo. Ở đây là đổi *cách đọc*: pool đang là dải ngang xếp chồng thì thành cột dọc đứng cạnh nhau, dòng chảy từ trái sang phải thành từ trên xuống dưới, còn chữ vẫn nằm ngang.

Phép biến đổi là **chuyển vị**, `(x, y) → (y, x)`, không phải phép quay. Quay 90 độ thì hoặc dòng chảy chạy ngược, hoặc lane đầu tiên rơi xuống cuối. Chuyển vị giữ được cả hai thứ tự: điểm bắt đầu vẫn ở góc trên trái, lane khai trước vẫn đứng trước. Về hình học nó là phản chiếu chứ không phải phép quay, nhưng với bản vẽ toàn hình chữ nhật thẳng trục thì không ai nhận ra.

Ba chỗ một phép nhân ma trận thuần tuý làm sai, và đó là phần lớn nội dung của bản này:

**Khung thì hoán kích thước, ký hiệu thì không.** Chuyển vị nguyên xi cả `width` lẫn `height` sẽ biến task 100×80 thành 80×100, cao hơn rộng, mà BPMN luôn vẽ task rộng hơn cao bất kể sơ đồ đi theo phương nào. Ngược lại một pool 3000×250 thì phải thành 250×3000, nếu không thì không còn là cột. Ranh giới đúng là vùng chứa (participant, lane, subprocess đã mở, group) thì hoán, ký hiệu (task, event, gateway, data object, ghi chú) thì giữ. Ký hiệu giữ kích thước thì phải chuyển vị **tâm** rồi đặt lại hộp quanh tâm, chứ không chuyển vị góc trên trái.

**Cạnh phải neo lại.** Ký hiệu không đổi kích thước nên waypoint đã chuyển vị không còn nằm trên viền của chúng. Hai đầu mỗi cạnh được neo lại vào viền theo hướng của đoạn kề, kẹp toạ độ còn lại vào trong cạnh đó nên đoạn thẳng đứng vẫn thẳng đứng sau khi neo. Các điểm gãy ở giữa thì giữ nguyên: định tuyến lại cho bố cục dọc là việc của `build.py` ở chế độ dọc, đã ghi vào [`TODO.md`](TODO.md).

**Nhãn chuyển vị theo ký hiệu.** Đã thử giữ nguyên độ lệch của nhãn so với tâm ký hiệu, để nhãn của event vẫn nằm dưới như trong bản ngang, rồi dựng thử: cạnh đi xuống cắt ngang qua chữ. Quy ước thật không phải "nhãn nằm dưới" mà là "nhãn nằm vuông góc với dòng chảy", nên nhãn chuyển vị theo và chuyển từ dưới sang bên cạnh.

Gốc bản vẽ được giữ nguyên: chuyển vị đổi chỗ hai toạ độ của góc trên trái, không dịch lại thì sơ đồ nhảy sang một chỗ khác trên mặt phẳng mà không vì lý do gì.

Kết quả là *bố cục ngang đã chuyển vị*, không phải bố cục dọc sinh ra từ đầu. Nó dùng được ngay với mọi file `.bpmn`, kể cả file có subprocess hay group mà `bpmn-brief` chưa dựng lại được, và đó là lý do nó tồn tại như một bộ lọc riêng thay vì một cờ của `bpmn-brief`.

Thêm `tests/test_rotate.py`, 19 khẳng định. Cái đáng giá nhất là "xoay hai lần thì mọi hộp về đúng chỗ cũ": chuyển vị là phép đối hợp, nên bất kỳ chỗ nào tính sai một chiều đều lộ ra khi đi ngược lại. Đã kiểm trên mô hình Thẩm Định Thầu B2B, 39 shape và 42 cạnh, lệch 0.

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
