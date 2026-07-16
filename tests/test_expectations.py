"""Test hoi quy theo bang ky vong documents/06 (bo sample PCRS).

Chay:  python -m unittest discover tests   (hoac: pytest tests)

Moi lan sua comparator/normalizer PHAI chay lai bo test nay — status cua
tung method trong bang duoi la hop dong khong duoc degrade.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tool"))

from core.comparator import scan_folders
from core.mapping import load_mapping
from core.config import Config, set_config

_ROOT = Path(__file__).parent.parent
_VB = str(_ROOT / "samples" / "pcrs" / "legacy_vb")
_CS = str(_ROOT / "samples" / "pcrs" / "new_aspcore")
_MAP = str(_ROOT / "samples" / "pcrs" / "method_mapping.csv")

# Bang ky vong (documents/06). Khong co --map.
EXPECTED_NO_MAP = {
    "CustomerMaster_Load": "MISSING",
    "F8_Click": "MISSING",
    "CheckDuplicateCustomer": "PASS",
    "CheckExistCustomer": "PASS",
    "GetCustomerList": "WARNING",
    "RegisterCustomer": "WARNING",
    "UpdateCustomer": "FAIL",
    "DeleteCustomer": "WARNING",
    "GetCustomerName": "MISSING",
    "OrderEntry_Load": "MISSING",
    "txtQuantity_TextChanged": "MISSING",
    "CalcOrderAmount": "PASS",
    "CalcTax": "FAIL",
    "CheckOrderLimit": "PASS",
    "RegisterOrder": "WARNING",
    "CancelOrder": "FAIL",
    "GetOrderList": "WARNING",
    "PrintOrderReport": "MISSING",
    "ProductStock_Load": "MISSING",
    "GetStockQuantity": "PASS",
    "UpdateStock": "FAIL",
    "CheckStockShortage": "PASS",
    # Sample dot 3
    "SearchProductByName": "MISSING",   # doi ten, chua khai bao mapping
    "GetMonthlySales": "WARNING",       # SQL C# con NVL/SYSDATE
    # Sample dot 4 (rule-based check — documents/03 muc 11)
    "CalcRoundedPrice": "PASS",             # PASS nhung co note RULE VB-CINT/VB-INTDIV
    "CheckDuplicateProductName": "PASS",    # PASS nhung co note RULE SELF-EXCL
    "ApplyMemberDiscount": "WARNING",       # thieu 1 nhanh check -> note RULE JP-MSG
    # Sample dot 10 (1 method VB tach thanh nhieu method C#)
    "TransferStock": "WARNING",       # tach 2 noi CUNG TEN: cap chinh + EXTRA (khong can map)
    "ArchiveOldOrders": "MISSING",    # tach + DOI TEN (PurgeOrders*) — khong map thi MISSING
    # Sample dot 11 (A chua logic A1+A2 -> tach thanh B (A1) + C (A2), ten khac han)
    "CloseCustomerAccount": "MISSING",  # khong map thi khong the tu noi (ten khac)
}

# UI event phai duoc xac nhan handler frontend qua .razor (dot 3 task 6)
FRONTEND_HANDLED = {
    "CustomerMaster_Load", "F8_Click", "OrderEntry_Load",
    "txtQuantity_TextChanged", "ProductStock_Load",
}


class TestPcrsExpectations(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        set_config(Config())  # dam bao config mac dinh
        cls.result = scan_folders(_VB, _CS)
        cls.by_name = {}
        for c in cls.result.comparisons:
            cls.by_name.setdefault(c.name, []).append(c)

    def test_tong_so_dong(self):
        self.assertEqual(len(self.result.comparisons), 54)

    def test_status_tung_method_vb(self):
        for name, expected in EXPECTED_NO_MAP.items():
            comps = self.by_name.get(name)
            self.assertIsNotNone(comps, f"khong thay method {name}")
            self.assertEqual(comps[0].status, expected,
                             f"{name}: ky vong {expected}, thuc te {comps[0].status}")

    def test_tong_theo_status(self):
        counts = self.result.count_by_status()
        self.assertEqual(counts["PASS"], 8)
        self.assertEqual(counts["WARNING"], 8)
        self.assertEqual(counts["FAIL"], 4)
        self.assertEqual(counts["MISSING"], 10)
        self.assertEqual(counts["EXTRA"], 24)

    def test_extra_kien_truc_moi(self):
        self.assertEqual(self.result.count_new_arch(), 16)
        # EXTRA thuong (khong thuoc kien truc moi)
        for name in ("ExportStockCsvAsync", "FindProductsAsync", "ApplyDiscountToOrderAsync",
                     "PurgeOrdersAsync", "PurgeOrders",
                     "DeactivateCustomerAsync", "CancelPendingOrdersAsync"):
            comp = self.by_name[name][0]
            self.assertEqual(comp.status, "EXTRA")
            self.assertFalse(comp.is_new_arch)

    def test_dot10_mot_vb_tach_nhieu_cs(self):
        """TransferStock: 1 VB -> cap chinh (Features) + EXTRA cung ten (Services)."""
        comps = self.by_name["TransferStock"]
        self.assertEqual(len(comps), 2)
        pair = next(c for c in comps if c.vb and c.cs)
        extra = next(c for c in comps if c.status == "MISSING" or (c.cs and not c.vb))
        self.assertEqual(pair.status, "WARNING")
        self.assertEqual(pair.cs.name, "TransferStockAsync")
        self.assertIn("StockTransferCommands.cs", pair.cs.file)
        self.assertEqual(extra.status, "EXTRA")
        self.assertIn("StockAuditService.cs", extra.cs.file)
        # 2 manh C# nam o 2 folder khac nhau
        self.assertNotEqual(Path(pair.cs.file).parent, Path(extra.cs.file).parent)

    def test_ui_event_da_xac_nhan_frontend(self):
        self.assertEqual(self.result.count_frontend_handled(), len(FRONTEND_HANDLED))
        for name in FRONTEND_HANDLED:
            comp = self.by_name[name][0]
            self.assertTrue(comp.has_frontend_handler, f"{name} chua xac nhan handler")
            self.assertIn(".razor", comp.note_text)
        # MISSING khong phai UI event thi khong duoc danh dau
        self.assertFalse(self.by_name["GetCustomerName"][0].has_frontend_handler)
        self.assertFalse(self.by_name["PrintOrderReport"][0].has_frontend_handler)

    def test_sql_oracle_leftover_co_note(self):
        comp = self.by_name["GetMonthlySales"][0]
        self.assertIn("cu phap Oracle", comp.note_text)
        self.assertIn("NVL(", comp.note_text)
        self.assertIn("SYSDATE", comp.note_text)
        # Cac method LINQ khong bi phat SQL
        self.assertNotIn("cu phap Oracle", self.by_name["GetStockQuantity"][0].note_text)


class TestPcrsWithMapping(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        set_config(Config())
        cls.result = scan_folders(_VB, _CS, mapping=load_mapping(_MAP), mapping_file=_MAP)
        # giu dong DAU TIEN moi ten (dot 10: TransferStock co 2 dong — cap + EXTRA cung ten)
        cls.by_name = {}
        for c in cls.result.comparisons:
            cls.by_name.setdefault(c.name, c)

    def test_method_doi_ten_ghep_dung(self):
        comp = self.by_name["SearchProductByName"]
        self.assertEqual(comp.status, "PASS")
        self.assertTrue(comp.matched_by_mapping)
        self.assertIn("bang mapping", comp.note_text)
        self.assertEqual(comp.cs.name, "FindProductsAsync")

    def test_dot10_tach_kem_doi_ten_can_mapping(self):
        """ArchiveOldOrders: doi ten + tach 2 noi — co map thi ghep PurgeOrdersAsync,
        ban batch PurgeOrders van la EXTRA cung khoa ten."""
        comp = self.by_name["ArchiveOldOrders"]
        self.assertEqual(comp.status, "WARNING")
        self.assertTrue(comp.matched_by_mapping)
        self.assertEqual(comp.cs.name, "PurgeOrdersAsync")
        self.assertIn("OrderArchiveCommands.cs", comp.cs.file)
        batch = self.by_name["PurgeOrders"]
        self.assertEqual(batch.status, "EXTRA")
        self.assertIn("OrderBatchService.cs", batch.cs.file)

    def test_dot11_tach_1_n_ten_khac_han(self):
        """A (logic A1+A2) -> B (A1) + C (A2), ten khac hoan toan — noi qua mapping 1-n."""
        pair = self.by_name["CloseCustomerAccount"]
        self.assertEqual(pair.status, "WARNING")
        self.assertTrue(pair.matched_by_mapping)
        self.assertEqual(pair.cs.name, "DeactivateCustomerAsync")
        self.assertIn("CustomerDeactivationCommands.cs", pair.cs.file)
        self.assertIn("TACH thanh nhieu method", pair.note_text)
        self.assertIn("cancelpendingorders", pair.related_names)
        piece = self.by_name["CancelPendingOrdersAsync"]
        self.assertEqual(piece.status, "EXTRA")
        self.assertIn("OrderCancellationCommands.cs", piece.cs.file)
        self.assertIn("manh tach", piece.note_text)
        self.assertIn("CloseCustomerAccount", piece.note_text)  # truy nguon ve method goc
        self.assertIn("closecustomeraccount", piece.related_names)

    def test_khong_con_missing_extra_gia(self):
        self.assertEqual(len(self.result.comparisons), 51)
        counts = self.result.count_by_status()
        self.assertEqual(counts["PASS"], 9)
        self.assertEqual(counts["WARNING"], 10)
        self.assertEqual(counts["MISSING"], 7)
        self.assertEqual(counts["EXTRA"], 21)

    def test_cac_method_khac_khong_doi(self):
        for name, expected in EXPECTED_NO_MAP.items():
            if name in ("SearchProductByName", "ArchiveOldOrders", "CloseCustomerAccount"):
                continue  # cac method doi ten/tach — status thay doi khi co mapping
            self.assertEqual(self.by_name[name].status, expected, name)


if __name__ == "__main__":
    unittest.main()
