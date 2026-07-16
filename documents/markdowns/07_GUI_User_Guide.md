# Hướng dẫn sử dụng GUI — Migration Checker (VB.NET → ASP.NET Core, Backend)

> Đối tượng: người review chất lượng migration, không cần biết Python.
> Tool so sánh **mức method** giữa source VB.NET (hệ thống cũ) và source C#/ASP.NET Core
> (hệ thống mới), chấm điểm theo 5 tiêu chí C1–C5 và xuất báo cáo Excel.

---

## 1. Khởi động ứng dụng

| Cách | Thao tác |
|------|----------|
| **File exe (Windows — khuyên dùng)** | Double-click `dist\MigrationChecker.exe`. Không cần cài Python. Lần mở đầu chậm vài giây (giải nén nội bộ) — bình thường. |
| Từ source (Windows/macOS) | `python tool/main.py` (yêu cầu Python 3.10+ và `pip install openpyxl`) |

Nếu Windows SmartScreen cảnh báo (exe chưa ký số): chọn **More info → Run anyway**.

## 2. Bố cục màn hình

```
┌─────────────────────────────────────────────────────────────────────┐
│ Folder VB.NET (hệ thống cũ):        [________________] [Chọn...]   │  (1)
│ Folder ASP.NET Core (hệ thống mới): [________________] [Chọn...]   │  (2)
│ File mapping tên method (tùy chọn): [________________] [Chọn...]   │  (3)
│ Business Logic (tự phát hiện):      — hiển thị sau khi Scan —       │  (4)
├─────────────────────────────────────────────────────────────────────┤
│ [▶ Scan] [⬇ Export Excel]  Lọc trạng thái: [ALL ▼]  Tìm method: [ ] │  (5)(6)(7)
├─────────────────────────────────────────────────────────────────────┤
│ Method | Status | Score | Similarity | AI đánh giá | VB File | ... │  (8)
│  … bảng kết quả, mỗi dòng 1 method, tô màu theo trạng thái …        │
├─────────────────────────────────────────────────────────────────────┤
│ Chi tiết method:  [Tổng quan] [Code VB ⇄ C#]                        │  (9)
└─────────────────────────────────────────────────────────────────────┘
```

1. **Folder VB.NET** — folder gốc source hệ thống cũ.
2. **Folder ASP.NET Core** — folder gốc source hệ thống mới.
3. **File mapping tên method** (đợt 3 — tùy chọn) — file CSV/JSON khai báo các method
   bị **đổi tên** khi migrate, mỗi dòng `TenVB,TenCSharp`
   (xem file mẫu `samples/pcrs/method_mapping.csv`). Bỏ trống nếu không có method đổi tên.
   Đợt 11: method bị **tách thành nhiều method tên khác nhau** khai báo thêm cột:
   `TenVB,TenCSharpChinh,ManhTach1,ManhTach2...` — cột 2 để ghép cặp chấm điểm,
   các cột sau được đánh dấu "EXTRA (mảnh tách)" và gom vào mục liên quan của sheet mô tả.
4. **Business Logic (tự phát hiện)** — sau khi Scan, tool hiển thị thư mục Business Logic
   phía C# mà nó đã tự tìm ra và thực sự quét (xem mục 4).
5. **▶ Scan** — bắt đầu phân tích. **⬇ Export Excel** — xuất báo cáo (bật sau khi Scan xong).
6. **Lọc trạng thái** — chỉ hiện các dòng PASS / WARNING / FAIL / MISSING / EXTRA.
7. **Tìm method** (đợt 3) — gõ một phần tên method, bảng lọc ngay lập tức (kết hợp được
   với bộ lọc trạng thái).
8. **Bảng kết quả** — click 1 dòng để xem chi tiết ở panel (9). Cột **AI đánh giá**
   (đợt 6) hiển thị PASS/WARNING do Claude chấm khi bật AI trong config (mục 6.1);
   chưa bật thì hiển thị "-".
9. **Panel chi tiết** — 2 tab (đợt 3):
   - **Tổng quan**: chữ ký VB/C# (kèm file:dòng), kết quả từng tiêu chí, similarity,
     ghi chú; nếu có chạy AI thì thêm phần **"AI đánh giá [PASS/WARNING]"** kèm
     nội dung nhận định (đợt 6).
   - **Code VB ⇄ C#**: body method 2 hệ thống đặt cạnh nhau để đối chiếu bằng mắt
     không cần mở IDE; bên nào không tồn tại hiển thị "(không có)".

