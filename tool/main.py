"""Migration Checker — GUI (Tkinter).

Tool kiem tra chat luong migration backend VB.NET -> ASP.NET Core:
chon 2 folder, scan, xem ket qua theo method va export bao cao Excel.
Chay duoc tren Windows va macOS (chi can Python 3.10+ va openpyxl).
"""

import sys
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, str(Path(__file__).parent))

from core.comparator import scan_folders
from core.excel_exporter import export_excel
from core.mapping import load_mapping
from core.config import load_config, find_default_config, get_config
from core.llm_reviewer import review_result
from core.models import (STATUS_PASS, STATUS_WARNING, STATUS_FAIL,
                         STATUS_MISSING, STATUS_EXTRA, AI_PASS, AI_WARNING)

_STATUS_COLORS = {
    STATUS_PASS: "#C6EFCE", STATUS_WARNING: "#FFEB9C", STATUS_FAIL: "#FFC7CE",
    STATUS_MISSING: "#D9D9D9", STATUS_EXTRA: "#DDEBF7",
}
_ALL = "ALL"


class MigrationCheckerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.result = None
        root.title("Migration Checker — VB.NET → ASP.NET Core (Backend)")
        root.geometry("1200x700")
        root.minsize(900, 550)
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        self.vb_var = tk.StringVar()
        self.cs_var = tk.StringVar()

        ttk.Label(top, text="Folder VB.NET (hệ thống cũ):").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.vb_var, width=80).grid(row=0, column=1, padx=6, sticky="we")
        ttk.Button(top, text="Chọn...", command=lambda: self._browse(self.vb_var)).grid(row=0, column=2)

        ttk.Label(top, text="Folder ASP.NET Core (hệ thống mới):").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(top, textvariable=self.cs_var, width=80).grid(row=1, column=1, padx=6, pady=(6, 0), sticky="we")
        ttk.Button(top, text="Chọn...", command=lambda: self._browse(self.cs_var)).grid(row=1, column=2, pady=(6, 0))

        ttk.Label(top, text="File mapping tên method (tùy chọn):").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.map_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.map_var, width=80).grid(row=2, column=1, padx=6, pady=(6, 0), sticky="we")
        ttk.Button(top, text="Chọn...", command=self._browse_mapping).grid(row=2, column=2, pady=(6, 0))

        ttk.Label(top, text="Business Logic (tự phát hiện):").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.bl_var = tk.StringVar(value="— chọn folder gốc, tool sẽ tự tìm project *Application* (Features/) khi Scan —")
        ttk.Label(top, textvariable=self.bl_var, foreground="#1F4E78").grid(
            row=3, column=1, columnspan=2, padx=6, pady=(6, 0), sticky="w")
        top.columnconfigure(1, weight=1)

        bar = ttk.Frame(self.root, padding=(10, 4))
        bar.pack(fill="x")
        self.scan_btn = ttk.Button(bar, text="▶ Scan", command=self.on_scan)
        self.scan_btn.pack(side="left")
        self.export_btn = ttk.Button(bar, text="⬇ Export Excel", command=self.on_export, state="disabled")
        self.export_btn.pack(side="left", padx=6)

        ttk.Label(bar, text="Lọc trạng thái:").pack(side="left", padx=(20, 4))
        self.filter_var = tk.StringVar(value=_ALL)
        self.filter_box = ttk.Combobox(
            bar, textvariable=self.filter_var, state="readonly", width=12,
            values=[_ALL, STATUS_PASS, STATUS_WARNING, STATUS_FAIL, STATUS_MISSING, STATUS_EXTRA])
        self.filter_box.pack(side="left")
        self.filter_box.bind("<<ComboboxSelected>>", lambda e: self._refresh_tree())

        ttk.Label(bar, text="Tìm method:").pack(side="left", padx=(20, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_tree())
        ttk.Entry(bar, textvariable=self.search_var, width=24).pack(side="left")

        self.summary_var = tk.StringVar(value="Chưa scan.")
        ttk.Label(bar, textvariable=self.summary_var).pack(side="right")
        # Dot 8: thanh tien do cham AI (chi hien trong luc AI dang chay)
        self.ai_progress = ttk.Progressbar(bar, orient="horizontal",
                                           length=180, mode="determinate")

        # Bang ket qua
        mid = ttk.Frame(self.root, padding=(10, 0))
        mid.pack(fill="both", expand=True)

        columns = ("method", "status", "score", "sim", "ai", "vbfile", "csfile", "notes")
        headings = ("Method", "Status", "Score", "Similarity", "AI đánh giá",
                    "VB File", "C# File", "Notes")
        widths = (200, 80, 60, 80, 100, 180, 220, 320)
        self.tree = ttk.Treeview(mid, columns=columns, show="headings", selectmode="browse")
        for col, head, w in zip(columns, headings, widths):
            self.tree.heading(col, text=head)
            self.tree.column(col, width=w, anchor="w")
        for status, color in _STATUS_COLORS.items():
            self.tree.tag_configure(status, background=color)

        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(mid, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="we")
        mid.rowconfigure(0, weight=1)
        mid.columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Panel chi tiet: Notebook 2 tab (Tong quan / Code VB <-> C#)
        detail_frame = ttk.LabelFrame(self.root, text="Chi tiết method", padding=6)
        detail_frame.pack(fill="x", padx=10, pady=(4, 10))
        self.detail_nb = ttk.Notebook(detail_frame)
        self.detail_nb.pack(fill="both", expand=True)

        tab_overview = ttk.Frame(self.detail_nb)
        self.detail_nb.add(tab_overview, text="Tổng quan")
        self.detail_text = tk.Text(tab_overview, height=8, wrap="word", state="disabled",
                                   font=("Consolas", 9))
        self.detail_text.pack(fill="both", expand=True)

        tab_code = ttk.Frame(self.detail_nb)
        self.detail_nb.add(tab_code, text="Code VB ⇄ C#")
        self.code_vb_text = self._make_code_pane(tab_code, "VB.NET (hệ thống cũ)", 0)
        self.code_cs_text = self._make_code_pane(tab_code, "C# (hệ thống mới)", 1)
        tab_code.columnconfigure(0, weight=1)
        tab_code.columnconfigure(1, weight=1)
        tab_code.rowconfigure(1, weight=1)

    def _make_code_pane(self, parent, title, col):
        ttk.Label(parent, text=title).grid(row=0, column=col, sticky="w", padx=(0, 8))
        frame = ttk.Frame(parent)
        frame.grid(row=1, column=col, sticky="nsew", padx=(0, 8) if col == 0 else 0)
        text = tk.Text(frame, height=10, wrap="none", state="disabled", font=("Consolas", 9))
        vsb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=vsb.set)
        text.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        return text

    @staticmethod
    def _set_text(widget, content):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.config(state="disabled")

    def _browse(self, var):
        folder = filedialog.askdirectory()
        if folder:
            var.set(folder)

    def _browse_mapping(self):
        path = filedialog.askopenfilename(
            filetypes=[("Mapping (CSV/JSON)", "*.csv;*.json"), ("Tất cả", "*.*")])
        if path:
            self.map_var.set(path)

    # ---------- Scan ----------
    def on_scan(self):
        vb, cs = self.vb_var.get().strip(), self.cs_var.get().strip()
        if not vb or not Path(vb).is_dir():
            messagebox.showerror("Lỗi", "Folder VB.NET không hợp lệ.")
            return
        if not cs or not Path(cs).is_dir():
            messagebox.showerror("Lỗi", "Folder ASP.NET Core không hợp lệ.")
            return
        map_file = self.map_var.get().strip()
        if map_file and not Path(map_file).is_file():
            messagebox.showerror("Lỗi", "File mapping tên method không tồn tại.")
            return
        self.scan_btn.config(state="disabled")
        self.summary_var.set("Đang scan...")
        threading.Thread(target=self._scan_worker, args=(vb, cs, map_file), daemon=True).start()

    def _scan_worker(self, vb, cs, map_file):
        try:
            # Tu dong doc config.json neu dat canh exe (dong goi) hoac canh thu muc tool
            cfg_path = find_default_config(
                Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd(),
                Path(__file__).parent.parent)
            config = load_config(cfg_path) if cfg_path else None
            mapping = load_mapping(map_file) if map_file else None
            result = scan_folders(vb, cs, mapping=mapping,
                                  mapping_file=map_file, config=config)
            # Dot 6: gate danh gia AI neu bat llm.enabled trong config.json —
            # chay sau scan, khong anh huong diem/status C1-C5.
            # Dot 8: bao tien do tung method len GUI (thanh progress + so x/N).
            if get_config().llm_enabled:
                total = len(result.comparisons)
                self.root.after(0, self._ai_progress_start, total)
                try:
                    review_result(result, get_config(),
                                  progress=self._ai_progress_from_worker)
                finally:
                    self.root.after(0, self._ai_progress_stop)
            self.root.after(0, self._scan_done, result, None)
        except Exception:
            self.root.after(0, self._scan_done, None, traceback.format_exc())

    # ---------- Tien do cham AI (dot 8) ----------
    def _ai_progress_start(self, total):
        self._ai_cached = 0
        self.ai_progress.configure(maximum=max(total, 1), value=0)
        self.ai_progress.pack(side="right", padx=(0, 8))
        self.summary_var.set(f"Đang chấm AI 0/{total} method... "
                             "(free tier có thể phải chờ giữa các lần gọi)")

    def _ai_progress_from_worker(self, i, total, cached):
        # duoc goi tu thread scan -> chuyen ve main thread cua Tkinter
        self.root.after(0, self._ai_progress_apply, i, total, cached)

    def _ai_progress_apply(self, i, total, cached):
        if cached:
            self._ai_cached += 1
        self.ai_progress.configure(value=i)
        cache_note = f" (cache: {self._ai_cached})" if self._ai_cached else ""
        self.summary_var.set(f"Đang chấm AI {i}/{total} method{cache_note}...")

    def _ai_progress_stop(self):
        self.ai_progress.pack_forget()

    def _scan_done(self, result, error):
        self.scan_btn.config(state="normal")
        if error:
            self.summary_var.set("Scan lỗi.")
            messagebox.showerror("Lỗi khi scan", error)
            return
        self.result = result
        self.export_btn.config(state="normal")
        counts = result.count_by_status()
        self.bl_var.set(f"{result.cs_scan_folder}   [{result.cs_detect_note}]")
        frontend = (f" (handler frontend: {result.count_frontend_handled()})"
                    if result.count_frontend_handled() else "")
        ai_part = ""
        if result.ai_reviewed():
            ai = result.count_ai()
            ai_part = (f" | AI: PASS {ai[AI_PASS]} / WARNING {ai[AI_WARNING]}"
                       f" / chưa đánh giá {ai['not_run']}")
        self.summary_var.set(
            f"PASS: {counts[STATUS_PASS]} | WARNING: {counts[STATUS_WARNING]} | "
            f"FAIL: {counts[STATUS_FAIL]} | MISSING: {counts[STATUS_MISSING]}{frontend} | "
            f"EXTRA: {counts[STATUS_EXTRA]} (kiến trúc mới: {result.count_new_arch()}) | "
            f"Điểm TB: {result.average_score()}{ai_part}")
        self._refresh_tree()

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        if not self.result:
            return
        flt = self.filter_var.get()
        needle = self.search_var.get().strip().lower()
        for idx, comp in enumerate(self.result.comparisons):
            if flt != _ALL and comp.status != flt:
                continue
            if needle and needle not in comp.name.lower():
                continue
            sim = f"{comp.similarity:.2f}" if comp.vb and comp.cs else "-"
            score = f"{comp.score:.0f}" if comp.vb and comp.cs else "-"
            self.tree.insert("", "end", iid=str(idx), tags=(comp.status,), values=(
                comp.name, comp.status, score, sim,
                comp.ai_status or "-",
                comp.vb.file if comp.vb else "-",
                comp.cs.file if comp.cs else "-",
                comp.note_text))

    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel or not self.result:
            return
        comp = self.result.comparisons[int(sel[0])]
        lines = [f"Method : {comp.name}    [{comp.status}]"]
        if comp.vb:
            lines.append(f"VB  ({comp.vb.file}:{comp.vb.line}): {comp.vb.signature}")
        if comp.cs:
            lines.append(f"C#  ({comp.cs.file}:{comp.cs.line}): {comp.cs.signature}")
        if comp.vb and comp.cs:
            crit = "  ".join(f"{c.code}={c.label}" for c in comp.criteria)
            lines.append(f"Tiêu chí: {crit}   |   Similarity: {comp.similarity:.2f}   |   Score: {comp.score:.0f}/100")
        if comp.notes:
            lines.append("Ghi chú:")
            lines.extend(f"  - {n}" for n in comp.notes)
        if comp.ai_status:
            lines.append(f"AI đánh giá [{comp.ai_status}]:")
            lines.append(f"  {comp.ai_comment or '(không có nội dung)'}")
        if comp.ai_suggestion:
            lines.append(f"AI đề xuất giải pháp: {comp.ai_suggestion}")
            if comp.ai_suggestion_detail or comp.ai_suggestion_code:
                lines.append("  (Giải thích chi tiết + code đề xuất: xem sheet mô tả "
                             "của method này trong báo cáo Excel)")
        self._set_text(self.detail_text, "\n".join(lines))
        self._set_text(self.code_vb_text,
                       f"{comp.vb.signature}\n{comp.vb.body}" if comp.vb else "(không có)")
        self._set_text(self.code_cs_text,
                       f"{comp.cs.signature}\n{comp.cs.body}" if comp.cs else "(không có)")

    # ---------- Export ----------
    def on_export(self):
        if not self.result:
            return
        # Dot 9b: ten mac dinh kem timestamp de cac lan export khong ghi de nhau
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"migration_report_{stamp}.xlsx")
        if not path:
            return
        try:
            export_excel(self.result, path)
            messagebox.showinfo("Hoàn tất", f"Đã xuất báo cáo:\n{path}")
        except Exception as e:
            messagebox.showerror("Lỗi export", str(e))


def main():
    root = tk.Tk()
    try:
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "aqua" in style.theme_names():
            style.theme_use("aqua")
    except tk.TclError:
        pass
    MigrationCheckerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
