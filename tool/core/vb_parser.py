"""Parser trich xuat method (Sub/Function) tu source code VB.NET.

Dung regex + xu ly theo dong (du tot cho code VB thong thuong,
khong nham thay the compiler day du).
"""

import re
from pathlib import Path

from .models import MethodInfo, Parameter

# Cac modifier hop le dung truoc Sub/Function
_MODIFIERS = r"(?:Public|Private|Protected|Friend|Shared|Overridable|Overrides|Overloads|Async|NotOverridable|MustOverride)"

_METHOD_HEAD = re.compile(
    rf"^\s*(?:{_MODIFIERS}\s+)*(Sub|Function)\s+(\w+)\s*\(",
    re.IGNORECASE,
)

_RETURN_RE = re.compile(r"^\s*As\s+(.+?)\s*(?:Implements\s+[\w\.\s,]+)?\s*$", re.IGNORECASE)


def _match_method_start(line: str):
    """Tach chu ky method: (kind, name, raw_params, return_type) hoac None.

    Khong dung regex mot phat cho ca dong vi kieu tra ve generic
    (vd: As List(Of String)) chua ngoac se lam regex tham lam nuot sai
    ranh gioi tham so — thay bang dem ngoac can bang.
    """
    m = _METHOD_HEAD.match(line)
    if not m:
        return None
    kind, name = m.group(1), m.group(2)
    open_pos = m.end() - 1
    depth = 0
    close_pos = -1
    for i in range(open_pos, len(line)):
        if line[i] == "(":
            depth += 1
        elif line[i] == ")":
            depth -= 1
            if depth == 0:
                close_pos = i
                break
    if close_pos == -1:
        return None
    raw_params = line[open_pos + 1:close_pos]
    rest = line[close_pos + 1:].strip()
    ret = None
    if rest:
        rm = _RETURN_RE.match(rest)
        if rm:
            ret = rm.group(1)
        elif not rest.lower().startswith("implements"):
            return None  # phan duoi khong hop le -> khong phai chu ky method
    return kind, name, raw_params, ret

_METHOD_END = re.compile(r"^\s*End\s+(Sub|Function)\b", re.IGNORECASE)


def _strip_line_comment(line: str) -> str:
    """Xoa comment (dau ') nhung khong dong cham vao dau ' nam trong chuoi."""
    result = []
    in_string = False
    for ch in line:
        if ch == '"':
            in_string = not in_string
        if ch == "'" and not in_string:
            break
        result.append(ch)
    return "".join(result)


def _join_continuations(lines):
    """Noi cac dong ket thuc bang ' _' (line continuation cua VB)."""
    joined, buffer = [], ""
    for line in lines:
        stripped = _strip_line_comment(line).rstrip()
        if stripped.endswith(" _") or stripped == "_":
            buffer += stripped[:-1].rstrip() + " "
        else:
            joined.append(buffer + stripped)
            buffer = ""
    if buffer:
        joined.append(buffer)
    return joined


def _split_top_level(text: str, sep: str = ",") -> list:
    """Tach chuoi theo dau phay o cap ngoai cung (bo qua phay trong ngoac)."""
    parts, depth, current = [], 0, ""
    for ch in text:
        if ch in "(<":
            depth += 1
        elif ch in ")>":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current.strip())
    return parts


_PARAM_RE = re.compile(
    r"^(?:Optional\s+)?(?:ByVal\s+|ByRef\s+)?(?:ParamArray\s+)?"
    r"(\w+)(\(\))?\s*(?:As\s+(.+?))?\s*(?:=\s*.+)?$",
    re.IGNORECASE,
)


def _parse_params(raw: str) -> list:
    params = []
    raw = raw.strip()
    if not raw:
        return params
    for part in _split_top_level(raw):
        m = _PARAM_RE.match(part)
        if m:
            name, array_suffix, ptype = m.group(1), m.group(2), m.group(3) or "Object"
            if array_suffix:
                ptype = ptype + "()"
            params.append(Parameter(name=name, type=ptype.strip()))
    return params


def parse_vb_file(path: Path, base: Path) -> list:
    """Trich xuat toan bo method tu mot file .vb."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = _join_continuations(text.splitlines())

    methods = []
    current = None
    body_lines = []

    for idx, line in enumerate(lines, start=1):
        if current is None:
            m = _match_method_start(line)
            if m:
                kind, name, raw_params, ret = m
                return_type = (ret or "").strip() or ("void" if kind.lower() == "sub" else "Object")
                if kind.lower() == "sub":
                    return_type = "void"
                current = MethodInfo(
                    name=name,
                    kind=kind.lower(),
                    return_type=return_type,
                    params=_parse_params(raw_params),
                    file=str(path.relative_to(base)),
                    line=idx,
                    signature=line.strip(),
                )
                body_lines = []
        else:
            if _METHOD_END.match(line):
                current.body = "\n".join(body_lines)
                methods.append(current)
                current = None
            else:
                body_lines.append(line)

    return methods


def parse_vb_folder(folder: str):
    """Quet de quy folder, tra ve (list[MethodInfo], so_file)."""
    base = Path(folder)
    methods, file_count = [], 0
    for path in sorted(base.rglob("*.vb")):
        file_count += 1
        methods.extend(parse_vb_file(path, base))
    return methods, file_count