## 3. Quy trình chuẩn 5 bước

1. **Chọn folder VB.NET**: bấm *Chọn...* dòng (1), trỏ tới **folder gốc** chứa source
   hệ thống cũ (chứa các file `*.vb`). Business logic của VB nằm lẫn trong code-behind
   nên tool luôn quét toàn bộ `*.vb` trong folder này — cứ chọn thư mục gốc là đủ.
2. **Chọn folder ASP.NET Core**: bấm *Chọn...* dòng (2), trỏ tới **folder gốc của cả
   solution** (ví dụ folder chứa PCRS.Server / PCRS.Client / PCRS.Application...).
   **Không cần** tự trỏ vào project Application — tool tự tìm.
3. **Bấm ▶ Scan** và chờ (bảng kết quả hiện ra, dòng (3) hiển thị folder Business Logic
   đã phát hiện). Với source lớn có thể mất một lúc — GUI không bị treo.
4. **Review kết quả**: lọc theo trạng thái, ưu tiên xem **FAIL trước, WARNING sau**
   (xem mục 5). Click từng dòng để đọc ghi chú chi tiết.
5. **Bấm ⬇ Export Excel**, chọn nơi lưu file `.xlsx` để gửi team review — tên
   file mặc định đã kèm timestamp (`migration_report_YYYYMMDD_HHMMSS.xlsx`,
   đợt 9b) nên các lần export không ghi đè lên nhau.

**Thử ngay với bộ sample kèm theo:**
- Folder VB.NET: `samples\pcrs\legacy_vb`
- Folder ASP.NET Core: `samples\pcrs\new_aspcore`
- File mapping: `samples\pcrs\method_mapping.csv`
- Kết quả đúng (có mapping): 51 dòng — PASS 9, WARNING 10, FAIL 4, MISSING 7
  (5 đã xác nhận handler frontend), EXTRA 21 (16 kiến trúc mới), 17 method có ghi chú RULE;
  Business Logic phát hiện = `...\PCRS.Application`.
  Không chọn file mapping: 54 dòng — SearchProductByName, ArchiveOldOrders,
  CloseCustomerAccount thành MISSING + các bản C# tương ứng thành EXTRA.
  Xem ví dụ **1 method VB tách thành nhiều method C#**: click các dòng sau rồi mở
  sheet mô tả Mxxx để thấy mục "METHOD LIEN QUAN TRUNG TEN":
  - `TransferStock` (đợt 10) — tách 2 nơi **cùng tên** → không cần mapping;
  - `ArchiveOldOrders` (đợt 10) — tách + đổi tên PurgeOrders* → mapping 1 dòng thường;
  - `CloseCustomerAccount` (đợt 11) — **A chứa logic A1+A2 tách thành B (A1) +
    C (A2), tên khác hoàn toàn** → khai báo mapping **nhiều cột**
    `CloseCustomerAccount,DeactivateCustomer,CancelPendingOrders`; mảnh C hiện
    ghi chú "EXTRA (mảnh tách)" truy nguồn về method gốc.

## 4. Tính năng tự tìm thư mục Business Logic (phía C#)

Sau khi bấm Scan, tool tìm theo thứ tự ưu tiên:

1. Folder tên `*Application*` có folder con `Features/` (kiến trúc PCRS/CQRS — documents/04);
2. Folder tên `*Application*` chứa file `.cs`;
3. Folder tên `Features` / `BusinessLogic` / `Business_Logic`;
4. Không thấy → quét **toàn bộ** folder đã chọn.

Kết quả hiển thị ở dòng (3), ví dụ:
`D:\src\PCRS\PCRS.Application   [kien truc PCRS/CQRS (*Application* chua Features/)]`

Nghĩa là các project khác (Server / Client / Domain / Infrastructure) **không bị quét** —
đúng chủ trương chỉ đánh giá Business Logic backend. Nếu dòng (3) chỉ ra sai thư mục
mong muốn, hãy chọn lại folder (2) trỏ thẳng vào thư mục bạn muốn quét (khi đó rule 4
sẽ quét đúng toàn bộ thư mục đó).

## 5. Cách đọc kết quả

### 5.1. Trạng thái và hướng xử lý

