"""So sanh method giua he thong cu (VB.NET) va he thong moi (C# / ASP.NET Core).

Trien khai cac tieu chi C1..C5 theo documents/03_Backend_Migration_Check_Spec.md:
  C1 (30d): ton tai o ca 2 ben (map theo ten, khong phan biet hoa thuong,
            hoac qua bang mapping thu cong — dot 3)
  C2 (20d): so luong + kieu tham so (theo bang mapping VB -> C#)
  C3 (15d): kieu tra ve (chap nhan Task<X> cho async)
  C4 (15d): cau truc dieu khien (if/loop/try/return/throw)
  C5 (20d): do tuong dong logic sau chuan hoa token (seq + token-bag)

Dot 3 (documents/03 muc 10): trong so/nguong doc tu config (mac dinh giu nguyen),
mapping ten thu cong, ghep overload best-match, kiem tra SQL Oracle sot,
xac nhan UI event MISSING qua .razor.
"""

import re
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

from .models import (MethodComparison, CriterionResult, ScanResult,
                     STATUS_PASS, STATUS_WARNING, STATUS_FAIL,
                     STATUS_MISSING, STATUS_EXTRA)
from .normalizer import (normalize_vb_body, normalize_cs_body,
                         count_structures_vb, count_structures_cs)
from .vb_parser import parse_vb_folder
from .cs_parser import parse_cs_folder
from .locator import find_business_logic_folder
from .config import get_config, set_config
from .sql_checker import check_pair_sql, check_extra_sql
from .razor_scanner import build_razor_index
from .rule_checker import (get_rules, set_rules, load_rules, find_default_rules,
                           check_vb_side, check_cs_side, check_pair_rules,
                           validator_split_note)

# ---------- Chuan hoa kieu du lieu ----------

_TYPE_CANON = {
    "integer": "int", "int": "int", "int32": "int",
    "long": "long", "int64": "long",
    "short": "short", "int16": "short",
    "string": "string",
    "boolean": "bool", "bool": "bool",
    "decimal": "decimal", "double": "double",
    "single": "float", "float": "float",
    "date": "datetime", "datetime": "datetime", "dateonly": "datetime",
    "object": "object", "dynamic": "object",
    "byte": "byte", "char": "char", "void": "void", "task": "void",
    "datatable": "datatable", "dataset": "datatable",
}

_LIST_LIKE = {"list", "ilist", "ienumerable", "icollection", "ireadonlylist"}
_DICT_LIKE = {"dictionary", "idictionary", "ireadonlydictionary"}


def canonical_type(raw: str) -> str:
    """Dua kieu VB hoac C# ve dang chuan de so sanh."""
    if not raw:
        return "object"
    t = raw.strip().rstrip("?").strip()
    # Mang: X() hoac X[] -> list<x>
    m = re.match(r"^([\w\.<>\(\), ]+?)\s*(\(\)|\[\])$", t)
    if m:
        return f"list<{canonical_type(m.group(1))}>"
    # Generic VB: List(Of X) -> chuyen ve List<X> truoc
    t = re.sub(r"\(Of\s+(.+)\)$", r"<\1>", t, flags=re.I)
    # Generic: Name<A, B>
    m = re.match(r"^([\w\.]+)\s*<(.+)>$", t)
    if m:
        name = m.group(1).split(".")[-1].lower()
        args = [canonical_type(a) for a in _split_generic_args(m.group(2))]
        if name == "task" or name == "valuetask":
            return args[0] if args else "void"
        if name in _LIST_LIKE:
            return f"list<{args[0]}>"
        if name in _DICT_LIKE:
            return f"dict<{','.join(args)}>"
        return f"{name}<{','.join(args)}>"
    simple = t.split(".")[-1].lower()
    return _TYPE_CANON.get(simple, simple)


