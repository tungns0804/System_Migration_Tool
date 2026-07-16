"""Quet frontend .razor xac nhan diem den cua UI event (dot 3 — documents/03 muc 10.6).

Method VB dang {Control}_{Event} (btnSave_Click, Form_Load...) khong duoc convert
sang Business Logic ma chuyen thanh handler trong file .razor / .razor.cs.
Module nay index toan bo file razor duoi folder C# goc va tim handler tuong ung
de note cho cac dong MISSING la UI event — status van MISSING (dot nay chi xac
nhan diem den, chua cham diem frontend).

Luat khop (documents/03 muc 10.6):
  - {Form}_Load  <-> file {Form}.razor(.cs) co OnInitialized/OnInitializedAsync/OnAfterRender
  - {Control}_{Event}: core control (bo tien to btn/txt/...) khop core handler
    (bo tien to on/handle + hau to click/changed/async/...)
"""

import re
from pathlib import Path

# Tien to dat ten control WinForms pho bien
_CONTROL_PREFIX_RE = re.compile(
    r"^(btn|txt|cmb|cbo|chk|rdo|dgv|lst|cmd|mnu|lbl|frm|pnl)", re.I)

# Handler: bo tien to on/handle, hau to async + ten event
_HANDLER_PREFIX_RE = re.compile(r"^(on|handle)", re.I)
_HANDLER_SUFFIX_RE = re.compile(
    r"(click|clicked|changed|change|textchanged|keydown|keyup|keypress"
    r"|input|submit|selected)$", re.I)

# Method khai bao trong @code / class partial cua razor
_RAZOR_METHOD_RE = re.compile(
    r"\b(?:void|Task|Task<[^>]+>)\s+(\w+)\s*\(")
# Handler gan truc tiep vao attribute: @onclick="OnSave" / @onchange=OnChanged
_RAZOR_ATTR_RE = re.compile(r"@on\w+\s*=\s*\"?@?(\w+)")

_LIFECYCLE_RE = re.compile(r"\bOnInitialized(?:Async)?\b|\bOnAfterRender(?:Async)?\b")


def _handler_core(name: str) -> str:
    s = _HANDLER_PREFIX_RE.sub("", name.lower(), count=1)
    if s.endswith("async") and len(s) > 5:
        s = s[:-5]
    s = _HANDLER_SUFFIX_RE.sub("", s, count=1)
    return s or name.lower()


def _control_core(control: str) -> str:
    s = _CONTROL_PREFIX_RE.sub("", control.lower(), count=1)
    return s or control.lower()


class RazorIndex:
    """Chi muc handler trong cac file .razor / .razor.cs."""

    def __init__(self):
        self.files = []          # [(ten_file_hien_thi, stem_lower, has_lifecycle)]
        self.handlers = []       # [(handler_name, core, ten_file_hien_thi)]
        self.file_count = 0

    def add_file(self, display: str, stem: str, text: str):
        self.file_count += 1
        names = set(_RAZOR_METHOD_RE.findall(text)) | set(_RAZOR_ATTR_RE.findall(text))
        self.files.append((display, stem.lower(), bool(_LIFECYCLE_RE.search(text))))
        for n in names:
            self.handlers.append((n, _handler_core(n), display))

    def find_handler(self, vb_event_name: str):
        """Tim handler frontend cho UI event VB. Tra ve mo ta hoac None."""
        if "_" not in vb_event_name:
            return None
        control, event = vb_event_name.rsplit("_", 1)
        event = event.lower()

        # {Form}_Load -> file cung ten co lifecycle method
        if event == "load":
            for display, stem, has_lifecycle in self.files:
                if stem == control.lower() and has_lifecycle:
                    return f"OnInitializedAsync trong {display}"
            return None

        core = _control_core(control)
        for name, hcore, display in self.handlers:
            if hcore == core or (len(core) >= 3 and (core in hcore or hcore in core)):
                return f"handler '{name}' trong {display}"
        return None


def build_razor_index(root: str) -> RazorIndex:
    """Quet de quy *.razor va *.razor.cs duoi folder goc he thong moi."""
    base = Path(root)
    index = RazorIndex()
    for path in sorted(base.rglob("*.razor")):
        index.add_file(str(path.relative_to(base)), path.stem,
                       path.read_text(encoding="utf-8", errors="replace"))
    for path in sorted(base.rglob("*.razor.cs")):
        stem = path.name[:-len(".razor.cs")]
        index.add_file(str(path.relative_to(base)), stem,
                       path.read_text(encoding="utf-8", errors="replace"))
    return index
