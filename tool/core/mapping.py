"""Bang mapping ten method thu cong (dot 3 — documents/03 muc 10.1).

Dung cho method bi DOI TEN khi migrate (vd SearchProductByName -> FindProducts):
map theo ten tu dong se bao MISSING + EXTRA gia, nguoi dung khai bao file mapping
de tool ghep dung cap.

Dot 11 — khai bao method bi TACH thanh nhieu method (1-n): them cac cot/phan tu
tiep theo la cac MANH TACH (ten khac hoan toan). Method VB duoc ghep cap voi
method C# CHINH (cot 2); cac manh con lai duoc noi vao nhom "METHOD LIEN QUAN"
cua sheet mo ta va mang ghi chu "manh tach".

Dinh dang ho tro:
  - CSV : "TenVB,TenCSharpChinh[,ManhTach1,ManhTach2...]";
          bo qua dong trong va dong bat dau '#'
  - JSON: {"TenVB": "TenCSharp"} hoac {"TenVB": ["TenCSharpChinh", "ManhTach1", ...]}

Khong phan biet hoa thuong; hau to Async phia C# duoc bo nhu quy uoc chung.
"""

import json
from pathlib import Path


def _norm_key(name: str) -> str:
    """Ve cung dang voi khoa map cua comparator: lower + bo hau to Async."""
    key = name.strip().lower()
    if key.endswith("async") and len(key) > 5:
        key = key[:-5]
    return key


class Mapping(dict):
    """dict {key_vb: key_cs_chinh} (giu nguyen hop dong cu de moi noi dung dict)
    + splits {key_vb: [key_cs_manh_tach, ...]} cho khai bao tach 1-n (dot 11)."""

    def __init__(self):
        super().__init__()
        self.splits = {}


def load_mapping(path: str) -> Mapping:
    """Doc file mapping, tra ve Mapping {key_vb: key_cs_chinh} (da chuan hoa)."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Khong tim thay file mapping: {path}")
    text = p.read_text(encoding="utf-8-sig")

    mapping = Mapping()
    if p.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"File mapping khong phai JSON hop le: {e}") from e
        if not isinstance(data, dict):
            raise ValueError(
                "File mapping JSON phai la object {\"TenVB\": \"TenCSharp\" | [\"Chinh\", \"ManhTach\"...]}")
        items = []
        for vb_name, value in data.items():
            targets = value if isinstance(value, list) else [value]
            items.append((vb_name, [str(t) for t in targets]))
    else:
        items = []
        for lineno, line in enumerate(text.splitlines(), start=1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = [x.strip() for x in s.split(",")]
            if len(parts) < 2 or not all(parts):
                raise ValueError(
                    f"File mapping dong {lineno} sai dinh dang "
                    f"(can 'TenVB,TenCSharp[,ManhTach...]'): {line}")
            items.append((parts[0], parts[1:]))

    for vb_name, targets in items:
        if not targets or not str(targets[0]).strip():
            raise ValueError(f"File mapping: '{vb_name}' thieu ten C# dich")
        vb_key = _norm_key(vb_name)
        mapping[vb_key] = _norm_key(targets[0])
        extras = [_norm_key(t) for t in targets[1:] if str(t).strip()]
        if extras:
            mapping.splits[vb_key] = extras
    return mapping
