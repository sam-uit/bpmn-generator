# bpmn-generator

Viết sơ đồ BPMN 2.0 bằng một file YAML mô tả, thay vì kéo thả trong trình vẽ.

```bash
uv run bpmn-brief quy-trinh-brief.yaml -o quy-trinh.bpmn
```

Bạn khai **có những bước gì và nối với nhau ra sao**; chỗ đặt từng phần tử, bề rộng cột, đường đi của từng cạnh và toàn bộ khối BPMNDI thì máy tính. Kết quả mở được bằng Camunda Modeler như một file BPMN bình thường.

## Vì sao

Trình vẽ đồ hoạ tốt cho một sơ đồ, dở cho hai mươi sơ đồ phải nhất quán với nhau. Ba thứ nó không ép được:

- **Luật cấu trúc.** Modeler cho phép hai luồng chảy thẳng vào một task, hoặc một cổng loại trừ không có nhánh mặc định. Vẽ ra vẫn đẹp, nhưng đọc thì sai: token "thoát" ra khỏi nhánh, hoặc gộp ngầm ở chỗ người đọc không nhìn thấy. `bpmn-lint` bắt những thứ đó, và `bpmn-brief` tự sửa những cái sửa được mà không cần đặt tên.
- **Quy ước đặt id.** `Task_1`, `Gateway_3` là mặc định của trình vẽ. Nhưng id là thứ   người khác phải gõ lại khi trích một lát cắt của sơ đồ vào báo cáo. `task-user-lap-ke-hoach` thì đọc là biết. `bpmn-id` sinh, kiểm, và đổi tên hàng loạt.
- **Diff đọc được.** Hai file `.bpmn` khác nhau vài toạ độ thì `git diff` vô dụng. Một file brief thì diff đúng chỗ bạn đã sửa.

## Năm lệnh

