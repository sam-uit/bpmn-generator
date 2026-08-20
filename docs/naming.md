# Quy ước đặt id cho phần tử BPMN

id của một phần tử BPMN không phải chuyện nội bộ của file mô hình: nó là thứ **người viết phải gõ lại bằng tay**.

```typ
#bpmn-span(M, from: "gateway-exclusive-phan-loai-huong-xu-ly", to: "task-send-gui-hang-ve-hang",
           lane: "Kỹ Thuật Viên")
#bpmn-span(M, from: "task-user-kiem-ton-kho", to: "task-user-cap-phat-linh-kien")
```

```yaml
- ask: Tại sao thời gian chờ linh kiện lâu?
  node: gateway-exclusive-co-san-linh-kien      # whywhy neo vào đây
```

So với id cũ `Gateway_PhanLoai`, `Task_GuiHang`, `Gateway_CoLinhKien` thì dài hơn, nhưng đọc là biết ngay loại và phân loại con, không phải mở file mô hình ra tra.

Nên id phải tự nói được nó là cái gì. Ba mục tiêu, **đúng thứ tự ưu tiên**, khi hai mục tiêu xung khắc thì mục tiêu đứng trước thắng:

1. **Duy nhất**:  hai phần tử không bao giờ trùng id.
2. **Nhất quán**: cùng loại thì cùng khuôn, không ngoại lệ.
3. **Tường minh**: đọc id biết ngay loại, phân loại con, và tên.

Công cụ: `bpmn-id` (kiểm tra + đổi tên hàng loạt), và `bpmn-lint` gọi nó sẵn trên mọi brief.

## Khuôn

```
<type>-<subtype>-<subsubtype>-<name>[-<hash>]
```

| Ô | Bắt buộc | Nội dung |
| --- | --- | --- |
| `type` | có | Loại phần tử, tập đóng, xem bảng dưới |
| `subtype` | khi loại đó có | Phân loại con: `start`/`end`, `user`/`service`, `exclusive`/`parallel`… |
| `subsubtype` | khi có | Với sự kiện: bắt/ném bằng gì (`message`, `timer`, `signal`…) |
| `name` | có | Slug tiếng Việt không dấu, tối đa **5 âm tiết** |
| `hash` | chỉ khi trùng | 6 ký tự băm, gắn cho **cả hai** phần tử trùng nhau |

Ô nào không có thì **bỏ hẳn**, không để chỗ trống:

```
task-lap-ke-hoach            ✓  task thường
task-none-lap-ke-hoach       ✗  ô trống là chỗ để sai chính tả nảy sinh
```

Ví dụ đầy đủ:

```
event-start-message-nhu-cau-bao-hanh     sự kiện · bắt đầu · bằng message
event-intermediate-timer-het-han         sự kiện · giữa chừng · hẹn giờ
task-user-lap-ke-hoach                   task · người dùng thao tác
task-service-do-luong-kpi                task · hệ thống tự chạy
gateway-exclusive-du-ngan-sach           cổng · loại trừ
gateway-parallel-trien-khai-dong-thoi    cổng · song song
participant-cong-ty-cptm-hong-ha         pool
lane-phong-marketing                     lane
flow-gwy-tsk-du-ngan-sach                luồng · từ gateway · tới task · nhãn nhánh
message-tsk-prt-de-nghi-ho-tro           message flow · từ task · tới participant
definitions-l03-management-ke-hoach-khuyen-mai    cấp file: lấy tên file
```

Ba id **cấp file** (`definitions`, `collaboration`, `process`) lấy *tên file* làm ô tên, không lấy tiêu đề quy trình: chúng không bao giờ bị gõ lại trong hàm, mà tên file thì đã ngắn, đã duy nhất trong repo, và mở ra là khớp ngay.

Cùng lý do, id của **pool và lane** không bị chặn 5 âm tiết: hàm gọi lát cắt bằng *tên hiển thị* (`bpmn-figure(M, view: (lane: "Kho Vật Tư"))`), không bằng id. Chỉ những id thật sự bị gõ lại: task, event, gateway, mới phải ngắn.

## Bảng từ khoá

### Ô 1: `type` (tập đóng)

