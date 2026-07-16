"""Kiem tra SQL trong body method (dot 3 — documents/03 muc 10.5).

Muc tieu: bat loi migration tang SQL Oracle 19c -> PostgreSQL 17:
  1. SQL phia C# con cu phap rieng cua Oracle (NVL, ROWNUM, SYSDATE, DUAL,
     .NEXTVAL, DECODE, join (+)) — chac chan loi runtime tren PostgreSQL.
  2. Tap bang truy cap 2 ben lech nhau (chi so sanh khi ca 2 ben deu co SQL;
     phia C# dung EF Core/LINQ khong co SQL thi bo qua, khong phat).

Chi lam viec tren string literal trong body — khong doc file .sql rieng.
"""

import re

from .config import get_config

# String literal: C# "..." (co escape \") — VB "..." (escape "")
_CS_STRING_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
_VB_STRING_RE = re.compile(r'"((?:[^"]|"")*)"')

_SQL_HINT_RE = re.compile(
    r"\b(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|MERGE\s+INTO)\b", re.I)

# Ten bang sau FROM / JOIN / INTO / UPDATE (bo alias, bo subquery)
_TABLE_RE = re.compile(
    r"\b(?:FROM|JOIN|INTO|UPDATE)\s+([A-Za-z_][\w\.]*)", re.I)

_SQL_KEYWORD_NOT_TABLE = {"dual", "select"}


def extract_sql_strings(body: str, vb: bool) -> list:
    """Lay cac string literal trong body co dang cau lenh SQL."""
    pattern = _VB_STRING_RE if vb else _CS_STRING_RE
    sqls = []
    for m in pattern.finditer(body or ""):
        content = m.group(1)
        if _SQL_HINT_RE.search(content):
            sqls.append(content)
    return sqls


def find_oracle_leftovers(sql: str) -> list:
    """Tra ve danh sach cu phap Oracle con sot trong mot cau SQL."""
    cfg = get_config()
    return [label for label, rx in cfg.oracle_res.items() if rx.search(sql)]


def extract_tables(sql: str) -> set:
    """Tap ten bang duoc SQL truy cap (lower, bo schema prefix)."""
    tables = set()
    for m in _TABLE_RE.finditer(sql):
        name = m.group(1).split(".")[-1].lower()
        if name not in _SQL_KEYWORD_NOT_TABLE:
            tables.add(name)
    return tables


def check_pair_sql(vb_body: str, cs_body: str):
    """Kiem tra SQL cua mot cap method VB <-> C#.

    Tra ve (notes, has_oracle_leftover):
      notes                 danh sach ghi chu de gan vao MethodComparison
      has_oracle_leftover   True -> status toi thieu phai WARNING
    """
    notes, has_leftover = [], False
    cs_sqls = extract_sql_strings(cs_body, vb=False)

    leftovers = sorted({l for sql in cs_sqls for l in find_oracle_leftovers(sql)})
    if leftovers:
        has_leftover = True
        notes.append(
            f"SQL: con cu phap Oracle ({', '.join(leftovers)}) trong SQL phia C# "
            "— se loi tren PostgreSQL, can sua")

    vb_sqls = extract_sql_strings(vb_body, vb=True)
    if vb_sqls and cs_sqls:
        vb_tables = set().union(*(extract_tables(s) for s in vb_sqls))
        cs_tables = set().union(*(extract_tables(s) for s in cs_sqls))
        missing = sorted(vb_tables - cs_tables)
        if missing:
            notes.append(
                f"SQL: bang {', '.join(t.upper() for t in missing)} co o SQL phia VB "
                "nhung khong thay trong SQL phia C# — can review")
    return notes, has_leftover


def check_extra_sql(cs_body: str):
    """Quet leftover Oracle cho method chi co phia C# (EXTRA). Tra ve notes."""
    leftovers = sorted({l for sql in extract_sql_strings(cs_body, vb=False)
                        for l in find_oracle_leftovers(sql)})
    if leftovers:
        return [f"SQL: con cu phap Oracle ({', '.join(leftovers)}) — se loi tren PostgreSQL, can sua"]
    return []
