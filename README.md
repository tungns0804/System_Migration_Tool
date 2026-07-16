# Migration Checker — VB.NET → ASP.NET Core (Backend)

Tool desktop (Windows + macOS) kiểm tra chất lượng migration **mức method** giữa
hệ thống cũ (VB.NET / .NET Framework 4.8) và hệ thống mới (C# / ASP.NET Core),
xuất báo cáo Excel.

## Cấu trúc thư mục

```
assets/       Ảnh kiến trúc migration (đầu vào study)
documents/
  markdowns/  01_Study / 02_Chọn ngôn ngữ / 03_Đặc tả kiểm tra (kèm lịch sử các đợt
              ở mục 9-15) / 04_Mapping kiến trúc PCRS / 06_Bảng kỳ vọng sample PCRS /
              07_GUI_User_Guide / 10_Master_Prompt_v5 / 12_Tổng hợp tiêu chí /
              13_Master_Prompt_v6 / 14_Master_Prompt_v9 (prompt mới nhất)
  excels/     11_Tool_Usage_Guideline.xlsx — guideline sử dụng tool bản Excel
rules/        conversion_rules.json — TIÊU CHÍ rule check (tool đọc để chạy, người
              review đọc/sửa được bằng Notepad, không cần build lại)
              conversion_rules.xlsx — bản Excel của tiêu chí (sinh từ JSON)
samples/      pcrs/ — bộ sample theo kiến trúc PCRS 6 project (documents/04):
                legacy_vb (3 form code-behind, 30 method)
                new_aspcore (PCRS.Application/Features CQRS + Server/Domain/Infrastructure
                             + Server/Pages/*.razor cho kiểm tra UI event)
                method_mapping.csv — file mapping tên method mẫu (đợt 3)
              migration_report_pcrs.xlsx / .json — báo cáo mẫu đã xuất sẵn
tests/        Bộ test tự động (unittest): bảng kỳ vọng documents/06 + unit test core
tool/         Ứng dụng Python
  main.py       GUI (Tkinter): chọn folder → Scan → xem kết quả → Export Excel
  cli.py        Chạy không cần GUI (CI/CD, retest tự động, quality gate)
  core/         Engine: vb_parser, cs_parser, normalizer, comparator, locator,
                excel_exporter, config, mapping, sql_checker, razor_scanner,
                report_io, llm_reviewer (đợt 6 — gate đánh giá AI)
config.sample.json  Mẫu file cấu hình (trọng số, ngưỡng, khoan dung — đợt 3;
                    mục "llm" cài đặt Claude API + token — đợt 6)
```

## Chạy bằng file exe (Windows — không cần cài Python)

Chạy trực tiếp **`dist\MigrationChecker.exe`** (double-click) — GUI mở ngay.

Build lại exe khi sửa code: chạy `build_exe.bat` (yêu cầu `pip install openpyxl pyinstaller`).
Trên macOS: chạy từ source (`python tool/main.py`) hoặc build tương tự bằng PyInstaller
ngay trên máy Mac (`python -m PyInstaller --onefile --windowed tool/main.py`) —
PyInstaller không cross-compile nên exe Windows phải build trên Windows, app macOS build trên macOS.

## Cài đặt & chạy từ source

```bash
# Yêu cầu: Python 3.10+ (đã kèm Tkinter)
pip install openpyxl

# GUI
python tool/main.py

# CLI — thử ngay với bộ sample PCRS (kiến trúc CQRS theo documents/04)
python tool/cli.py samples/pcrs/legacy_vb samples/pcrs/new_aspcore --map samples/pcrs/method_mapping.csv --out report_pcrs.xlsx

# Bộ test tự động (chạy sau mỗi lần sửa engine)
python -m unittest discover tests
```

Chỉ cần chọn **folder gốc** của 2 bộ source — tool tự tìm thư mục Business Logic
phía C# (project `*Application*` chứa `Features/` theo kiến trúc PCRS; nếu không có
thì quét toàn bộ). Thêm `--no-detect` để tắt tính năng này ở CLI.

