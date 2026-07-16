"""Parser trich xuat method tu source code C# (ASP.NET Core).

Dung regex + dem ngoac nhon (du tot cho code C# thong thuong).
Chi bat cac method co access modifier ro rang (public/private/...),
tu dong bo qua constructor, property va cau lenh dieu khien.
"""

import re
from pathlib import Path

from .models import MethodInfo, Parameter

_MODIFIERS = r"(?:public|private|protected|internal|static|async|override|virtual|abstract|sealed|new|partial|extern)"

_METHOD_SIG = re.compile(
    rf"^\s*(?:\[[^\]]*\]\s*)*((?:{_MODIFIERS}\s+)+)"
    r"([\w\.<>\[\],\s\?]+?)\s+(\w+)\s*\((.*)\)\s*(?:where\s+[^{{=]+)?(\{{|=>)?\s*$"
)

# Method expression-bodied tren 1 dong: public static Result Success() => new Result(...);
_METHOD_SIG_ARROW = re.compile(
    rf"^\s*(?:\[[^\]]*\]\s*)*((?:{_MODIFIERS}\s+)+)"
    r"([\w\.<>\[\],\s\?]+?)\s+(\w+)\s*\((.*?)\)\s*=>\s*.+$"
)

_CONTROL_KEYWORDS = {"if", "for", "foreach", "while", "switch", "catch", "using",
                     "lock", "return", "new", "else", "do", "try"}


def _strip_comments(text: str) -> str:
    """Xoa // va /* */ nhung giu nguyen noi dung trong chuoi."""
    result = []
    i, n = 0, len(text)
    in_string = in_char = in_line_comment = in_block_comment = False
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                result.append(ch)
        elif in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 1
            elif ch == "\n":
                result.append(ch)
        elif in_string:
            result.append(ch)
            if ch == "\\":
                if i + 1 < n:
                    result.append(nxt)
                    i += 1
            elif ch == '"':
                in_string = False
        elif in_char:
            result.append(ch)
            if ch == "'":
                in_char = False
        else:
            if ch == "/" and nxt == "/":
                in_line_comment = True
                i += 1
            elif ch == "/" and nxt == "*":
                in_block_comment = True
                i += 1
            elif ch == '"':
                in_string = True
                result.append(ch)
            elif ch == "'":
                in_char = True
                result.append(ch)
            else:
                result.append(ch)
        i += 1
    return "".join(result)


def _split_top_level(text: str) -> list:
    parts, depth, current = [], 0, ""
    for ch in text:
        if ch in "(<[":
            depth += 1
        elif ch in ")>]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current.strip())
    return parts


def _parse_params(raw: str) -> list:
    params = []
    raw = raw.strip()
    if not raw:
        return params
    for part in _split_top_level(raw):
        part = re.sub(r"\s*=\s*.+$", "", part)  # bo gia tri mac dinh
        part = re.sub(r"^(?:this|ref|out|in|params)\s+", "", part)
        tokens = part.rsplit(None, 1)
        if len(tokens) == 2:
            params.append(Parameter(name=tokens[1], type=tokens[0].strip()))
        elif len(tokens) == 1:
            params.append(Parameter(name=tokens[0], type="object"))
    return params


def _extract_body(text: str, start_pos: int, opener: str) -> tuple:
    """Lay than method tu vi tri sau chu ky. Tra ve (body, end_pos)."""
    if opener == "=>":
        end = text.find(";", start_pos)
        end = end if end != -1 else len(text)
        return text[start_pos:end], end
    depth = 0
    body_start = None
    i = start_pos
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
            if depth == 1:
                body_start = i + 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[body_start:i], i
        i += 1
    return text[body_start:] if body_start else "", len(text)


def parse_cs_file(path: Path, base: Path) -> list:
    """Trich xuat toan bo method tu mot file .cs."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = _strip_comments(raw)
    lines = text.splitlines()
    methods = []

    # Vi tri bat dau (offset) cua tung dong trong text
    offsets, pos = [], 0
    for line in lines:
        offsets.append(pos)
        pos += len(line) + 1

    i = 0
    while i < len(lines):
        line = lines[i]
        candidate = line
        joined_end = i
        # Noi cac dong neu chu ky method trai nhieu dong (ngoac chua dong)
        if re.match(rf"^\s*(?:\[[^\]]*\]\s*)*(?:{_MODIFIERS}\s+)+", line) and "(" in line:
            while candidate.count("(") > candidate.count(")") and joined_end + 1 < len(lines):
                joined_end += 1
                candidate = candidate + " " + lines[joined_end].strip()

        m = _METHOD_SIG.match(candidate.rstrip())
        if not m:
            m2 = _METHOD_SIG_ARROW.match(candidate.rstrip())
            if m2:
                _mods, return_type, name, raw_params = m2.groups()
                return_type = return_type.strip()
                if name not in _CONTROL_KEYWORDS and return_type not in _CONTROL_KEYWORDS:
                    arrow_at = text.find("=>", offsets[i])
                    body, end_pos = _extract_body(text, arrow_at + 2, "=>")
                    methods.append(MethodInfo(
                        name=name,
                        kind="method",
                        return_type=return_type,
                        params=_parse_params(raw_params),
                        body=body,
                        file=str(path.relative_to(base)),
                        line=i + 1,
                        signature=re.sub(r"\s+", " ", candidate.strip()).rstrip(";").strip(),
                    ))
                    consumed = text[:end_pos].count("\n")
                    i = max(i + 1, consumed + 1)
                    continue
        if m:
            _mods, return_type, name, raw_params, opener = m.groups()
            return_type = return_type.strip()
            # Bo qua truong hop khong phai method
            if name in _CONTROL_KEYWORDS or return_type in _CONTROL_KEYWORDS:
                i += 1
                continue

            # Tim opener that su ({ hoac =>) neu chua co tren dong chu ky
            sig_end = offsets[joined_end] + len(lines[joined_end])
            search_from = sig_end
            if opener is None:
                rest = text[sig_end:sig_end + 200].lstrip()
                if rest.startswith("=>"):
                    opener = "=>"
                elif rest.startswith("{"):
                    opener = "{"
                else:
                    i += 1
                    continue
            body, end_pos = _extract_body(text, offsets[i], opener)

            methods.append(MethodInfo(
                name=name,
                kind="method",
                return_type=return_type,
                params=_parse_params(raw_params),
                body=body,
                file=str(path.relative_to(base)),
                line=i + 1,
                signature=re.sub(r"\s+", " ", candidate.strip()).rstrip("{").strip(),
            ))
            # Nhay qua het body
            consumed = text[:end_pos].count("\n")
            i = max(i + 1, consumed + 1)
            continue
        i += 1

    return methods


def parse_cs_folder(folder: str):
    """Quet de quy folder, tra ve (list[MethodInfo], so_file)."""
    base = Path(folder)
    methods, file_count = [], 0
    for path in sorted(base.rglob("*.cs")):
        file_count += 1
        methods.extend(parse_cs_file(path, base))
    return methods, file_count
