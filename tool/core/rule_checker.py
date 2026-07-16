"""Rule-based check cho convert method Business Logic (dot 4 — documents/03 muc 11).

Tieu chi nam trong file rules/conversion_rules.json (nguoi dung doc + sua duoc,
khong can sua code). Module nay chi la engine: load file rule, quet body VB/C#
va so sanh cap method theo pair_rules.

Nguyen tac: rule chi THEM ghi chu "RULE <id>: ..." de reviewer doi chieu tay —
khong tru diem C1-C5. Ngoai le duy nhat: JP-MSG (message tieng Nhat bien mat =
kha nang thieu nhanh check) duoc phep nang PASS -> WARNING.
"""

import json
import re
import sys
from pathlib import Path

# String literal (giong sql_checker)
_CS_STRING_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
_VB_STRING_RE = re.compile(r'"((?:[^"]|"")*)"')
_JP_CHAR_RE = re.compile(r"[぀-ヿ一-鿿]")


def _strip_vb_comments(body: str) -> str:
    out = []
    for line in (body or "").splitlines():
        result, in_string = [], False
        for ch in line:
            if ch == '"':
                in_string = not in_string
            if ch == "'" and not in_string:
                break
            result.append(ch)
        out.append("".join(result))
    return "\n".join(out)


class Rules:
    """Bo rule da compile tu file JSON."""

    def __init__(self, data: dict = None):
        data = data or {}
        self.data = data
        self.vb_patterns = self._compile(data.get("vb_patterns", []))
        self.cs_patterns = self._compile(data.get("cs_patterns", []))
        self.pair = data.get("pair_rules", {})

    @staticmethod
    def _compile(items):
        compiled = []
        for r in items:
            try:
                rx = re.compile(r["pattern"], re.I)
            except re.error as e:
                raise ValueError(f"rule '{r.get('id', '?')}' co regex loi: {e}") from e
            compiled.append((r["id"], r["title"], rx, r.get("flags", "")))
        return compiled

    def pair_cfg(self, name: str) -> dict:
        cfg = self.pair.get(name, {})
        return cfg if cfg.get("enabled") else {}

    @property
    def empty(self) -> bool:
        return not (self.vb_patterns or self.cs_patterns or self.pair)


def load_rules(path: str) -> Rules:
    """Doc file rule JSON. path rong -> bo rule rong (tat moi check)."""
    if not path:
        return Rules()
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Khong tim thay file rule: {path}")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise ValueError(f"File rule khong phai JSON hop le: {e}") from e
    return Rules(data)


def find_default_rules() -> str:
    """Tu tim rules/conversion_rules.json: canh exe -> bundle exe -> goc repo -> cwd."""
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).parent / "rules" / "conversion_rules.json")
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            candidates.append(Path(meipass) / "rules" / "conversion_rules.json")
    candidates.append(Path(__file__).parent.parent.parent / "rules" / "conversion_rules.json")
    candidates.append(Path.cwd() / "rules" / "conversion_rules.json")
    for c in candidates:
        if c.is_file():
            return str(c)
    return ""


# ---------- Quet mot phia ----------

def _scan_targets_vb(body: str):
    no_comment = _strip_vb_comments(body)
    return no_comment, _VB_STRING_RE.sub(" S ", no_comment)


def check_vb_side(rules: Rules, body: str) -> list:
    """Quet body VB — diem khac biet ngu nghia ngam can doi chieu ben C#."""
    with_strings, stripped = _scan_targets_vb(body)
    notes = []
    for rid, title, rx, flags in rules.vb_patterns:
        target = with_strings if flags == "scan_with_strings" else stripped
        if rx.search(target):
            notes.append(f"RULE {rid}: {title} — can review (chi tiet: rules/conversion_rules.json)")
    return notes


