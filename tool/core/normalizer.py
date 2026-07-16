"""Chuan hoa body method VB va C# ve dang token trung tinh de so sanh logic.

Muc dich: code moi duoc viet lai 80-120% nen khong the so text tho;
ca hai ben duoc dua ve cung mot "ngon ngu trung gian" roi so khop token.
Chuoi literal (bao gom SQL Oracle/PostgreSQL) bi thay bang "S" de khong
lam sai lech diem — dung chu truong khoan dung voi thay doi tang DB.
"""

import re

# ---------- Tien xu ly chung ----------

_STRING_RE = re.compile(r'"(?:[^"\\]|\\.)*"')
_VB_STRING_RE = re.compile(r'"(?:[^"]|"")*"')


def _replace_strings(text: str, vb: bool) -> str:
    pattern = _VB_STRING_RE if vb else _STRING_RE
    return pattern.sub(" S ", text)


def strip_vb_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        result, in_string = [], False
        for ch in line:
            if ch == '"':
                in_string = not in_string
            if ch == "'" and not in_string:
                break
            result.append(ch)
        out.append("".join(result))
    return "\n".join(out)


# ---------- Khoan dung tang DB (documents/04) ----------
# Code truy cap du lieu "plumbing" (mo ket noi, gan parameter, chuoi SQL) va
# chuoi LINQ EF Core (_context...) duoc dua ve cung token trung tinh "db" o ca
# 2 phia, vi thay doi ADO.NET/Oracle -> EF Core/PostgreSQL la co chu dich.
# Logic nghiep vu (if/loop/gan gia tri/return) van duoc giu nguyen de so sanh.

_VB_DB_SKIP_RE = re.compile(
    r"^(?:Using\s+\w+\s+As\s+New\s+\w*(?:Connection|Command|DataAdapter)\b"
    r"|\w+\.Open(?:Async)?\s*\("
    r"|[\w\.]*\bParameters\.Add"
    r"|Dim\s+(?:sql|strsql|sqlstr|query|sqltext)\s+As\s+String\s*=\s*S\s*$)",
    re.I)

_CS_DB_SKIP_RE = re.compile(
    r"^(?:using\s*\(?\s*(?:var\s+)?\w+\s*=\s*new\s+\w*(?:Connection|Command|DataAdapter)\b"
    r"|\w+\.Open(?:Async)?\s*\("
    r"|[\w\.]*\bParameters\.Add"
    r"|(?:var|string)\s+(?:sql|strsql|sqlstr|query|sqltext)\s*=\s*S\s*$)",
    re.I)

_EXEC_CALL_RE = re.compile(
    r"[\w\.]*\.Execute(?:Scalar|NonQuery|Reader)(?:Async)?\s*\(\s*\)", re.I)
_FILL_CALL_RE = re.compile(r"[\w\.]*\.Fill\s*\([^)]*\)", re.I)
# Chuoi LINQ EF Core: tu "_context." / "context." den het statement -> "db"
_CS_CONTEXT_RE = re.compile(r"(?:await\s+)?\b_?\w*context\.\S.*$", re.I)


# ---------- Bang mapping token dung chung ----------

# Cac ten class/API rieng cua tung DB provider -> token trung tinh
_DB_TOKEN_MAP = {
    "oracleconnection": "dbconnection", "npgsqlconnection": "dbconnection",
    "sqlconnection": "dbconnection",
    "oraclecommand": "dbcommand", "npgsqlcommand": "dbcommand",
    "sqlcommand": "dbcommand",
    "oracledataadapter": "dbadapter", "npgsqldataadapter": "dbadapter",
    "addwithvalue": "add",
    "executereaderasync": "executereader", "executenonqueryasync": "executenonquery",
    "executescalarasync": "executescalar", "openasync": "open",
}

_VB_TYPE_WORDS = {
    "integer": "int", "long": "long", "short": "short", "string": "string",
    "boolean": "bool", "decimal": "decimal", "double": "double",
    "single": "float", "date": "datetime", "object": "object",
    "byte": "byte", "char": "char",
}