| Lệnh | Việc |
| --- | --- |
| `bpmn-brief <ten>-brief.yaml -o <ten>.bpmn` | Sinh sơ đồ: tự phân tầng, tự bố cục, tự sửa luật sửa được |
| `bpmn-lint <file>` | Kiểm luật cấu trúc + quy ước id. Nhận cả `.bpmn` lẫn `.yaml` |
| `bpmn-id <file> --rename --also <...>` | Đổi id hàng loạt theo quy ước, sửa luôn chỗ tham chiếu |
| `bpmn2yaml <file>.bpmn -o <file>.yaml` | Chuyển sang YAML rút gọn cho [typst-bpmn](https://github.com/sam-uit/typst-bpmn) đọc |
| `bpmn-rotate <file>.bpmn -o <file>-doc.bpmn` | Đổi phương sơ đồ: ngang thành dọc, hoặc ngược lại |

## Ngang hay dọc

`bpmn-rotate` đổi *cách đọc* sơ đồ, không phải xoay hình. Pool đang là dải ngang xếp chồng thì thành cột dọc đứng cạnh nhau, dòng chảy từ trái sang phải thành từ trên xuống dưới, chữ vẫn nằm ngang.

Phép biến đổi là chuyển vị `(x, y) → (y, x)`, không phải phép quay: quay 90 độ thì hoặc dòng chảy chạy ngược, hoặc lane đầu tiên rơi xuống cuối. Chỗ tinh tế là **khung thì hoán kích thước, ký hiệu thì không**: pool 3000×250 phải thành 250×3000, còn task thì vẫn 100×80, vì BPMN luôn vẽ task rộng hơn cao bất kể sơ đồ đi theo phương nào.

Kết quả là bố cục ngang đã chuyển vị, không phải bố cục dọc sinh ra từ đầu, nên các điểm gãy giữa cạnh giữ nguyên chỗ cũ. Đổi lại, nó chạy được với mọi file `.bpmn` kể cả file có subprocess hay group. Bố cục dọc thật thì nằm trong [`docs/TODO.md`](docs/TODO.md).

## Vòng làm việc

Brief chỉ dùng **một lần**. Sau vòng đầu, thứ bạn sửa là file `.yaml` do `bpmn2yaml` sinh ra, nó quay ngược lại được vào `bpmn-brief`:

```
<ten>-brief.yaml ──► [bpmn-brief] ──► <ten>.bpmn ──► Camunda Modeler
   (nguyên bản,                                             │
    một lần)                                          [bpmn2yaml]
                                                            │
                        ┌── chưa hài lòng: sửa <ten>.yaml ──┤
                        │                                   │
                        └──────► [bpmn-brief] ◄───────────┘
```

Một vòng giữ nguyên **mọi id** (node, sequence flow, message flow, data association), **mọi phần tử** kể cả kho dữ liệu và ghi chú, **nhánh mặc định** của mọi cổng, và **mọi toạ độ bạn đã chỉnh tay trong Modeler**: `bounds`, `waypoints`, vị trí nhãn, màu. Cái gì `.yaml` nói tường minh thì thắng thuật toán, cùng một luật với `row`/`col`. Toàn bộ: [`docs/workflow.md`](docs/workflow.md).

Dùng như thư viện:

```python
from bpmn_generator import brief, ids, rules

g = rules.load_bpmn("quy-trinh.bpmn")
for f in rules.check(g):
    print(f.level, f.code, f.node, f.message)
```

## Brief trông thế nào

Không toạ độ, không `row`/`col`, chỉ nói cái gì nối với cái gì:

```yaml
meta:
  id: definitions-xu-ly-bao-hanh
  title: Xử lý bảo hành

pools:
  - id: participant-trung-tam-dich-vu
    name: Trung Tâm Dịch Vụ
    process: process-xu-ly-bao-hanh
    lanes:
      - { id: lane-cskh, name: Tiếp Nhận }
      - { id: lane-ky-thuat, name: Kỹ Thuật Viên }

nodes:
  - { id: event-start-nhan-yeu-cau, name: Nhận yêu cầu bảo hành, kind: event, event: start, lane: lane-cskh }
  - { id: task-user-chan-doan-loi, name: Chẩn đoán lỗi thiết bị, kind: task, task: user, lane: lane-ky-thuat }
  - { id: gateway-exclusive-con-han, name: Còn hạn bảo hành?, kind: gateway, gateway: exclusive, lane: lane-cskh }
  - { id: task-user-goi-lai-khach, name: Gọi lại khách, kind: task, task: user, lane: lane-cskh, markers: [loop] }

flows:
  - { source: event-start-nhan-yeu-cau, target: gateway-exclusive-con-han }
  - { source: gateway-exclusive-con-han, target: task-user-chan-doan-loi, name: Còn hạn }
```

**Thứ tự khai báo có nghĩa.** Trong các nhánh rời một cổng, nhánh khai *trước* giữ dòng chảy chính khi bố cục, và là nhánh mặc định khi sửa luật. Happy path chỉ cần nói một lần.

Khai `row`/`col` cho node nào thì node đó giữ nguyên, **người viết luôn thắng máy**.

`markers:` là ký hiệu BPMN vẽ dọc cạnh dưới một activity: `loop`, `mi-parallel`, `mi-sequential`, `compensation`. Bảng đầy đủ ở [`docs/workflow.md`](docs/workflow.md).

## Hai chỗ máy dừng lại

Ranh giới: *máy chỉ sửa những gì không cần đặt tên; cái gì cần đặt tên thì dừng lại và báo.* Chèn cổng hợp lưu thì máy làm, cổng hợp lưu không có nhãn nên không phải hỏi ai. Nhưng message flow chạm vào cổng thì **không** tự sửa: sửa đúng phải chèn một sự kiện bắt thông điệp, mà sự kiện thì cần một cái tên, và chỉ người viết mới biết đặt gì.

Cùng tinh thần, `bpmn-id` không tự rút gọn một nhãn mười âm tiết thành ba: chọn ba âm tiết nào *chính là đặt tên*. Nó báo `ID-LONG` và chờ bạn khai `slug:`.

## Tài liệu

- [`docs/workflow.md`](docs/workflow.md), quy trình: brief một lần, `.yaml` nhiều lần, cái gì giữ được qua mỗi vòng và cái gì không
- [`docs/naming.md`](docs/naming.md), quy ước id: khuôn, bảng từ khoá và viết tắt đầy đủ, và quy trình đổi tên hàng loạt
- [`docs/rules.md`](docs/rules.md), luật well-formed: cái gì bắt, cái gì tự sửa, và vì sao
- [`CONTRIBUTING.md`](CONTRIBUTING.md), quy ước của repo: ngôn ngữ, đặt tên, changelog, phụ thuộc, và việc phải chạy trước khi commit

## Cài đặt và phát triển

```bash
uv sync                                          # môi trường phát triển
uv run bpmn-lint <file>                          # chạy thẳng từ repo
for t in tests/*.py; do PYTHONPATH=src python3 "$t"; done   # 88 khẳng định
```

Dùng từ một dự án khác, khai path dependency, để sửa thư viện là dự án thấy ngay:

```toml
[tool.uv.sources]
bpmn-generator = { path = "../bpmn-generator", editable = true }
```

Đường dẫn là tương đối *so với `pyproject.toml` của dự án kia*, không phải so với thư mục bạn đang đứng. Repo nằm sâu một tầng thì phải là `../../bpmn-generator`.

## Liên quan

[typst-bpmn](https://github.com/sam-uit/typst-bpmn) kết xuất những file này thành hình trong tài liệu Typst. Ranh giới giữa hai repo là **chiều đi của dữ liệu**:

```
brief.yaml ──► .bpmn         bpmn-generator   (soạn thảo)
.bpmn ──► .yaml ──► figure    typst-bpmn      (kết xuất)
```

`bpmn2yaml` nằm ở đây dù nó phục vụ phía kết xuất, vì nó là công cụ Python thao tác trên file BPMN, gom về một chỗ thì chỉ có một nơi để sửa khi lược đồ đổi.
