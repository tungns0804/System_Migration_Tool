"""Cau hinh tool (dot 3 — documents/03 muc 10.2).

Moi gia tri truoc day hardcode trong comparator/normalizer duoc gom ve day.
Nguoi dung co the ghi de bang file config.json (xem config.sample.json o goc
repo); thieu key nao thi dung gia tri mac dinh key do — vi vay hanh vi mac
dinh (khong co file config) GIONG HET cac dot truoc.
"""

import copy
import json
import re
from pathlib import Path

# Gia tri mac dinh = dung bang hang so cua dot 1/2 (khong duoc doi)
DEFAULTS = {
    # Trong so C1..C5 (documents/03 muc 4)
    "weights": {"C1": 30.0, "C2": 20.0, "C3": 15.0, "C4": 15.0, "C5": 20.0},
    "thresholds": {
        "sim_ok": 0.75,        # C5: >= la OK
        "sim_warn": 0.5,       # C5: >= la WARN
        "bag_warn": 0.8,       # C5: token-bag >= nang NG->WARN (task 4)
        "score_pass": 85.0,    # tong diem >= la PASS (neu khong co WARN/NG)
        "score_fail": 60.0,    # tong diem < la FAIL
        "c4_light": 2,         # C4: tong lech <= -> WARN nhe
        "c4_heavy": 4,         # C4: tong lech <= -> WARN nang
        # Ti le diem khi WARN (nhan voi trong so tieu chi)
        "c3_warn_ratio": 10.0 / 15.0,
        "c4_light_ratio": 11.0 / 15.0,
        "c4_heavy_ratio": 6.0 / 15.0,
        "c5_warn_ratio": 12.0 / 20.0,
    },
    # Thanh phan moi cua kien truc CQRS (documents/04 muc 4.4) — khong phai thua code
    "new_arch": {
        "method_names": ["handle", "configure", "success", "failure", "validate"],
        "file_patterns": [
            r"(validators?\.cs$|dtos?\.cs$|result\.cs$|baseentity\.cs$|configuration\.cs$)"
            r"|[\\/](dtos?|common)[\\/]",
        ],
    },
    # Hau to nhan dien UI event cua WinForms
    "ui_event_suffixes": [
        "click", "load", "shown", "closing", "closed", "textchanged",
        "selectedindexchanged", "checkedchanged", "keydown", "keyup", "keypress",
        "validating", "validated", "cellclick", "cellvaluechanged",
        "leave", "enter", "doubleclick",
    ],
    # Task 5: quet SQL phia C# con cu phap Oracle (khong chay duoc tren PostgreSQL).
    # TO_DATE/TO_CHAR/|| khong quet vi PostgreSQL ho tro.
    "sql_check": {
        "enabled": True,
        "oracle_patterns": {
            "NVL(": r"\bNVL\s*\(",
            "DECODE(": r"\bDECODE\s*\(",
            "ROWNUM": r"\bROWNUM\b",
            "SYSDATE": r"\bSYSDATE\b",
            "FROM DUAL": r"\bFROM\s+DUAL\b",
            ".NEXTVAL": r"\.\s*NEXTVAL\b",
            "(+) join": r"\(\s*\+\s*\)",
        },
    },
    # Task 6: quet *.razor xac nhan UI event MISSING da co handler frontend
    "razor_scan": {"enabled": True},
    # Dot 4: rule-based check convert method (documents/03 muc 11). file rong -> tu tim
    # rules/conversion_rules.json (canh exe / goc repo); enabled=false de tat han.
    "rules": {"enabled": True, "file": ""},
    # Dot 9 (documents/03 muc 15): sheet mo ta chi tiet tung method trong Excel
    # (M001, M002... — hyperlink tu sheet Detail). method_sheets=false de tat
    # (he thong cuc lon, tranh file xlsx phinh to); max_body_lines gioi han so
    # dong code in ra moi phia.
    "excel": {"method_sheets": True, "max_body_lines": 400},
    # Dot 6 (documents/03 muc 12): gate danh gia AI — lop danh gia thu 3, doc lap
    # voi C1-C5 va rule-based, KHONG anh huong diem/status.
    # api_key uu tien neu khac rong, nguoc lai doc tu bien moi truong api_key_env
    # (user doi token chi can sua config.json, khong can build lai).
    # Dot 8: provider "auto" tu nhan dien theo key — "AIza..." la Google AI Studio
    # (Gemini, co free tier), "sk-ant..." la Anthropic (Claude); ghi ro
    # "anthropic"/"google" de ep. Model khong hop provider -> tu dung model
    # mac dinh cua provider do.
    "llm": {
        "enabled": False,
        "provider": "auto",
        "model": "claude-sonnet-5",
        "api_key": "",
        "api_key_env": "ANTHROPIC_API_KEY",
        "cache_file": "",            # rong -> llm_cache.json canh exe/config
        "timeout_seconds": 60,
        "max_retries": 2,
        # dot 12: AI tra them suggestion_detail + suggestion_code (method C# day
        # du) nen can tran output lon hon — 4096 co the lam cut JSON voi method dai
        "max_output_tokens": 8192,
    },
}


