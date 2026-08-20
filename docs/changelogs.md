# Changelogs

Mỗi version được tag ghi một mục ở đây. Mục TODO nào hoàn thành thì chuyển từ [`TODO.md`](TODO.md) sang đây, ở version phát hành nó.

## v0.5.6

**A model with no pool is a model**

A plain process with no collaboration is legitimate BPMN and it is what a modeler writes for a diagram with no pool drawn on it. `bpmn2yaml` converted one happily, writing `pools: []`, and then `bpmn-brief` left every node with no lane and `layout()` died on `KeyError: None`. A crash on valid input, with a message about a missing dictionary key, on the simplest kind of diagram there is.

The fix reuses the implicit band from v0.5.4 one level up: a model with no real pool gets **one implicit pool holding one implicit band**. Layout, routing and the process body then work unchanged, because from their point of view there is a pool like any other. Neither is written to XML.

What comes out is the shape that went in: no `<bpmn:collaboration>` at all, one bare `<bpmn:process>`, and the `BPMNPlane` pointing at that process rather than at a collaboration. An empty collaboration would have been legal and one line cheaper, but reading it back would invent a participant the author never drew, and inventing elements is the thing the whole round trip exists to prevent.

One consequence had to be handled rather than inherited: an artifact with no pool is normally written in the collaboration, and with no collaboration there is nowhere for it to go. In a poolless model those artifacts join the one process.

Checked on `tests/fixtures/leading-comment.bpmn` from typst-bpmn, which is exactly this shape: it now builds, and every bound and waypoint comes back identical. The only additions are label boxes for the two named events, which the emitter has always written when a file arrives without them.

**`tests/test_roundtrip.py`** gains five assertions: no collaboration is written, exactly one process is, the plane points at it, the model comes back with no pool, and every node keeps its coordinates.

With this the open list is down to one item, the vertical layout mode, and it is the only thing left that `bpmn2yaml` states in the `.yaml` and `bpmn-brief` still ignores.

## v0.5.5

**An annotation can hang off a sequence flow again**

`brief.py` built a link only when one end of an `association` was a node. An association whose other end was a *flow* was skipped, the annotation was then left with no host, and the orphan sweep deleted it together with both of its associations. Annotating one branch of a gateway is the main thing annotations are for, so the case that silently lost data was the common one, and it lost it quietly: the only trace was one `[chú ý]` line counting orphans.

A data association still has to end on a node, because it moves data between an activity and a data object. Only a plain `association` may now name a flow.

Three things follow from letting a flow be a host, and each is a place where a flow is not a box:

- **Where the annotation sits.** A sequence flow has no bounds, so it stands in as a zero-sized point at the middle of its own route, and the annotation hangs below that point the way it hangs below a task. The midpoint is measured by length rather than by vertex count, because an orthogonal route is mostly short jogs plus one long run and the middle vertex is usually a corner.
- **Which process owns it.** Neither, and that is not a gap in the model. Camunda Modeler writes a flow-level annotation into the `<bpmn:collaboration>`, next to the message flows, and so does this now: an artifact with no pool is written there along with its associations. A node still lends its pool to whatever hangs off it, so nothing changes for an annotation on a task.
- **Which end is the source.** An association can be drawn from the annotation to the thing or from the thing to the annotation, and `direction` was the only record of which. The emitter used to write `sourceRef="host"` unconditionally and flipped every annotation-first association on the way through. It now follows what the file said.

Measured on `samples/b04-btvn01.bpmn`, the model that has one of these: every node, every flow, the annotation and both associations now survive a full round trip with identical coordinates, and the emitted `<bpmn:collaboration>` block matches Camunda Modeler's own element for element. The only remaining differences are the exclusive gateway `bpmn-brief` deliberately inserts to fix a merge into an event, and the two flows retargeted onto it.

**`tests/test_roundtrip.py`** gains five assertions on a document whose annotation hangs off a sequence flow: it survives, its association survives with the same two ends, it is written at collaboration level, and both come back with the same bounds and waypoints.

## v0.5.4

**A pool without a lane is a pool, not a black box**

`bpmn2yaml` wrote neither `process:` nor `blackbox:`, so `bpmn-brief` had to guess which participants were collapsed, and it guessed from the absence of `lanes:`. A participant that owns a process and declares no lane set is ordinary BPMN and the usual shape of a single-role pool. Every one of them was read as a black box: the pool lost its process, and every node it owned was moved into the first lane of whichever pool happened to be listed first.