def _split_generic_args(text: str) -> list:
    parts, depth, cur = [], 0, ""
    for ch in text:
        if ch in "<(":
            depth += 1
        elif ch in ">)":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def is_ui_event(name: str) -> bool:
    return bool(get_config().ui_event_re.search(name))


# ---------- Nhan dien thanh phan moi cua kien truc (documents/04 muc 4.4) ----------
# DTO / Result pattern / FluentValidation / MediatR Handler / EF Configuration
# khong ton tai ben VB — khong duoc bao la "thua code".

def is_new_arch_component(cs) -> bool:
    """Method C# thuoc thanh phan moi cua kien truc CQRS?"""
    cfg = get_config()
    if cs.name.lower() in cfg.new_arch_names:
        return True
    return bool(cfg.new_arch_file_re.search(cs.file))


def _match_key(method, mapping: dict = None) -> str:
    """Khoa map 2 he thong: ten thuong + bo hau to Async (quy uoc C#).

    mapping (chi ap dung phia VB): ten VB co trong bang mapping thu cong
    -> dung ten C# dich lam khoa (documents/03 muc 10.1).
    """
    key = method.key
    if key.endswith("async") and len(key) > 5:
        key = key[:-5]
    if mapping and key in mapping:
        key = mapping[key]
    return key


# ---------- So sanh mot cap method ----------

def _compare_params(vb, cs, comp) -> CriterionResult:
    """C2: so luong va kieu tham so."""
    max_score = get_config().weight("C2")
    vb_params, cs_params = vb.params, cs.params
    if len(vb_params) != len(cs_params):
        comp.notes.append(
            f"C2: so tham so khac nhau (VB: {len(vb_params)}, C#: {len(cs_params)})")
        return CriterionResult("C2", "NG", 0.0, max_score, "Lech so luong tham so")

    if not vb_params:
        return CriterionResult("C2", "OK", max_score, max_score)

    matched, warn = 0.0, False
    for pv, pc in zip(vb_params, cs_params):
        cv, cc = canonical_type(pv.type), canonical_type(pc.type)
        if cv == cc:
            matched += 1
        elif cv == "datatable" and cc.startswith("list<"):
            matched += 1
            warn = True
            comp.notes.append(f"C2: tham so '{pv.name}' DataTable -> {pc.type} (thay doi co chu dich khi bo ADO.NET, can review)")
        else:
            comp.notes.append(
                f"C2: tham so '{pv.name}' sai kieu (VB: {pv.type} -> C#: {pc.type})")
        if pv.name.lower() != pc.name.lower():
            warn = True
            comp.notes.append(f"C2: ten tham so khac ('{pv.name}' vs '{pc.name}')")

    score = max_score * (matched / len(vb_params))
    if matched == len(vb_params):
        return CriterionResult("C2", "WARN" if warn else "OK", score, max_score)
    return CriterionResult("C2", "NG", score, max_score, "Sai kieu tham so")


def _compare_return(vb, cs, comp) -> CriterionResult:
    """C3: kieu tra ve (Task<X> ~ X, DataTable ~ List<DTO> chi canh bao)."""
    cfg = get_config()
    max_score = cfg.weight("C3")
    warn_score = round(max_score * cfg.th("c3_warn_ratio"), 1)
    cv, cc = canonical_type(vb.return_type), canonical_type(cs.return_type)
    if cv == cc:
        return CriterionResult("C3", "OK", max_score, max_score)
    if cv == "datatable" and cc.startswith("list<"):
        comp.notes.append(
            f"C3: kieu tra ve DataTable -> {cs.return_type} (thay doi co chu dich khi bo ADO.NET, can review)")
        return CriterionResult("C3", "WARN", warn_score, max_score)
    if cv in ("bool", "void") and (cc == "result" or cc.startswith("result<")):
        comp.notes.append(
            f"C3: kieu tra ve {vb.return_type} -> {cs.return_type} (Result pattern — quy uoc kien truc moi, can review)")
        return CriterionResult("C3", "WARN", warn_score, max_score)
    comp.notes.append(f"C3: kieu tra ve khac nhau (VB: {vb.return_type} -> C#: {cs.return_type})")
    return CriterionResult("C3", "NG", 0.0, max_score, "Sai kieu tra ve")


