"""CLI cua Migration Checker — chay scan + export Excel/JSON khong can GUI.

Cach dung:
    python tool/cli.py <folder_VB> <folder_ASPCore> [--out report.xlsx]
        [--map mapping.csv] [--config config.json]
        [--json report.json] [--baseline lan_truoc.json]
        [--fail-on FAIL,MISSING] [--min-score 85]

Exit code (dung cho CI — documents/03 muc 10.7):
    0  dat
    1  loi input (folder/file khong hop le)
    2  khong dat nguong chat luong (--fail-on / --min-score)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.comparator import scan_folders
from core.excel_exporter import export_excel
from core.mapping import load_mapping
from core.config import load_config, get_config
from core.llm_reviewer import review_result, resolve_provider, effective_model
from core.report_io import save_json, load_json, diff_reports, apply_timestamp
from core.models import (STATUS_PASS, STATUS_WARNING, STATUS_FAIL,
                         STATUS_MISSING, STATUS_EXTRA, AI_PASS, AI_WARNING)

_ALL_STATUSES = (STATUS_PASS, STATUS_WARNING, STATUS_FAIL, STATUS_MISSING, STATUS_EXTRA)


def _print_diff(diff):
    print()
    print("=== So sanh voi baseline (lan scan truoc) ===")
    if not any(diff.values()):
        print("Khong co thay doi nao so voi baseline.")
        return
    for name, old, new in diff["improved"]:
        print(f"  [TOT LEN ] {name:<28} {old} -> {new}")
    for name, old, new, why in diff["regressed"]:
        print(f"  [XAU DI  ] {name:<28} {old} -> {new} ({why})")
    for name, status in diff["added"]:
        print(f"  [MOI     ] {name:<28} {status}")
    for name, status in diff["removed"]:
        print(f"  [BIEN MAT] {name:<28} (truoc la {status})")
    print(f"Tong: tot len {len(diff['improved'])} · xau di {len(diff['regressed'])}"
          f" · moi {len(diff['added'])} · bien mat {len(diff['removed'])}")


def _check_quality_gate(result, fail_on: set, min_score: float) -> list:
    """Tra ve danh sach ly do khong dat nguong (rong = dat)."""
    reasons = []
    if fail_on:
        for comp in result.comparisons:
            if comp.status not in fail_on:
                continue
            # EXTRA thuoc kien truc moi va MISSING da co handler frontend khong tinh
            if comp.status == STATUS_EXTRA and comp.is_new_arch:
                continue
            if comp.status == STATUS_MISSING and comp.has_frontend_handler:
                continue
            reasons.append(f"method '{comp.name}' co status {comp.status}")
    if min_score is not None and result.average_score() < min_score:
        reasons.append(f"diem trung binh {result.average_score()} < nguong {min_score}")
    return reasons


def main():
    parser = argparse.ArgumentParser(
        description="Kiem tra chat luong migration backend VB.NET -> ASP.NET Core")
    parser.add_argument("vb_folder", help="Folder source VB.NET (he thong cu)")
    parser.add_argument("cs_folder", help="Folder source C# ASP.NET Core (he thong moi)")
    parser.add_argument("--out", default="",
                        help="Duong dan file Excel bao cao (.xlsx). Ho tro token {ts} "
                             "de tu chen timestamp tranh trung ten (vd report_{ts}.xlsx)")
    parser.add_argument("--no-detect", action="store_true",
                        help="Tat auto-detect thu muc Business Logic (quet toan bo folder C#)")
    parser.add_argument("--map", default="", metavar="FILE",
                        help="File mapping ten method thu cong (CSV 'TenVB,TenCSharp' hoac JSON)")
    parser.add_argument("--config", default="", metavar="FILE",
                        help="File config.json ghi de trong so/nguong/khoan dung (xem config.sample.json)")
    parser.add_argument("--rules", default="", metavar="FILE",
                        help="File rule check convert (mac dinh tu tim rules/conversion_rules.json)")
    parser.add_argument("--llm", action="store_true",
                        help="Bat gate danh gia AI qua Claude API cho lan chay nay "
                             "(hoac bat co dinh bang llm.enabled trong config.json)")
    parser.add_argument("--json", default="", metavar="FILE", dest="json_out",
                        help="Xuat ket qua scan ra JSON (dung lam baseline cho lan sau)")
    parser.add_argument("--baseline", default="", metavar="FILE",
                        help="File JSON cua lan scan truoc de in bang so sanh tien do")
    parser.add_argument("--fail-on", default="", metavar="ST[,ST]",
                        help=f"Exit code 2 neu co method thuoc status liet ke ({'/'.join(_ALL_STATUSES)})")
    parser.add_argument("--min-score", type=float, default=None, metavar="N",
                        help="Exit code 2 neu diem trung binh < N")
    args = parser.parse_args()

    for folder in (args.vb_folder, args.cs_folder):
        if not Path(folder).is_dir():
            print(f"[LOI] Khong tim thay folder: {folder}")
            return 1

    fail_on = set()
    if args.fail_on:
        fail_on = {s.strip().upper() for s in args.fail_on.split(",") if s.strip()}
        invalid = fail_on - set(_ALL_STATUSES)
        if invalid:
            print(f"[LOI] --fail-on khong hop le: {', '.join(sorted(invalid))}")
            return 1

    try:
        config = load_config(args.config) if args.config else None
        mapping = load_mapping(args.map) if args.map else None
        baseline = load_json(args.baseline) if args.baseline else None
        if args.rules and not Path(args.rules).is_file():
            raise FileNotFoundError(f"Khong tim thay file rule: {args.rules}")
    except (FileNotFoundError, ValueError) as e:
        print(f"[LOI] {e}")
        return 1

    result = scan_folders(args.vb_folder, args.cs_folder,
                          auto_detect=not args.no_detect,
                          mapping=mapping, mapping_file=args.map, config=config,
                          rules_file=args.rules)
    counts = result.count_by_status()

    # Dot 6: gate danh gia AI (Claude API) — chay SAU scan, khong sua diem C1-C5
    llm_on = args.llm or get_config().llm_enabled
    ai_stats = None
    if llm_on:
        n = len(result.comparisons)
        provider = resolve_provider(get_config())
        model = effective_model(get_config(), provider)
        print(f"[AI] Dang danh gia {n} method qua {provider} API "
              f"(model {model}, cache theo hash noi dung)...")

        def _ai_progress(i, total, cached):
            print(f"\r[AI] Da cham {i}/{total} method...", end="", flush=True)

        ai_stats = review_result(result, get_config(), progress=_ai_progress)
        print("\r", end="")  # xoa dong tien do truoc khi in ket qua
        if ai_stats["error"]:
            print(f"[AI] Khong goi duoc AI API: {ai_stats['error']}")

    print(f"Scan luc      : {result.scanned_at}")
    print(f"Folder VB     : {result.vb_folder}  ({result.vb_file_count} file)")
    print(f"Folder C#     : {result.cs_folder}")
    print(f"Business Logic: {result.cs_scan_folder}  ({result.cs_file_count} file)")
    print(f"                [{result.cs_detect_note}]")
    if result.mapping_file:
        print(f"Mapping       : {result.mapping_file}  ({len(mapping)} cap ten)")
    print(f"Tong so dong so sanh: {len(result.comparisons)}")
    print("-" * 100)
    print(f"{'Method':<28} {'Status':<9} {'Score':>6} {'Sim':>6}  Notes")
    print("-" * 100)
    for comp in result.comparisons:
        sim = f"{comp.similarity:.2f}" if comp.vb and comp.cs else "-"
        score = f"{comp.score:.0f}" if comp.vb and comp.cs else "-"
        note = comp.note_text[:120]
        print(f"{comp.name:<28} {comp.status:<9} {score:>6} {sim:>6}  {note}")
    print("-" * 100)
    frontend_note = (f", da xac nhan handler frontend: {result.count_frontend_handled()}"
                     if result.count_frontend_handled() else "")
    print(f"PASS: {counts[STATUS_PASS]}  WARNING: {counts[STATUS_WARNING]}  "
          f"FAIL: {counts[STATUS_FAIL]}  MISSING: {counts[STATUS_MISSING]}{frontend_note}  "
          f"EXTRA: {counts[STATUS_EXTRA]} (trong do kien truc moi: {result.count_new_arch()})"
          f"  |  Diem TB: {result.average_score()}"
          f"  |  Method co ghi chu RULE: {result.count_rule_hits()}")
    if llm_on:
        ai = result.count_ai()
        cached = f" (cache hit: {ai_stats['cached']})" if ai_stats else ""
        print(f"AI danh gia   : PASS: {ai[AI_PASS]}  WARNING: {ai[AI_WARNING]}  "
              f"Chua danh gia: {ai['not_run']}{cached} — xem 2 cot AI trong Excel")

    if args.out:
        out_path = apply_timestamp(args.out)
        export_excel(result, out_path)
        print(f"Da xuat bao cao Excel: {out_path}")
    if args.json_out:
        json_path = apply_timestamp(args.json_out)
        save_json(result, json_path)
        print(f"Da xuat ket qua JSON: {json_path}")
    if baseline is not None:
        _print_diff(diff_reports(baseline, result))

    reasons = _check_quality_gate(result, fail_on, args.min_score)
    if reasons:
        print()
        print("[KHONG DAT] Nguong chat luong khong dat:")
        for r in reasons[:20]:
            print(f"  - {r}")
        if len(reasons) > 20:
            print(f"  ... va {len(reasons) - 20} ly do khac")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
