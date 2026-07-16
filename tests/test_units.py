"""Unit test cho cac module core (dot 3 — documents/03 muc 10.10)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tool"))

from core.comparator import canonical_type, _pair_up, _compare_logic, _bag_similarity
from core.config import Config, load_config, set_config, DEFAULTS
from core.mapping import load_mapping
from core.models import MethodInfo, Parameter, MethodComparison
from core.normalizer import normalize_vb_body, normalize_cs_body
from core.razor_scanner import RazorIndex, _control_core, _handler_core
from core.sql_checker import (extract_sql_strings, find_oracle_leftovers,
                              extract_tables, check_pair_sql)


def _write_tmp(content: str, suffix: str) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False,
                                    encoding="utf-8")
    f.write(content)
    f.close()
    return f.name


class TestCanonicalType(unittest.TestCase):
    def setUp(self):
        set_config(Config())

    def test_kieu_don(self):
        self.assertEqual(canonical_type("Integer"), "int")
        self.assertEqual(canonical_type("Boolean"), "bool")
        self.assertEqual(canonical_type("String"), "string")

    def test_generic_va_mang(self):
        self.assertEqual(canonical_type("List(Of String)"), "list<string>")
        self.assertEqual(canonical_type("Task<List<CustomerDto>>"), "list<customerdto>")
        self.assertEqual(canonical_type("String()"), "list<string>")
        self.assertEqual(canonical_type("int[]"), "list<int>")
        self.assertEqual(canonical_type("Dictionary<int, string>"), "dict<int,string>")

    def test_task_bao_ngoai(self):
        self.assertEqual(canonical_type("Task<int>"), "int")
        self.assertEqual(canonical_type("Task"), "void")


class TestNormalizer(unittest.TestCase):
    def test_vb_dim_va_toan_tu(self):
        tokens = normalize_vb_body(
            'Dim x As Integer = 5\nIf x IsNot Nothing AndAlso x > 3 Then\nReturn True\nEnd If')
        self.assertIn("int", tokens)
        self.assertIn("&&", tokens)
        self.assertIn("return", tokens)
        self.assertNotIn("dim", tokens)

    def test_cs_bo_hau_to_async(self):
        tokens = normalize_cs_body("var x = await GetListAsync();")
        self.assertIn("getlist", tokens)
        self.assertNotIn("getlistasync", tokens)


class TestMapping(unittest.TestCase):
    def test_csv_voi_comment(self):
        path = _write_tmp("# chu thich\n\nSearchProductByName,FindProducts\nA,BAsync\n", ".csv")
        m = load_mapping(path)
        self.assertEqual(m["searchproductbyname"], "findproducts")
        self.assertEqual(m["a"], "b")  # hau to Async duoc bo

    def test_json(self):
        path = _write_tmp(json.dumps({"OldName": "NewNameAsync"}), ".json")
        self.assertEqual(load_mapping(path), {"oldname": "newname"})

    def test_loi_dinh_dang(self):
        path = _write_tmp("chi_mot_cot\n", ".csv")
        with self.assertRaises(ValueError):
            load_mapping(path)

    def test_file_khong_ton_tai(self):
        with self.assertRaises(FileNotFoundError):
            load_mapping("khong_ton_tai.csv")

    # ---- Dot 11: khai bao tach 1-n ----

    def test_csv_nhieu_cot_tach_1_n(self):
        path = _write_tmp("A,BAsync,CAsync,D\nX,Y\n", ".csv")
        m = load_mapping(path)
        self.assertEqual(m["a"], "b")               # cot 2 = method chinh
        self.assertEqual(m.splits["a"], ["c", "d"])  # cot 3+ = manh tach
        self.assertEqual(m["x"], "y")
        self.assertNotIn("x", m.splits)             # dong 1-1 khong co splits

    def test_json_gia_tri_list(self):
        path = _write_tmp(json.dumps({
            "CloseCustomerAccount": ["DeactivateCustomer", "CancelPendingOrdersAsync"],
            "OldName": "NewName"}), ".json")
        m = load_mapping(path)
        self.assertEqual(m["closecustomeraccount"], "deactivatecustomer")
        self.assertEqual(m.splits["closecustomeraccount"], ["cancelpendingorders"])
        self.assertEqual(m["oldname"], "newname")

    def test_csv_cot_rong_bao_loi(self):
        path = _write_tmp("A,,C\n", ".csv")
        with self.assertRaises(ValueError):
            load_mapping(path)


class TestDeclaredSplits(unittest.TestCase):
    """Dot 11: noi cap chinh voi manh tach khai bao trong mapping 1-n."""

    @staticmethod
    def _mk(vb_name, cs_name, status, criteria=()):
        from core.models import MethodComparison
        vb = MethodInfo(name=vb_name, kind="function", return_type="Boolean",
                        signature=vb_name, file="Form.vb") if vb_name else None
        cs = MethodInfo(name=cs_name, kind="typed", return_type="Task",
                        signature=cs_name, file=f"{cs_name}.cs") if cs_name else None
        comp = MethodComparison(name=vb_name or cs_name, vb=vb, cs=cs, status=status)
        comp.criteria = list(criteria)
        return comp

    def _run(self, pair_criteria, pair_status):
        from core.comparator import _link_declared_splits
        from core.mapping import Mapping
        from core.models import ScanResult
        m = Mapping()
        m["a"] = "b"
        m.splits["a"] = ["c"]
        pair = self._mk("A", "BAsync", pair_status, pair_criteria)
        piece = self._mk(None, "CAsync", "EXTRA")
        result = ScanResult()
        result.comparisons = [pair, piece]
        _link_declared_splits(result, m)
        return pair, piece

    def test_noi_2_chieu_va_khoan_dung_fail_do_c5(self):
        from core.models import CriterionResult
        pair, piece = self._run(
            [CriterionResult("C2", "OK", 20, 20), CriterionResult("C3", "WARN", 10, 15),
             CriterionResult("C5", "NG", 0, 20)], "FAIL")
        self.assertEqual(pair.status, "WARNING")  # FAIL chi vi C5 -> khoan dung
        self.assertIn("TACH thanh nhieu method", pair.note_text)
        self.assertIn("CAsync.cs", pair.note_text)
        self.assertIn("c", pair.related_names)
        self.assertIn("manh tach", piece.note_text)
        self.assertIn("a", piece.related_names)

    def test_khong_khoan_dung_khi_sai_chu_ky(self):
        from core.models import CriterionResult
        pair, _ = self._run(
            [CriterionResult("C2", "NG", 0, 20), CriterionResult("C5", "NG", 0, 20)],
            "FAIL")
        self.assertEqual(pair.status, "FAIL")  # C2 NG that su -> giu FAIL
        self.assertIn("TACH thanh nhieu method", pair.note_text)

    def test_warning_giu_nguyen(self):
        from core.models import CriterionResult
        pair, _ = self._run([CriterionResult("C5", "WARN", 12, 20)], "WARNING")
        self.assertEqual(pair.status, "WARNING")


class TestConfig(unittest.TestCase):
    def tearDown(self):
        set_config(Config())

    def test_mac_dinh_giu_hanh_vi_cu(self):
        cfg = Config()
        self.assertEqual(cfg.weight("C1"), 30.0)
        self.assertEqual(cfg.th("sim_ok"), 0.75)
        self.assertEqual(round(cfg.weight("C3") * cfg.th("c3_warn_ratio"), 1), 10.0)
        self.assertEqual(round(cfg.weight("C4") * cfg.th("c4_light_ratio"), 1), 11.0)
        self.assertEqual(round(cfg.weight("C4") * cfg.th("c4_heavy_ratio"), 1), 6.0)
        self.assertEqual(round(cfg.weight("C5") * cfg.th("c5_warn_ratio"), 1), 12.0)
        self.assertTrue(cfg.ui_event_re.search("btnSave_Click"))
        self.assertFalse(cfg.ui_event_re.search("GetCustomerName"))

    def test_ghi_de_mot_phan(self):
        cfg = Config({"thresholds": {"sim_ok": 0.9}})
        self.assertEqual(cfg.th("sim_ok"), 0.9)
        self.assertEqual(cfg.th("sim_warn"), 0.5)  # key khac giu mac dinh

    def test_key_sai_bao_loi(self):
        with self.assertRaises(ValueError):
            Config({"khong_co_key_nay": 1})

    def test_load_file(self):
        path = _write_tmp(json.dumps({"weights": {"C5": 25.0}}), ".json")
        cfg = load_config(path)
        self.assertEqual(cfg.weight("C5"), 25.0)
        self.assertEqual(cfg.weight("C1"), 30.0)

    def test_sample_json_hop_le(self):
        sample = Path(__file__).parent.parent / "config.sample.json"
        data = json.loads(sample.read_text(encoding="utf-8"))
        data.pop("_huong_dan", None)
        cfg = Config(data)
        # config.sample.json phai dung bang gia tri mac dinh
        for code, w in DEFAULTS["weights"].items():
            self.assertEqual(cfg.weight(code), w)


class TestSqlChecker(unittest.TestCase):
    def setUp(self):
        set_config(Config())

    def test_trich_sql_tu_string(self):
        vb = 'Dim sql As String = "SELECT * FROM T_ORDER WHERE ID = :id"'
        self.assertEqual(len(extract_sql_strings(vb, vb=True)), 1)
        self.assertEqual(extract_sql_strings('var x = "khong phai sql";', vb=False), [])

    def test_oracle_leftover(self):
        sql = "SELECT NVL(A, 0) FROM T WHERE ROWNUM <= 10 AND D < SYSDATE"
        found = find_oracle_leftovers(sql)
        self.assertIn("NVL(", found)
        self.assertIn("ROWNUM", found)
        self.assertIn("SYSDATE", found)
        # PostgreSQL ho tro TO_DATE / || -> khong bao
        self.assertEqual(find_oracle_leftovers("SELECT TO_DATE(x) || 'a' FROM t"), [])

    def test_bang(self):
        tables = extract_tables(
            "SELECT * FROM T_ORDER o JOIN T_CUSTOMER c ON o.ID = c.ID")
        self.assertEqual(tables, {"t_order", "t_customer"})

    def test_cap_leftover_va_linq(self):
        vb = 'Dim sql As String = "SELECT NVL(A,0) FROM T_SALES"'
        cs_bad = 'var sql = "SELECT NVL(A,0) FROM T_SALES";'
        notes, leftover = check_pair_sql(vb, cs_bad)
        self.assertTrue(leftover)
        # C# dung LINQ (khong co SQL) -> khong phat
        notes, leftover = check_pair_sql(vb, "return await _context.Sales.SumAsync();")
        self.assertFalse(leftover)
        self.assertEqual(notes, [])


class TestRazorScanner(unittest.TestCase):
    def test_core_names(self):
        self.assertEqual(_control_core("txtQuantity"), "quantity")
        self.assertEqual(_control_core("F8"), "f8")
        self.assertEqual(_handler_core("OnQuantityChanged"), "quantity")
        self.assertEqual(_handler_core("OnF8Click"), "f8")
        self.assertEqual(_handler_core("HandleSaveAsync"), "save")

    def test_find_handler(self):
        idx = RazorIndex()
        idx.add_file("Pages/OrderEntry.razor", "OrderEntry",
                     '<button @onclick="OnF8Click">x</button>\n'
                     "@code { protected override async Task OnInitializedAsync() { } "
                     "private async Task OnF8Click() { } }")
        self.assertIn("OnInitializedAsync", idx.find_handler("OrderEntry_Load") or "")
        self.assertIn("OnF8Click", idx.find_handler("F8_Click") or "")
        self.assertIsNone(idx.find_handler("CustomerMaster_Load"))  # file khac ten
        self.assertIsNone(idx.find_handler("btnDelete_Click"))      # khong co handler


def _mk(name, params_n=0, body="", return_type="void"):
    return MethodInfo(name=name, kind="method", return_type=return_type,
                      params=[Parameter(f"p{i}", "int") for i in range(params_n)],
                      body=body)


class TestOverloadBestMatch(unittest.TestCase):
    def setUp(self):
        set_config(Config())

    def test_ghep_theo_so_tham_so(self):
        # Thu tu dao nguoc: greedy theo thu tu cu se ghep cheo
        vb = [_mk("Foo", 2, "Return a + b"), _mk("Foo", 1, "Return a")]
        cs = [_mk("Foo", 1, "return a;"), _mk("Foo", 2, "return a + b;")]
        pairs, vb_left, cs_left = _pair_up(vb, cs)
        self.assertEqual(len(pairs), 2)
        self.assertFalse(vb_left or cs_left)
        for p in pairs:
            self.assertEqual(len(p.vb.params), len(p.cs.params))

    def test_du_thua_ra_missing_extra(self):
        vb = [_mk("Foo", 1, "Return a")]
        cs = [_mk("Foo", 1, "return a;"), _mk("Foo", 3, "return 0;")]
        pairs, vb_left, cs_left = _pair_up(vb, cs)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(len(cs_left), 1)
        self.assertEqual(len(cs_left[0].params), 3)


class TestTokenBag(unittest.TestCase):
    def setUp(self):
        set_config(Config())

    def test_bag_similarity(self):
        self.assertEqual(_bag_similarity(["a", "b"], ["b", "a"]), 1.0)
        self.assertEqual(_bag_similarity(["a"], ["b"]), 0.0)
        self.assertEqual(_bag_similarity([], []), 1.0)

    def test_dao_thu_tu_nang_ng_thanh_warn(self):
        # 6 cau lenh giong het nhau nhung dao nguoc thu tu -> seq thap, bag = 1.0
        stmts_vb = [f"total{i} = value{i} * rate{i} + base{i} - fee{i}" for i in range(6)]
        stmts_cs = [f"total{i} = value{i} * rate{i} + base{i} - fee{i};" for i in range(6)]
        vb = _mk("Calc", 0, "\n".join(stmts_vb), "Integer")
        cs = _mk("Calc", 0, "\n".join(reversed(stmts_cs)), "int")
        comp = MethodComparison(name="Calc", vb=vb, cs=cs)
        c5 = _compare_logic(vb, cs, comp)
        self.assertEqual(c5.label, "WARN")
        self.assertIn("khac thu tu", comp.note_text)

    def test_logic_khac_han_van_ng(self):
        vb = _mk("Calc", 0, "a = b + c\nIf a > 5 Then\nReturn a\nEnd If", "Integer")
        cs = _mk("Calc", 0, "var x = LoadConfig(); Save(x); Log(x); Notify(x);", "int")
        comp = MethodComparison(name="Calc", vb=vb, cs=cs)
        c5 = _compare_logic(vb, cs, comp)
        self.assertEqual(c5.label, "NG")


if __name__ == "__main__":
    unittest.main()
