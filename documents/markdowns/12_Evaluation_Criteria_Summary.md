# Tổng hợp tiêu chí đánh giá Migration Method (VB.NET → ASP.NET Core)

> Tài liệu tổng hợp cho người review — tóm tắt các tiêu chí đang được tool dùng để
> đánh giá một method convert đạt hay không, kèm nơi chứa rule trong source code.
> Đặc tả chi tiết gốc: [03_Backend_Migration_Check_Spec.md](03_Backend_Migration_Check_Spec.md).

## 1. Ba lớp kiểm tra

Tool đánh giá mỗi method qua 3 lớp độc lập:

1. **Lớp chấm điểm C1–C5** — cho điểm 0–100 và xếp trạng thái PASS/WARNING/FAIL.
2. **Lớp rule-based** — quét các bẫy ngôn ngữ/nghiệp vụ VB→C# thực tế, chỉ thêm
   ghi chú để người review đối chiếu tay, **không trừ điểm** (trừ 1 ngoại lệ).
3. **Lớp AI review (đợt 6, tùy chọn — mặc định tắt)** — gọi Claude API đánh giá
   từng method, ghi vào 2 cột riêng trong báo cáo, **không ảnh hưởng** điểm/status
   của 2 lớp trên (xem mục 4).

Hai lớp đầu là **rule cứng viết sẵn trong code/JSON**, chạy offline hoàn toàn;
lớp 3 là lớp gợi ý bằng LLM, chỉ chạy khi bật trong config.

## 2. Lớp 1 — Tiêu chí chấm điểm C1–C5

| Mã | Tiêu chí | Cách kiểm tra | Trọng số |
|----|----------|---------------|:--:|
| **C1** | Tồn tại | Tên method (case-insensitive, khớp cả hậu tố `Async`) có ở cả 2 bên | 30 |
| **C2** | Tham số | Số lượng tham số bằng nhau; kiểu từng tham số khớp theo bảng mapping VB→C#; tên khác nhau chỉ cảnh báo nhẹ | 20 |
| **C3** | Kiểu trả về | `Sub` ↔ `void`/`Task`; `Function As X` ↔ `X`/`Task<X>` (chấp nhận async hoá) | 15 |
| **C4** | Cấu trúc điều khiển | So số lượng if / vòng lặp / try-catch / return / throw; chênh ±1 → cảnh báo, chênh lớn → fail | 15 |
| **C5** | Độ tương đồng logic | Chuẩn hóa body 2 bên về token trung tính rồi so bằng `difflib.SequenceMatcher`: ≥0.75 đạt, 0.50–0.75 cảnh báo, <0.50 fail | 20 |

**Điểm chất lượng = Σ(điểm tiêu chí × trọng số) / 100**, thang 0–100.

### Trạng thái tổng hợp

| Trạng thái | Điều kiện |
|-----------|-----------|
| **PASS** | Điểm ≥ 85 và không tiêu chí nào fail |
| **WARNING** | 60 ≤ điểm < 85, hoặc có cảnh báo (tên tham số khác, DataTable→List, chênh cấu trúc ±1...) |
| **FAIL** | Điểm < 60, hoặc fail C2/C3 (sai chữ ký), hoặc C5 < 0.5 |
| **MISSING** | Chỉ có ở VB, không tìm thấy ở C# (kèm chú thích nếu là UI event có thể đã chuyển sang .razor) |
| **EXTRA** | Chỉ có ở C# (method viết mới) — không tính là lỗi |

### Nơi chứa rule trong source code

| Thành phần | File |
|---|---|
| Logic chấm điểm C1–C5 | [tool/core/comparator.py](../../tool/core/comparator.py) |
| Chuẩn hóa body cho C5 | [tool/core/normalizer.py](../../tool/core/normalizer.py) |
| Trọng số / ngưỡng (chỉnh không cần build) | [config.sample.json](../../config.sample.json) đọc bởi [tool/core/config.py](../../tool/core/config.py) |
| Parser trích xuất method VB | [tool/core/vb_parser.py](../../tool/core/vb_parser.py) |
| Parser trích xuất method C# | [tool/core/cs_parser.py](../../tool/core/cs_parser.py) |
| Map method theo tên/mapping thủ công | [tool/core/mapping.py](../../tool/core/mapping.py) |