def normalize_vb_body(body: str) -> list:
    """Chuan hoa body VB -> danh sach token."""
    text = strip_vb_comments(body)
    text = _replace_strings(text, vb=True)

    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        # Bo cac dong thuan cu phap
        if re.match(r"^(End\s+(If|Using|While|Try|Select|Sub|Function)|Next\b|Loop\b)", s, re.I):
            continue
        # Khoan dung tang DB: bo dong plumbing ADO.NET, thay Execute*/Fill bang "db"
        if _VB_DB_SKIP_RE.match(s):
            continue
        s = _EXEC_CALL_RE.sub(" db ", s)
        s = _FILL_CALL_RE.sub(" db ", s)
        if not s.strip():
            continue
        # For Each x As T In xs -> foreach T x in xs
        s = re.sub(r"^For\s+Each\s+(\w+)\s+As\s+([\w\.\(\)]+)\s+In\s+(.+)$",
                   r"foreach \2 \1 in \3", s, flags=re.I)
        # For i As T = a To b -> for T i = a to b
        s = re.sub(r"^For\s+(\w+)\s+As\s+([\w\.]+)\s*=\s*(.+)\s+To\s+(.+)$",
                   r"for \2 \1 = \3 to \4", s, flags=re.I)
        # Dim x As New T(...) -> var x = new T(...)
        s = re.sub(r"^Dim\s+(\w+)\s+As\s+New\s+(.+)$", r"var \1 = new \2", s, flags=re.I)
        # Dim x As T = v -> T x = v
        s = re.sub(r"^Dim\s+(\w+)\s+As\s+([^=]+?)\s*=\s*(.+)$", r"\2 \1 = \3", s, flags=re.I)
        # Dim x As T -> T x
        s = re.sub(r"^Dim\s+(\w+)\s+As\s+(.+)$", r"\2 \1", s, flags=re.I)
        # Dim x = v -> var x = v
        s = re.sub(r"^Dim\s+(\w+)\s*=\s*(.+)$", r"var \1 = \2", s, flags=re.I)
        # Using x As New T(...) -> using var x = new T(...)
        s = re.sub(r"^Using\s+(\w+)\s+As\s+New\s+(.+)$", r"using var \1 = new \2", s, flags=re.I)
        s = re.sub(r"^Using\s+(\w+)\s*=\s*(.+)$", r"using var \1 = \2", s, flags=re.I)
        lines.append(s)

    text = "\n".join(lines)

    # Toan tu / keyword VB -> trung tinh
    replacements = [
        (r"\bIsNot\s+Nothing\b", "!= null"), (r"\bIs\s+Nothing\b", "== null"),
        (r"\bNothing\b", "null"), (r"\bAndAlso\b", "&&"), (r"\bOrElse\b", "||"),
        (r"\bAnd\b", "&&"), (r"\bOr\b", "||"), (r"\bNot\s+", "! "),
        (r"\bMe\.", ""), (r"\bTrue\b", "true"), (r"\bFalse\b", "false"),
        (r"\bThen\b", ""), (r"\bElseIf\b", "else if"), (r"\bElse\b", "else"),
        (r"\bReturn\b", "return"), (r"\bIf\b", "if"), (r"\bWhile\b", "while"),
        (r"\bTry\b", "try"), (r"\bCatch\b", "catch"), (r"\bFinally\b", "finally"),
        (r"\bThrow\b", "throw"), (r"\bNew\b", "new"), (r"\bSelect\s+Case\b", "switch"),
        (r"\bCase\b", "case"), (r"\bExit\s+(Sub|Function)\b", "return"),
        (r"\bCInt\b", "int"), (r"\bCLng\b", "long"), (r"\bCDec\b", "decimal"),
        (r"\bCDbl\b", "double"), (r"\bCStr\b", "string"), (r"\bCBool\b", "bool"),
        (r"\bCType\b", "cast"), (r"\bDirectCast\b", "cast"),
        (r"(?<!&)&(?!&)", "+"),  # noi chuoi (& don le; khong duoc dinh vao && sinh ra tu AndAlso)
        (r"\(Of\s+([\w\.,\s]+)\)", r"<\1>"),  # generic
        (r"(\d+(?:\.\d+)?)[DFRL]\b", r"\1"),  # hau to literal: 0.1D -> 0.1
    ]
    for pat, rep in replacements:
        text = re.sub(pat, rep, text, flags=re.I)

    for word, canon in _VB_TYPE_WORDS.items():
        text = re.sub(rf"\b{word}\b", canon, text, flags=re.I)

    return _tokenize(text)


