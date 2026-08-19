# Luật well-formed cho mô hình BPMN

Một mô hình sai cấu trúc vẫn vẽ ra hình đẹp, nhưng **đọc sai**: token thoát ra khỏi nhánh, hoặc gộp ngầm ở chỗ người đọc không nhìn thấy. Sơ đồ trong báo cáo là để người khác đọc, nên phải đúng ngay cả khi không ai chạy nó.

Kiểm tra bất cứ lúc nào:

```bash
bpmn-lint                                      # mọi model trong content/processes/
bpmn-lint content/processes/<ten>-brief.yaml   # ngay từ bước 1, trước khi sinh
```

Cùng một bộ luật gác ở cả hai đầu quy trình: chạy được trên `-brief.yaml` (bước 1) lẫn `.bpmn` (sau bước 3). `--strict` thoát khác 0 khi có lỗi.

## Bảng luật

| Mã | Mức | Luật |
| --- | --- | --- |
| `E-MERGE` | lỗi | Không gộp ngầm: nhiều luồng đi vào phải đi qua một cổng |
| `E-DEFAULT` | lỗi | Cổng exclusive/inclusive rẽ nhiều nhánh phải có nhánh mặc định |
| `E-SPLIT-JOIN` | lỗi | Mở bằng cổng nào thì đóng bằng cổng đó |
| `E-MSG-GATEWAY` | lỗi | Message flow không được chạm vào cổng |
| `E-START-IN` / `E-END-OUT` | lỗi | Sự kiện bắt đầu không có luồng vào; kết thúc không có luồng ra |
| `E-DEAD-END` / `E-NO-IN` | lỗi | Node cụt hai đầu |
| `E-UNREACHABLE` | lỗi | Node không tới được từ sự kiện bắt đầu |
| `W-GW-NAME` | cảnh báo | Cổng rẽ nhánh nên có tên là một câu hỏi |
| `W-BRANCH-LABEL` | cảnh báo | Nhánh của cổng rẽ nhánh nên có nhãn là câu trả lời |

## 1. Không gộp ngầm `E-MERGE`

**Không cho phép nhiều hơn một luồng đi thẳng vào một task/event/gateway thường.** Mọi chỗ hợp lưu phải đi qua một cổng.

```
SAI                                ĐÚNG
  A ─┐                               A ─┐
     ├──> Task                          ├─> (X) ──> Task
  B ─┘                               B ─┘
```

BPMN cho phép viết kiểu sai, và nó có nghĩa: mỗi token tới là một lần kích hoạt task. Vấn đề là **người đọc không nhìn thấy điều đó**, hình vẽ trông y hệt một chỗ gộp. Bắt buộc vẽ cổng ra là bắt buộc nói rõ ý định: gộp loại trừ hay chờ đủ.

Áp dụng cho cả vòng rework: nhánh *"không đạt $\rightarrow$ làm lại"* quay về phải nhập vào một cổng trước bước bị làm lại, chứ không đâm thẳng vào task.

`bpmn-brief` **tự chèn** cổng này (xem phần Tự sửa bên dưới).

## 2. Nhánh mặc định `E-DEFAULT`

**Cổng exclusive và inclusive rẽ nhiều nhánh luôn phải có một nhánh mặc định**, và nhánh đó là **happy path**.

Thiếu nó thì khi mọi điều kiện đều sai, token kẹt lại ở cổng, quy trình chết đứng mà nhìn hình không thấy gì bất thường. Có nó thì luôn còn một đường ra.

Trong `.bpmn` là thuộc tính `default="flow_..."` trên cổng; Camunda Modeler vẽ một gạch chéo nhỏ ở gốc nhánh đó.

`bpmn-brief` **tự đặt** nhánh khai đầu tiên làm mặc định, cùng quy ước với bố cục (nhánh khai trước là dòng chảy chính), nên happy path chỉ cần nói một lần.