### Tùy chọn CLI (đợt 3)

| Tham số | Ý nghĩa |
|---------|---------|
| `--out report_{ts}.xlsx` | Xuất Excel; token `{ts}` tự thay bằng timestamp `YYYYMMDD_HHMMSS` để các lần xuất không trùng tên (áp dụng cả `--json`); GUI thì tên mặc định đã kèm sẵn timestamp |
| `--map file.csv` | Bảng mapping tên method thủ công (`TenVB,TenCSharp` hoặc JSON) cho method bị đổi tên; đợt 11 hỗ trợ khai báo **tách 1-n**: `TenVB,TenCSharpChinh,ManhTach1,...` (mảnh tách thành "EXTRA (mảnh tách)" + gom vào sheet mô tả) |
| `--config file.json` | Ghi đè trọng số C1–C5 / ngưỡng / khoan dung (xem `config.sample.json`; GUI tự đọc `config.json` cạnh exe) |
| `--json out.json` | Xuất kết quả scan ra JSON (làm baseline cho lần sau) |
| `--baseline old.json` | So sánh với lần scan trước: in bảng tốt lên / xấu đi / mới / biến mất |
| `--fail-on FAIL,MISSING` | Exit code 2 nếu còn method thuộc status liệt kê (dùng cho CI; EXTRA kiến trúc mới và MISSING đã xác nhận frontend không tính) |
| `--min-score 85` | Exit code 2 nếu điểm trung bình dưới ngưỡng |
| `--rules file.json` | Thay file rule check convert (đợt 4; mặc định tự tìm `rules/conversion_rules.json`) |
| `--llm` | Bật gate đánh giá AI qua Claude API cho lần chạy này (đợt 6; hoặc bật cố định bằng `"llm": {"enabled": true}` trong config.json) |

Exit code: `0` đạt · `1` lỗi input · `2` không đạt ngưỡng chất lượng.

## Trạng thái đánh giá

| Trạng thái | Ý nghĩa |
|-----------|---------|
| PASS 🟩 | Convert đúng (điểm ≥ 85, không tiêu chí nào fail) |
| WARNING 🟨 | Cần review tay (có cảnh báo hoặc điểm 60–85) |
| FAIL 🟥 | Nhiều khả năng convert sai (sai chữ ký / logic lệch lớn / điểm < 60) |
| MISSING ⬜ | Chỉ có ở VB (chưa convert / bị loại bỏ / đã chuyển sang frontend) |
| EXTRA 🟦 | Chỉ có ở C# (method viết mới — ghi nhận, không phải lỗi) |

Chi tiết tiêu chí chấm điểm (C1–C5): xem `documents/03_Backend_Migration_Check_Spec.md`.

## Khoan dung với thay đổi có chủ đích của kiến trúc mới (đợt 2 — theo documents/04)

- Khớp tên method qua hậu tố `Async` (`GetList` ↔ `GetListAsync`).
- `Boolean/Sub` → `Result` pattern: chỉ cảnh báo, không fail.
- `DELETE` vật lý → soft delete (`IsDeleted = true`): chỉ cảnh báo.
- `DataTable` → `List<DTO>` (tham số lẫn kiểu trả về, body đổi sang EF Core): chỉ cảnh báo.
- Code plumbing ADO.NET và chuỗi LINQ `_context...` được chuẩn hóa về token `db`
  ở cả 2 phía trước khi so logic (thay đổi tầng DB là có chủ đích).
- Method `Handle` / DTO / `Result` / Validator (thành phần mới của CQRS) được đánh dấu
  **EXTRA (kiến trúc mới)** — không tính là thừa code.

## Cải tiến đợt 3 (2026-07-10 — chi tiết: documents/03 mục 10)

