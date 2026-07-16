# Master Prompt v6 — Đợt 6: Tích hợp gate đánh giá AI (Claude API)

Bổ sung **lớp đánh giá thứ 3** cho Migration Checker: mỗi lần scan, gọi Claude API
(model Sonnet) để AI review chất lượng convert của **từng method**, song song và
**độc lập hoàn toàn** với lớp chấm điểm C1–C5 và lớp rule-based (đợt 4).

Yêu cầu đã chốt với user (2026-07-16, xem lịch sử Q&A):

| Hạng mục | Quyết định |
|---|---|
| Model | Claude Sonnet — `claude-sonnet-5`, gọi qua Claude API bằng API key của user |
| Phạm vi | **Tất cả** method, kể cả MISSING (chỉ có VB) và EXTRA (chỉ có C#) |
| Ảnh hưởng C1–C5 | **KHÔNG** — không sửa điểm, không sửa status PASS/WARNING/FAIL/MISSING/EXTRA |
| Output | 2 cột mới trong Excel Detail: **"Nội dung AI đánh giá"** (text) + **"Status AI đánh giá"** (chỉ PASS hoặc WARNING) |
| Tiêu chí PASS/WARNING | Hoàn toàn theo nhận định tự do của model, tool không áp rubric cứng |
| Khi API lỗi / mất mạng / thiếu key | Cột Status AI ghi **"AI chưa thực hiện đánh giá"**, KHÔNG chặn scan |
| Cache | Theo hash nội dung method (model + prompt version + VB body + C# body) để không gọi lại API tốn token khi retest |
| Token API | Đổi được dễ dàng qua file setting (config.json), **không hardcode trong code** |

## Nguyên tắc bất di bất dịch (không degrade)

1. `llm.enabled` mặc định **false** → khi không cấu hình, mọi output CLI/JSON
   giống 100% baseline trước đợt 6 (đã chụp: no-map 42 dòng PASS8/W7/F4/M8/E15,
   điểm TB 90.6, rule-hits 14; 56 unittest OK).
2. LLM chạy **sau** `scan_folders()` (hậu xử lý trên `ScanResult`) — không đụng
   vào comparator/normalizer/parser, do đó không thể làm lệch điểm C1–C5.
3. Bộ test không bao giờ gọi API thật — reviewer phải nhận injectable `call_fn`
   để mock; test chạy offline, không cần package `anthropic`.
4. Tool vẫn chạy được khi **không cài** package `anthropic` (import lazy):
   llm tắt → không import; llm bật mà thiếu package → mọi method ghi
   "AI chưa thực hiện đánh giá" kèm lý do, scan vẫn hoàn thành.

## Task 1 — Cấu hình (`tool/core/config.py` + `config.sample.json`)

Thêm section `"llm"` vào `DEFAULTS` (pattern y hệt `"rules"`):

```json
"llm": {
  "enabled": false,
  "model": "claude-sonnet-5",
  "api_key": "",
  "api_key_env": "ANTHROPIC_API_KEY",
  "cache_file": "",
  "timeout_seconds": 60,
  "max_retries": 2,
  "max_output_tokens": 4096
}
```

- **Thứ tự lấy key**: `api_key` trong config nếu khác rỗng → biến môi trường
  `api_key_env`. User đổi token chỉ cần sửa `config.json` cạnh exe (hoặc đổi
  biến môi trường), không cần build lại.
- `cache_file` rỗng → mặc định `llm_cache.json` cạnh config/exe (frozen) hoặc
  thư mục làm việc.
- Thêm property `llm_enabled` và accessor `llm(key)` vào class `Config`.
- `config.sample.json` thêm section tương ứng + ghi chú "KHÔNG commit
  config.json chứa api_key lên git".

## Task 2 — Model (`tool/core/models.py`)

- `MethodComparison` thêm 2 field: `ai_status: str = ""`, `ai_comment: str = ""`.
- Hằng `AI_NOT_RUN = "AI chưa thực hiện đánh giá"`.
- `ScanResult.count_ai()` → dict `{PASS, WARNING, not_run}` phục vụ summary.

## Task 3 — `tool/core/llm_reviewer.py` (file mới)

```
review_result(result, cfg, call_fn=None, progress=None) -> dict thống kê
```

- Duyệt **mọi** `result.comparisons` (cặp đủ 2 bên, MISSING, EXTRA).
- **Prompt** (system, tiếng Việt): vai trò senior reviewer migration
  VB.NET/.NET Framework 4.8/Oracle → ASP.NET Core/.NET/PostgreSQL; biết các thay
  đổi có chủ đích của kiến trúc mới (Result pattern, soft delete,
  DataTable→List<DTO>, async hóa, CQRS/MediatR — documents/04) để không báo oan;
  tự nhận định theo hiểu biết của model, KHÔNG bị ép theo C1–C5.
- **User content mỗi method**: tên, status + notes hiện có của tool (chỉ để tham
  khảo), signature + body VB (nếu có), signature + body C# (nếu có). MISSING/EXTRA
  ghi rõ "chỉ tồn tại một phía" để model đánh giá rủi ro tương ứng.
- **Ép JSON bằng structured outputs** (`output_config.format` = json_schema):
  `{"status": "PASS"|"WARNING", "comment": "<tiếng Việt, ngắn gọn>"}`.
- **Gọi API**: SDK `anthropic` (lazy import), `Anthropic(api_key=..., timeout=...,
  max_retries=...)`, `messages.create(model=..., max_tokens=...)`. Không set
  temperature/top_p (Sonnet 5 từ chối non-default sampling).
- **Cache**: key = `sha256(model | PROMPT_VERSION | name | vb_body | cs_body)`;
  file JSON `{key: {"status", "comment"}}`; hit → không gọi API; ghi file sau
  khi review xong (lỗi ghi cache không làm hỏng kết quả).
- **Xử lý lỗi**:
  - Thiếu key / thiếu package / lỗi xác thực (authentication) → dừng gọi tiếp,
    đánh dấu tất cả method còn lại `AI_NOT_RUN` + lý do ngắn trong `ai_comment`.
  - Lỗi lẻ tẻ (timeout, rate limit sau retry, response không parse được) →
    method đó `AI_NOT_RUN`, các method sau vẫn tiếp tục.
  - Mọi exception đều bắt — reviewer **không bao giờ** raise ra ngoài.
- `call_fn(payload) -> (status, comment)` tiêm được từ test.
- `PROMPT_VERSION` là hằng — đổi prompt thì cache cũ tự vô hiệu.

## Task 4 — Output

1. **Excel** (`excel_exporter.py`):
   - Sheet Detail thêm 2 cột cuối: **"Nội dung AI đánh giá"** (wrap text, rộng 60)
     và **"Status AI đánh giá"** (PASS tô xanh / WARNING tô vàng — dùng lại style
     sẵn có; "AI chưa thực hiện đánh giá" tô xám). `auto_filter` mở rộng A1:Q.
   - Ô rỗng (chưa chạy AI) → hiển thị "AI chưa thực hiện đánh giá".
   - Sheet Summary: thêm dòng thống kê "AI đánh giá (Claude ...)" khi có ít nhất
     1 method được AI chấm.
2. **JSON** (`report_io.py`): mỗi method thêm `ai_status`, `ai_comment`
   (null khi chưa chạy) — không phá `diff_reports` (chỉ đọc key cũ).
3. **CLI** (`cli.py`): thêm cờ `--llm` (bật cho lần chạy đó, override config);
   khi chạy in thêm 1 dòng thống kê `AI danh gia: PASS x WARNING y chua danh gia z`
   (ASCII-safe); bảng method GIỮ NGUYÊN cột cũ.
4. **GUI** (`main.py`): thêm cột "AI" vào bảng kết quả; tab Tổng quan hiển thị
   "AI đánh giá" + nội dung; nếu config bật llm thì chạy review ngay trong
   thread scan (summary hiện "Đang chấm AI...").

## Task 5 — Test (`tests/test_llm.py`)

Mock hoàn toàn (`call_fn` giả), không mạng, không cần package `anthropic`:
1. Mặc định (không config) → `llm.enabled` False, `ai_status` rỗng, CLI/JSON
   không đổi so với trước.
2. Review với fake call_fn → `ai_status`/`ai_comment` gán đúng cho đủ 3 loại
   (cặp, MISSING, EXTRA); status ngoài PASS/WARNING bị ép về WARNING.
3. Cache: chạy 2 lần cùng nội dung → lần 2 không gọi `call_fn`; đổi body → gọi lại.
4. Lỗi call_fn → `AI_NOT_RUN`, không raise, method sau vẫn được chấm.
5. Thiếu key (config bật, không api_key/env, không call_fn) → tất cả `AI_NOT_RUN`.
6. Excel xuất ra có đúng 2 header mới ở cột P/Q; giá trị fallback đúng.
7. Toàn bộ test cũ (56) pass nguyên vẹn.

## Task 6 — Tài liệu

- `documents/03` thêm mục **12. Cập nhật đợt 6** (đặc tả như trên; mục
  "Giới hạn đã biết" dồn xuống thành mục 13).
- `documents/12_Evaluation_Criteria_Summary.md` thêm lớp 3 (AI review) + cách
  đổi token + vị trí cache.
- Ghi chú chi phí: mỗi method 1 request; cache đảm bảo retest không tốn thêm.

## Retest bắt buộc

1. `python -m unittest discover tests` — pass 100%.
2. CLI trên `samples/pcrs` (không map + có map, **không bật llm**) → output
   trùng khớp baseline đã chụp từng ký tự (trừ dòng "Scan luc").
3. `PYTHONIOENCODING=utf-8` khi chạy console (quy ước sẵn có).