The damage was not subtle and it was sitting in this repository's own fixtures. `samples/b04-btvn01.bpmn` has two real participants; it came back out with one, and half the model relocated. `tests/fixtures/two-blackboxes.bpmn` did not come back out at all, it crashed with `KeyError: None`, because the nodes of the flattened pool ended up with no lane to be placed in.

The fix is the same principle the coordinates already follow: **what the file states wins over what the algorithm infers.**

- `convert.py` states the kind. A participant with a `processRef` gets `process: <id>`, one without gets `blackbox: true`. Nothing is left to be deduced downstream.
- `brief.py` trusts the statement. `blackbox:` decides if present, `process:` decides next, and the lane heuristic survives only for a hand-written brief that says neither.
- A real pool with no lane set gets **one implicit band**, keyed by the pool's own id so no invented id can collide, purely so the layout has a rectangle to place nodes in. It is marked `implicit` and never written to XML, so a file that arrived with no laneSet leaves with no laneSet. When the pool's bounds are pinned, the band follows them rather than staying on the computed grid.

Two smaller faults surfaced on the way and both are the same shape, an inference beating a statement:

**The default band ignored the node's own pool.** A node in a laneless pool names a `pool:` and no `lane:`, and `brief.py` reached straight for the first band in the model. It now takes the first band *of the pool the node names*, and only then falls back. This is what let nodes migrate between pools on a round trip.

**An artifact could not stay in its own pool.** `place_artifacts` gave every artifact its host's pool. A data object shared by two tasks in two different pools therefore followed whichever host was recorded, not the pool it was declared in. An artifact that states `pool:` now keeps it, exactly as `bounds` and `waypoints` do.

Measured on the fixtures rather than asserted: `b04-btvn01` now round-trips with no node moving pool, and the only remaining differences are the gateway `bpmn-brief` deliberately inserts to fix a rule violation, and one known limitation filed below. `vertical-pools` differs by exactly one key, `horizontal`, which is the open vertical-mode item.

**`tests/test_roundtrip.py`** gains six assertions on a two-pool document where one pool declares no lane: the process survives, both processes are written, no laneSet is invented, no node changes pool, and the pool comes back byte-identical.

**Filed, not fixed**, both found by running the fixtures through: a text annotation attached to a *sequence flow* is dropped along with its associations, and a model with no pool at all still crashes. Both are in [`TODO.md`](TODO.md) with a reproducer.