1. **Mapping tên method thủ công** (`--map` / ô trên GUI) cho method bị đổi tên khi migrate.
2. **File cấu hình** `config.json` — trọng số, ngưỡng, danh sách khoan dung không cần sửa code.
3. **Ghép overload best-match** — chấm mọi tổ hợp, chọn cặp điểm cao nhất.
4. **C5 token-bag** — logic bị đảo thứ tự câu lệnh được nâng NG → WARN kèm ghi chú.
5. **Kiểm tra SQL** — SQL phía C# còn cú pháp Oracle (`NVL`, `ROWNUM`, `SYSDATE`, `DUAL`,
   `.NEXTVAL`, `DECODE`, join `(+)`) bị cảnh báo "sẽ lỗi trên PostgreSQL"; so tập bảng 2 bên.
6. **Xác nhận UI event qua `.razor`** — MISSING dạng `xxx_Click`/`xxx_Load` được tự tìm
   handler đích bên frontend và ghi chú xác nhận.
7. **Exit code cho CI** — `--fail-on`, `--min-score`.
8. **Theo dõi tiến độ giữa 2 lần scan** — `--json` + `--baseline`.
9. **GUI**: ô tìm kiếm method + tab "Code VB ⇄ C#" xem body 2 bên cạnh nhau.
10. **Bộ test tự động** `tests/` (34 test — bảng kỳ vọng documents/06 + unit test core).

## Rule-based check convert method (đợt 4 — chi tiết: documents/03 mục 11)