## 3. Mở bằng cổng nào, đóng bằng cổng đó `E-SPLIT-JOIN`

| Mở bằng | Phải đóng bằng | Nếu sai |
| --- | --- | --- |
| Parallel (`+`) | Parallel | Đóng bằng exclusive: mỗi nhánh chạy tiếp một lần $\rightarrow$ phần sau chạy hai lần |
| Exclusive (`×`) | Exclusive | Đóng bằng parallel: cổng chờ mãi nhánh không bao giờ tới $\rightarrow$ kẹt |
| Event-based | Exclusive | (chấp nhận: cổng event chỉ có một nhánh thắng) |
| Inclusive (`○`) | Inclusive | |

Bao đóng đối xứng là cách duy nhất để token không "thoát" đi lung tung.

Luật này **không** áp cho nhánh quay lui: một vòng rework không có điểm đóng, và không cần có. Bộ kiểm tra nhận ra cạnh quay lui bằng DFS rồi bỏ qua.

## 4. Message flow không chạm vào cổng `E-MSG-GATEWAY`

Cổng chỉ **định tuyến**; nó không nhận và không gửi được gì. Muốn nhận thông điệp từ pool khác thì phải có một **sự kiện bắt thông điệp** rồi mới tới cổng:

```
SAI                                     ĐÚNG
  [Pool NCC] ─ ─ ─> (×) Đồng ý?          [Pool NCC] ─ ─ ─> (✉) Nhận phản hồi ──> (×) Đồng ý?
```

Đây là lỗi **không được tự sửa**: sửa đúng phải chèn một sự kiện, mà sự kiện thì cần một cái tên, và chỉ người viết mới biết đặt tên gì. Bộ kiểm tra chỉ báo và gợi ý.

## 5. Đặt tên `W-GW-NAME`, `W-BRANCH-LABEL`

Cổng rẽ nhánh đặt tên là **câu hỏi** (`Còn hạn bảo hành?`), nhánh đặt tên là **câu trả lời** (`Còn hạn` / `Hết hạn`, không phải `Yes` / `No`). Cổng hợp lưu không cần tên — nó không hỏi gì.

## Tự sửa: cái gì máy làm, cái gì người làm

`bpmn-brief` chạy `tools/bpmnrules.normalize()` trước khi bố cục, và in ra từng thay đổi.

Ranh giới rất rõ:

| Vi phạm | Máy sửa? | Vì sao |
| --- | --- | --- |
| `E-MERGE` | ✓ chèn cổng hợp lưu | Cổng hợp lưu **không có tên**, không cần hỏi ai |
| `E-DEFAULT` | ✓ đặt nhánh đầu tiên | Thứ tự khai báo đã nói happy path là nhánh nào |
| `E-MSG-GATEWAY` | ✗ | Phải chèn một sự kiện, mà sự kiện cần một cái tên |
| `E-SPLIT-JOIN` | một phần | Loại cổng hợp lưu chèn vào được chọn khớp với cổng đã mở |
| Còn lại | ✗ | Là lỗi mô hình hoá, không phải lỗi cơ học |

Loại cổng hợp lưu được chọn bằng cách đi ngược từ mỗi luồng vào tới cổng rẽ gần nhất: mọi đường cùng chỉ về một cổng song song thì chèn cổng song song, còn lại chèn exclusive (đúng cho vòng rework và cho các nhánh loại trừ).

## Ở bước 3, refine trong Modeler

Camunda Modeler không ngăn được các lỗi này, nên sau khi chỉnh xong **chạy lại**:

```bash
bpmn-lint content/processes/<ten>.bpmn
```

Hai thao tác trong Modeler hay sinh lỗi mới:

- Nối thêm một mũi tên vào một task đã có mũi tên vào → `E-MERGE`.
- Nối message flow từ pool ngoài thẳng vào một cổng → `E-MSG-GATEWAY`.

Xem quy trình vận hành ở repo báo cáo cho toàn bộ quy trình bốn bước.