| Từ khoá | Viết tắt | Phần tử BPMN |
| --- | --- | --- |
| `collaboration` | (không có) | `<collaboration>`: khung chứa các pool |
| `definitions` | (không có) | `<definitions>`: gốc của file |
| `event` | `evt` | `startEvent`, `intermediateCatch/ThrowEvent`, `endEvent`, `boundaryEvent` |
| `flow` | `flw` `seq` | `sequenceFlow` |
| `gateway` | `gwy` | mọi loại cổng |
| `lane` | `lnn` | `<lane>` |
| `message` | `msg` | `messageFlow` |
| `participant` | `prt` `poo` | `<participant>` (pool) |
| `process` | `prc` | `<process>` |
| `subprocess` | `sub` | `subProcess` |
| `task` | `tsk` | mọi loại task |

### Ô 2: `subtype`

**Sự kiện** (`event`)

| Từ khoá | Viết tắt | Nghĩa |
| --- | --- | --- |
| `boundary` | `bdr` | Sự kiện biên, gắn vào một task |
| `end` | `end` | Kết thúc |
| `intermediate` | `int` | Giữa chừng (bắt hoặc ném) |
| `start` | `stt` | Bắt đầu |

**Task** (`task`, `subprocess`)

| Từ khoá | Viết tắt | Nghĩa |
| --- | --- | --- |
| `call` | `cal` | `callActivity`: gọi quy trình khác |
| `manual` | `man` | Việc tay, không có hệ thống hỗ trợ |
| `receive` | `rcv` | Chờ nhận message |
| `rule` | `rul` | `businessRuleTask`, quyết định theo luật/DMN |
| `script` | `scr` | Script chạy trong engine |
| `send` | `snd` | Gửi message |
| `service` | `svc` | Hệ thống tự thực hiện |
| `user` | `usr` | Người thao tác trên hệ thống |

Task thường (`task: none` trong brief) **không có ô 2**.

**Cổng** (`gateway`)

| Từ khoá | Viết tắt | Nghĩa |
| --- | --- | --- |
| `complex` | `cmx` | Điều kiện hợp lưu phức tạp (nên tránh) |
| `event` | `evt` | `eventBasedGateway`: rẽ theo sự kiện nào tới trước |
| `exclusive` | `exc` | Đúng một nhánh |
| `inclusive` | `inc` | Một hoặc nhiều nhánh |
| `parallel` | `par` | Mọi nhánh |

**Luồng** (`flow`, `message`) ô 2 và ô 3 là **loại của hai đầu**, viết tắt:

```
flow-gwy-tsk-...     từ gateway tới task
flow-evt-gwy-...     từ event tới gateway
message-tsk-prt-...  từ task tới participant
```

### Ô 3: `subsubtype` (chỉ sự kiện)

| Từ khoá | Viết tắt | Nghĩa |
| --- | --- | --- |
| `compensation` | `cmp` | Bù trừ |
| `conditional` | `cnd` | Điều kiện dữ liệu thành true |
| `error` | `err` | Lỗi nghiệp vụ |
| `escalation` | `esc` | Chuyển cấp |
| `link` | `lnk` | Nối hai chỗ trong cùng process |
| `message` | `msg` | Nhận/gửi message |
| `signal` | `sgn` | Tín hiệu phát rộng |
| `terminate` | `trm` | Kết thúc tức thì toàn process |
| `timer` | `tmr` | Hẹn giờ / chu kỳ |

### Viết tắt xuất hiện ở đâu

**Chỉ ở hai ô loại của id luồng.** Mọi chỗ khác viết đủ chữ, id được đọc nhiều hơn được gõ, mà `flow-gateway-task-du-ngan-sach` thì dài hơn `flow-gwy-tsk-du-ngan-sach` mà không nói thêm gì.

Bảng viết tắt vẫn được **nhận ở đầu vào**: khai `kind: evt` trong brief thì công cụ tự mở ra thành `event`. Tiện lúc gõ, không ảnh hưởng id sinh ra.

## Hai chỗ máy dừng lại

Ranh giới tự động hoá của repo: *máy chỉ sửa những gì không cần đặt tên; cái gì cần đặt tên thì dừng lại và báo.* Với id, có đúng hai chỗ như vậy.

**`ID-NONAME`: phần tử không có `name`.** Không có gì để đặt vào ô tên, mà máy không được phép nghĩ ra một cái tên. Hay gặp nhất là cổng hợp lưu không nhãn:

```
? Gateway_HopTrienKhai
```

Cách xử lý: đặt tên cho nó (`name: Hợp lưu triển khai`), hoặc nếu cố ý để trống nhãn trên hình thì khai `slug: hop-trien-khai`, nhãn và id là hai chuyện khác nhau.