def _compare_structure(vb, cs, comp) -> CriterionResult:
    """C4: so luong cau truc dieu khien."""
    cfg = get_config()
    max_score = cfg.weight("C4")
    sv, sc = count_structures_vb(vb.body), count_structures_cs(cs.body)
    diffs = {k: sc.get(k, 0) - sv.get(k, 0) for k in sv}
    total = sum(abs(v) for v in diffs.values())
    detail = ", ".join(f"{k}: {sv[k]}->{sc[k]}" for k, v in diffs.items() if v != 0)
    if total == 0:
        return CriterionResult("C4", "OK", max_score, max_score)
    if total <= cfg.th("c4_light"):
        comp.notes.append(f"C4: cau truc lech nhe ({detail})")
        return CriterionResult("C4", "WARN", round(max_score * cfg.th("c4_light_ratio"), 1), max_score)
    if total <= cfg.th("c4_heavy"):
        comp.notes.append(f"C4: cau truc lech ({detail})")
        return CriterionResult("C4", "WARN", round(max_score * cfg.th("c4_heavy_ratio"), 1), max_score)
    comp.notes.append(f"C4: cau truc lech nhieu ({detail})")
    return CriterionResult("C4", "NG", 0.0, max_score)


_DELETE_SQL_RE = re.compile(r"\bDELETE\s+FROM\b", re.I)
_SOFT_DELETE_RE = re.compile(r"\bIsDeleted\s*=\s*true\b", re.I)


def _bag_similarity(tv: list, tc: list) -> float:
    """Do tuong dong theo TAP token (bo qua thu tu) — documents/03 muc 10.4."""
    if not tv and not tc:
        return 1.0
    if not tv or not tc:
        return 0.0
    inter = sum((Counter(tv) & Counter(tc)).values())
    return 2.0 * inter / (len(tv) + len(tc))


def _compare_logic(vb, cs, comp) -> CriterionResult:
    """C5: do tuong dong logic sau chuan hoa token."""
    cfg = get_config()
    max_score = cfg.weight("C5")
    warn_score = round(max_score * cfg.th("c5_warn_ratio"), 1)
    tv, tc = normalize_vb_body(vb.body), normalize_cs_body(cs.body)
    sim = SequenceMatcher(None, tv, tc).ratio()
    comp.similarity = round(sim, 3)
    if sim >= cfg.th("sim_ok"):
        return CriterionResult("C5", "OK", max_score, max_score, f"similarity={sim:.2f}")
    if sim >= cfg.th("sim_warn"):
        comp.notes.append(f"C5: do tuong dong logic trung binh ({sim:.2f}) — can review")
        return CriterionResult("C5", "WARN", warn_score, max_score)
    # Khoan dung: DELETE vat ly -> soft delete (IsDeleted = true) la thay doi
    # co chu dich cua kien truc moi (documents/04 muc 4.3) -> chi canh bao
    if _DELETE_SQL_RE.search(vb.body) and _SOFT_DELETE_RE.search(cs.body):
        comp.notes.append(
            f"C5: DELETE vat ly -> soft delete IsDeleted=true (thay doi co chu dich cua kien truc moi, sim={sim:.2f}) — can review")
        return CriterionResult("C5", "WARN", warn_score, max_score)
    # Khoan dung: DataTable -> List<DTO> keo theo body doi tu adapter.Fill sang
    # mapping tung dong / EF Core LINQ — thay doi co chu dich tang DB -> chi canh bao
    if (canonical_type(vb.return_type) == "datatable"
            and canonical_type(cs.return_type).startswith("list<")):
        comp.notes.append(
            f"C5: body viet lai theo List<DTO>/EF Core thay DataTable (thay doi co chu dich tang DB, sim={sim:.2f}) — can review")
        return CriterionResult("C5", "WARN", warn_score, max_score)
    # Task 4: cung tap token nhung khac thu tu cau lenh -> nghi dao cau truc,
    # nang NG->WARN de reviewer xem tay thay vi bao FAIL oan
    bag = _bag_similarity(tv, tc)
    if bag >= cfg.th("bag_warn"):
        comp.notes.append(
            f"C5: cung tap token nhung khac thu tu cau lenh (seq={sim:.2f}, bag={bag:.2f}) "
            "— nghi dao cau truc, can review")
        return CriterionResult("C5", "WARN", warn_score, max_score)
    comp.notes.append(f"C5: logic khac biet lon ({sim:.2f}) — nhieu kha nang convert sai/viet lai")
    return CriterionResult("C5", "NG", 0.0, max_score)


