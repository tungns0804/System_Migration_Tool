# Tổng hợp Study — Kiến trúc Migration VB.NET → ASP.NET Core

> Tài liệu này tổng hợp nội dung study từ 2 ảnh trong thư mục `assets/`
> (`1.jpg` — kiến trúc tổng thể AS-IS/TO-BE, `2.jpg` — quy tắc chuyển đổi file).

---

## 1. Ảnh 1 — Kiến trúc tổng thể: AS-IS (bản PC) → TO-BE (bản WEB)

### 1.1. Phạm vi migration (移行対象)

| # | Hạng mục | AS-IS (PC版) | Phương pháp | TO-BE (WEB版) |
|---|----------|--------------|-------------|----------------|
| ① | UI/UX (làm mới) | VB .NET | Migrate (đáp ứng UI mới) + Enhance + Loại bỏ | .NET Core: **Razor**, HTML/CSS |
| ② | Business Logic (業務ロジック) | VB .NET | Migrate + Enhance + Loại bỏ | .NET Core: **Blazor** |
| ③ | Third Party | ActiveReports for .NET 16.0J SP2, SPREAD for Windows Forms 15.0J SP2 | **Thay thế** (置き換え) | **FastReport** (OSS free/Commercial), **Radzen Grid / Radzen Blazor component** |
| ④ | Database | Oracle Database 19c (19.16.0) | Migrate (bao gồm cả migration dữ liệu DB) | **PostgreSQL 17.6** |

### 1.2. Môi trường & thông tin kỹ thuật (環境・技術情報)

| Hạng mục | AS-IS | TO-BE |
|----------|-------|-------|
| Ngôn ngữ / Platform | Visual Basic .NET, .NET Framework 4.8 | .NET Core Blazor, .NET Framework 10.0 (.NET 10) |
| Server OS | Windows Server 2022, Windows 11 (x86, WOW64) | Windows Server 2022, Windows Server 2025, Windows 11 |

### 1.3. Nhận xét chính

- Đây là migration **đổi cả kiến trúc** (PC desktop → Web), không phải chỉ dịch ngôn ngữ 1-1.
- Business logic là phần chuyển từ VB.NET sang C#/Blazor — **đây chính là scope backend mà tool cần kiểm tra đầu tiên**.
- Third party không migrate mà **thay thế bằng sản phẩm khác** → hành vi báo cáo/grid có thể khác biệt, cần test riêng (ngoài scope đợt 1).
- Database đổi từ Oracle → PostgreSQL → các câu SQL, kiểu dữ liệu, function DB (NVL → COALESCE, SYSDATE → CURRENT_TIMESTAMP, ...) chắc chắn thay đổi → khi so sánh logic method cần **chấp nhận khác biệt có chủ đích ở tầng truy vấn**.

---

## 2. Ảnh 2 — Quy tắc chuyển đổi cấu trúc file (theo từng màn hình)

Ảnh 2 mô tả 5 cột: **Hiện trạng → Trạng thái mong muốn → Phương pháp chuyển đổi → Tỷ lệ chuyển đổi mã nguồn (hiện tại) → Tỷ lệ thay đổi mã nguồn (mới)**.

### 2.1. Client

| Hiện trạng | Trạng thái mong muốn | Phương pháp chuyển đổi | Tỷ lệ chuyển đổi | Tỷ lệ thay đổi (mới) |
|------------|----------------------|------------------------|------------------|----------------------|
| `{Tên màn hình}.Designer.vb` | `*.css` | Chuyển thuộc tính hiển thị của hệ thống cũ sang file css | 60% | 100% |
| | `{Tên màn hình}.razor` | Chuyển các mục màn hình sang file razor định dạng html | 30% | 50% |
| | `{Model}.cs` | Chuyển dữ liệu model hiển thị trên màn hình thành file cs, dùng chung giữa client và server | 10% | 80% |

### 2.2. Server (scope backend — trọng tâm của tool)

| Hiện trạng | Trạng thái mong muốn | Phương pháp chuyển đổi | Tỷ lệ chuyển đổi | Tỷ lệ thay đổi (mới) |
|------------|----------------------|------------------------|------------------|----------------------|
| `*.vb` | `{Tên màn hình}.razor` | Các sự kiện UI (form load, click, nhập liệu…) được xử lý ở file frontend (razor) | 32% | 80% |
| | `{Tên màn hình}Configuration.cs` | Tập trung kết nối DB, query, EF Core vào file này | 4% | 120% |
| | `{Tên màn hình}DTO.cs` | Chuyển các object sang file dto của từng màn hình | 8% | 105% |
| | `{Tên màn hình}Service.cs` | Xử lý logic màn hình (kiểm tra điều kiện, xử lý dữ liệu trước khi lưu DB) | 48% | 90% |
| | `{Tên màn hình}Query.cs` | Tập trung kết nối query vào file này | 8% | 100% |

### 2.3. Báo cáo

| Hiện trạng | Trạng thái mong muốn | Phương pháp chuyển đổi | Tỷ lệ chuyển đổi | Tỷ lệ thay đổi (mới) |
|------------|----------------------|------------------------|------------------|----------------------|
| `*.vb` | `*.frx` | Tích hợp mã nguồn file báo cáo vào một file định dạng mới (FastReport) | 100% | 90% |

### 2.4. Nhận xét chính cho việc xây tool kiểm tra backend

1. **1 file VB → nhiều file C#**: một `*.vb` bị tách thành Razor / Configuration / DTO / Service / Query. Do đó tool **không thể so sánh theo cặp file**, mà phải:
   - Quét **toàn bộ** method trong folder VB nguồn,
   - Quét **toàn bộ** method trong folder C# đích,
   - **Map theo tên method** (case-insensitive), bất kể method đó nằm ở file nào.
2. **Trọng tâm backend là `Service.cs` (48%) và `Query.cs` (8%)** — logic nghiệp vụ chủ yếu rơi vào Service; tool đợt 1 tập trung đối chiếu logic method VB ↔ method trong các file Service/Query/DTO.
3. Phần sự kiện UI (32%) chuyển sang `.razor` (frontend) → method dạng `Button_Click`, `Form_Load` **có thể không còn ở backend mới**; tool nên cho phép nhận diện/ghi chú nhóm này thay vì báo lỗi cứng là "thiếu".
4. Tỷ lệ thay đổi mã nguồn mới 80–120% nghĩa là code mới **được viết lại đáng kể**, không phải dịch máy 1-1 → tiêu chí so sánh logic phải dùng **độ tương đồng sau chuẩn hóa** (normalize) chứ không so text thô.

---

## 3. Hệ quả thiết kế cho tool kiểm tra (đợt 1 — Backend)

| Quyết định | Lý do bắt nguồn từ study |
|------------|--------------------------|
| So sánh ở mức **method**, map theo tên trên toàn folder | 1 file VB tách thành nhiều file C# (mục 2.4-1) |
| Chuẩn hóa cú pháp VB → tương đương C# trước khi tính độ tương đồng | Code mới bị viết lại 80–120% (mục 2.4-4) |
| Có trạng thái riêng cho method thiếu (MISSING) và method thừa (EXTRA) | Có method bị loại bỏ (削除) hoặc chuyển sang frontend hợp lệ (mục 1.1, 2.4-3) |
| Khoan dung với khác biệt ở câu SQL/kiểu DB | Oracle → PostgreSQL (mục 1.3) |
| Báo cáo Excel để chia sẻ cho team review thủ công các case WARNING | Tỷ lệ chuyển đổi từng phần khác nhau, cần con người phán đoán case biên |