| Trạng thái | Màu | Ý nghĩa | Việc cần làm |
|-----------|-----|---------|--------------|
| PASS | 🟩 Xanh lá | Convert đúng (điểm ≥ 85, không tiêu chí nào fail) | Không cần làm gì |
| WARNING | 🟨 Vàng | Có thay đổi cần xác nhận (điểm 60–85 hoặc có cảnh báo) | Đọc Notes, review tay để xác nhận thay đổi là có chủ đích |
| FAIL | 🟥 Đỏ | Nhiều khả năng convert sai (sai chữ ký, logic lệch lớn, điểm < 60) | **Bắt buộc kiểm tra** — đối chiếu code 2 bên tại file:dòng trong panel chi tiết |
| MISSING | ⬜ Xám | Chỉ có ở VB — chưa convert / bị loại / đã chuyển sang frontend | Xác nhận lý do; nếu có ghi chú *"UI event"* thì thường đã chuyển hợp lệ sang `.razor` |
| EXTRA | 🟦 Xanh dương | Chỉ có ở C# — method viết mới | Ghi nhận. Nếu note là **"EXTRA (kiến trúc mới)"** (Handler/DTO/Result/Validator) thì bỏ qua — không phải thừa code |

### 5.2. Tiêu chí C1–C5 (trong panel chi tiết và Excel)

