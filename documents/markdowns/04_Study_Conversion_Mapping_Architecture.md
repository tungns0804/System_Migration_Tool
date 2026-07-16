# Tổng hợp Study — Sơ đồ mapping chi tiết VB.NET WinForms → Blazor Server (.NET)

> Tài liệu này tổng hợp nội dung study từ ảnh `assets/3.png` — sơ đồ mapping chi tiết
> từng thành phần của hệ thống cũ (AS-IS — WinForms VB.NET) sang kiến trúc mới
> (To-Do — Blazor Server .NET, solution `PCRS` gồm 6 project).
> Bổ sung cho tài liệu [01_Study_Migration_Architecture.md](01_Study_Migration_Architecture.md).

---

## 1. Tổng quan kiến trúc

### 1.1. AS-IS — WinForms VB.NET

Mỗi màn hình của hệ thống cũ gồm các thành phần:

| Thành phần | File | Nội dung |
|------------|------|----------|
| Menu | `Menu.Designer.vb` / `Menu.vb` | Menu điều hướng của ứng dụng |
| Report | (ActiveReports) | Báo cáo in ấn |
| UI Controls | `*.Designer.vb` | TextBox, Button, ComboBox, DataGridView... |
| UI Events | `*.vb` (Code Behind Form) | Arrow key, Enter key / scroll grid |
| Form Events | `*.vb` (Code Behind Form) | `Form_Load`, `F8_Click` (追加変更削除 — thêm/sửa/xóa) |
| Data Access | `*.vb` (Code Behind Form) | `SqlConnection`, `SqlCommand`, SQL string (Oracle) |
| Business Core / Invariants | `*.vb` (Code Behind Form) | Quy tắc nghiệp vụ cốt lõi của hệ thống |
| Business Logic | `*.vb` (Code Behind Form) | Check duplicate, check exist... |

Đặc điểm: **toàn bộ UI, sự kiện, truy cập dữ liệu và nghiệp vụ trộn lẫn trong code-behind của form** — đây là điểm khác biệt kiến trúc lớn nhất so với bản mới.

### 1.2. To-Do — Blazor Server .NET (solution PCRS, 6 project)

| Project | Vai trò | Thành phần chính |
|---------|---------|------------------|
| **PCRS.Server** | ASP.NET Core Host | `Program.cs` (DI Registration, MediatR / FluentValidation scan assembly), `Components/Layout/NavMenu.razor`, `Reports/*.frx` (FastReport template) |
| **PCRS.Client** | Blazor UI — Razor Pages | `Pages/Masters/[ScreenName].razor`, `wwwroot/css/pages/[ScreenName].css` |
| **PCRS.Shared** | Cross-cutting (DTO, interface dùng chung toàn ứng dụng) | `Services/IReportService.cs`, `Helpers/`, `Extensions/`, `Constants/` |
| **PCRS.Domain** | Business core | `Common/BaseEntity.cs`, `Entities/[ScreenName].cs` |
| **PCRS.Infrastructure** | Database + EF Core | `Persistence/Configurations/[ScreenName]Configuration.cs`, `Reporting/FastReportService.cs` |
| **PCRS.Application** | Business Logic — CQRS | `DTOs/`, `Features/[ScreenName]/` (Commands / Queries / Validators), `Common/Models/Result.cs` |

---

## 2. Bảng mapping chi tiết AS-IS → To-Do

### 2.1. Menu & Report

| AS-IS | To-Do | Quy tắc chuyển đổi |
|-------|-------|---------------------|
| `Menu.Designer.vb` / `Menu.vb` | `PCRS.Server` → `Components/Layout/NavMenu.razor` | Thêm một `NavLink` mới cho mỗi menu |
| Report | `PCRS.Server` → `Reports/*.frx` | Chuyển sang FastReport template |

### 2.2. UI Controls (`*.Designer.vb`)

| AS-IS | To-Do | Quy tắc chuyển đổi |
|-------|-------|---------------------|
| Thuộc tính hiển thị (style, display...) | `PCRS.Client` → `wwwroot/css/pages/[ScreenName].css` | Custom CSS riêng cho từng page |
| Controls (TextBox, Button, ComboBox, DataGridView...) | `PCRS.Client` → `Pages/Masters/[ScreenName].razor` | Thay bằng **Radzen Components** (TextBox / DropDown / DataGrid) |

Quy tắc file razor:
- Route: `/[kebab-case-screen-name]`
- `@inject IMediator Mediator` — gọi nghiệp vụ qua MediatR, không gọi trực tiếp service.

### 2.3. UI Events & Form Events (`*.vb` Code Behind)

| AS-IS | To-Do | Quy tắc chuyển đổi |
|-------|-------|---------------------|
| UI Events (Arrow key, Enter key / scroll grid) | `[ScreenName].razor` | `@onclick` / `RowClick`, `@bind-Value:after` |
| `Form_Load` | `[ScreenName].razor` | `OnInitializedAsync()` |
| `F8_Click` (thêm/sửa/xóa) | `[ScreenName].razor` | `Mediator.Send(Command)` |

### 2.4. Data Access (`SqlConnection` / `SqlCommand` / SQL Oracle)

| AS-IS | To-Do | Quy tắc chuyển đổi |
|-------|-------|---------------------|
| `SqlConnection` + SQL string (Oracle) | `PCRS.Infrastructure` → `Persistence/Configurations/[ScreenName]Configuration.cs` | Chuyển sang **EF Core LINQ**, cấu hình bằng Fluent API, mapping bảng PostgreSQL |

Quy tắc dịch SQL Oracle → EF Core LINQ:

