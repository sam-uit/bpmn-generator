#!/usr/bin/env python3
"""Quy ước đặt id cho phần tử BPMN, sinh, kiểm tra, và đổi tên hàng loạt.

    python3 tools/ids.py <file>-brief.yaml            # kiểm tra, in bảng đối chiếu
    python3 tools/ids.py <file>-brief.yaml --rename    # ghi id mới vào chính file đó
    python3 tools/ids.py <file>-brief.yaml --rename \\
        --also content/chapter03.md content/analysis/*.yaml   # sửa luôn chỗ tham chiếu

Vì sao cần: id là thứ **người khác** phải gõ lại, trong `bpmn-span(from:, to:)`, trong khoá
`node:` của `whywhy`, trong `bpmn-span(from:, to:)`. Một id nói được nó là cái gì thì
người viết chương không phải mở file mô hình ra tra. Ba mục tiêu, đúng thứ tự ưu tiên:

    1. duy nhất  : hai phần tử không bao giờ trùng id
    2. nhất quán : cùng một loại thì cùng một khuôn, không có ngoại lệ
    3. tường minh: đọc id biết ngay loại, phân loại con, và tên

Khuôn (xem `docs/naming.md`):

    <type>-<subtype>-<subsubtype>-<name>[-<hash>]

    event-start-message-nhu-cau-bao-hanh      loại · start · bắt bằng message · tên
    task-user-lap-ke-hoach                    loại · task người dùng · tên
    gateway-exclusive-du-ngan-sach            loại · cổng loại trừ · tên
    flow-gwy-tsk-du-ngan-sach                 luồng · từ gateway · tới task · nhãn

Ô nào không có thì **bỏ hẳn**, không để chỗ trống: `task-lap-ke-hoach` (task thường)
chứ không phải `task-none-lap-ke-hoach`. Ô trống là chỗ để sai chính tả nảy sinh.

Viết tắt chỉ xuất hiện ở **đúng một chỗ**: hai ô loại của id luồng. Lý do là độ dài,
`flow-gateway-task-...` dài mà không nói thêm gì. Mọi chỗ khác viết đủ chữ, vì id được
đọc nhiều hơn được gõ. Bảng viết tắt vẫn nhận ở đầu vào (`evt`, `gwy`, `tsk`…) và được
mở ra thành chữ đủ khi sinh id.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import sys
import unicodedata

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("cần PyYAML: pip install pyyaml --break-system-packages")


# --- từ vựng ---------------------------------------------------------------------------
# Viết tắt -> chữ đủ. Sắp theo bảng chữ cái để tra bằng mắt được; xem bảng đầy đủ kèm
# nghĩa trong `docs/naming.md`.
SHORTHANDS: dict[str, str] = {
    "bdr": "boundary",
    "cal": "call",
    "cmp": "compensation",
    "cmx": "complex",
    "cnd": "conditional",
    "end": "end",
    "err": "error",
    "esc": "escalation",
    "evt": "event",
    "exc": "exclusive",
    "flw": "flow",
    "gwy": "gateway",
    "inc": "inclusive",
    "int": "intermediate",
    "lnk": "link",
    "lnn": "lane",
    "man": "manual",
    "msg": "message",
    "par": "parallel",
    "poo": "pool",
    "prc": "process",
    "prt": "participant",
    "rcv": "receive",
    "rul": "rule",
    "scr": "script",
    "seq": "sequence",
    "sgn": "signal",
    "snd": "send",
    "stt": "start",
    "sub": "subprocess",
    "svc": "service",
    "tmr": "timer",
    "trm": "terminate",
    "tsk": "task",
    "usr": "user",
}
FULL_TO_SHORT: dict[str, str] = {v: k for k, v in SHORTHANDS.items()}

# Ô 1: loại phần tử. Đây là tập đóng: thêm loại mới thì thêm ở đây, không đặt tuỳ ý.
TYPES = {
    "event", "task", "subprocess", "gateway", "flow", "message",
    "participant", "lane", "process", "definitions", "collaboration",
}

# Ô 2 theo từng loại. `None` = loại đó không dùng ô 2.
SUBTYPES: dict[str, set[str] | None] = {
    "event": {"start", "intermediate", "end", "boundary"},
    "task": {"user", "service", "send", "receive", "manual", "script", "rule", "call"},
    "subprocess": {"embedded", "call", "event", "transaction"},
    "gateway": {"exclusive", "parallel", "inclusive", "event", "complex"},
    "flow": set(FULL_TO_SHORT) | set(SHORTHANDS),   # ô loại của hai đầu
    "message": set(FULL_TO_SHORT) | set(SHORTHANDS),
    "participant": None,
    "lane": None,
    "process": None,
    "definitions": None,
    "collaboration": None,
}

# Ô 3: chỉ sự kiện và cổng dựa-trên-sự-kiện mới có: bắt/ném bằng cái gì.
EVENT_DEFINITIONS = {
    "message", "timer", "signal", "error", "escalation",
    "conditional", "compensation", "link", "terminate",
}


def expand(token: str) -> str:
    """`gwy` -> `gateway`. Không phải viết tắt thì trả nguyên văn."""
    return SHORTHANDS.get(token.strip().lower(), token.strip().lower())


def shorten(token: str) -> str:
    """`gateway` -> `gwy`. Dùng cho hai ô loại của id luồng."""
    t = token.strip().lower()
    return FULL_TO_SHORT.get(t, t[:3])


# --- slug ------------------------------------------------------------------------------
_NONWORD = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """"Đủ ngân sách?" -> "du-ngan-sach". Bỏ dấu tiếng Việt, giữ trật tự chữ.

    `đ` phải xử lý riêng: nó không phải `d` + dấu tổ hợp nên NFD không tách ra được.
    """
    t = (text or "").strip().lower().replace("đ", "d")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = _NONWORD.sub("-", t).strip("-")
    return t


# Ô tên dài bao nhiêu là vừa? id được **gõ lại bằng tay**, trong `bpmn-span(..)`, trong
# khoá `node:` của whywhy, trong `bpmn-span(from:, to:)`. Nhãn đầy đủ của một task
# ("Lập bản thảo kế hoạch và dự trù kinh phí") quá dài để làm id.
#
# Nhưng máy **không cắt bừa**. Chọn ba âm tiết nào đại diện cho một nhãn mười âm tiết
# chính là *đặt tên*, mà đặt tên thì vượt ranh giới tự động hoá của repo: máy chỉ làm
# những gì không cần đặt tên. Cắt máy móc cho ra `task-user-lap-ban-thao-ke-hoach-va`
#: cụt ở một hư từ, tệ hơn cả id cũ.
#
# Nên: nhãn quá dài thì báo ID-LONG và **dừng**, chờ người viết khai `slug:` trong brief:
#
#     - id: Task_LapKeHoach
#       name: Lập bản thảo kế hoạch và dự trù kinh phí
#       slug: lap-ke-hoach          # -> task-user-lap-ke-hoach
MAX_WORDS = 5


def short_slug(text: str, max_words: int = MAX_WORDS) -> tuple[str, bool]:
    """(slug, có quá dài không). Quá dài thì trả nguyên vẹn, người gọi quyết định."""
    words = [w for w in slugify(text).split("-") if w]
    return "-".join(words), len(words) > max_words


def _hash6(seed: str) -> str:
    """Hậu tố phân biệt khi trùng id. Băm tất định, cùng đầu vào cho cùng kết quả,
    nếu không thì mỗi lần chạy lại sinh ra một diff giả."""
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:6]


# --- sinh id ---------------------------------------------------------------------------
def make_id(type_: str, name: str, subtype: str = "", subsub: str = "",
            suffix: str = "", slug: str = "") -> str:
    """`slug` khai tay thì thắng: cùng nguyên tắc với `row`/`col` trong brief."""
    parts = [expand(type_)]
    if subtype:
        parts.append(expand(subtype))
    if subsub:
        parts.append(expand(subsub))
    s = slugify(slug) if slug else short_slug(name)[0]
    if s:
        parts.append(s)
    if suffix:
        parts.append(suffix)
    return "-".join(parts)


def node_id(node: dict) -> str:
    """id chuẩn cho một node của brief. Trả chuỗi rỗng khi node **không có tên**.

    Không có tên thì không có gì để đặt vào ô tên, và máy không được phép tự nghĩ ra
    một cái, đúng ranh giới tự động hoá của repo: máy chỉ sửa những gì không cần đặt
    tên, cái gì cần đặt tên thì dừng lại và báo. `bpmnrules` đã có W-GW-NAME cho đúng
    trường hợp hay gặp nhất (cổng không tên).
    """
    kind = expand(node.get("kind", "task"))
    name = node.get("name", "")
    slug = node.get("slug", "")
    if not slugify(name) and not slugify(slug):
        return ""
    if not slug and short_slug(name)[1]:
        return ""       # nhãn quá dài -> chờ `slug:`, xem MAX_WORDS
    if kind == "event":
        sub = expand(node.get("event", "start"))
        # `definition` là ô 3: bắt/ném bằng message, timer, signal...
        d = expand(node.get("definition", "") or "")
        return make_id("event", name, sub, d if d in EVENT_DEFINITIONS else "", slug=slug)
    if kind == "gateway":
        return make_id("gateway", name, expand(node.get("gateway", "exclusive")), slug=slug)
    if kind in ("task", "subprocess"):
        sub = expand(node.get("task", "") or "")
        # `none` trong lược đồ nghĩa là task thường -> không có ô 2
        return make_id(kind, name, "" if sub in ("", "none") else sub, slug=slug)
    return make_id(kind, name, slug=slug)


def type_of(node: dict | None) -> str:
    if node is None:
        return "participant"       # đầu còn lại của message flow là một pool
    return expand(node.get("kind", "task"))


def flow_id(kind: str, src: dict | None, tgt: dict | None, name: str,
            fallback: str = "") -> str:
    """`flow-gwy-tsk-du-ngan-sach`.

    Nhãn luồng là thứ đáng đưa vào id nhất (nó nói *điều kiện*), nhưng luồng thường
    không có nhãn: khi đó lấy tên node đích, vì "chảy tới đâu" là thông tin còn lại.
    """
    label = name or fallback
    # Không đi qua `make_id`: nó mở viết tắt ra chữ đủ, mà id luồng là đúng chỗ duy
    # nhất quy ước *muốn* giữ viết tắt.
    parts = [expand(kind), shorten(type_of(src)), shorten(type_of(tgt))]
    slug = short_slug(label)[0]
    if slug:
        parts.append(slug)
    return "-".join(parts)


# --- phân tích ngược -------------------------------------------------------------------
def parse(eid: str) -> dict | None:
    """Tách một id ra các ô. Trả `None` nếu không theo khuôn."""
    parts = eid.split("-")
    if not parts or parts[0] not in TYPES:
        return None
    out = {"type": parts[0], "subtype": "", "subsub": "", "name": "", "raw": eid}
    rest = parts[1:]
    allowed = SUBTYPES.get(parts[0])
    if allowed and rest and rest[0] in allowed:
        out["subtype"] = rest.pop(0)
        if parts[0] in ("flow", "message") and rest and rest[0] in allowed:
            out["subsub"] = rest.pop(0)
        elif parts[0] == "event" and rest and rest[0] in EVENT_DEFINITIONS:
            out["subsub"] = rest.pop(0)
    out["name"] = "-".join(rest)
    return out


# --- kiểm tra và đổi tên ---------------------------------------------------------------
def with_slugs(brief: dict, slugs: dict | None) -> dict:
    """Trộn bảng {id: slug} khai ngoài vào brief, dùng cho mô hình chỉ có `.bpmn`
    (dựng từ spec Python), vì XML không có chỗ khai `slug:` như brief.

    Trộn **một lần ở đầu vào** rồi mọi hàm phía sau chỉ thấy một dạng dữ liệu: nếu để
    mỗi hàm tự trộn thì `no_name` và `too_long` sẽ nhìn thấy hai thế giới khác nhau,
    đúng lỗi đã mắc lần đầu.
    """
    if not slugs:
        return brief
    out = dict(brief)
    out["nodes"] = [dict(n, **({"slug": slugs[n["id"]]} if slugs.get(n["id"]) else {}))
                    for n in brief.get("nodes", [])]
    return out


def no_name(brief: dict) -> list[str]:
    """id của những phần tử không có tên, máy dừng lại ở đây, không tự đặt."""
    # Kiểm thẳng `name`, không đi qua `node_id`: `node_id` cũng trả rỗng cho nhãn quá
    # dài, mà đó là ID-LONG chứ không phải ID-NONAME, hai chuyện, hai cách xử lý.
    return [n["id"] for n in brief.get("nodes", [])
            if not slugify(n.get("name", "")) and not slugify(n.get("slug", ""))]


def too_long(brief: dict, slugs: dict | None = None) -> list[tuple[str, str]]:
    """[(id, slug đề nghị rút gọn từ)], nhãn dài quá cap và chưa khai `slug:`."""
    out = []
    for n in brief.get("nodes", []):
        if n.get("slug") or (slugs or {}).get(n["id"]):
            continue
        full, long_ = short_slug(n.get("name", ""))
        if long_:
            out.append((n["id"], full))
    return out


def rename_map(brief: dict, stem: str = "", slugs: dict | None = None) -> dict[str, str]:
    """{id cũ: id mới} cho mọi phần tử của một brief.

    Trùng id thì gắn hậu tố băm cho **cả hai** phần tử chứ không chỉ phần tử thứ hai:
    nếu chỉ gắn cho cái sau thì thêm/bớt một node ở giữa file sẽ làm hậu tố nhảy sang
    node khác, và diff không đọc được nữa.
    """
    brief = with_slugs(brief, slugs)
    nodes = {n["id"]: n for n in brief.get("nodes", [])}
    proposed: dict[str, str] = {}
    meta = brief.get("meta", {}) or {}
    # Ba id cấp file (definitions / collaboration / process) không bao giờ được gõ lại
    # trong chương, nên chúng lấy **tên file** làm ô tên: đã ngắn, đã duy nhất trong repo,
    # và mở file ra là khớp ngay. Tiêu đề quy trình thì quá dài để làm id.
    base = stem or slugify(meta.get("title", ""))
    if meta.get("id"):
        proposed[meta["id"]] = make_id("definitions", base)
    if meta.get("collaboration"):
        proposed[meta["collaboration"]] = make_id("collaboration", base)

    for p in brief.get("pools", []):
        proposed[p["id"]] = make_id("participant", p.get("name", ""))
        for ln in p.get("lanes", []) or []:
            proposed[ln["id"]] = make_id("lane", ln.get("name", ""))
        if p.get("process"):
            proposed[p["process"]] = make_id("process", base)

    for n in brief.get("nodes", []):
        nid = node_id(n)
        if nid:
            proposed[n["id"]] = nid

    for f in brief.get("flows", []):
        if "id" not in f:
            continue
        kind = "message" if f.get("kind") == "message" else "flow"
        tgt = nodes.get(f["target"])
        fid = flow_id(kind, nodes.get(f["source"]), tgt, f.get("name", ""),
                      fallback=(tgt or {}).get("name", ""))
        if slugify(fid.split("-", 3)[-1] if fid.count("-") >= 3 else ""):
            proposed[f["id"]] = fid

    # duy nhất: mục tiêu số 1, nên nó thắng cả tính ngắn gọn
    seen: dict[str, list[str]] = {}
    for old, new in proposed.items():
        seen.setdefault(new, []).append(old)
    for new, olds in seen.items():
        if len(olds) <= 1:
            continue
        # Hạt giống băm là (id mới, thứ tự khai báo), KHÔNG phải id cũ. Nếu băm theo id
        # cũ thì chạy `--rename` lần thứ hai sẽ ra hậu tố khác, id vừa đổi xong đã trở
        # thành "id cũ" mới. Đã dính đúng lỗi đó một lần.
        for i, old in enumerate(olds):
            proposed[old] = f"{new}-{_hash6(f'{new}|{i}')}"
    return proposed


def check(brief: dict, stem: str = "", slugs: dict | None = None) -> list[tuple[str, str, str]]:
    """[(mã, id, mô tả)]: mã: ID-SHAPE (sai khuôn) | ID-STALE (đúng khuôn, sai nội dung)."""
    # Trộn slug NGAY Ở ĐÂY chứ không để từng hàm tự lo: `no_name` không nhận `slugs`,
    # nên nếu quên bước này thì lint báo ID-NONAME cho phần tử đã có slug trong sidecar.
    brief = with_slugs(brief, slugs)
    out: list[tuple[str, str, str]] = []
    for nid, full in too_long(brief, slugs):
        out.append(("ID-LONG", nid,
                    f"nhãn dài hơn {MAX_WORDS} âm tiết (`{full}`), khai `slug:` "
                    "trong brief để tự chọn cách rút gọn"))
    for nid in no_name(brief):
        out.append(("ID-NONAME", nid,
                    "phần tử không có `name` nên không đặt id tường minh được, "
                    "đặt tên cho nó, hoặc khai `slug:` nếu cố ý để trống nhãn trên hình"))
    for old, new in rename_map(brief, stem, slugs).items():
        if old == new:
            continue
        if parse(old) is None:
            out.append(("ID-SHAPE", old, f"không theo khuôn; đề nghị `{new}`"))
        else:
            out.append(("ID-STALE", old, f"khuôn đúng nhưng lệch nội dung; đề nghị `{new}`"))
    return out


def apply_to_text(text: str, mapping: dict[str, str]) -> tuple[str, int]:
    """Thay id trong một file bất kỳ (YAML mô hình, .md của chương, .bpmn).

    Thay theo id dài trước để `Task_Sua` không ăn mất phần đầu của `Task_SuaChua`, và
    chặn hai biên bằng lookaround để không đụng vào một id dài hơn chứa nó.
    """
    n = 0
    for old in sorted(mapping, key=len, reverse=True):
        new = mapping[old]
        if old == new:
            continue
        pat = re.compile(r"(?<![\w-])" + re.escape(old) + r"(?![\w-])")
        text, k = pat.subn(new, text)
        n += k
    return text, n


# --- đọc ngược từ .bpmn ----------------------------------------------------------------
# Hai trong ba mô hình của báo cáo được dựng từ spec Python chứ không từ brief, nên nếu
# công cụ chỉ đọc được brief thì đúng hai phần ba số mô hình không theo được quy ước.
# Đọc `.bpmn` ra một dict *hình dạng brief* là đủ để dùng lại toàn bộ phần trên.
_TAG_GATEWAY = {
    "exclusiveGateway": "exclusive", "parallelGateway": "parallel",
    "inclusiveGateway": "inclusive", "eventBasedGateway": "event",
    "complexGateway": "complex",
}
_TAG_EVENT = {
    "startEvent": "start", "endEvent": "end", "boundaryEvent": "boundary",
    "intermediateCatchEvent": "intermediate", "intermediateThrowEvent": "intermediate",
}
_TAG_TASK = {
    "task": "none", "userTask": "user", "serviceTask": "service", "sendTask": "send",
    "receiveTask": "receive", "manualTask": "manual", "scriptTask": "script",
    "businessRuleTask": "rule", "callActivity": "call",
}


def brief_from_bpmn(path: str | pathlib.Path) -> dict:
    """`.bpmn` -> dict cùng hình dạng brief, đủ cho `rename_map`/`check`."""
    import xml.etree.ElementTree as ET

    root = ET.parse(str(path)).getroot()
    loc = lambda e: e.tag.split("}")[-1]                      # noqa: E731
    brief: dict = {"meta": {}, "pools": [], "nodes": [], "flows": []}

    if root.get("id"):
        brief["meta"]["id"] = root.get("id")
    for e in root.iter():
        t, eid = loc(e), e.get("id")
        if not eid:
            continue
        if t == "collaboration":
            brief["meta"]["collaboration"] = eid
        elif t == "participant":
            brief["pools"].append({"id": eid, "name": e.get("name") or "",
                                   "process": e.get("processRef") or "", "lanes": []})
        elif t == "lane" and brief["pools"]:
            brief["pools"][-1]["lanes"].append({"id": eid, "name": e.get("name") or ""})
        elif t in _TAG_GATEWAY:
            brief["nodes"].append({"id": eid, "kind": "gateway",
                                   "gateway": _TAG_GATEWAY[t], "name": e.get("name") or ""})
        elif t in _TAG_EVENT:
            defn = ""
            for c in e:
                cn = loc(c)
                if cn.endswith("EventDefinition"):
                    defn = cn[: -len("EventDefinition")].lower()
            brief["nodes"].append({"id": eid, "kind": "event", "event": _TAG_EVENT[t],
                                   "definition": defn, "name": e.get("name") or ""})
        elif t in _TAG_TASK:
            brief["nodes"].append({"id": eid, "kind": "task", "task": _TAG_TASK[t],
                                   "name": e.get("name") or ""})
        elif t in ("sequenceFlow", "messageFlow"):
            brief["flows"].append({
                "id": eid, "source": e.get("sourceRef"), "target": e.get("targetRef"),
                "name": e.get("name") or "",
                **({"kind": "message"} if t == "messageFlow" else {}),
            })

    # lane nằm trong pool nào thì `lanes` đã đúng; process id lấy từ participant
    return brief


def sidecar_slugs(path: pathlib.Path) -> dict:
    """Đọc `<mô hình>-slugs.yaml` nằm cạnh nếu có.

    Bảng rút gọn phải sống *cạnh dữ liệu*, không nằm trong đầu người chạy lệnh: mô hình
    dựng từ spec Python không có brief để khai `slug:`, mà nếu bảng chỉ tồn tại lúc
    migrate thì lần lint sau lại báo ID-LONG cho những id đã cố ý rút gọn.
    """
    stem = re.sub(r"-brief$", "", path.stem)
    side = path.with_name(f"{stem}-slugs.yaml")
    if not side.exists():
        return {}
    return yaml.safe_load(side.read_text(encoding="utf-8")) or {}


def load_any(path: pathlib.Path) -> dict:
    """Nhận cả `-brief.yaml` lẫn `.bpmn`: cùng một quy ước, hai nguồn."""
    if path.suffix.lower() == ".bpmn":
        return brief_from_bpmn(path)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# --- CLI -------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief", help="file <ten>-brief.yaml hoặc <ten>.bpmn")
    ap.add_argument("--rename", action="store_true", help="ghi id mới vào file brief")
    ap.add_argument("--also", nargs="*", default=[],
                    help="file khác cũng chứa id (chương .md, .yaml phân tích, .bpmn)")
    ap.add_argument("--slugs", help="file YAML {id cũ: slug ngắn}, cho mô hình chỉ có .bpmn")
    ap.add_argument("--propose-slugs", metavar="FILE",
                    help="ghi ra khuôn {id: slug} cho mọi nhãn quá dài, để sửa tay rồi dùng lại")
    ap.add_argument("--strict", action="store_true", help="thoát khác 0 khi còn id lệch")
    args = ap.parse_args()

    path = pathlib.Path(args.brief)
    brief = load_any(path)
    stem = re.sub(r"-brief$", "", path.stem)
    slugs = sidecar_slugs(path)
    if args.slugs:
        slugs.update(yaml.safe_load(pathlib.Path(args.slugs).read_text(encoding="utf-8")) or {})
    brief = with_slugs(brief, slugs)

    if args.propose_slugs:
        lines = [f"# {path.name}: sửa vế phải cho gọn rồi dùng lại với --slugs",
                 "# Máy chỉ chép nguyên nhãn xuống đây; RÚT GỌN LÀ VIỆC CỦA NGƯỜI VIẾT.", ""]
        for nid, full in too_long(brief, slugs):
            name = next((n.get("name", "") for n in brief.get("nodes", []) if n["id"] == nid), "")
            lines.append(f"# {name}")
            lines.append(f"{nid}: {full}")
        for nid in no_name(brief):
            lines.append("# (không có nhãn: đặt tên trên hình, hoặc chọn slug ở đây)")
            lines.append(f"{nid}: ")
        pathlib.Path(args.propose_slugs).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"-> {args.propose_slugs} ({len(too_long(brief, slugs)) + len(no_name(brief))} mục)")
        return 0

    mapping = {o: n for o, n in rename_map(brief, stem, slugs).items() if o != n}

    long_ = too_long(brief, slugs)
    if long_:
        print(f"{path}: {len(long_)} nhãn dài hơn {MAX_WORDS} âm tiết, khai `slug:` "
              f"trong brief rồi chạy lại:")
        for nid, full in long_:
            print(f"  ~ {nid}  ({full})")
        print()

    blank = no_name(brief)
    if blank:
        print(f"{path}: {len(blank)} phần tử không có tên, máy không đặt id thay được:")
        for b in blank:
            print(f"  ? {b}")
        print()

    if not mapping:
        print(f"{path}: mọi id đã đúng quy ước")
        return 1 if (args.strict and (blank or long_)) else 0

    width = max(len(o) for o in mapping)
    print(f"{path}: {len(mapping)} id lệch quy ước")
    for old, new in mapping.items():
        flag = " " if parse(old) else "!"
        print(f"  {flag} {old.ljust(width)}  ->  {new}")

    if not args.rename:
        print("\nChạy lại với --rename để ghi (nhớ --also cho các file tham chiếu).")
        return 1 if args.strict else 0

    targets = [path] + [pathlib.Path(p) for p in args.also]
    for t in targets:
        if not t.exists():
            print(f"  [bỏ qua] {t} không tồn tại")
            continue
        text = t.read_text(encoding="utf-8")
        new_text, k = apply_to_text(text, mapping)
        if k:
            t.write_text(new_text, encoding="utf-8")
        print(f"  [ghi] {t}: {k} chỗ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