| Mã | Kiểm tra | Trọng số |
|----|----------|:--:|
| C1 | Method tồn tại ở cả 2 bên (khớp tên không phân biệt hoa thường, chấp nhận hậu tố `Async`) | 30 |
| C2 | Số lượng + kiểu tham số (theo bảng mapping VB→C#) | 20 |
| C3 | Kiểu trả về (`Sub`↔`void/Task`, `Function As X`↔`X/Task<X>`) | 15 |
| C4 | Cấu trúc điều khiển (số if / vòng lặp / try / return / throw) | 15 |
| C5 | Độ tương đồng logic sau chuẩn hóa token (Similarity: ≥0.75 tốt, 0.5–0.75 cảnh báo, <0.5 fail) | 20 |

Nhãn từng tiêu chí: **OK** đạt · **WARN** cảnh báo · **NG** fail · **-** không áp dụng.

### 5.3. Các cảnh báo là "thay đổi có chủ đích" — không phải lỗi convert

Gặp các ghi chú sau thì chỉ cần xác nhận nhanh, không phải bug:

- *"khop ten qua hau to Async"* — `GetList` ↔ `GetListAsync` (quy ước async C#).
- *"khop qua bang mapping"* (đợt 3) — method đổi tên đã được khai báo trong file mapping.
- *"Result pattern"* — `Boolean/Sub` → `Result` (lỗi nghiệp vụ trả `Result.Failure`, message tiếng Nhật).
- *"soft delete IsDeleted=true"* — DELETE vật lý → xóa mềm.
- *"DataTable -> List<...>"* — bỏ ADO.NET sang EF Core/DTO.
- *"da tim thay handler ... trong ....razor (frontend)"* (đợt 3) — UI event MISSING đã
  xác nhận có điểm đến bên frontend, thường không cần xử lý thêm.
- *"cung tap token nhung khac thu tu cau lenh"* (đợt 3) — logic dùng cùng tập lệnh nhưng
  bị đảo cấu trúc; review nhanh xem có chủ đích không.
- *"EXTRA (kien truc moi)"* — Handler/DTO/Result/Validator, thành phần mới của CQRS.

Riêng ghi chú **"SQL: con cu phap Oracle (...)"** (đợt 3) là **lỗi thật** cần sửa:
SQL phía C# còn `NVL` / `ROWNUM` / `SYSDATE` / `DUAL` / `.NEXTVAL` / join `(+)`
sẽ lỗi runtime trên PostgreSQL — tool ép status tối thiểu WARNING.

### 5.4. Ghi chú "RULE ..." — điểm cần review tay (đợt 4)

Ghi chú bắt đầu bằng `RULE <mã>:` đến từ file tiêu chí **`rules/conversion_rules.json`**
(đặt cạnh exe — mở bằng Notepad để đọc giải thích + cách xử lý từng rule, sửa được
không cần build lại tool). Rule **không trừ điểm** — nó đánh dấu chỗ code VB dùng đặc
tính ngầm của ngôn ngữ (ví dụ `CInt` làm tròn kiểu banker's rounding, `\` chia nguyên,
`IIf` tính cả 2 vế) hoặc chỗ bản C# có dấu hiệu nghi vấn (mất điều kiện loại trừ chính
record, `First` không `OrderBy`, `.Result`/`.Wait()`).

Hai rule đặc biệt:
- **RULE JP-MSG** — message tiếng Nhật có bên VB nhưng biến mất bên C#: khả năng
  **thiếu cả nhánh check nghiệp vụ** (hoặc quên `return` sau `Result.Failure`).
  Đây là nghi vấn lỗi thật nên PASS bị nâng lên WARNING.
- **RULE VALIDATOR-SPLIT** — C4/C5 lệch nhưng cùng thư mục có `*Validators.cs`:
  một phần check có thể đã tách sang FluentValidation theo kiến trúc mới —
  **đối chiếu file Validator trước khi kết luận thiếu logic**.

Method PASS vẫn có thể mang ghi chú RULE (ví dụ sample `CalcRoundedPrice`) — nghĩa là
"convert khớp về cấu trúc, nhưng có điểm ngầm về ngữ nghĩa cần con người xác nhận".

## 6. File Excel xuất ra

- **Sheet `Summary`**: thời gian scan, 2 folder đã chọn, **folder Business Logic đã quét**,
  số file mỗi bên, đếm theo trạng thái (kèm số EXTRA thuộc kiến trúc mới), tỷ lệ PASS,
  điểm trung bình; đợt 3 thêm dòng file mapping (nếu dùng) và số MISSING đã xác nhận
  có handler frontend; đợt 6 thêm dòng thống kê AI (khi có chạy AI).
- **Sheet `Detail`**: mỗi dòng 1 method — file + chữ ký 2 bên, C1–C5, Similarity, Score,
  Status (tô màu), Notes, và 3 cột review bổ sung:

| Cột | Ai ghi | Nội dung |
|-----|--------|----------|
| **Nội dung AI đánh giá** (P, đợt 6) | Claude API | Nhận định của AI về chất lượng convert (tiếng Việt) |
| **Status AI đánh giá** (Q, đợt 6) | Claude API | PASS 🟩 / WARNING 🟨; API lỗi/chưa bật → "AI chưa thực hiện đánh giá" ⬜ |
| **Status DEV đánh giá** (R, đợt 7) | **Người review** | Ô trống có **dropdown** — click ô, chọn PASS/WARNING/FAIL/MISSING/EXTRA theo kết luận cuối cùng của bạn; ô tự tô màu theo giá trị chọn. Tool/AI không đụng vào cột này |

  Có sẵn auto-filter để lọc theo mọi cột (Status, Status AI, Status DEV...).
  Quy ước dùng 3 cột: **Status** = máy chấm tự động, **Status AI** = AI gợi ý,
  **Status DEV** = phán quyết cuối của người review (điền tay trong Excel sau khi
  đối chiếu 2 cột kia).
- **Sheet mô tả từng method `M001`, `M002`...** (đợt 9): **click tên method
  (chữ xanh, cột B) ở sheet Detail** để nhảy sang sheet mô tả riêng của dòng đó —
  gồm source VB và source ASP Core (file nằm đâu, chữ ký, **toàn bộ body code**)
  đặt trong cùng một sheet để đánh giá bằng mắt không cần mở IDE; MISSING ghi rõ
  "CHUA IMPLEMENT", EXTRA ghi rõ "KHONG CO o source VB"; mục "METHOD LIEN QUAN
  TRUNG TEN" liệt kê đầy đủ các bản C# trùng tên ở folder khác (trường hợp 1 VB
  → nhiều C#). Đầu mỗi sheet có link "← Quay lại sheet Detail". Tắt tính năng:
  `"excel": {"method_sheets": false}` trong config.json.

### 6.1. Bật đánh giá AI (đợt 6/8 — tùy chọn)

1. Copy `config.sample.json` thành `config.json` đặt cạnh exe (hoặc gốc repo).
2. Trong mục `"llm"`: đặt `"enabled": true` và dán token vào `"api_key"`.
   Tool tự nhận diện loại token (đợt 8):
   - Token `AIza...` — **Google Gemini, CÓ FREE TIER**: lấy tại
     **aistudio.google.com** → Get API key → chọn project **không gắn billing**.
     Không cần cài thêm gì. Free tier giới hạn số request/phút nên scan bộ lớn
     sẽ chậm hơn (tool tự chờ và gọi lại).
   - Token `sk-ant...` — **Anthropic Claude, trả phí**: lấy tại
     platform.claude.com → API Keys (cần nạp credit ở Billing; gói Claude Pro
     KHÔNG dùng được cho API). Chạy từ source cần `pip install anthropic`;
     bản exe cần build lại trên máy đã cài package này.
3. Scan lại — GUI hiện "Đang chấm AI..." rồi điền cột AI. Kết quả được **cache**
   theo nội dung method (`llm_cache.json`) nên scan lại không tốn thêm phí/quota.
4. Đổi token: chỉ cần sửa `api_key` trong `config.json` rồi lưu.

**Không chia sẻ `config.json` sau khi đã dán token.**

File mẫu: `samples\migration_report_pcrs.xlsx`.

## 7. Lỗi thường gặp & FAQ

| Tình huống | Nguyên nhân / cách xử lý |
|-----------|--------------------------|
| Thông báo *"Folder VB.NET / ASP.NET Core không hợp lệ"* | Đường dẫn không tồn tại hoặc chưa chọn. Chọn lại bằng nút *Chọn...* |
| Scan xong 0 method phía C# | Folder chọn không chứa `.cs`, hoặc Business Logic phát hiện sai — xem dòng (3) và mục 4 |
| Method chắc chắn đã convert nhưng báo MISSING + xuất hiện EXTRA cùng nghĩa | Method bị **đổi tên** khi convert (khác hơn là thêm `Async`). Khai báo cặp tên vào **file mapping** (dòng (3), định dạng `TenVB,TenCSharp`) rồi Scan lại — tool sẽ ghép đúng cặp (đợt 3) |
| Muốn đổi trọng số C1–C5 / ngưỡng điểm / danh sách khoan dung | Copy `config.sample.json` thành `config.json` đặt cạnh `MigrationChecker.exe` (hoặc gốc repo khi chạy source), sửa giá trị rồi Scan lại — tool tự đọc (đợt 3) |
| Nhiều dòng MISSING tên dạng `xxx_Click`, `xxx_Load` | UI event của WinForms — thường đã chuyển hợp lệ sang `.razor` (frontend), có ghi chú kèm theo |
| Rất nhiều dòng EXTRA tên `Handle` | MediatR Handler của CQRS — đã được đánh dấu "kiến trúc mới", không phải lỗi |
| Nút Export Excel bị mờ | Chưa Scan hoặc Scan lỗi — Scan thành công thì nút mới bật |
| Kết quả PASS nhưng vẫn nghi ngờ | Tool dùng parser heuristic (không phải compiler) — PASS nghĩa là "khớp về chữ ký + cấu trúc + logic bề mặt". Nghiệp vụ quan trọng vẫn nên có test |
| Cột AI ghi "AI chưa thực hiện đánh giá" | Chưa bật `llm.enabled`, chưa dán token, chưa cài `pip install anthropic`, mất mạng, hoặc API lỗi — đọc lý do ở cột "Nội dung AI đánh giá". Scan vẫn hoàn thành bình thường (đợt 6) |
| Muốn AI chấm lại 1 method sau khi model trả kết quả lạ | Xóa file `llm_cache.json` (cạnh exe/gốc repo) rồi Scan lại — mất cache thì các method khác cũng gọi lại API (tốn token), nên chỉ xóa khi thật cần |
| Chọn nhầm giá trị ở cột "Status DEV đánh giá" | Chọn lại từ dropdown hoặc nhấn Delete để xóa trống — cột này chỉ do người review quản lý (đợt 7) |

## 8. Giới hạn hiện tại (sau đợt 7)

- Backend vẫn là trọng tâm; frontend `.razor` mới dừng ở mức **xác nhận UI event có
  handler đích** (không chấm điểm nội dung); SQL mới kiểm tra **cú pháp Oracle còn sót
  + tập bảng truy cập**, chưa so sánh ngữ nghĩa WHERE/JOIN.
- Parser regex/heuristic: generic phức tạp, partial method, code sinh tự động có thể cần review tay.
- Ghi chú RULE là heuristic "điểm cần review", không khẳng định bug; chưa phát hiện
  method bị tách/gộp (1 VB → nhiều C#).
- So sánh 2 lần scan (`--json` / `--baseline`) hiện chỉ có ở CLI, chưa có trên GUI.
- Kết quả AI (đợt 6) là nhận định của LLM — không tất định, chỉ mang tính gợi ý;
  phán quyết cuối cùng thuộc về người review (ghi vào cột "Status DEV đánh giá").
- Cột "Status DEV đánh giá" chỉ tồn tại trong file Excel — tool không đọc lại
  giá trị DEV đã chọn ở lần scan sau (mỗi lần export là file mới).

---

*Tài liệu liên quan: đặc tả tiêu chí `03_Backend_Migration_Check_Spec.md` ·
kiến trúc mapping PCRS `04_Study_Conversion_Mapping_Architecture.md` ·
bảng kỳ vọng bộ sample `06_PCRS_Sample_Expectations.md`.*
