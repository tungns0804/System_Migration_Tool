# Lựa chọn ngôn ngữ / công nghệ cho Tool kiểm tra Migration

## 1. Yêu cầu đối với tool

- Ứng dụng **desktop có GUI** (dạng "WinForm-like": chọn folder, bảng kết quả, nút bấm).
- Chạy được trên **Windows và macOS**.
- Phân tích source code VB.NET và C# (đọc file text, parse method).
- **Export Excel** báo cáo đánh giá.
- Dễ bảo trì, dễ mở rộng cho các đợt kiểm tra sau (frontend, DB, báo cáo).

## 2. So sánh các phương án

| Tiêu chí | Python + Tkinter | Python + PySide6/Qt | .NET WinForms | .NET MAUI | Avalonia (.NET) | Electron (JS) |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|
| Chạy Windows | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Chạy macOS | ✅ | ✅ | ❌ **(WinForms không hỗ trợ macOS)** | ✅ | ✅ | ✅ |
| GUI có sẵn trong runtime, không cần cài thêm | ✅ (Tkinter đi kèm Python) | ❌ (cài PySide6 ~200MB) | ✅ | ❌ (workload lớn) | ❌ (NuGet + template) | ❌ (Node + Chromium nặng) |
| Xử lý text/regex để parse code | ✅ rất mạnh, nhanh viết | ✅ | ✅ | ✅ | ✅ | ✅ |
| Export Excel | ✅ openpyxl (nhẹ, thuần Python) | ✅ | ✅ ClosedXML/EPPlus | ✅ | ✅ | ⚠️ exceljs |
| Tốc độ phát triển / sửa đổi | ✅ nhanh nhất | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ |
| Có thể dùng Roslyn để parse C# chuẩn compiler | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| Đóng gói phân phối | PyInstaller (per-OS) | PyInstaller | dotnet publish | dotnet publish | dotnet publish | electron-builder |

## 3. Kết luận & khuyến nghị

### Lưu ý quan trọng về "WinForms"
**.NET WinForms thật sự chỉ chạy trên Windows** — Microsoft không hỗ trợ WinForms trên macOS.
Vì yêu cầu bắt buộc là chạy cả Windows + macOS, nếu muốn giao diện "kiểu WinForms" thì phải chọn một trong: **Python (Tkinter/Qt)**, **Avalonia**, hoặc **.NET MAUI**.

### Khuyến nghị: **Python 3 + Tkinter + openpyxl** ✅ (đã chọn để triển khai)

Lý do:
1. **Cross-platform thật sự**: Tkinter là GUI toolkit đi kèm sẵn Python trên cả Windows và macOS — không phải cài framework GUI nào thêm; phụ thuộc ngoài duy nhất là `openpyxl` (thuần Python).
2. **Bản chất của tool là xử lý text**: parse method VB/C# bằng regex, chuẩn hóa token, tính độ tương đồng — đây là thế mạnh của Python (`re`, `difflib` trong thư viện chuẩn).
3. **Tốc độ phát triển và chỉnh sửa nhanh**: tiêu chí đánh giá migration sẽ được tinh chỉnh nhiều lần theo phản hồi của team QA; Python cho vòng lặp sửa–chạy ngắn nhất, không cần build.
4. **Excel export đơn giản** với openpyxl: tô màu trạng thái, nhiều sheet, autofilter.
5. Kiến trúc tool được tách **core engine (không GUI) + GUI + CLI**, nên sau này nếu cần chuyển GUI sang công nghệ khác (hoặc chạy trong CI/CD pipeline bằng CLI) đều không phải viết lại phần phân tích.

### Phương án dự phòng (khi nào nên cân nhắc lại)
- **Avalonia (.NET/C#)**: chọn khi cần parse C# **chuẩn compiler bằng Roslyn** (phân tích ngữ nghĩa sâu: type resolution, call graph) thay vì regex heuristic, và khi team bảo trì tool là team .NET thuần.
- **Python + PySide6**: chọn khi GUI cần phức tạp hơn nhiều (dock panel, diff viewer 2 cột có highlight cú pháp).

Đợt 1 (kiểm tra method-level heuristic) chưa cần Roslyn, nên Python + Tkinter là lựa chọn tối ưu về chi phí/tốc độ.

## 4. Cách chạy & phân phối

```bash
# Yêu cầu: Python 3.10+ và openpyxl
pip install openpyxl

# Chạy GUI
python tool/main.py

# Chạy CLI (không cần GUI — dùng cho CI hoặc retest tự động)
python tool/cli.py <folder_VB> <folder_ASPCore> --out report.xlsx
```

Đóng gói thành file thực thi độc lập (tùy chọn):
```bash
pip install pyinstaller
pyinstaller --onefile --windowed tool/main.py   # chạy trên từng OS để tạo bản cho OS đó
```
