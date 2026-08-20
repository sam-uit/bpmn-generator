#!/usr/bin/env python3
"""Kiểm thử `bpmn_generator.ids`: chạy: python3 -m pytest tests/  (hoặc: python3 tests/test_ids.py)

Không dùng pytest: repo này không có hạ tầng test Python, mà quy ước đặt id thì cần
một lưới an toàn ngay bây giờ. Mỗi khẳng định dưới đây tương ứng một quyết định thiết
kế trong `docs/naming.md`: sửa quy ước thì phải sửa cả ở đây, và đó là chủ ý.
"""

from bpmn_generator import ids as B

CASES = []


def eq(got, want, why):
    CASES.append((got == want, why, got, want))


# --- slug: bỏ dấu tiếng Việt, `đ` phải xử lý riêng ---
eq(B.slugify("Đủ ngân sách?"), "du-ngan-sach", "bỏ dấu + `đ` -> `d`")
eq(B.slugify("Tiếp Nhận & CSKH"), "tiep-nhan-cskh", "ký tự không phải chữ/số -> gạch nối")

# --- viết tắt: hai chiều ---
eq(B.expand("gwy"), "gateway", "mở viết tắt")
eq(B.expand("gateway"), "gateway", "chữ đủ giữ nguyên")
eq(B.shorten("gateway"), "gwy", "rút gọn cho id luồng")

# --- khuôn id theo từng loại ---
eq(B.node_id({"kind": "task", "task": "user", "name": "Lập kế hoạch"}),
   "task-user-lap-ke-hoach", "task có phân loại con")
eq(B.node_id({"kind": "task", "task": "none", "name": "Soạn hàng"}),
   "task-soan-hang", "`none` = task thường -> KHÔNG có ô trống")
eq(B.node_id({"kind": "gateway", "gateway": "exclusive", "name": "Đủ ngân sách?"}),
   "gateway-exclusive-du-ngan-sach", "cổng")
eq(B.node_id({"kind": "event", "event": "start", "definition": "message",
              "name": "Nhu cầu bảo hành"}),
   "event-start-message-nhu-cau-bao-hanh", "sự kiện đủ ba ô")
eq(B.node_id({"kind": "event", "event": "end", "name": "Hoàn tất"}),
   "event-end-hoan-tat", "sự kiện không có ô 3")

# --- hai chỗ máy dừng lại ---
eq(B.node_id({"kind": "gateway", "gateway": "parallel", "name": ""}), "",
   "không tên -> máy không tự đặt (ID-NONAME)")
eq(B.node_id({"kind": "task", "task": "user",
              "name": "Lập bản thảo kế hoạch và dự trù kinh phí"}), "",
   "nhãn quá dài -> chờ `slug:` (ID-LONG)")
eq(B.node_id({"kind": "task", "task": "user",
              "name": "Lập bản thảo kế hoạch và dự trù kinh phí",
              "slug": "lap-ke-hoach"}), "task-user-lap-ke-hoach",
   "`slug:` khai tay thì thắng máy")

# --- id luồng giữ viết tắt, và KHÔNG bị mở ngược ra chữ đủ ---
eq(B.flow_id("flow", {"kind": "gateway"}, {"kind": "task"}, "Đủ ngân sách"),
   "flow-gwy-tsk-du-ngan-sach", "hai ô loại của luồng dùng viết tắt")
eq(B.flow_id("message", {"kind": "task"}, None, "Báo giá"),
   "message-tsk-prt-bao-gia", "đầu kia của message flow là một pool")
eq(B.flow_id("flow", {"kind": "task"}, {"kind": "gateway", "name": "Đạt yêu cầu?"}, "",
             fallback="Đạt yêu cầu?"),
   "flow-tsk-gwy-dat-yeu-cau", "luồng không nhãn -> lấy tên node đích")

# --- phân tích ngược ---
p = B.parse("event-start-message-nhu-cau-bao-hanh")
eq((p or {}).get("subsub"), "message", "tách được ô 3")
eq((p or {}).get("name"), "nhu-cau-bao-hanh", "tách được ô tên")
eq(B.parse("Task_LapKeHoach"), None, "id kiểu cũ -> không khớp khuôn (ID-SHAPE)")

# --- thay thế trong văn bản: id ngắn không được ăn mất id dài ---
eq(B.apply_to_text("Task_Sua và Task_SuaChua",
                   {"Task_Sua": "task-sua", "Task_SuaChua": "task-sua-chua"})[0],
   "task-sua và task-sua-chua", "thay id dài trước, chặn hai biên")
eq(B.apply_to_text('node: "Task_Sua"', {"Task_Sua": "task-sua"})[1], 1,
   "đếm đúng số chỗ đã thay")

# --- trùng id thì CẢ HAI được gắn hậu tố ---
m = B.rename_map({"nodes": [
    {"id": "A", "kind": "task", "name": "Kiểm tra"},
    {"id": "B", "kind": "task", "name": "Kiểm tra"},
]})
eq(m["A"] != m["B"], True, "hai phần tử trùng tên vẫn ra hai id khác nhau")
eq(m["A"].startswith("task-kiem-tra-") and m["B"].startswith("task-kiem-tra-"), True,
   "hậu tố gắn cho cả hai, không chỉ cái sau")
eq(m, B.rename_map({"nodes": [
    {"id": "A", "kind": "task", "name": "Kiểm tra"},
    {"id": "B", "kind": "task", "name": "Kiểm tra"},
]}), "băm tất định: chạy lại cho cùng kết quả, không sinh diff giả")


def main() -> int:
    bad = [c for c in CASES if not c[0]]
    for ok, why, got, want in CASES:
        if not ok:
            print(f"  ✗ {why}\n      nhận: {got!r}\n      cần : {want!r}")
    print(f"bpmn_generator.ids: {len(CASES) - len(bad)}/{len(CASES)} đạt")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