| Oracle SQL | EF Core / C# |
|------------|--------------|
| `NVL` | `??` (null-coalescing) |
| `DECODE` | Toán tử ternary `? :` |
| `ROWNUM` | `.Take()` |
| `DELETE` | `IsDeleted = true` (soft delete) |

Cấu hình EF Core bắt buộc:
- `HasQueryFilter(e => !e.IsDeleted)` — global query filter cho soft delete.
- Reporting: `Reporting/FastReportService.cs` implement `IReportService` (interface đặt ở `PCRS.Shared`).

### 2.5. Business Core / Invariants → PCRS.Domain

| AS-IS | To-Do | Quy tắc chuyển đổi |
|-------|-------|---------------------|
| Business Core / Invariants trong code-behind | `PCRS.Domain` | Business core của hệ thống tách riêng thành Entity |

Quy tắc tầng Domain:
- `Common/BaseEntity.cs` — base class cho mọi entity (audit fields + domain events).
- `Entities/[ScreenName].cs` — entity kế thừa `BaseEntity`.
- Property chuẩn: `(Entity)Code`, `(Entity)Name`.
- `IsDeleted` — soft delete (không xóa vật lý).

### 2.6. Business Logic → PCRS.Application (CQRS)

| AS-IS | To-Do | Quy tắc chuyển đổi |
|-------|-------|---------------------|
| Business Logic (check duplicate, check exist...) | `PCRS.Application` → `Features/[ScreenName]/` | Chuyển thành Handler; lỗi nghiệp vụ trả về `Result.Failure(...)` với **message tiếng Nhật (日本語)** |

Cấu trúc `Features/[ScreenName]/` — **1 folder = 1 feature**:

| File | Nội dung |
|------|----------|
| `[ScreenName]Commands.cs` | Create / Update / Delete + Handlers |
| `[ScreenName]Queries.cs` | Tất cả Query + Handler (GetById / GetList) |
| `[ScreenName]Validators.cs` | FluentValidation + shared helper |

Thành phần mới (không có trên VB.NET, ghi chú "New on Blazor Server — dùng cho Application layer"):
- `DTOs/[ScreenName]Dto.cs` — strongly-typed DTO, chỉ dùng trong Application layer.
- `Common/Models/Result.cs` — **Result / Result&lt;T&gt; pattern**: nghiệp vụ **không throw exception**, mọi lỗi nghiệp vụ trả về `Result.Failure`.

### 2.7. Hosting & DI — PCRS.Server

- `Program.cs`: đăng ký DI, scan assembly cho **MediatR** và **FluentValidation** (mặc định trên Blazor Server).
- Luồng gọi chuẩn: **Razor page → `IMediator.Send()` → Command/Query Handler (Application) → EF Core (Infrastructure) → PostgreSQL**.

---

## 3. Sơ đồ luồng tổng hợp

```
AS-IS (WinForms VB.NET)                To-Do (Blazor Server .NET — PCRS)
─────────────────────────              ─────────────────────────────────────────────
Menu.vb ─────────────────────────────► PCRS.Server/Components/Layout/NavMenu.razor
Report ──────────────────────────────► PCRS.Server/Reports/*.frx (FastReport)

*.Designer.vb (UI Controls) ──style──► PCRS.Client/wwwroot/css/pages/[Screen].css
              └───────────controls──► PCRS.Client/Pages/Masters/[Screen].razor
                                        (Radzen Components, @inject IMediator)

*.vb  UI Events ─────────────────────► @onclick / RowClick, @bind-Value:after
      Form_Load ─────────────────────► OnInitializedAsync()
      F8_Click ──────────────────────► Mediator.Send(Command)

      Data Access (Oracle SQL) ──────► PCRS.Infrastructure/Persistence/
                                        Configurations/[Screen]Configuration.cs
                                        (EF Core LINQ, PostgreSQL, soft delete)

      Business Core / Invariants ────► PCRS.Domain/Entities/[Screen].cs
                                        (kế thừa BaseEntity, IsDeleted)

      Business Logic ────────────────► PCRS.Application/Features/[Screen]/
                                        Commands + Queries + Validators
                                        (Result.Failure, message 日本語)
```

---

## 4. Nhận xét chính (liên quan đến tool kiểm tra migration)

1. **1 file code-behind VB tách thành nhiều file trên nhiều layer** — khi so khớp logic, tool phải map 1 method VB sang đúng vị trí mới: sự kiện UI → razor, truy vấn → Configuration/Queries, validate/nghiệp vụ → Commands/Validators. Không tồn tại mapping file-to-file 1-1.
2. **Quy ước đặt tên theo `[ScreenName]`** xuyên suốt tất cả các layer (razor, css, Dto, Configuration, Commands, Queries, Validators) → tool có thể dựa vào tên màn hình để gom nhóm file cần đối chiếu.
3. **Khác biệt có chủ đích cần chấp nhận khi so sánh logic**:
   - `DELETE` vật lý → soft delete (`IsDeleted = true` + `HasQueryFilter`).
   - `NVL` → `??`, `DECODE` → ternary, `ROWNUM` → `.Take()`.
   - Throw exception / message box → `Result.Failure` với message tiếng Nhật.
4. **Thành phần hoàn toàn mới, không có đối chiếu bên VB**: DTO, Result pattern, FluentValidation, MediatR pipeline, BaseEntity (audit fields + domain events) → tool không được báo "thừa code" cho các thành phần này.
5. **Kiến trúc CQRS**: mọi thao tác dữ liệu đi qua Command/Query Handler — điểm vào để kiểm tra nghiệp vụ backend chính là các file trong `PCRS.Application/Features/[ScreenName]/`.
