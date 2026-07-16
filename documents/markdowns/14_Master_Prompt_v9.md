# Master Prompt v9 — Đợt 9: Sheet mô tả chi tiết từng method trong báo cáo Excel

Người review muốn **nhìn bằng mắt** để đánh giá từng method mà không phải mở IDE:
mỗi dòng trong sheet Detail phải **reference (hyperlink) sang một sheet riêng**
mô tả đầy đủ method đó — source VB nằm file nào, sang ASP Core thành (những)
method nào ở (những) file nào, kèm **toàn bộ logic (body code)** của cả 2 bên.

## Yêu cầu đã chốt với user (2026-07-16)

1. Mỗi row sheet Detail → 1 sheet mô tả riêng, click từ Detail nhảy thẳng sang.
2. Sheet mô tả gồm: **Source VB** (đường dẫn file, chữ ký, body đầy đủ) và
   **Source ASP** (đường dẫn file, chữ ký, body đầy đủ) — người dùng đọc trực
   tiếp trên Excel để tự đánh giá.
3. **Cover đầy đủ mọi trường hợp**:
   - Cặp 1-1 bình thường (PASS/WARNING/FAIL).
   - **1 method VB → nhiều method ASP Core ở nhiều folder khác nhau**
     (overload/trùng tên): phải liệt kê đầy đủ tất cả method liên quan.
   - Có ở VB nhưng **chưa implement** trên ASP Core (MISSING).
   - Có trên ASP Core nhưng **không có ở VB** (EXTRA — method viết mới).
4. Không degrade tính năng đã có; retest sau khi xong; rà soát lại một lượt cuối.

## Thiết kế

### Sheet mô tả (đặt tên `M001`, `M002`, ... theo số thứ tự dòng Detail)

- Tên sheet ngắn + duy nhất (tránh giới hạn 31 ký tự và ký tự cấm của Excel);
  tiêu đề trong sheet hiển thị tên method đầy đủ + status (tô màu như Detail).
- Link **2 chiều**: ô "Method" (cột B) ở Detail là hyperlink nhảy tới sheet
  `Mxxx`; đầu sheet `Mxxx` có link "← Quay lại Detail" nhảy về đúng dòng.
- Bố cục mỗi sheet:
  1. Tiêu đề: `Mxxx — <tên method>  [STATUS]`, dòng link quay lại.
  2. Bảng tóm tắt: Status / Score / Similarity / khớp qua mapping (nếu có) /
     AI đánh giá (nếu đã chấm) / toàn bộ Notes của tool.
  3. **SOURCE VB (hệ thống cũ)**: `File: <đường dẫn> : dòng N` + chữ ký +
     body nguyên văn (font Consolas, mỗi dòng code một dòng Excel, nền xám nhạt).
  4. **SOURCE ASP.NET CORE (hệ thống mới)**: tương tự cho method C# đã ghép cặp.
  5. **METHOD LIÊN QUAN TRÙNG TÊN**: bảng liệt kê mọi dòng Detail khác có cùng
     khóa tên (bỏ hậu tố Async, tính cả tên 2 phía để cover method đổi tên qua
     mapping) — mỗi dòng: sheet đích (hyperlink), tên, phía có mặt, file, status.
     Đây là chỗ thể hiện "1 VB → nhiều C# ở nhiều folder": các bản C# trùng tên
     chưa ghép cặp là dòng EXTRA riêng, có sheet riêng, và được liệt kê ở đây.

### Ma trận trường hợp phải xử lý