def compare_pair(vb, cs) -> MethodComparison:
    """So sanh day du mot cap method VB <-> C#."""
    cfg = get_config()
    comp = MethodComparison(name=vb.name, vb=vb, cs=cs)
    comp.criteria.append(CriterionResult("C1", "OK", cfg.weight("C1"), cfg.weight("C1")))
    c2 = _compare_params(vb, cs, comp)
    c3 = _compare_return(vb, cs, comp)
    c4 = _compare_structure(vb, cs, comp)
    c5 = _compare_logic(vb, cs, comp)
    comp.criteria.extend([c2, c3, c4, c5])

    comp.score = round(sum(c.score for c in comp.criteria), 1)
    has_fail = any(c.label == "NG" for c in (c2, c3, c5))
    has_warn = any(c.label == "WARN" for c in comp.criteria)

    if has_fail or comp.score < cfg.th("score_fail"):
        comp.status = STATUS_FAIL
    elif has_warn or comp.score < cfg.th("score_pass"):
        comp.status = STATUS_WARNING
    else:
        comp.status = STATUS_PASS

    # Task 5: SQL phia C# con cu phap Oracle -> toi thieu WARNING
    if cfg.sql_check_enabled:
        sql_notes, has_leftover = check_pair_sql(vb.body, cs.body)
        comp.notes.extend(sql_notes)
        if has_leftover and comp.status == STATUS_PASS:
            comp.status = STATUS_WARNING

    # Dot 4: rule-based check (rules/conversion_rules.json) — chi them note;
    # ngoai le JP-MSG (thieu message tieng Nhat) duoc nang PASS -> WARNING
    if cfg.rules_enabled:
        rules = get_rules()
        if not rules.empty:
            comp.notes.extend(check_vb_side(rules, vb.body))
            comp.notes.extend(check_cs_side(rules, cs.body))
            pair_notes, escalate = check_pair_rules(rules, vb, cs)
            comp.notes.extend(pair_notes)
            if escalate and comp.status == STATUS_PASS:
                comp.status = STATUS_WARNING
    return comp


# ---------- Khai bao tach method 1-n (dot 11 — documents/03 muc 17) ----------