## 3. Lớp 2 — Rule-based check bổ sung (đợt 4)

Bổ sung cho các trường hợp thực tế khi convert method Business Logic: bẫy ngôn
ngữ VB→C#, luồng lỗi Result pattern, nghiệp vụ dính tầng dữ liệu, async.

- **Nguồn sự thật:** [rules/conversion_rules.json](../../rules/conversion_rules.json)
  — sửa/thêm rule tại đây, **không cần sửa code**. Exe đóng gói ưu tiên dùng
  file này nếu đặt cạnh nó, fallback về bản copy bundle trong exe.
- **Engine đọc rule:** [tool/core/rule_checker.py](../../tool/core/rule_checker.py)
- **Nguyên tắc:** rule chỉ thêm ghi chú `RULE <id>: ...` (điểm cần review tay),
  không trừ điểm C1–C5. Ngoại lệ duy nhất: `JP-MSG` nâng PASS → WARNING vì
  message tiếng Nhật biến mất đồng nghĩa khả năng thiếu nhánh check nghiệp vụ.

### Rule quét body VB (khác biệt ngữ nghĩa ngầm)

| Rule | Ý nghĩa |
|---|---|
| `VB-CINT` | Banker's rounding của `CInt` |
| `VB-INTDIV` | Chia nguyên `\` |
| `VB-IIF` | `IIf` tính cả 2 vế (không lazy) |
| `VB-ONERROR` | `On Error` nuốt lỗi |
| `VB-ROWS0` | Xử lý bảng rỗng |
| `VB-EMPTYSTR` | `""` vs `Nothing` |
| `VB-ANDOR` | `And`/`Or` không short-circuit |

### Rule quét body C#

| Rule | Ý nghĩa |
|---|---|
| `CS-WAITRESULT` | Sync-over-async (`.Result`/`.Wait()`) |
| `CS-FIREFORGET` | `_ = XxxAsync(...)` không await |

### Pair rules (so 2 chiều một cặp)

| Rule | Ý nghĩa |
|---|---|
| `JP-MSG` | Message tiếng Nhật của VB không thấy ở `Result.Failure` bên C# |
| `SELF-EXCL` | Method check/exist/dup mất điều kiện `<>` loại trừ chính record |
| `VALIDATOR-SPLIT` | C4/C5 lệch + cùng thư mục có `*Validators.cs` → nhắc đối chiếu FluentValidation |
| `ROWNUM-ORDER` | `First`/`Take` thiếu `OrderBy` trong khi SQL cũ dùng `ROWNUM` |

### Module hỗ trợ riêng

| Module | Chức năng |
|---|---|
| [tool/core/sql_checker.py](../../tool/core/sql_checker.py) | Dò cú pháp Oracle còn sót trong SQL string phía C# (`NVL`, `DECODE`, `ROWNUM`, `SYSDATE`, `FROM DUAL`, `.NEXTVAL`, join `(+)`) → ép status tối thiểu WARNING |
| [tool/core/razor_scanner.py](../../tool/core/razor_scanner.py) | Xác nhận UI event VB (`Form_Load`, `{control}_{event}`) có handler tương ứng trong `.razor`/`.razor.cs` |

## 4. Lớp 3 — AI review qua Claude API (đợt 6, mặc định tắt)

Từ đợt 6 (2026-07-16), tool có thêm **gate đánh giá AI** — đặc tả đầy đủ ở
[03_Backend_Migration_Check_Spec.md](03_Backend_Migration_Check_Spec.md) mục 12
và [13_Master_Prompt_v6.md](13_Master_Prompt_v6.md):

- **Phạm vi**: tất cả method (kể cả MISSING/EXTRA), tiêu chí PASS/WARNING theo
  nhận định tự do của model. 2 provider tự nhận diện theo key (đợt 8):
  Anthropic Claude (`claude-sonnet-5`, trả phí) hoặc Google Gemini
  (`gemini-2.5-flash`, có free tier — key `AIza...` từ aistudio.google.com).
- **Output**: 2 cột trong sheet Detail — "Nội dung AI đánh giá" và
  "Status AI đánh giá" (PASS/WARNING; lỗi API/mất mạng/thiếu key →
  "AI chưa thực hiện đánh giá"). **Không sửa** điểm C1–C5, status, hay Notes.
- **Bật/tắt & đổi token**: mục `"llm"` trong `config.json`
  (`enabled`, `model`, `api_key` — đổi token chỉ cần sửa giá trị này,
  hoặc dùng biến môi trường `ANTHROPIC_API_KEY`). Không commit config chứa key.
- **Cache**: `llm_cache.json` theo hash nội dung method — retest không gọi lại
  API, không tốn thêm token. Engine: [tool/core/llm_reviewer.py](../../tool/core/llm_reviewer.py).
- **Cách chạy**: CLI thêm cờ `--llm`; GUI tự chạy khi `llm.enabled=true`.
  Cần `pip install anthropic`. Quality gate CI (`--fail-on`/`--min-score`)
  không tính kết quả AI.
- **Cột "Status DEV đánh giá"** (đợt 7): cột thứ 3 trong bộ status của sheet
  Detail — ô trống kèm dropdown (PASS/WARNING/FAIL/MISSING/EXTRA, tự tô màu)
  để **người review chấm tay kết luận cuối cùng**; tool và AI không ghi vào.
  Quy ước: Status (máy) → Status AI (AI gợi ý) → Status DEV (người quyết).
- **Sheet mô tả từng method** (đợt 9): mỗi dòng Detail có sheet riêng `Mxxx`
  (click tên method để nhảy tới) — source VB + ASP Core (file, chữ ký, body
  đầy đủ), MISSING/EXTRA ghi rõ lý do vắng mặt, mục "liên quan trùng tên"
  liệt kê đủ trường hợp 1 VB → nhiều C#. Cấu hình mục `"excel"` trong config.

## 5. Cơ chế đánh giá lớp 1 + 2: rule-based thuần, không dùng AI/LLM

Hai lớp chấm điểm chính **không gọi AI/LLM API nào** — kết quả tất định, chạy
offline, tái lập được (đây là lớp quyết định PASS/FAIL). Cơ chế dựa hoàn toàn vào:

- **Parser regex/heuristic** ([vb_parser.py](../../tool/core/vb_parser.py),
  [cs_parser.py](../../tool/core/cs_parser.py)) để trích xuất method — không phải
  compiler đầy đủ.
- **Thuật toán so khớp chuỗi** (`difflib.SequenceMatcher`) cho C5 — không phải
  mô hình ngôn ngữ.
- **Rule tường minh** viết sẵn trong `rules/conversion_rules.json`, engine chạy
  regex/pattern-match theo rule đó.

### Giới hạn đã biết

- Parser dùng regex/heuristic, không phải compiler đầy đủ → method sinh bởi
  generic phức tạp, partial method, code sinh tự động có thể cần review tay.
- SQL mới kiểm tra cú pháp Oracle còn sót + tập bảng, chưa so sánh ngữ nghĩa
  điều kiện WHERE/JOIN.
- Razor scan chỉ xác nhận "có handler đích", chưa chấm điểm nội dung frontend.
- Rule check là heuristic "điểm cần review", không khẳng định bug; chưa phát
  hiện method bị tách/gộp (1 VB → nhiều C#), chưa quét static state / thiếu
  `await` dạng biểu thức phức tạp.

## 6. Tham khảo thêm

- Đặc tả gốc đầy đủ (bao gồm lịch sử các đợt cập nhật): [03_Backend_Migration_Check_Spec.md](03_Backend_Migration_Check_Spec.md)
- Hướng dẫn dùng GUI cho người review: [07_GUI_User_Guide.md](07_GUI_User_Guide.md)
- Bảng kỳ vọng sample PCRS: [06_PCRS_Sample_Expectations.md](06_PCRS_Sample_Expectations.md)
- Bản Excel liệt kê rule (để người không đọc JSON vẫn xem được): `rules/conversion_rules.xlsx`
  và `11_Tool_Usage_Guideline.xlsx` (sinh từ `rules/conversion_rules.json` qua
  `python tool/docs_exporter.py`)
