# Master Prompt v5 — Đợt 5: Hoàn thiện đợt 4 + dọn tài liệu + xuất Excel (rules & guideline)

> Viết TRƯỚC khi thực thi. Quy trình mỗi task: thực hiện → tự rà soát (checklist ở mục
> tương ứng) → mới chuyển task kế. Đây là prompt MỚI NHẤT — các prompt cũ (00, 05, 08, 09)
> bị xóa theo yêu cầu user; nội dung đặc tả của từng đợt đã được chốt trong
> documents/03 (mục 9 = đợt 2, mục 10 = đợt 3, mục 11 = đợt 4) nên không mất thông tin.

## Task 1 — Hoàn thành phần còn dở của đợt 4

1. Generate lại report: `python tool/cli.py samples/pcrs/legacy_vb samples/pcrs/new_aspcore
   --map samples/pcrs/method_mapping.csv --out samples/migration_report_pcrs.xlsx
   --json samples/migration_report_pcrs.json` (ghi đè file cũ).
2. Build lại exe bằng lệnh trong build_exe.bat (đã thêm `--add-data rules\conversion_rules.json`),
   smoke test exe mở được rồi đóng.
3. Cập nhật memory dự án (đợt 4 + các thay đổi đợt 5).

**Rà soát**: Excel Summary có dòng "Method co ghi chu RULE"; exe chạy; 54 test pass.

## Task 2 — Dọn documents: chỉ giữ version mới nhất

1. Xóa: `00_Master_Prompt.md`, `05_Master_Prompt_v2.md`, `08_Master_Prompt_v3.md`,
   `09_Master_Prompt_v4.md` (prompt cũ — bản mới nhất là file này).
   Giữ nguyên số thứ tự các file còn lại (01/02/03/04/06/07) — không renumber để khỏi
   gãy tham chiếu trong code/git/memory.
2. Quét toàn bộ tham chiếu tới file đã xóa trong: README.md, documents/*.md,
   tool/**/*.py (docstring/comment), rules/conversion_rules.json, tests/ —
   đổi về đích còn tồn tại (documents/03 mục 9/10/11) hoặc bỏ.
3. Rà nội dung markdown khớp source code hiện tại: con số thống kê sample
   (42/41 dòng, PASS 8/9...), tên tham số CLI, tên module trong README, mô tả GUI
   (documents/07), bảng kỳ vọng (documents/06).

**Rà soát**: `grep -r "documents/00\|documents/05\|documents/08\|documents/09\|Master_Prompt_v2\|Master_Prompt_v3\|Master_Prompt_v4"`
không còn kết quả (ngoài file này); grep các con số cũ (35 dòng, "22 method", PASS 6·WARNING 5)
không còn trong tài liệu hướng dẫn (trừ bản ghi lịch sử trong 03 nếu ghi rõ "đợt cũ").

## Task 3 — Xuất file rule sang Excel (tồn tại song song JSON + XLSX)

1. Script mới `tool/docs_exporter.py`:
   - `export_rules_excel(json_path, xlsx_path)`: đọc `rules/conversion_rules.json`,
     ghi `rules/conversion_rules.xlsx` gồm sheet:
     - `GioiThieu` — giới thiệu, cách đọc, bảng tóm tắt C1–C5 + SQL check.
     - `RuleVB` — id / tiêu đề / regex / vì sao nguy hiểm / cần kiểm tra gì bên C#.
     - `RuleCS` — như trên cho phía C#.
     - `PairRules` — id / bật-tắt / mô tả / hành động (note hay nâng status).
   - Style thống nhất với excel_exporter (header xanh đậm, border, wrap text).
2. **JSON vẫn là nguồn sự thật** (tool đọc JSON khi chạy); XLSX là bản trình bày cho
   người review — ghi rõ điều này trong sheet GioiThieu + README. Sửa JSON xong chạy
   `python tool/docs_exporter.py` để tái sinh XLSX.
3. Test mới trong tests/test_rules.py: export ra file tạm, mở lại bằng openpyxl,
   số dòng RuleVB/RuleCS/PairRules khớp số rule trong JSON.

**Rà soát**: mở xlsx kiểm tra đủ 7 rule VB + 2 rule CS + 4 pair rule; chạy lại test.

## Task 4 — Guideline sử dụng tool dạng Excel

1. `export_guideline_excel(xlsx_path)` trong cùng `tool/docs_exporter.py`,
   ghi `documents/11_Tool_Usage_Guideline.xlsx`:
   - `TongQuan` — tool là gì, 2 cách chạy (exe / source / CLI), cấu trúc thư mục.
   - `QuyTrinh` — 5 bước GUI (chọn folder VB/C#, mapping, Scan, đọc kết quả, Export)
     + bảng mô tả từng thành phần màn hình.
   - `TrangThai` — PASS/WARNING/FAIL/MISSING/EXTRA + hướng xử lý; tiêu chí C1–C5.
   - `GhiChu` — cách đọc note: thay đổi có chủ đích / SQL Oracle / RULE (tham chiếu
     rules/conversion_rules.xlsx); JP-MSG & VALIDATOR-SPLIT giải thích riêng.
   - `CLI_CICD` — bảng tham số CLI + exit code + ví dụ lệnh retest.
   - `FAQ` — bảng lỗi thường gặp (đồng bộ documents/07 mục 7).
   Nội dung lấy đồng bộ từ documents/07 (không chép mâu thuẫn).
2. `python tool/docs_exporter.py` (không tham số) tái sinh cả 2 file xlsx.
3. README thêm mục nói về 2 file xlsx này và lệnh tái sinh.

**Rà soát**: mở guideline xlsx đủ 6 sheet, số liệu sample khớp (41 dòng có --map...);
chạy toàn bộ test lần cuối; xác nhận không degrade.
