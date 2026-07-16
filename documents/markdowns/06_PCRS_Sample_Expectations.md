# Bảng kỳ vọng kết quả — bộ sample PCRS (samples/pcrs/)

> Bảng kỳ vọng viết TRƯỚC khi chạy tool, cập nhật qua các đợt (lịch sử thay đổi từng
> đợt: documents/03 mục 9/10/11). Bảng này đã được mã hóa thành test tự động:
> `python -m unittest discover tests`.
> Lệnh retest: `python tool/cli.py samples/pcrs/legacy_vb samples/pcrs/new_aspcore --map samples/pcrs/method_mapping.csv --out samples/migration_report_pcrs.xlsx --json samples/migration_report_pcrs.json`
> Kỳ vọng auto-detect: folder Business Logic phía C# = `PCRS.Application` (theo rule `*Application*` chứa `Features/`).
> Các project PCRS.Server / PCRS.Domain / PCRS.Infrastructure KHÔNG được quét
> (riêng file `.razor` trong PCRS.Server được index để xác nhận UI event — đợt 3).

## Method phía VB (29 — thêm 2 sample đợt 3, 3 sample đợt 4, 2 sample đợt 10)

| # | Method (VB) | Case cố ý | Kỳ vọng | Lý do chính |
|---|-------------|-----------|---------|-------------|
| 1 | CustomerMaster_Load | UI event không convert | MISSING | Note "UI event — có thể đã chuyển sang .razor" |
| 2 | F8_Click | UI event không convert | MISSING | Note UI event |
| 3 | CheckDuplicateCustomer | Convert đúng (khớp qua hậu tố Async) | PASS | C1–C5 OK; note khớp Async |
| 4 | CheckExistCustomer | Convert đúng | PASS | C1–C5 OK |
| 5 | GetCustomerList | DataTable → List\<Dto\> | WARNING | C3 WARN (chấp nhận, cần review) |
| 6 | RegisterCustomer | Boolean → Result pattern | WARNING | C3 WARN (Result pattern) + C5 review |
| 7 | UpdateCustomer | Sai kiểu tham số String → int | FAIL | C2 NG |
| 8 | DeleteCustomer | DELETE vật lý → soft delete | WARNING | C5 nâng NG→WARN nhờ khoan dung soft delete |
| 9 | GetCustomerName | Quên chưa convert | MISSING | Không có note UI event |
| 10 | OrderEntry_Load | UI event | MISSING | Note UI event |
| 11 | txtQuantity_TextChanged | UI event | MISSING | Note UI event |
| 12 | CalcOrderAmount | Convert đúng (logic thuần) | PASS | Similarity ~1.0 |
| 13 | CalcTax | Sai kiểu trả về Decimal → int | FAIL | C3 NG |
| 14 | CheckOrderLimit | Convert đúng (NVL → ??) | PASS | C1–C5 OK |
| 15 | RegisterOrder | DataTable param → List\<Dto\>, Result pattern | WARNING | C2 WARN + C3 WARN |
| 16 | CancelOrder | Thiếu tham số reason | FAIL | C2 NG (lệch số lượng) |
| 17 | GetOrderList | DataTable → List\<Dto\>, ROWNUM → Take | WARNING | C3 WARN |
| 18 | PrintOrderReport | Report → FastReport .frx | MISSING | Không note UI event |
| 19 | ProductStock_Load | UI event | MISSING | Note UI event |
| 20 | GetStockQuantity | Convert đúng | PASS | C1–C5 OK |
| 21 | UpdateStock | Logic bị viết lại khác hẳn | FAIL | C5 NG (similarity < 0.5, token-bag cũng thấp) |
| 22 | CheckStockShortage | Convert đúng | PASS | C1–C5 OK |
| 23 | SearchProductByName | **Đổi tên** thành FindProductsAsync (đợt 3, task 1) | MISSING (không --map) / **PASS** (có --map) | Cần khai báo trong method_mapping.csv |
| 24 | GetMonthlySales | Raw SQL C# còn **NVL + SYSDATE** (đợt 3, task 5) | WARNING | Note "SQL: còn cú pháp Oracle (NVL(, SYSDATE)" |
| 25 | CalcRoundedPrice | `CInt` + chia nguyên `\` (đợt 4) | PASS | Note **RULE VB-CINT, VB-INTDIV** — PASS vẫn cần review điểm ngầm |
| 26 | CheckDuplicateProductName | C# quên `!=` loại trừ chính record (đợt 4) | PASS | Note **RULE SELF-EXCL** (+ VB-CINT) |
| 27 | ApplyMemberDiscount | C# thiếu nhánh check memberRank (đợt 4) | WARNING | Note **RULE JP-MSG** chỉ đích message '会員ランクが不正です。' bị mất |
| 28 | TransferStock | **1 VB tách thành 2 C# CÙNG TÊN ở 2 folder** (đợt 10): TransferStockAsync (Features/ProductStock — chuyển kho) + TransferStock (Services/StockAuditService — ghi log) | WARNING | Ghép cặp với TransferStockAsync (C3 Result pattern + C5 ~0.62); bản ghi log thành EXTRA cùng tên → sheet Mxxx liệt kê ở "METHOD LIEN QUAN TRUNG TEN". **Không cần mapping** vì trùng tên |
| 29 | ArchiveOldOrders | **1 VB vừa ĐỔI TÊN vừa tách thành 2 C#** (đợt 10): PurgeOrdersAsync (Features/OrderEntry) + PurgeOrders (Services/OrderBatchService) | MISSING (không `--map`) / **WARNING** (có `--map`) | Đổi tên → **PHẢI khai báo `ArchiveOldOrders,PurgeOrders` trong method_mapping.csv**; có map thì ghép PurgeOrdersAsync (C4/C5 lệch nhẹ + note VALIDATOR-SPLIT), bản batch PurgeOrders vẫn là EXTRA cùng khóa tên |
| 30 | CloseCustomerAccount | **A chứa logic A1+A2 → TÁCH thành B (A1) + C (A2), TÊN KHÁC HOÀN TOÀN** (đợt 11): DeactivateCustomerAsync (Features/CustomerMaster — A1 vô hiệu hóa khách) + CancelPendingOrdersAsync (Features/OrderEntry — A2 hủy đơn chờ) | MISSING (không `--map`) / **WARNING** (có `--map`) | Khai báo mapping **1-n**: `CloseCustomerAccount,DeactivateCustomer,CancelPendingOrders` — ghép cặp với B (sim ~0.64), C thành **EXTRA (mảnh tách)** có note truy nguồn; cả nhóm gom vào mục "METHOD LIEN QUAN" của sheet mô tả |

**Tổng kỳ vọng phía VB (không `--map`): PASS 8 · WARNING 8 · FAIL 4 · MISSING 10.**
**Có `--map`: PASS 9 · WARNING 10 · FAIL 4 · MISSING 7.**

5 MISSING là UI event (`CustomerMaster_Load`, `F8_Click`, `OrderEntry_Load`,
`txtQuantity_TextChanged`, `ProductStock_Load`) phải có note **"đã tìm thấy
handler/OnInitializedAsync trong ...razor (frontend)"** nhờ 3 file razor sample trong
`PCRS.Server/Pages/` (đợt 3, task 6); dòng "đã xác nhận handler frontend: 5" xuất hiện
ở summary. `GetCustomerName` và `PrintOrderReport` vẫn là MISSING không có note frontend.

## Method chỉ có phía C# (EXTRA)

| Method (C#) | File | Kỳ vọng |
|-------------|------|---------|
| Handle × 13 | Features/*/Commands.cs, Queries.cs (kèm StockTransfer/OrderArchive đợt 10, CustomerDeactivation/OrderCancellation đợt 11) | EXTRA (kiến trúc mới — MediatR Handler, không phải lỗi) |
| Success, Failure | Common/Models/Result.cs | EXTRA (kiến trúc mới — Result pattern) |
| HasValidCustomerCodeFormat | CustomerMasterValidators.cs | EXTRA (kiến trúc mới — Validator helper) |
| ExportStockCsv(Async) | ProductStockQueries.cs | EXTRA thường (method nghiệp vụ viết mới, ghi nhận) |
| FindProducts(Async) | ProductStockQueries.cs | EXTRA thường khi không `--map`; biến mất khi có `--map` (ghép với SearchProductByName) |
| ApplyDiscountToOrderAsync | OrderEntryCommands.cs | EXTRA thường (helper mới — đợt 4) |
| TransferStock | Services/StockAuditService.cs (đợt 10) | EXTRA thường — mảnh ghi log tách từ VB TransferStock, **cùng tên** với cặp chính → liệt kê chéo trong sheet mô tả |
| PurgeOrders(Async) | Features/OrderEntry/OrderArchiveCommands.cs + Services/OrderBatchService.cs (đợt 10) | Không `--map`: cả 2 là EXTRA; có `--map`: PurgeOrdersAsync ghép với ArchiveOldOrders, PurgeOrders (batch) vẫn EXTRA |
| DeactivateCustomerAsync | Features/CustomerMaster/CustomerDeactivationCommands.cs (đợt 11) | Không `--map`: EXTRA; có `--map`: ghép với CloseCustomerAccount (cặp chính) |
| CancelPendingOrdersAsync | Features/OrderEntry/OrderCancellationCommands.cs (đợt 11) | EXTRA; có `--map` mang note **"EXTRA (mảnh tách): phần logic tách ra từ method VB 'CloseCustomerAccount'"** |

**Tổng kỳ vọng EXTRA: 24 (không `--map`) / 21 (có `--map`), trong đó 16 thuộc kiến trúc mới.**
**Tổng số dòng so sánh: 54 (không `--map`) / 51 (có `--map`).**

## Rule-based check (đợt 4 — rules/conversion_rules.json)

- Tổng **14 method có ghi chú RULE** (không `--map`; có `--map` là 17 vì
  SearchProductByName thành cặp mang note VB-CINT + VB-EMPTYSTR, ArchiveOldOrders
  thành cặp mang note VALIDATOR-SPLIT — đợt 10, và CloseCustomerAccount thành cặp
  mang note VALIDATOR-SPLIT — đợt 11): VB-CINT ở CheckDuplicateCustomer /
  CheckExistCustomer / GetStockQuantity / CalcRoundedPrice / CheckDuplicateProductName;
  VALIDATOR-SPLIT ở các method C4/C5 lệch trong CustomerMaster & OrderEntry (2 folder này
  có *Validators.cs); JP-MSG ở UpdateStock (×2 message) và ApplyMemberDiscount.
- Rule chỉ thêm note, không đổi status — trừ JP-MSG được nâng PASS → WARNING
  (bộ sample hiện không có method PASS nào dính nên status giữ nguyên toàn bộ).
- Tắt rule (`"rules": {"enabled": false}`) phải cho kết quả status y hệt.

## Kiểm chứng khác

- File Excel xuất ra phải có 2 sheet Summary + Detail, Summary có dòng "Folder Business Logic (C#)",
  dòng đếm EXTRA thuộc kiến trúc mới, dòng "File mapping tên method" (khi dùng `--map`) và
  dòng "MISSING là UI event đã xác nhận có handler frontend".
- CLI exit code: `--fail-on FAIL` → 2 (sample có 4 FAIL); `--min-score 80` → 0; `--min-score 95` → 2;
  `--map`/`--config`/`--baseline` trỏ file không tồn tại → 1.
- `--json` xuất JSON; `--baseline` in bảng tốt lên/xấu đi/mới/biến mất.