Tiêu chí nằm trong **`rules/conversion_rules.json`** (tool đọc để chạy, người review
đọc/sửa được — mỗi rule có giải thích vì sao nguy hiểm và cần kiểm tra gì bên C#):

- Bẫy ngữ nghĩa VB → C#: `CInt` (banker's rounding), chia nguyên `\`, `IIf` tính cả
  2 vế, `On Error` nuốt lỗi, `.Rows(0)` với bảng rỗng, `"" vs Nothing`, `And/Or`
  không short-circuit.
- Code smell bản mới: `.Result`/`.Wait()` (deadlock), `_ = XxxAsync()` (fire-and-forget).
- So 2 chiều một cặp method: **JP-MSG** (message tiếng Nhật của MessageBox/VB không thấy
  ở `Result.Failure`/C# → khả năng thiếu nhánh check, PASS bị nâng WARNING) ·
  **SELF-EXCL** (mất điều kiện `<>` loại trừ chính record khi check trùng) ·
  **VALIDATOR-SPLIT** (nhắc đối chiếu `*Validators.cs` khi C4/C5 lệch) ·
  **ROWNUM-ORDER** (`First/Take` không `OrderBy`).

Rule chỉ **thêm ghi chú "RULE ..."** để review tay, không trừ điểm C1–C5 (trừ JP-MSG
như trên). Tắt bằng config `"rules": {"enabled": false}` hoặc thay file bằng `--rules`.

## Gate đánh giá AI qua Claude API (đợt 6 — chi tiết: documents/03 mục 12)

Lớp đánh giá **thứ 3**, độc lập hoàn toàn — **không sửa điểm/status C1–C5**:

- AI đánh giá **tất cả** method, kể cả MISSING/EXTRA, theo nhận định tự do của model.
- **2 provider** (đợt 8), tự nhận diện theo dạng key trong config:
  key `sk-ant...` → **Anthropic Claude** (`claude-sonnet-5`, trả phí, cần
  `pip install anthropic`); key `AIza...` → **Google Gemini**
  (`gemini-2.5-flash`, **có free tier** — lấy key tại aistudio.google.com,
  gọi bằng stdlib nên không cần cài thêm gì). Ép provider bằng `llm.provider`.
- Kết quả ghi vào 2 cột mới trong sheet Detail: **"Nội dung AI đánh giá"** và
  **"Status AI đánh giá"** (PASS 🟩 / WARNING 🟨). API lỗi / mất mạng / thiếu key
  → ô ghi "AI chưa thực hiện đánh giá" (⬜), scan vẫn hoàn thành bình thường.
- Đợt 7 thêm cột **"Status DEV đánh giá"** (dropdown PASS/WARNING/FAIL/MISSING/EXTRA,
  tự tô màu) để **người review chấm tay kết luận cuối** — quy ước 3 cột:
  Status (máy) → Status AI (AI gợi ý) → Status DEV (người quyết định).

## Sheet mô tả chi tiết từng method (đợt 9 — chi tiết: documents/markdowns/03 mục 15)

Mỗi dòng sheet Detail có **sheet mô tả riêng** (`M001`, `M002`...) — click tên
method (chữ xanh) ở cột B để nhảy tới, có link quay lại đúng dòng:

- **Source VB** và **Source ASP.NET Core**: file nằm đâu (đường dẫn : dòng),
  chữ ký, **toàn bộ body code** — đánh giá bằng mắt không cần mở IDE.
- MISSING ghi rõ *"CHUA IMPLEMENT tren ASP.NET Core"*; EXTRA ghi rõ
  *"KHONG CO o source VB (method viết mới)"*.
- Mục **"METHOD LIEN QUAN TRUNG TEN"** liệt kê đầy đủ các bản trùng tên ở
  folder khác (trường hợp **1 method VB → nhiều method C#**), kèm hyperlink chéo.
- Tắt/tùy chỉnh: mục `"excel"` trong config.json (`method_sheets`, `max_body_lines`).
- **Cài đặt & token**: `pip install anthropic`, rồi điền `api_key` vào mục
  `"llm"` của `config.json` (hoặc set biến môi trường `ANTHROPIC_API_KEY`).
  Đổi token chỉ cần sửa `api_key` — **không commit config.json chứa key**.
  Lưu ý bản exe: exe đóng gói sẵn KHÔNG chứa package `anthropic` — muốn dùng AI
  trên exe phải build lại (`build_exe.bat`) trên máy đã `pip install anthropic`;
  chạy từ source thì chỉ cần pip install là xong.
- **Cache** `llm_cache.json` theo hash nội dung method — retest không gọi lại
  API, không tốn thêm token.
- Chạy: CLI thêm `--llm`; GUI tự chạy sau scan khi `llm.enabled=true`.

## Tài liệu dạng Excel (đợt 5)

- `rules/conversion_rules.xlsx` — bản Excel của bộ tiêu chí rule (sinh từ JSON;
  **JSON là nguồn sự thật**, tool đọc JSON khi chạy).
- `documents/11_Tool_Usage_Guideline.xlsx` — guideline sử dụng tool đầy đủ
  (6 sheet: TongQuan / QuyTrinh / TrangThai / GhiChu / CLI_CICD / FAQ).

Sau khi sửa `rules/conversion_rules.json` hoặc muốn tái sinh 2 file trên:

```bash
python tool/docs_exporter.py
```

## Kết quả retest trên bộ sample (đã chạy tự động)

Sample PCRS với `--map` — 51 dòng: **PASS 9, WARNING 10, FAIL 4, MISSING 7 (5 đã xác nhận
handler frontend), EXTRA 21 (16 thuộc kiến trúc mới), 17 method có ghi chú RULE**,
auto-detect đúng `PCRS.Application` — khớp 100% bảng kỳ vọng
`documents/markdowns/06_PCRS_Sample_Expectations.md`; toàn bộ **99 test** trong
`tests/` pass (đợt 6-9: AI review mock hoàn toàn, cột DEV, provider Gemini,
sheet mô tả method — không test nào gọi API thật).
Method của các đợt trước giữ nguyên status/score (không degrade); tắt `llm`
(mặc định) thì output CLI/JSON trùng khớp 100% baseline trước đợt 6.

## Hướng dẫn sử dụng GUI

Xem `documents/07_GUI_User_Guide.md` — bố cục màn hình, quy trình 5 bước, cách đọc
trạng thái/tiêu chí C1–C5, các cảnh báo "thay đổi có chủ đích" và FAQ.
