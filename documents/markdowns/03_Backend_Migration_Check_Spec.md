# Đặc tả kiểm tra Migration Backend (mức Method) — VB.NET → C# (ASP.NET Core)

## 1. Mục đích

Kiểm tra tự động xem các **method** trong hệ thống cũ (VB.NET) đã được convert sang
hệ thống mới (C# / ASP.NET Core) **chính xác hay chưa**, và xuất báo cáo Excel để
team review.

## 2. Nguyên tắc map method (từ kết quả study ảnh 2)

- Một file `*.vb` bị tách thành nhiều file C# (`Service.cs`, `Query.cs`, `DTO.cs`, ...),
  do đó **không so sánh theo cặp file** mà:
  1. Quét đệ quy toàn bộ `*.vb` trong folder nguồn → trích xuất mọi method
     (`Sub` / `Function`, bỏ qua `Property`).
  2. Quét đệ quy toàn bộ `*.cs` trong folder đích → trích xuất mọi method.
  3. **Map theo tên method, không phân biệt hoa thường** (VB không phân biệt case).
- Method chỉ có ở VB → **MISSING** (chưa convert / bị削除 / chuyển sang frontend).
- Method chỉ có ở C# → **EXTRA** (viết mới — không phải lỗi, chỉ ghi nhận).
- Method UI-event của VB (đuôi `_Click`, `_Load`, `_TextChanged`, `_SelectedIndexChanged`, ...)
  được đánh dấu chú thích *"UI event — có thể đã chuyển sang .razor"* để người review
  không hiểu nhầm là lỗi convert backend.

## 3. Các tiêu chí kiểm tra từng cặp method

| Mã | Tiêu chí | Cách kiểm tra | Trọng số |
|----|----------|---------------|:--:|
| C1 | **Tồn tại** | Tên method (case-insensitive) có ở cả 2 bên | 30 |
| C2 | **Tham số** | Số lượng tham số bằng nhau; kiểu từng tham số khớp theo bảng mapping VB→C# (mục 4). Tên tham số khác nhau chỉ cảnh báo nhẹ | 20 |
| C3 | **Kiểu trả về** | `Sub` ↔ `void`/`Task`; `Function As X` ↔ `X` hoặc `Task<X>` (chấp nhận async hoá) | 15 |
| C4 | **Cấu trúc điều khiển** | So sánh số lượng: if, vòng lặp (For/While/Do ↔ for/foreach/while/do), try/catch, return, throw. Chênh lệch nhỏ (±1) → cảnh báo; lớn → fail tiêu chí | 15 |
| C5 | **Độ tương đồng logic** | Chuẩn hóa cả 2 body về dạng token trung tính (mục 5) rồi tính tỷ lệ tương đồng bằng thuật toán so khớp chuỗi (difflib SequenceMatcher):<br>≥ 0.75 → đạt; 0.50–0.75 → cảnh báo; < 0.50 → fail tiêu chí | 20 |

**Điểm chất lượng method = Σ(điểm tiêu chí × trọng số) / 100**, thang 0–100.

## 4. Bảng mapping kiểu dữ liệu VB → C#

| VB.NET | C# chấp nhận |
|--------|--------------|
| Integer | int, Int32 |
| Long | long, Int64 |
| Short | short, Int16 |
| String | string, String |
| Boolean | bool, Boolean |
| Decimal | decimal |
| Double | double |
| Single | float |
| Date / DateTime | DateTime, DateOnly |
| Object | object, dynamic |
| Byte | byte |
| Char | char |
| List(Of X) | List<X>, IList<X>, IEnumerable<X> |
| Dictionary(Of K, V) | Dictionary<K,V>, IDictionary<K,V> |
| DataTable / DataSet | (chấp nhận List<DTO> — do bỏ ADO.NET sang EF Core, chỉ cảnh báo) |
| X() (mảng) | X[], List<X> |

Ghi chú: kiểu trả về `Task<X>` / `ValueTask<X>` ở C# được coi là **tương đương X**
(do chuyển sang async là thay đổi có chủ đích của kiến trúc web).

## 5. Chuẩn hóa (normalize) trước khi so sánh logic (C5)

Vì code mới được viết lại 80–120% (theo ảnh 2), so sánh text thô sẽ luôn fail.
Cả body VB và C# được đưa về dạng trung tính:

1. Xóa comment (`'`, `//`, `/* */`) và chuỗi literal → thay bằng `"S"`.
2. Đưa keyword 2 ngôn ngữ về token chung, ví dụ:
   `If/Then/End If` & `if(){}` → `IF`; `For Each` & `foreach` → `LOOP`;
   `Nothing` & `null` → `NULL`; `AndAlso` & `&&` → `AND`; `Me.` & `this.` → bỏ;
   `.ToString()` giữ nguyên; `Dim x As T` & `T x` → `VAR x`.
3. Lowercase toàn bộ định danh, xóa khoảng trắng thừa.
4. Bỏ qua khác biệt thuần cú pháp: `End Sub/End Function`, dấu `;`, `{}`.

Khác biệt trong **chuỗi SQL** (Oracle → PostgreSQL) đã bị thay bằng `"S"` nên
không làm sai lệch điểm — đúng chủ trương "khoan dung với thay đổi tầng DB".

## 6. Thang trạng thái tổng hợp của một method

| Trạng thái | Điều kiện | Màu trong báo cáo |
|-----------|-----------|-------------------|
| **PASS** | Điểm ≥ 85 và không tiêu chí nào fail | 🟩 Xanh lá |
| **WARNING** | 60 ≤ điểm < 85, hoặc có cảnh báo (khác tên tham số, DataTable→List, chênh cấu trúc ±1...) | 🟨 Vàng |
| **FAIL** | Điểm < 60, hoặc fail C2/C3 (sai chữ ký), hoặc C5 < 0.5 | 🟥 Đỏ |
| **MISSING** | Chỉ có ở VB, không tìm thấy ở C# | ⬜ Xám (kèm chú thích nếu là UI event) |
| **EXTRA** | Chỉ có ở C# (method viết mới) | 🟦 Xanh dương nhạt |

## 7. Báo cáo Excel xuất ra

**Sheet 1 — `Summary`**
- Thời gian scan, folder nguồn/đích, số file mỗi bên.
- Tổng số method VB / C#; đếm theo trạng thái PASS/WARNING/FAIL/MISSING/EXTRA.
- Tỷ lệ convert đạt (`PASS / (tổng method VB)`), điểm trung bình.

**Sheet 2 — `Detail`** — mỗi dòng một method:
| Cột | Nội dung |
|-----|----------|
| No, Method | Tên method |
| VB File / C# File | File chứa (đường dẫn tương đối) |
| VB Signature / C# Signature | Chữ ký đầy đủ 2 bên |
| C1..C5 | Kết quả từng tiêu chí (OK / WARN / NG / -) |
| Similarity | Tỷ lệ tương đồng logic (0–1) |
| Score | Điểm 0–100 |
| Status | PASS / WARNING / FAIL / MISSING / EXTRA (tô màu) |
| Notes | Diễn giải chi tiết (sai kiểu tham số nào, chênh cấu trúc gì, ...) |

## 8. Luồng sử dụng tool

```
[Chọn folder VB nguồn] → [Chọn folder ASP.NET Core đích] → [Scan]
      → Bảng kết quả trên GUI (lọc theo trạng thái, xem chi tiết từng method)
      → [Export Excel] → file .xlsx báo cáo
```

## 9. Cập nhật đợt 2 (theo documents/04 — kiến trúc PCRS/CQRS)

1. **Tự tìm thư mục Business Logic** (`tool/core/locator.py`): người dùng chọn folder
   gốc; phía C# tool ưu tiên (a) folder `*Application*` chứa `Features/`,
   (b) folder `*Application*` có file .cs, (c) folder tên `Features`/`BusinessLogic`,
   (d) fallback quét toàn bộ. Phía VB luôn quét toàn bộ (logic nằm trong code-behind).
   Folder hiệu dụng hiển thị trên GUI, CLI và sheet Summary.
2. **Khớp tên qua hậu tố `Async`**: `GetList` ↔ `GetListAsync` (ghi chú, không phải lỗi).
3. **Khoan dung thay đổi có chủ đích** (mục 4.3 tài liệu 04):
   - C2/C3: `DataTable` → `List<DTO>` chỉ WARN (đợt 1 tham số bị tính NG — đã sửa).
   - C3: `Boolean`/`Sub` → `Result`/`Result<T>` (Result pattern) chỉ WARN.
   - C5: DELETE vật lý → soft delete (`IsDeleted = true`) nâng NG → WARN.
   - C5: body đổi từ `adapter.Fill`/DataTable sang mapping `List<DTO>`/EF Core nâng NG → WARN.
   - Chuẩn hóa: dòng plumbing ADO.NET (Using connection/command, `Open()`,
     `Parameters.Add`, khai báo chuỗi SQL) bị loại; `Execute*`/`Fill`/chuỗi LINQ
     `_context...` → token `db` ở cả 2 phía; hậu tố `Async` bị bỏ khi token hóa.
4. **EXTRA (kiến trúc mới)**: method `Handle`/`Configure`/`Success`/`Failure`/`Validate`
   hoặc nằm trong `*Validators.cs`, `*Dto(s).cs`, `Result.cs`, `BaseEntity.cs`,
   `*Configuration.cs`, thư mục `DTOs/`, `Common/` — đánh dấu riêng, không tính là
   thừa code (mục 4.4 tài liệu 04), đếm riêng trong Summary.
5. Parser C# bắt thêm method expression-bodied một dòng (`=> ...;`).

## 10. Cập nhật đợt 3 (2026-07-10 — 10 cải tiến)

1. **Bảng mapping tên method thủ công** (`tool/core/mapping.py`): method bị đổi tên khi
   migrate khai báo trong file CSV (`TenVB,TenCSharp`) hoặc JSON; CLI `--map <file>`,
   GUI có ô "File mapping tên method". Cặp khớp qua mapping có note riêng ở C1.
   File mẫu: `samples/pcrs/method_mapping.csv`.
2. **File cấu hình** (`tool/core/config.py` + `config.sample.json`): trọng số C1–C5,
   ngưỡng similarity/điểm, danh sách nhận diện kiến trúc mới, hậu tố UI event, pattern
   SQL Oracle đều cấu hình được. Thiếu key nào dùng mặc định key đó (mặc định = hành vi
   đợt 1/2). CLI `--config <file>`; GUI tự đọc `config.json` đặt cạnh exe.
3. **Ghép overload best-match**: nhóm method trùng tên có overload được chấm thử mọi
   tổ hợp rồi ghép theo điểm cao nhất (ưu tiên cùng số tham số) thay vì ghép theo thứ tự.
4. **C5 thêm token-bag similarity**: nếu seq-similarity < 0.5 nhưng độ trùng TẬP token
   ≥ 0.8 → nâng NG → WARN với note "khác thứ tự câu lệnh" (giảm FAIL oan khi code bị
   đảo cấu trúc có chủ đích). Cột Similarity vẫn là seq-similarity.
5. **Kiểm tra SQL Oracle → PostgreSQL** (`tool/core/sql_checker.py`): quét string literal
   SQL phía C#; còn `NVL(`, `DECODE(`, `ROWNUM`, `SYSDATE`, `FROM DUAL`, `.NEXTVAL`,
   join `(+)` → note "sẽ lỗi trên PostgreSQL" và ép status tối thiểu WARNING; so tập
   bảng 2 bên khi cả 2 đều có SQL. C# dùng LINQ (không có SQL) không bị phạt.
6. **Xác nhận UI event qua .razor** (`tool/core/razor_scanner.py`): index `*.razor`/
   `*.razor.cs` toàn bộ folder C#; `{Form}_Load` khớp file `{Form}.razor` có
   `OnInitialized*`; `{control}_{event}` khớp handler theo core-name (bỏ tiền tố
   btn/txt/on/handle, hậu tố click/changed...). MISSING là UI event tìm thấy handler
   → note xác nhận + đếm riêng trong Summary; status vẫn MISSING.
7. **Exit code cho CI** (CLI): `--fail-on FAIL,MISSING` / `--min-score N` → exit 2 khi
   không đạt (EXTRA kiến trúc mới và MISSING đã xác nhận frontend không tính); exit 1
   lỗi input; exit 0 đạt.
8. **Baseline diff** (`tool/core/report_io.py`): `--json out.json` xuất kết quả;
   `--baseline truoc.json` in bảng tốt lên / xấu đi / mới / biến mất giữa 2 lần scan.
9. **GUI**: ô "Tìm method" lọc realtime; panel chi tiết thành 2 tab (Tổng quan /
   Code VB ⇄ C# hiển thị body 2 bên cạnh nhau).
10. **Bộ test tự động** (`tests/`): `python -m unittest discover tests` — bảng kỳ vọng
    documents/06 thành test hồi quy + unit test cho các module core.
    Sửa kèm 1 bug normalizer: `AndAlso` → `&&` trước đây bị rule nối chuỗi `&` → `+`
    phá thành `++`.

## 11. Cập nhật đợt 4 (2026-07-10 — rule-based check convert method)

Bổ sung lớp kiểm tra **rule-based** cho các trường hợp thực tế khi convert method
Business Logic (bẫy ngôn ngữ VB→C#, luồng lỗi Result pattern, nghiệp vụ dính tầng
dữ liệu, async). Tiêu chí nằm ở file **`rules/conversion_rules.json`** — tool đọc để
chạy, người review đọc để hiểu; sửa/thêm rule không cần sửa code.

1. **Nguyên tắc**: rule chỉ **thêm ghi chú** `RULE <id>: ...` (điểm cần review tay),
   không trừ điểm C1–C5. Ngoại lệ duy nhất: `JP-MSG` nâng PASS → WARNING vì message
   tiếng Nhật biến mất đồng nghĩa khả năng thiếu nhánh check nghiệp vụ.
2. **Rule quét body VB** (khác biệt ngữ nghĩa ngầm cần đối chiếu bên C#):
   `VB-CINT` (banker's rounding) · `VB-INTDIV` (chia nguyên `\`) · `VB-IIF` (tính cả
   2 vế) · `VB-ONERROR` (nuốt lỗi) · `VB-ROWS0` (bảng rỗng) · `VB-EMPTYSTR`
   (`""` vs `Nothing`) · `VB-ANDOR` (không short-circuit).
3. **Rule quét body C#**: `CS-WAITRESULT` (sync-over-async) · `CS-FIREFORGET`
   (`_ = XxxAsync(...)`). EXTRA cũng được quét.
4. **Pair rules** (so 2 chiều một cặp): `JP-MSG` (message 日本語 của VB không thấy ở
   `Result.Failure` bên C#) · `SELF-EXCL` (method check/exist/dup mất điều kiện `<>`
   loại trừ chính record) · `VALIDATOR-SPLIT` (C4/C5 lệch + cùng thư mục có
   `*Validators.cs` → nhắc đối chiếu FluentValidation trước khi kết luận) ·
   `ROWNUM-ORDER` (`First/Take` không `OrderBy` trong khi SQL cũ dùng `ROWNUM`).
5. **Tùy biến**: CLI `--rules <file>`; config `"rules": {"enabled", "file"}`;
   exe tự tìm `rules/conversion_rules.json` đặt cạnh nó (ưu tiên) hoặc dùng bản
   đóng gói kèm trong exe. Summary CLI/Excel đếm "method có ghi chú RULE".
6. Sample minh họa: `CalcRoundedPrice` (PASS + VB-CINT/VB-INTDIV),
   `CheckDuplicateProductName` (PASS + SELF-EXCL), `ApplyMemberDiscount`
   (WARNING + JP-MSG chỉ đích message bị mất).

## 12. Cập nhật đợt 6 (2026-07-16 — gate đánh giá AI qua Claude API)

Bổ sung **lớp đánh giá thứ 3** (đặc tả gốc: documents/13_Master_Prompt_v6.md),
song song và độc lập với lớp C1-C5 và lớp rule-based — **không sửa điểm,
không sửa status** của 2 lớp trước.

1. **Phạm vi**: gọi Claude API (mặc định `claude-sonnet-5`) đánh giá **tất cả**
   method, kể cả MISSING (chỉ có VB) và EXTRA (chỉ có C#). Tiêu chí PASS/WARNING
   hoàn toàn theo nhận định tự do của model; prompt hệ thống có mô tả các thay
   đổi có chủ đích của kiến trúc mới (mục 9.3) để model không báo oan.
2. **Output**: sheet Detail thêm 2 cột — **"Nội dung AI đánh giá"** (text) và
   **"Status AI đánh giá"** (PASS xanh / WARNING vàng). Khi API lỗi, mất mạng,
   thiếu key, thiếu package → ô ghi **"AI chưa thực hiện đánh giá"** (xám),
   scan vẫn hoàn thành bình thường. Summary thêm dòng thống kê AI; JSON report
   thêm `ai_status`/`ai_comment`; GUI thêm cột "AI đánh giá" + hiển thị nội dung
   trong tab Tổng quan.
3. **Cấu hình** (`config.json`, mục `"llm"` — xem config.sample.json):
   `enabled` (mặc định false), `model`, `api_key` (ưu tiên nếu khác rỗng),
   `api_key_env` (mặc định `ANTHROPIC_API_KEY`), `cache_file`, `timeout_seconds`,
   `max_retries`, `max_output_tokens`. **Đổi token chỉ cần sửa `api_key` trong
   config.json** — không cần build lại; KHÔNG commit config.json chứa key.
4. **Cache** (`tool/core/llm_reviewer.py`): key = sha256(model + PROMPT_VERSION
   + tên + body VB + body C#) lưu vào `llm_cache.json` (cạnh exe/gốc repo, hoặc
   theo `cache_file`) — method không đổi nội dung thì retest không gọi lại API
   (không tốn token). Đổi prompt → tăng PROMPT_VERSION để cache cũ tự vô hiệu.
5. **CLI**: cờ `--llm` bật cho lần chạy (hoặc `llm.enabled=true` trong config);
   in thêm 1 dòng thống kê `AI danh gia: PASS/WARNING/Chua danh gia (cache hit)`.
   Bảng method và exit code giữ nguyên — quality gate (`--fail-on`/`--min-score`)
   KHÔNG tính kết quả AI.
6. **Yêu cầu môi trường khi bật AI**: `pip install anthropic` + API key. Không
   cài/không key → mọi method ghi "AI chưa thực hiện đánh giá" kèm lý do.
   Bản exe PyInstaller không tự thấy package cài sau khi build — muốn dùng AI
   trên exe phải build lại bằng `build_exe.bat` trên máy đã cài `anthropic`
   (chạy từ source thì không cần).
7. **Test** (`tests/test_llm.py`, 18 test): mock hoàn toàn qua `call_fn`, không
   mạng, không cần package; phủ cache hit/miss, lỗi lẻ tẻ, thiếu key, ép status
   lạ về WARNING, 2 cột Excel, và bất biến "không sửa điểm/status/notes cũ".

## 13. Cập nhật đợt 7 (2026-07-16 — cột "Status DEV đánh giá" trong Excel)

Sheet Detail thêm cột thứ 18 (R) **"Status DEV đánh giá"** — nơi **người review
tự chấm tay** kết luận cuối cùng cho từng method:

1. Ô để **trống** khi xuất file; tool và AI không bao giờ ghi vào cột này.
2. Mỗi ô có **dropdown** (Excel data validation, chặn giá trị ngoài danh sách)
   với đúng bộ trạng thái của tool: PASS / WARNING / FAIL / MISSING / EXTRA.
3. Ô tự **tô màu theo giá trị chọn** (conditional formatting, cùng bảng màu với
   cột Status của tool); auto-filter mở rộng tới cột R.
4. Sheet Summary thêm dòng giải thích cột DEV.
5. Quy ước 3 cột status trong báo cáo: **Status** (máy chấm C1-C5 + rule) →
   **Status AI đánh giá** (Claude gợi ý) → **Status DEV đánh giá** (phán quyết
   cuối của người review, điền tay trong Excel).
6. Giới hạn: giá trị DEV chỉ nằm trong file Excel — tool không đọc lại khi scan
   lần sau (mỗi lần export là file mới).

## 14. Cập nhật đợt 8 (2026-07-16 — hỗ trợ Google Gemini cho gate AI)

Gate AI (mục 12) hỗ trợ thêm **Google AI Studio / Gemini** (có free tier) bên
cạnh Anthropic Claude:

1. **Cấu hình**: `llm.provider` = `"auto"` (mặc định) | `"anthropic"` | `"google"`.
   `auto` nhận diện theo dạng key: `AIza...` → Google, còn lại → Anthropic.
   Model trong config không hợp provider → tự thay bằng model mặc định của
   provider (Google: `gemini-2.5-flash`; Anthropic: `claude-sonnet-5`); cache
   key dùng model thực dụng.
2. **Gọi Gemini bằng REST + urllib stdlib** (không cần cài package mới — exe
   không phình thêm); key đặt trong header `x-goog-api-key` (không nằm trên URL);
   ép JSON bằng `responseMimeType` + `responseSchema` (enum PASS/WARNING).
3. **Free tier**: gặp HTTP 429 rate-limit thì tự đọc `retryDelay` trong response
   và chờ rồi gọi lại (tối đa `max_retries` lần) — scan bộ lớn trên free tier
   chậm hơn nhưng vẫn hoàn thành.
4. **Lỗi chí mạng nhận diện thêm** (dừng ngay sau 1 lần gọi, không lặp vô ích):
   key Google sai ("API key not valid"), project Google hết credit trả trước
   ("credits are depleted" — 429 nhưng khác rate-limit), bên cạnh 2 lỗi cũ của
   Anthropic (sai key, hết credit).
5. Lấy key free: **aistudio.google.com** → Get API key → chọn project **không
   gắn billing** (project gắn billing trả trước mà hết credit sẽ bị lỗi ở mục 4).
6. Thông báo lỗi đổi trung tính: "Khong goi duoc AI API..." / "Loi khi goi AI
   API..." (không còn ghi cứng "Claude").

## 15. Cập nhật đợt 9 (2026-07-16 — sheet mô tả chi tiết từng method trong Excel)

Mỗi dòng sheet Detail **reference sang một sheet mô tả riêng** (`M001`, `M002`...
theo số thứ tự dòng) để người review **nhìn bằng mắt** đánh giá không cần mở IDE
(đặc tả gốc + ma trận 10 trường hợp: documents/markdowns/14_Master_Prompt_v9.md):

1. **Hyperlink 2 chiều**: ô tên method (cột B, Detail) → sheet `Mxxx`;
   đầu sheet `Mxxx` có link "← Quay lại sheet Detail" về đúng dòng.
2. **Nội dung mỗi sheet**: tóm tắt (Score/Similarity/mapping/AI/Notes) +
   **SOURCE VB (hệ thống cũ)** và **SOURCE ASP.NET CORE (hệ thống mới)** —
   mỗi bên gồm đường dẫn file : dòng, chữ ký, **body nguyên văn** (Consolas,
   mỗi dòng code một dòng Excel).
3. **Cover đủ trường hợp**: MISSING ghi rõ "CHUA IMPLEMENT tren ASP.NET Core";
   EXTRA ghi rõ "KHONG CO o source VB (method viết mới)"; body rỗng in
   "(body rong)"; body dài cắt ở `max_body_lines` kèm ghi chú số dòng còn lại.
4. **1 method VB → nhiều method C# ở nhiều folder**: mục "METHOD LIEN QUAN
   TRUNG TEN" liệt kê đầy đủ mọi dòng khác trùng khóa tên (bỏ hậu tố Async,
   tính cả 2 phía nên method đổi tên qua mapping cũng được nối nhóm) — mỗi
   dòng liên quan kèm hyperlink sang sheet của nó, phía có mặt và file.
5. **Cấu hình** mục `"excel"`: `method_sheets` (mặc định true; false để tắt
   với hệ thống cực lớn), `max_body_lines` (mặc định 400 dòng/phía).
6. Không degrade: Summary/Detail giữ nguyên bố cục cột A→R, dropdown DEV,
   2 cột AI, auto-filter; CLI stdout không đổi; `export_excel` giữ chữ ký.
7. **Tên file export kèm timestamp** (đợt 9b — tránh ghi đè giữa các lần xuất):
   GUI đặt tên mặc định `migration_report_YYYYMMDD_HHMMSS.xlsx` trong hộp thoại
   Save; CLI hỗ trợ token `{ts}` trong `--out`/`--json`
   (vd `--out report_{ts}.xlsx` → `report_20260716_190508.xlsx`) — path không
   có token giữ nguyên như cũ để script/CI dùng tên cố định không bị ảnh hưởng.

## 16. Cập nhật đợt 10 (2026-07-16 — sample "1 method VB tách thành nhiều method C#")

Bổ sung 2 case vào bộ sample PCRS (chỉ thay đổi sample + bảng kỳ vọng, engine
giữ nguyên) để minh họa trường hợp tách method khi migrate:

1. **Tách giữ cùng tên — KHÔNG cần mapping**: VB `TransferStock`
   (ProductStock.vb) → C# `TransferStockAsync`
   (Features/ProductStock/StockTransferCommands.cs — phần chuyển kho, ghép cặp
   WARNING sim ~0.62) + C# `TransferStock` (Services/StockAuditService.cs —
   phần ghi log tách ra, thành EXTRA cùng tên). Tool tự gom 2 bản vào mục
   "METHOD LIEN QUAN TRUNG TEN" của sheet mô tả nhờ trùng khóa tên.
2. **Tách kèm ĐỔI TÊN — PHẢI khai mapping**: VB `ArchiveOldOrders`
   (OrderEntry.vb) → C# `PurgeOrdersAsync`
   (Features/OrderEntry/OrderArchiveCommands.cs — phần chính) + C# `PurgeOrders`
   (Services/OrderBatchService.cs — bản chạy batch). Thêm dòng
   `ArchiveOldOrders,PurgeOrders` vào `samples/pcrs/method_mapping.csv`;
   không map → MISSING + 2 EXTRA, có map → WARNING + 1 EXTRA cùng khóa.
3. **Quy tắc chung rút ra** (ghi vào tài liệu hướng dẫn): mapping là quan hệ
   1-1 tới **method chính**; các mảnh tách thêm chỉ tự nối nhóm khi trùng khóa
   tên (bỏ hậu tố Async). Mảnh tách mang tên khác hẳn sẽ là EXTRA độc lập —
   tool chưa tự nối (ghi ở mục Giới hạn).
4. Bảng kỳ vọng mới (documents/markdowns/06): không map 49 dòng
   PASS8/W8/F4/M9/E20 (kiến trúc mới 14); có map 47 dòng PASS9/W9/F4/M7/E18,
   rule-hits 16. Suite 103 test.

## 17. Cập nhật đợt 11 (2026-07-16 — khai báo TÁCH method 1-n qua mapping)

Xử lý trường hợp user yêu cầu: **method VB `A` chứa logic A1 + A2, bên ASP Core
tách thành method `B` (chứa A1) + method `C` (chứa A2), tên khác hoàn toàn** —
trước đợt này tool không thể tự nối vì không trùng tên.

1. **Định dạng mapping mở rộng (tương thích ngược)**:
   - CSV: `TenVB,TenCSharpChinh[,ManhTach1,ManhTach2...]` — cột 2 là method C#
     **chính** (ghép cặp chấm C1-C5 như cũ), cột 3 trở đi là các **mảnh tách**.
   - JSON: `{"TenVB": ["Chinh", "ManhTach1", ...]}` (giá trị string như cũ vẫn hợp lệ).
   - `load_mapping` trả về `Mapping(dict)` — vẫn là dict `{vb: cs_chinh}` cho code
     cũ, thêm thuộc tính `.splits {vb: [manh_tach...]}`.
2. **Nối 2 chiều** (`_link_declared_splits` trong comparator, chạy cuối scan):
   - Cặp chính nhận note "C1: method được khai báo TÁCH thành nhiều method
     (mapping 1-n) — phần logic còn lại ở: ..." + `related_names`.
   - Mỗi mảnh tách (EXTRA) nhận note **"EXTRA (mảnh tách): phần logic tách ra từ
     method VB '...'"** — truy nguồn được về method gốc.
   - Sheet mô tả (đợt 9) gom cả nhóm vào mục "METHOD LIEN QUAN TRUNG TEN" nhờ
     `related_names` (dù tên khác hẳn nhau).
3. **Khoan dung có kiểm soát**: cặp chính bị FAIL **chỉ vì lệch logic**
   (C2/C3 không NG — body A đương nhiên thiếu phần đã tách sang C) → nâng
   WARNING kèm note giải thích, vì việc tách đã được khai báo có chủ đích.
   FAIL do sai chữ ký (C2/C3 NG) giữ nguyên FAIL.
4. **Sample đợt 11**: VB `CloseCustomerAccount(customerId)` (CustomerMaster.vb,
   logic A1 = vô hiệu hóa khách + logic A2 = hủy đơn chờ) → C#
   `DeactivateCustomerAsync` (Features/CustomerMaster/CustomerDeactivationCommands.cs,
   logic A1 — cặp chính WARNING sim ~0.64) + `CancelPendingOrdersAsync`
   (Features/OrderEntry/OrderCancellationCommands.cs, logic A2 — EXTRA mảnh tách).
   Dòng mapping: `CloseCustomerAccount,DeactivateCustomer,CancelPendingOrders`.
5. Bảng kỳ vọng mới: không map 54 dòng PASS8/W8/F4/M10/E24 (kiến trúc mới 16);
   có map 51 dòng PASS9/W10/F4/M7/E21, rule-hits 17. Suite 111 test.

## 18. Giới hạn đã biết (sau đợt 11)

- Parser dùng regex/heuristic, không phải compiler đầy đủ → method sinh bởi
  generic phức tạp, partial method, code sinh tự động có thể cần review tay.
- SQL mới kiểm tra cú pháp Oracle còn sót + tập bảng, chưa so sánh ngữ nghĩa
  điều kiện WHERE/JOIN.
- Razor scan chỉ xác nhận "có handler đích", chưa chấm điểm nội dung frontend.
- Rule check là heuristic "điểm cần review", không khẳng định bug; chưa phát hiện
  method bị tách/gộp (1 VB → nhiều C#), chưa quét static state / thiếu `await`
  dạng biểu thức phức tạp.
- Lớp AI (đợt 6) là nhận định của LLM — không tất định (cùng input có thể trả
  khác nhau giữa các lần gọi khi cache miss), chỉ mang tính gợi ý review, không
  thay thế người review và không tham gia quality gate CI.
- Method tách khi migrate: mảnh trùng khóa tên tự nối (đợt 10); mảnh tên khác
  hẳn nối được qua **khai báo mapping 1-n** (đợt 11). Giới hạn còn lại: mảnh
  tách **không được khai báo** trong mapping vẫn là EXTRA độc lập — tool không
  tự suy ra quan hệ ngữ nghĩa; và điểm C5 của cặp chính vẫn tính trên body
  method chính (các mảnh chỉ được nối để review, không cộng gộp body khi chấm).