**Downstream**: this changes what `bpmn2yaml` writes, so it was checked against [typst-bpmn](https://github.com/sam-uit/typst-bpmn) rather than assumed. Its three YAML-fed golden cases (`b04-btvn01`, `vertical-pools`, `leading-comment`) gain only `process:` keys, which the Typst side ignores, and no `blackbox: true` at all, because every participant in them owns a process. No golden number moves. The one case that does hold black boxes, `two-blackboxes`, is loaded through the XML parser, which has always set that flag itself. Where a black box *does* reach the Typst side through YAML from now on, the two parsers agree where they used to differ: the XML reader marked it collapsed and the YAML path drew it as an ordinary empty pool.

## v0.5.3

**Message flow routing: three shapes instead of one, and the `KeyError` that hid behind explicit waypoints**

`message_route` assumed every message flow had a collapsed participant at one end. It picked the endpoint that was not in `pool_bounds`, called it the node, and looked the *other* one up as a pool. A message flow joining two nodes therefore looked up a node id in `pool_bounds` and died with a bare `KeyError: 'Event_19kg7ym'`, a message that names the victim and says nothing about the cause.

How this survived so long is the interesting part. The first line of the function returns the author's own `waypoints` untouched, and since v0.5.0 every `.yaml` that came back from a modeler carries waypoints for every edge. The crash was therefore invisible on the improvement loop and only reachable from a hand-written brief, which is exactly the path a new user takes first. Strip the message waypoints from this repository's own sample, `samples/b04-btvn01.bpmn` converted and fed back, and the old code dies on it.

The routing is now three named methods, because there are three geometries and one of them cannot stand in for the others:

- `message_route_node_to_band`, unchanged behaviour, kept byte-identical output. The band spans the whole width so the flow drops at the node's centre x and the band contributes only a y.
- `message_route_node_to_node`, new. It picks the axis from the gap that actually exists between the two boxes rather than from the `isHorizontal` flag, which matters because that flag is still hard-coded and because a hand-placed diagram can disagree with it. Pools side by side leave a horizontal gap, pools stacked leave a vertical one, and the wider gap is the direction the message has to cross. With centres aligned it is one straight segment; otherwise it turns twice in the middle of the gap, the shape a modeler draws by hand.
- `message_route_band_to_band`, new. Two collapsed participants exchanging a message directly, one vertical segment at the centre of the span the two bands share.

Checked against the modeler rather than against itself: on `tests/fixtures/vertical-pools.bpmn` with its message waypoints removed, `MF_request` comes back as `340,300 -> 540,300`, which is what Camunda Modeler drew before the waypoints were stripped.

An id that is neither a node nor a pool now raises a message that names the id and says what to do about it, instead of a `KeyError`. That is also the first user-facing string written under the new English-only rule.

**`tests/test_message_routes.py`**, 20 assertions covering all three shapes, both directions, `offset` and `stub`, and the unknown-id message. It builds a `Model` without going through `layout()` and hands it only the two dictionaries the routers read, so each case reads as coordinates in and waypoints out.

**Found while fixing this, filed rather than fixed**: a real pool that declares no lane is read as a black box, because `bpmn2yaml` writes neither `blackbox:` nor `process:` and `brief.py` falls back to "no lanes means collapsed". It loses the process and moves the pool's nodes into another pool's first lane. That is a three-file change across `convert.py`, `brief.py` and `build.py`, and mixing it into a routing fix would make both unreviewable, so it is now the open `#bug #med` in [`TODO.md`](TODO.md).

## v0.5.2

**CONTRIBUTING.md, and English as a rule**

The conventions this repository follows were, until now, held in one person's head and in a memory file outside the repository. A clone did not carry them. [`CONTRIBUTING.md`](../CONTRIBUTING.md) writes them down: language, naming, punctuation, Markdown source, changelog, dependencies, and what to run before committing. Each rule carries the reason it is a rule, because a convention with no stated reason reads as taste, and taste is negotiable at three in the morning when something needs to ship.

**English only**, from 2026-08-20, for documentation, comments, docstrings, argparse help, and every string this package prints to a user. Existing Vietnamese prose is a scheduled backlog, translated in one planned pass rather than piecemeal, because a half-translated file costs the reader more than a consistently Vietnamese one.

One exception is written into the rule: **id slugs stay Vietnamese without diacritics**. `task-user-lap-ke-hoach` is not English prose that was left untranslated, it is the name of a real process step, and translating it would break every `bpmn-span` reference in the consuming report. The grammar that produces those slugs is [`docs/naming.md`](naming.md) and it is unaffected.

The **dependency** section states the two things that are invisible from inside any single file here. The version number lives only in `src/bpmn_generator/_version.py`, which both `__init__` and `build` import, so the `exporterVersion` stamped into a generated `.bpmn` cannot drift from the installed package; `pyproject.toml` carries the same number and is the one copy updated by hand. And typst-bpmn's CI installs this package from GitHub pinned to a **tag**, so a release is invisible downstream until it is pushed and tagged, and a change to `bpmn2yaml`'s output can move typst-bpmn's golden manifest. The pin is a tag rather than a branch precisely so that move is a decision somebody made.

The **before committing** section also corrects the README, which still named one test file from the days when there was one. There are four now, 68 assertions, and they are plain scripts: `PYTHONPATH=src python3 tests/<file>.py` runs them with no test-runner dependency.

## v0.5.1

**Quy ước viết áp cho code base, và bốn tham chiếu chết**

62 chỗ dùng em-dash trong docstring, chú thích và **chuỗi in ra cho người dùng**. Thay theo nghĩa chứ không máy móc thành dấu phẩy: nối hai mệnh đề độc lập thì thành chấm phẩy, gắn một nhãn hoặc mở một lời giải thích thì thành hai chấm.

Bốn tham chiếu chết lộ ra trong lúc quét, và cả bốn đều nằm trong chữ người dùng đọc rồi gõ theo:

- `bpmn-brief` in gợi ý "cắt bằng `bpmn-lane(M, ..)`, hoặc hẹp hơn nữa bằng `bpmn-part(M, ..)`". **Cả hai hàm đều không tồn tại** bên typst-bpmn. Đúng là `bpmn-figure(M, view: (lane: ..))` và `bpmn-span(M, from:, to:)`.
- Cùng dòng đó trỏ tới `docs/bpmn-workflow.md`, cũng không tồn tại. Ba đường dẫn tài liệu cũ (`bpmn-rules.md`, `bpmn-naming.md`, `bpmn-workflow.md`) còn nằm rải trong `brief.py`, `ids.py`, `rules.py`, `test_ids.py` và `docs/naming.md`, từ hồi tách repo khỏi báo cáo. Nay trỏ đúng `docs/rules.md`, `docs/naming.md`, `docs/workflow.md`.

Bốn bộ test xanh, không đổi hành vi nào.

## v0.5.0

**Vòng lặp cải tiến giữ đúng thứ người vẽ đã chỉnh** `#bug` `#high`

`bpmn-brief` bỏ qua mọi toạ độ có sẵn trong `.yaml` và vẽ lại từ đầu. Với `bounds` thì thường không thấy, vì bố cục tất định nên chạy lại ra đúng chỗ cũ; với `waypoints` thì thấy ngay, vì đường đi của một cạnh là chỗ được chỉnh tay nhiều nhất trong Modeler. Một cung rời cổng từ *cạnh dưới* đi vòng xuống, sinh lại thành cung rời từ *cạnh phải* rồi bẻ khúc.

Đây không phải chuyện thẩm mỹ. Vòng lặp cải tiến của bộ công cụ này nằm ở chỗ người vẽ chỉnh tay trong Modeler rồi quay lại sửa `.yaml`, nên mỗi lần sinh lại xoá đúng phần vừa chỉnh, và công cụ chống lại chính quy trình nó phục vụ. Tài liệu có nói "toạ độ cố ý không giữ", nhưng câu đó chỉ đúng cho vòng đầu tiên, khi `.yaml` chưa có toạ độ nào.

Nay mọi thứ người viết đưa vào đều thắng thuật toán, đúng cùng một luật với `row`/`col`. Cụ thể, những thứ trước đây bị vẽ lại và giờ đi thẳng qua:

| | Trước | Nay |
| --- | --- | --- |
| `waypoints` của sequence flow | định tuyến lại | dùng nguyên |
| `waypoints` của message flow | định tuyến lại | dùng nguyên |
| `waypoints` của data association | nối thẳng chủ tới artifact | dùng nguyên |
| `bounds` của node, pool, lane, black box, artifact | tính từ lưới | dùng nguyên |
| `label` của node, cạnh, artifact | tính từ tâm | dùng nguyên |
| `fill` / `stroke` hex | chỉ hiểu tên trong bảng màu | dùng nguyên, và thắng bảng màu |
| `marker` của cổng loại trừ (`isMarkerVisible`) | mất | giữ |

Ghim một nửa thì phần được ghim nằm ở chỗ Modeler đặt, phần còn lại ở chỗ lưới tính, và hai hệ toạ độ đó không biết nhau. `bpmn-brief` nay in `[chú ý]` khi gặp trường hợp đó thay vì lặng lẽ cho ra một hình chồng lấn.

Ba lỗi nhỏ hơn lộ ra trong lúc đo:

**Ngắt dòng trong tên bị nuốt.** `name="Phân loại\nhướng xử lý"` ghi ký tự xuống dòng trần vào một thuộc tính XML. Hợp lệ về cú pháp, nhưng bộ phân tích *chuẩn hoá giá trị thuộc tính* và biến nó thành dấu cách, nên ngắt dòng người vẽ đặt biến mất sau mỗi vòng. Nay mã hoá thành `&#10;`.

**Toạ độ lẻ bị làm tròn.** Mọi toạ độ đều in `%.0f`, hợp lý khi tất cả đều do lưới sinh ra. Nhưng Modeler đặt nhãn ở nửa đơn vị (`x="903.5"`), nên khi `bounds` đi thẳng từ file vào thì làm tròn là sửa dữ liệu của người vẽ.

**`exporterVersion` đứng yên ở "0.1.0"** qua ba lần phát hành, tức là nó nói sai chứ không phải nói thiếu. Số phiên bản chuyển vào `_version.py`, một chỗ duy nhất cho cả `__init__` lẫn `build`.

Đo trên năm mô hình L3 của báo cáo: vòng `yaml → bpmn → yaml` nay **không mất một dòng nội dung nào**. Phần còn khác chỉ là thứ tự của data association trong danh sách `flows`, vì BPMN bắt chúng nằm bên trong activity chứ không nằm cùng chỗ với sequence flow. Mô hình thứ sáu (Kế Hoạch Khuyến Mãi) vẫn dừng ở `group`, đúng như bảng "chưa qua được vòng lặp" đã ghi.

Thêm `tests/test_roundtrip.py`, 8 khẳng định, gồm cả vòng thứ hai để chắc rằng bất biến không phải chuyện may.

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
