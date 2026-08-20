#!/usr/bin/env python3
"""Kiểm tra mô hình BPMN theo luật well-formed.

    python3 tools/lint.py content/processes/*.bpmn
    python3 tools/lint.py content/processes/<ten>-brief.yaml --strict

Nạp được cả `.bpmn` (sau khi refine trong Modeler) lẫn `-brief.yaml` (trước khi sinh),
nhờ đó cùng một bộ luật gác ở cả hai đầu của quy trình.

Luật nằm trong `tools/rules.py`. `--strict` thoát khác 0 khi có lỗi, dùng cho CI.
"""

from __future__ import annotations

import argparse
import pathlib
import sys


import re  # noqa: E402

from . import ids as idcheck  # `ids` là tên biến cục bộ ngay dưới, đừng để trùng
from .rules import check, load_bpmn, load_brief

ICON = {"error": "✗", "warn": "!", "id": "~"}


def lint(path: pathlib.Path) -> tuple[int, int]:
    brief = None
    if path.suffix in (".yaml", ".yml"):
        import yaml

        brief = yaml.safe_load(path.read_text(encoding="utf-8"))
        g = load_brief(brief)
    else:
        g = load_bpmn(str(path))

    findings = check(g)
    errors = [f for f in findings if f.level == "error"]
    warns = [f for f in findings if f.level == "warn"]

    # Quy ước đặt id chỉ kiểm được trên brief: file `.bpmn` sau khi qua Modeler có thể
    # chứa id do Modeler tự sinh cho phần tử mới, mà đó là chuyện của bước 3, không phải
    # lỗi mô hình. Nguồn sự thật của id là brief.
    id_findings = (idcheck.check(brief, re.sub(r"-brief$", "", path.stem),
                        idcheck.sidecar_slugs(path)) if brief is not None else [])

    head = f"{path}: {len(g.nodes)} node, {len(g.flows)} luồng"
    if not findings and not id_findings:
        print(f"{head}: sạch")
        return 0, 0
    print(f"{head}: {len(errors)} lỗi, {len(warns)} cảnh báo, {len(id_findings)} id lệch")
    for f in errors + warns:
        print(f"  {ICON[f.level]} [{f.code}] {f.node}: {f.message}")
        if f.hint:
            print(f"      {f.hint}")
    for code, nid, msg in id_findings:
        print(f"  {ICON['id']} [{code}] {nid}: {msg}")
    if id_findings:
        print("      sửa hàng loạt: python3 tools/ids.py <brief> --rename --also <file...>")
    return len(errors), len(warns)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help=".bpmn hoặc -brief.yaml")
    ap.add_argument("--strict", action="store_true", help="thoát khác 0 khi có lỗi")
    args = ap.parse_args()

    total_e = total_w = 0
    for f in args.files:
        e, w = lint(pathlib.Path(f))
        total_e += e
        total_w += w
    if args.strict and total_e:
        print(f"\n{total_e} lỗi, không đạt.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