def _link_declared_splits(result, mapping):
    """Noi cap chinh voi cac MANH TACH da khai bao trong mapping (A -> B + C...).

    - Cap chinh (A<->B) va tung manh (C...) nhan note 2 chieu + related_names
      de sheet mo ta gom vao muc "METHOD LIEN QUAN".
    - Khoan dung: cap chinh FAIL chi vi lech logic (C2/C3 khong NG — body A con
      thieu phan da tach sang C) -> nang WARNING vi day la thay doi CO CHU DICH
      da duoc nguoi dung khai bao.
    """
    splits = getattr(mapping, "splits", None)
    if not splits:
        return
    by_cs_key = {}
    for comp in result.comparisons:
        if comp.cs:
            by_cs_key.setdefault(_match_key(comp.cs), []).append(comp)

    for vb_key, piece_keys in splits.items():
        pair = next((c for c in result.comparisons
                     if c.vb and c.cs and _match_key(c.vb) == vb_key), None)
        pieces = [p for k in piece_keys for p in by_cs_key.get(k, [])
                  if p is not pair]
        if pair is None or not pieces:
            continue
        listed = "; ".join(f"'{p.cs.name}' ({p.cs.file})" for p in pieces)
        pair.notes.append(
            f"C1: method duoc khai bao TACH thanh nhieu method (mapping 1-n) — "
            f"phan logic con lai o: {listed}. Xem muc METHOD LIEN QUAN trong sheet mo ta")
        pair.related_names.extend(piece_keys)
        c2c3_ng = any(c.code in ("C2", "C3") and c.label == "NG"
                      for c in pair.criteria)
        if pair.status == STATUS_FAIL and not c2c3_ng:
            pair.status = STATUS_WARNING
            pair.notes.append(
                "C5: body chi con MOT PHAN logic vi da tach method (da khai bao mapping) "
                "— nang FAIL -> WARNING, review bang cach doi chieu du cac manh tach")
        for p in pieces:
            p.related_names.append(vb_key)
            p.notes.append(
                f"EXTRA (manh tach): phan logic tach ra tu method VB "
                f"'{pair.vb.name}' theo khai bao mapping — doi chieu cung cap chinh "
                f"'{pair.cs.name}'")


# ---------- Scan 2 folder va tong hop ----------

def _group_by_key(methods, mapping: dict = None) -> dict:
    grouped = {}
    for m in methods:
        grouped.setdefault(_match_key(m, mapping), []).append(m)
    return grouped


def _pair_up(vb_list: list, cs_list: list):
    """Ghep cap trong mot nhom trung key. Tra ve (cap_da_cham, vb_du, cs_du).

    Task 3: co overload -> cham thu MOI to hop, ghep greedy theo score giam dan
    (tie-break uu tien cap cung so tham so). Nhom 1-1 ghep thang nhu cu.
    """
    if not vb_list or not cs_list:
        return [], vb_list, cs_list
    if len(vb_list) == 1 and len(cs_list) == 1:
        return [compare_pair(vb_list[0], cs_list[0])], [], []

    candidates = []
    for vi, vb in enumerate(vb_list):
        for ci, cs in enumerate(cs_list):
            trial = compare_pair(vb, cs)
            same_params = 0 if len(vb.params) == len(cs.params) else 1
            candidates.append((-trial.score, same_params, vi, ci, trial))
    candidates.sort(key=lambda t: t[:4])

    pairs, used_v, used_c = [], set(), set()
    for _negscore, _tie, vi, ci, trial in candidates:
        if vi in used_v or ci in used_c:
            continue
        used_v.add(vi)
        used_c.add(ci)
        pairs.append(trial)
    vb_left = [v for i, v in enumerate(vb_list) if i not in used_v]
    cs_left = [c for i, c in enumerate(cs_list) if i not in used_c]
    return pairs, vb_left, cs_left