| # | Trường hợp | Nội dung sheet |
|---|-----------|----------------|
| 1 | Cặp 1-1 đủ 2 bên | Mục VB + mục ASP đầy đủ file/chữ ký/body |
| 2 | 1 VB ↔ nhiều C# trùng tên (nhiều folder) | Cặp chính như (1); các C# còn lại là dòng EXTRA có sheet riêng; mục "liên quan" liệt kê chéo đầy đủ cả 2 chiều |
| 3 | Nhiều VB overload ↔ nhiều C# | Mỗi cặp một sheet; mục "liên quan" liệt kê nhau |
| 4 | MISSING (VB có, ASP chưa implement) | Mục VB đầy đủ; mục ASP ghi rõ **"CHƯA IMPLEMENT trên ASP.NET Core"** + ghi chú (UI event đã có handler .razor thì nêu rõ) |
| 5 | EXTRA (ASP có, VB không có) | Mục ASP đầy đủ; mục VB ghi rõ **"KHÔNG CÓ ở source VB (method viết mới)"** + ghi chú kiến trúc mới nếu có |
| 6 | Method đổi tên (khớp qua mapping) | Tiêu đề + mục liên quan dùng cả 2 tên; note mapping hiển thị trong tóm tắt |
| 7 | Khớp qua hậu tố Async | Như (6) — khóa liên quan đã bỏ hậu tố Async |
| 8 | Body rỗng / parser không lấy được body | In "(body rỗng)" thay vì bỏ trống |
| 9 | Body rất dài | Cắt ở `max_body_lines` (mặc định 400 dòng/side) kèm dòng "... (còn N dòng — xem file gốc)" |
| 10 | Tên method trùng nhau nhiều dòng | Tên sheet theo số thứ tự (M007, M012...) nên không bao giờ đụng độ |

### Cấu hình (`config.sample.json` — mục mới `"excel"`)

```json
"excel": { "method_sheets": true, "max_body_lines": 400 }
```

- `method_sheets: false` → tắt hẳn (báo cáo như đợt 8 — escape hatch cho hệ
  thống cực lớn, tránh file xlsx phình to).
- Mặc định bật vì đây là tính năng chính của đợt.

### Ràng buộc không-degrade

- Sheet Summary/Detail giữ **nguyên vị trí cột** (A→R) — chỉ thêm hyperlink vào
  ô Method (cột B) + 1 dòng giải thích trong Summary; auto-filter, dropdown DEV,
  2 cột AI, màu sắc giữ nguyên.
- CLI stdout không đổi → baseline diff phải = 0.
- `export_excel(result, out_path)` giữ nguyên chữ ký — GUI/CLI không phải sửa.
- Toàn bộ test hiện có (89) phải pass nguyên vẹn.

## Test bắt buộc (tests/test_llm.py hoặc file test mới)

1. Xuất result 3 dòng (pair + MISSING + EXTRA) → có đúng sheet Summary, Detail,
   M001..M003; ô B của Detail có hyperlink trỏ đúng sheet.
2. Sheet M của cặp: chứa đường dẫn file VB, file C#, chữ ký và body cả 2 bên.
3. Sheet MISSING: chứa "CHUA IMPLEMENT"; sheet EXTRA: chứa "KHONG CO o source VB".
4. Trường hợp 1 VB + 2 C# trùng tên (1 cặp + 1 EXTRA): sheet cặp liệt kê EXTRA
   ở mục liên quan (kèm hyperlink) và ngược lại.
5. Body dài hơn max_body_lines → bị cắt kèm ghi chú.
6. `method_sheets: false` → chỉ còn 2 sheet như cũ.
7. Toàn bộ suite cũ pass; CLI baseline (llm tắt) diff = 0.

## Trình tự thực hiện

1. Thêm `"excel"` vào DEFAULTS + config.sample.json + accessor.
2. Viết phần sinh sheet mô tả trong `tool/core/excel_exporter.py`
   (hyperlink 2 chiều, code block, related listing).
3. Test mới + chạy toàn bộ suite + baseline CLI.
4. Tái sinh sample report + guideline xlsx; cập nhật documents/03 (mục 15),
   07 (mục 6), 12, README; cập nhật memory.
5. Rà soát lại một lượt: mở file xlsx thật kiểm tra hyperlink/sheet bằng script.