class Config:
    """Goi cau hinh da merge + cac regex da compile san."""

    def __init__(self, data: dict = None):
        merged = copy.deepcopy(DEFAULTS)
        for section, value in (data or {}).items():
            if section.startswith("_"):
                continue  # key ghi chu trong file config (vd "_huong_dan")
            if section not in merged:
                raise ValueError(f"config: key khong hop le '{section}'")
            if isinstance(merged[section], dict):
                if not isinstance(value, dict):
                    raise ValueError(f"config: '{section}' phai la object")
                merged[section].update(value)
            else:
                merged[section] = value
        self.data = merged

        self.new_arch_names = {n.lower() for n in merged["new_arch"]["method_names"]}
        self.new_arch_file_re = re.compile(
            "|".join(f"(?:{p})" for p in merged["new_arch"]["file_patterns"]), re.I)
        self.ui_event_re = re.compile(
            "_(" + "|".join(merged["ui_event_suffixes"]) + ")$", re.I)
        self.oracle_res = {label: re.compile(pat, re.I)
                           for label, pat in merged["sql_check"]["oracle_patterns"].items()}

    def weight(self, code: str) -> float:
        return float(self.data["weights"][code])

    def th(self, name: str) -> float:
        return self.data["thresholds"][name]

    @property
    def sql_check_enabled(self) -> bool:
        return bool(self.data["sql_check"]["enabled"])

    @property
    def razor_scan_enabled(self) -> bool:
        return bool(self.data["razor_scan"]["enabled"])

    @property
    def rules_enabled(self) -> bool:
        return bool(self.data["rules"]["enabled"])

    @property
    def rules_file(self) -> str:
        return self.data["rules"]["file"] or ""

    @property
    def llm_enabled(self) -> bool:
        return bool(self.data["llm"]["enabled"])

    def llm(self, key: str):
        """Truy cap 1 gia tri trong section llm (dot 6)."""
        return self.data["llm"][key]

    def excel(self, key: str):
        """Truy cap 1 gia tri trong section excel (dot 9)."""
        return self.data["excel"][key]


def load_config(path: str = None) -> Config:
    """Doc config.json (path=None -> mac dinh)."""
    if not path:
        return Config()
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Khong tim thay file config: {path}")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise ValueError(f"File config khong phai JSON hop le: {e}") from e
    return Config(data)


def find_default_config(*dirs) -> str:
    """Tim file config.json dat canh exe / thu muc tool (cho GUI)."""
    for d in dirs:
        cand = Path(d) / "config.json"
        if cand.is_file():
            return str(cand)
    return ""


# Config hien hanh cua tien trinh (GUI/CLI set truoc khi scan)
_current = Config()


def get_config() -> Config:
    return _current


def set_config(cfg: Config):
    global _current
    _current = cfg