def check_cs_side(rules: Rules, body: str) -> list:
    """Quet body C# (parser da bo comment; chi can bo string literal)."""
    stripped = _CS_STRING_RE.sub(" S ", body or "")
    notes = []
    for rid, title, rx, flags in rules.cs_patterns:
        target = (body or "") if flags == "scan_with_strings" else stripped
        if rx.search(target):
            notes.append(f"RULE {rid}: {title} — can review (chi tiet: rules/conversion_rules.json)")
    return notes


# ---------- Pair rules ----------

def _jp_messages(body: str, vb: bool) -> list:
    pattern = _VB_STRING_RE if vb else _CS_STRING_RE
    msgs = []
    for m in pattern.finditer(body or ""):
        content = m.group(1).replace('""', '"') if vb else m.group(1)
        content = content.strip()
        if content and _JP_CHAR_RE.search(content):
            msgs.append(content)
    return msgs


def check_pair_rules(rules: Rules, vb, cs) -> tuple:
    """Rule so 2 chieu tren mot cap method. Tra ve (notes, escalate_pass_to_warning)."""
    notes, escalate = [], False

    cfg = rules.pair_cfg("jp_message")
    if cfg:
        vb_msgs = _jp_messages(vb.body, vb=True)
        cs_msgs = set(_jp_messages(cs.body, vb=False))
        missing = [m for m in dict.fromkeys(vb_msgs) if m not in cs_msgs]
        for m in missing[:int(cfg.get("max_notes_per_method", 3))]:
            notes.append(
                f"RULE {cfg.get('id', 'JP-MSG')}: message '{m}' co ben VB nhung khong thay ben C# "
                "— kha nang thieu nhanh check / quen return sau Failure, can doi chieu")
        if missing and cfg.get("escalate_pass_to_warning"):
            escalate = True

    cfg = rules.pair_cfg("self_exclusion")
    if cfg:
        name_re = re.compile(cfg.get("method_name_pattern", "check|exist|dup"), re.I)
        if (name_re.search(vb.name) and re.search(r"<>|!=", vb.body or "")
                and "!=" not in (cs.body or "")):
            notes.append(
                f"RULE {cfg.get('id', 'SELF-EXCL')}: SQL cu co dieu kien <> (loai tru chinh record) "
                "nhung khong thay != ben C# — update chinh record co the bao trung sai, can review")

    cfg = rules.pair_cfg("rownum_order")
    if cfg:
        if (re.search(r"\bROWNUM\b", vb.body or "", re.I)
                and re.search(r"\.(First|FirstOrDefault|Take)", cs.body or "")
                and "OrderBy" not in (cs.body or "")):
            notes.append(
                f"RULE {cfg.get('id', 'ROWNUM-ORDER')}: First/Take khong co OrderBy trong khi SQL cu "
                "dung ROWNUM — thu tu ban ghi khong dam bao, can review")

    return notes, escalate


def validator_split_note(rules: Rules, criteria, cs_file: str, bl_folder: str) -> str:
    """VALIDATOR-SPLIT: C4/C5 lech + cung thu muc co *Validators.cs -> note doi chieu."""
    cfg = rules.pair_cfg("validator_split")
    if not cfg:
        return ""
    if not any(c.code in ("C4", "C5") and c.label != "OK" for c in criteria):
        return ""
    folder = Path(bl_folder) / Path(cs_file).parent
    try:
        has_validator = any(folder.glob("*Validators.cs")) or any(folder.glob("*Validator.cs"))
    except OSError:
        has_validator = False
    if has_validator:
        return (f"RULE {cfg.get('id', 'VALIDATOR-SPLIT')}: cung thu muc co file *Validators.cs — "
                "mot phan check co the da tach sang FluentValidation (documents/04 muc 2.6), "
                "doi chieu truoc khi ket luan thieu logic")
    return ""


# Bo rule hien hanh cua tien trinh
_current = Rules()


def get_rules() -> Rules:
    return _current


def set_rules(rules: Rules):
    global _current
    _current = rules