**`ID-LONG`: nhãn dài hơn 5 âm tiết.** Chọn ba âm tiết nào đại diện cho một nhãn mười âm tiết *chính là đặt tên*. Cắt máy móc cho ra thứ tệ hơn id cũ:

```
"Lập bản thảo kế hoạch và dự trù kinh phí"
  -> task-user-lap-ban-thao-ke-hoach-va      ✗ cụt ở một hư từ
```

Cách xử lý: khai `slug:` trong brief, người viết luôn thắng máy (cùng nguyên tắc với `row`/`col`):

```yaml
- id: task-user-lap-ke-hoach
  name: Lập bản thảo kế hoạch và dự trù kinh phí
  slug: lap-ke-hoach
```

### Mô hình không có brief: `<mô hình>-slugs.yaml`

Hai trong ba mô hình của báo cáo dựng từ spec Python, và `.bpmn` thì không có chỗ khai `slug:`. Bảng rút gọn của chúng nằm cạnh mô hình:

```
content/processes/l03-core-xu-ly-bao-hanh.bpmn
content/processes/l03-core-xu-ly-bao-hanh-slugs.yaml    <- {id: ô tên đã chọn}
```

`bpmnid.py` và `bpmn-lint` **tự tìm** file này theo tên, không cần cờ. Lý do nó phải tồn tại lâu dài chứ không chỉ lúc migrate: nếu bảng chỉ sống trong một lần chạy lệnh thì lần lint sau lại báo `ID-LONG` cho đúng những id đã cố ý rút gọn, cảnh báo sai lặp lại là cách nhanh nhất để người ta thôi đọc cảnh báo.

Sinh khuôn ban đầu bằng `--propose-slugs`; máy chỉ chép nguyên nhãn xuống, rút gọn vẫn là việc của người:

```bash
bpmn-id content/processes/<ten>.bpmn --propose-slugs /tmp/slugs.yaml
```

### Cổng hợp lưu do máy chèn

`bpmnrules.normalize()` chèn cổng hợp lưu khi có nhiều luồng vào một task. Cổng đó không có nhãn (đúng chuẩn BPMN), nên id lấy tên **bước nó đứng trước**, `gateway-exclusive-hop-lap-ke-hoach`, vì đó đúng là cách người đọc gọi nó: "cổng hợp lưu trước bước Lập kế hoạch".

## Dùng công cụ

```bash
# 1. Xem lệch chỗ nào (không ghi gì)
bpmn-id content/processes/<ten>-brief.yaml

# 2. Khai `slug:` cho các nhãn dài, đặt tên cho phần tử chưa có tên, chạy lại

# 3. Đổi tên, nhớ liệt kê MỌI file có nhắc tới id
bpmn-id content/processes/<ten>-brief.yaml --rename \
    --also content/processes/<ten>.bpmn \
           content/processes/<ten>.yaml \
           content/chapter03.md \
           content/analysis/wh-ch03-bao-hanh.yaml

# 4. Dựng lại và biên dịch để chắc không sót tham chiếu
bpmn-brief <ten> && just report
```

`--also` là chỗ dễ sai nhất: quên một file thì file đó còn giữ id cũ, và Typst **không báo lỗi**, `bpmn-span` với id không tồn tại chỉ đơn giản là bỏ qua phần tử đó. Sau khi đổi tên, luôn mở PDF xem hình còn đủ phần tử không.

## Kiểm ở đâu

```bash
python3 tests/test_ids.py      # kiểm thử chính công cụ (24 khẳng định)
```

Mỗi khẳng định trong file đó tương ứng một quyết định thiết kế của tài liệu này, sửa quy ước thì phải sửa cả ở đó, và đó là chủ ý: quy ước không có lưới an toàn thì trôi.

`bpmn-lint` chạy trên `-brief.yaml` sẽ in cả luật cấu trúc lẫn id lệch quy ước.

Trên `.bpmn` thì **không** kiểm id: file `.bpmn` đi qua Camunda Modeler có thể chứa id do Modeler tự sinh cho phần tử mới thêm, mà đó là chuyện của bước 3 trong quy trình vận hành ở repo báo cáo, không phải lỗi mô hình. Nguồn sự thật của id là brief; sửa ở brief rồi sinh lại.

Xem thêm: [`rules.md`](rules.md) (luật cấu trúc), `README.md` (quy ước đặt tên file).