def scan_folders(vb_folder: str, cs_folder: str, auto_detect: bool = True,
                 mapping: dict = None, mapping_file: str = "",
                 config=None, rules_file: str = "") -> ScanResult:
    """Quet 2 folder, map method theo ten va cham diem tung cap.

    auto_detect=True: phia C# tu tim thu muc Business Logic (project
    *Application* theo kien truc PCRS) va chi quet trong do; phia VB business
    logic nam trong code-behind nen luon quet toan bo folder da chon.
    mapping   : bang mapping ten thu cong (documents/03 muc 10.1).
    config    : Config ghi de cau hinh mac dinh (documents/03 muc 10.2).
    rules_file: file rule dot 4 (documents/03 muc 11); rong -> theo config roi tu tim
                rules/conversion_rules.json.
    """
    if config is not None:
        set_config(config)
    cfg = get_config()

    # Dot 4: nap bo rule (uu tien tham so > config > tu tim canh exe/goc repo)
    if cfg.rules_enabled:
        set_rules(load_rules(rules_file or cfg.rules_file or find_default_rules()))

    vb_methods, vb_files = parse_vb_folder(vb_folder)

    if auto_detect:
        cs_bl, cs_note = find_business_logic_folder(cs_folder)
    else:
        cs_bl, cs_note = Path(cs_folder), "auto-detect tat — quet toan bo folder da chon"
    cs_methods, cs_files = parse_cs_folder(str(cs_bl))

    # Task 6: index *.razor tren TOAN BO folder C# goc (frontend khong nam trong BL)
    razor_index = build_razor_index(cs_folder) if cfg.razor_scan_enabled else None

    result = ScanResult(
        vb_folder=vb_folder, cs_folder=cs_folder,
        vb_file_count=vb_files, cs_file_count=cs_files,
        scanned_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        cs_scan_folder=str(cs_bl), cs_detect_note=cs_note,
        mapping_file=mapping_file if mapping else "",
    )

    vb_map = _group_by_key(vb_methods, mapping)
    cs_map = _group_by_key(cs_methods)

    for key in sorted(set(vb_map) | set(cs_map)):
        vb_list = list(vb_map.get(key, []))
        cs_list = list(cs_map.get(key, []))

        pairs, vb_list, cs_list = _pair_up(vb_list, cs_list)
        for pair in pairs:
            vb, cs = pair.vb, pair.cs
            # Dot 4: VALIDATOR-SPLIT can biet file *Validators.cs cung thu muc
            if cfg.rules_enabled and not get_rules().empty:
                note = validator_split_note(get_rules(), pair.criteria, cs.file, str(cs_bl))
                if note:
                    pair.notes.append(note)
            if mapping and _match_key(vb) in mapping:
                pair.matched_by_mapping = True
                pair.notes.append(
                    f"C1: khop qua bang mapping ('{vb.name}' -> '{cs.name}') — ten bi doi khi migrate, da khai bao thu cong")
            elif vb.name.lower() != cs.name.lower():
                pair.notes.append(
                    f"C1: khop ten qua hau to Async ('{vb.name}' <-> '{cs.name}') — quy uoc async cua C#, khong phai loi")
            result.comparisons.append(pair)

        for vb in vb_list:  # chi con o VB -> MISSING
            comp = MethodComparison(name=vb.name, vb=vb, status=STATUS_MISSING)
            comp.criteria.append(CriterionResult("C1", "NG", 0.0, cfg.weight("C1")))
            comp.notes.append("Khong tim thay method tuong ung o he thong moi (C#)")
            if is_ui_event(vb.name):
                found = razor_index.find_handler(vb.name) if razor_index else None
                if found:
                    comp.has_frontend_handler = True
                    comp.notes.append(
                        f"UI event — da tim thay {found} (frontend), da chuyen hop le")
                else:
                    comp.notes.append("UI event — co the da chuyen hop le sang file .razor (frontend)")
            result.comparisons.append(comp)

        for cs in cs_list:  # chi con o C# -> EXTRA
            comp = MethodComparison(name=cs.name, cs=cs, status=STATUS_EXTRA)
            if is_new_arch_component(cs):
                comp.is_new_arch = True
                comp.notes.append(
                    "EXTRA (kien truc moi): thanh phan MediatR Handler / DTO / Result / Validator "
                    "— khong ton tai ben VB theo documents/04, khong phai thua code")
            else:
                comp.notes.append("Method viet moi o he thong C#, khong co trong ban VB (khong phai loi)")
            if cfg.sql_check_enabled:
                comp.notes.extend(check_extra_sql(cs.body))
            if cfg.rules_enabled and not get_rules().empty:
                comp.notes.extend(check_cs_side(get_rules(), cs.body))
            result.comparisons.append(comp)

    # Dot 11: noi cac manh tach da khai bao trong mapping (A -> B + C...)
    if mapping is not None:
        _link_declared_splits(result, mapping)

    return result