def normalize_cs_body(body: str) -> list:
    """Chuan hoa body C# -> danh sach token (body da duoc strip comment o parser)."""
    text = _replace_strings(body, vb=False)
    # Tach theo statement ({ } ;) — mot chuoi LINQ nhieu dong = 1 statement
    lines = []
    for st in re.split(r"[{};]", text):
        s = " ".join(st.split())
        if not s:
            continue
        if _CS_DB_SKIP_RE.match(s):
            continue
        s = _CS_CONTEXT_RE.sub(" db ", s)
        s = _EXEC_CALL_RE.sub(" db ", s)
        s = _FILL_CALL_RE.sub(" db ", s)
        if not s.strip():
            continue
        lines.append(s)
    text = "\n".join(lines)
    replacements = [
        (r"\bawait\s+", ""), (r"\bthis\.", ""),
        (r"\bConvert\.ToInt32\b", "int"), (r"\bConvert\.ToInt64\b", "long"),
        (r"\bConvert\.ToDecimal\b", "decimal"), (r"\bConvert\.ToDouble\b", "double"),
        (r"\bConvert\.ToBoolean\b", "bool"), (r"\bConvert\.ToString\b", "string"),
        (r"\(\s*(int|long|decimal|double|float|string|bool|byte|char)\s*\)", r" \1 "),  # cast
        (r"(\d+(?:\.\d+)?)[mMdDfFlLuU]+\b", r"\1"),  # hau to literal: 0.1m -> 0.1
        (r"\bString\b", "string"), (r"\bInt32\b", "int"), (r"\bInt64\b", "long"),
        (r"\bBoolean\b", "bool"),
    ]
    for pat, rep in replacements:
        text = re.sub(pat, rep, text)
    return _tokenize(text)


_TOKEN_RE = re.compile(r"[A-Za-z_]\w*|\d+(?:\.\d+)?|==|!=|<=|>=|&&|\|\||[+\-*/%=<>!]")


def _tokenize(text: str) -> list:
    tokens = []
    for tok in _TOKEN_RE.findall(text):
        low = tok.lower()
        low = _DB_TOKEN_MAP.get(low, low)
        # Bo hau to Async (quy uoc dat ten cua C#): GetListAsync ~ GetList
        if len(low) > 5 and low.endswith("async"):
            low = low[:-5]
        tokens.append(low)
    return tokens


# ---------- Dem cau truc dieu khien ----------

def count_structures_vb(body: str) -> dict:
    text = _replace_strings(strip_vb_comments(body), vb=True)
    n_if = len(re.findall(r"\bIf\b", text, re.I)) - len(re.findall(r"\bEnd\s+If\b", text, re.I))
    n_if += len(re.findall(r"\bElseIf\b", text, re.I))
    n_loop = len(re.findall(r"^\s*(For|While|Do)\b", text, re.I | re.M))
    n_try = len(re.findall(r"\bTry\b", text, re.I)) - len(re.findall(r"\bEnd\s+Try\b", text, re.I))
    n_return = len(re.findall(r"\b(Return|Exit\s+(?:Sub|Function))\b", text, re.I))
    n_throw = len(re.findall(r"\bThrow\b", text, re.I))
    return {"if": n_if, "loop": n_loop, "try": n_try, "return": n_return, "throw": n_throw}


def count_structures_cs(body: str) -> dict:
    text = _replace_strings(body, vb=False)
    n_if = len(re.findall(r"\bif\b", text))
    n_loop = len(re.findall(r"\b(for|foreach|while)\b", text))
    n_try = len(re.findall(r"\btry\b", text))
    n_return = len(re.findall(r"\breturn\b", text))
    n_throw = len(re.findall(r"\bthrow\b", text))
    return {"if": n_if, "loop": n_loop, "try": n_try, "return": n_return, "throw": n_throw}
