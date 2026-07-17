"""Xuat ket qua scan ra JSON va so sanh 2 lan scan (dot 3 — documents/03 muc 10.8).

Dung de theo doi tien do fix giua cac dot migrate:
  python tool/cli.py <vb> <cs> --json lan2.json --baseline lan1.json
"""

import json
from datetime import datetime
from pathlib import Path


def apply_timestamp(path: str, when: datetime = None) -> str:
    """Thay token {ts} trong duong dan export bang timestamp YYYYMMDD_HHMMSS.

    Dot 9b: giup ten file export khong trung nhau giua cac lan xuat
    (vd --out report_{ts}.xlsx). Khong co token -> tra ve nguyen ven
    (giu tuong thich script/CI cu dung ten co dinh).
    """
    if "{ts}" not in (path or ""):
        return path
    stamp = (when or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return path.replace("{ts}", stamp)

_STATUS_RANK = {"PASS": 0, "WARNING": 1, "FAIL": 2, "MISSING": 3, "EXTRA": 1}
_SCORE_TOLERANCE = 5.0  # giam qua 5 diem cung tinh la xau di


def _method_key(comp) -> str:
    """Khoa nhan dang mot dong so sanh giua 2 lan scan (ten + file de phan biet overload)."""
    vb_file = comp.vb.file if comp.vb else "-"
    cs_file = comp.cs.file if comp.cs else "-"
    return f"{comp.name.lower()}|{vb_file}|{cs_file}"


def result_to_dict(result) -> dict:
    return {
        "scanned_at": result.scanned_at,
        "vb_folder": result.vb_folder,
        "cs_folder": result.cs_folder,
        "cs_scan_folder": result.cs_scan_folder,
        "summary": result.count_by_status(),
        "average_score": result.average_score(),
        "methods": [
            {
                "key": _method_key(c),
                "name": c.name,
                "status": c.status,
                "score": c.score if (c.vb and c.cs) else None,
                "similarity": c.similarity if (c.vb and c.cs) else None,
                "vb_file": c.vb.file if c.vb else None,
                "cs_file": c.cs.file if c.cs else None,
                "notes": c.notes,
                # Dot 6: lop danh gia AI (null khi chua chay) — diff_reports
                # khong doc cac key nay nen baseline cu van dung duoc
                "ai_status": c.ai_status or None,
                "ai_comment": c.ai_comment or None,
                # Dot 12: AI de xuat giai phap (null khi PASS/chua chay)
                "ai_suggestion": c.ai_suggestion or None,
                "ai_suggestion_detail": c.ai_suggestion_detail or None,
                "ai_suggestion_code": c.ai_suggestion_code or None,
            }
            for c in result.comparisons
        ],
    }


def save_json(result, out_path: str) -> str:
    Path(out_path).write_text(
        json.dumps(result_to_dict(result), ensure_ascii=False, indent=2),
        encoding="utf-8")
    return out_path


def load_json(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Khong tim thay file baseline: {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise ValueError(f"File baseline khong phai JSON hop le: {e}") from e


def diff_reports(baseline: dict, result) -> dict:
    """So sanh lan scan hien tai voi baseline JSON cua lan truoc.

    Tra ve dict:
      improved  [(name, status_cu, status_moi)]      trang thai tot len
      regressed [(name, status_cu, status_moi, ghi_chu)]  xau di (ke ca tut diem > 5)
      added     [(name, status)]                     dong moi xuat hien
      removed   [(name, status_cu)]                  dong bien mat
    """
    old = {m["key"]: m for m in baseline.get("methods", [])}
    new = {_method_key(c): c for c in result.comparisons}

    improved, regressed, added, removed = [], [], [], []
    for key, comp in new.items():
        if key not in old:
            added.append((comp.name, comp.status))
            continue
        o = old[key]
        old_rank = _STATUS_RANK.get(o["status"], 1)
        new_rank = _STATUS_RANK.get(comp.status, 1)
        if new_rank < old_rank:
            improved.append((comp.name, o["status"], comp.status))
        elif new_rank > old_rank:
            regressed.append((comp.name, o["status"], comp.status, "trang thai xau di"))
        elif (o.get("score") is not None and comp.vb and comp.cs
              and comp.score < o["score"] - _SCORE_TOLERANCE):
            regressed.append((comp.name, o["status"], comp.status,
                              f"diem giam {o['score']:.0f} -> {comp.score:.0f}"))
    for key, m in old.items():
        if key not in new:
            removed.append((m["name"], m["status"]))
    return {"improved": improved, "regressed": regressed,
            "added": added, "removed": removed}
