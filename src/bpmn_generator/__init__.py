"""bpmn-generator — dựng BPMN 2.0 từ mô tả YAML không toạ độ.

Dành cho người phân tích nghiệp vụ muốn *viết* sơ đồ quy trình thay vì kéo thả:
mô tả có những bước gì và nối với nhau ra sao, còn chỗ đặt từng phần tử thì để máy
tính. Kèm theo là bộ luật well-formed và quy ước đặt id — hai thứ mà trình vẽ đồ hoạ
không ép được.

    brief.yaml ──► .bpmn        gói này          (soạn thảo)
    .bpmn ──► .yaml ──► figure  typst-bpmn       (kết xuất)

Bốn lệnh:

    bpmn-brief <ten>-brief.yaml -o <ten>.bpmn   sinh sơ đồ, tự bố cục, tự sửa luật
    bpmn-lint  <file>                           kiểm luật cấu trúc + quy ước id
    bpmn-id    <file> --rename --also <...>      đổi id hàng loạt theo quy ước
    bpmn2yaml  <file>.bpmn -o <file>.yaml        chuyển sang YAML cho typst-bpmn đọc

Dùng như thư viện:

    from bpmn_generator import brief, rules, ids
    findings = rules.check(rules.load_bpmn("model.bpmn"))
"""

__version__ = "0.1.0"

from . import brief, build, convert, ids, lint, rules  # noqa: F401

__all__ = ["brief", "build", "convert", "ids", "lint", "rules", "__version__"]
