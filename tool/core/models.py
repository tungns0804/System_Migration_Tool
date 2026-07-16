"""Cac data model dung chung cho tool kiem tra migration."""

from dataclasses import dataclass, field


@dataclass
class Parameter:
    """Mot tham so cua method."""
    name: str
    type: str  # kieu goc (chua chuan hoa)


@dataclass
class MethodInfo:
    """Thong tin mot method trich xuat tu source code."""
    name: str
    kind: str                 # "sub" | "function" (VB) hoac "void" | "typed" (C#)
    return_type: str          # "void" neu la Sub/void
    params: list = field(default_factory=list)   # list[Parameter]
    body: str = ""            # phan than method (raw)
    file: str = ""            # duong dan tuong doi
    line: int = 0             # dong bat dau
    signature: str = ""       # chu ky goc (1 dong)

    @property
    def key(self) -> str:
        """Khoa map giua 2 he thong: ten method, khong phan biet hoa thuong."""
        return self.name.lower()


# Trang thai tong hop cua mot method sau khi so sanh
STATUS_PASS = "PASS"
STATUS_WARNING = "WARNING"
STATUS_FAIL = "FAIL"
STATUS_MISSING = "MISSING"   # chi co o VB
STATUS_EXTRA = "EXTRA"       # chi co o C#

# Dot 6: trang thai cot "Status AI danh gia" (lop danh gia AI qua Claude API,
# doc lap voi status o tren — khong anh huong diem/status C1-C5)
AI_PASS = "PASS"
AI_WARNING = "WARNING"
AI_NOT_RUN = "AI chưa thực hiện đánh giá"


@dataclass
class CriterionResult:
    """Ket qua mot tieu chi kiem tra (C1..C5)."""
    code: str        # "C1".."C5"
    label: str       # "OK" | "WARN" | "NG" | "-"
    score: float     # diem dat duoc (theo trong so)
    max_score: float
    note: str = ""


@dataclass
class MethodComparison:
    """Ket qua so sanh mot method giua VB va C#."""
    name: str
    vb: MethodInfo = None
    cs: MethodInfo = None
    criteria: list = field(default_factory=list)  # list[CriterionResult]
    similarity: float = 0.0
    score: float = 0.0
    status: str = STATUS_MISSING
    notes: list = field(default_factory=list)
    is_new_arch: bool = False  # EXTRA thuoc thanh phan moi cua kien truc (Handler/DTO/Result/Validator)
    has_frontend_handler: bool = False  # MISSING la UI event da tim thay handler trong .razor
    matched_by_mapping: bool = False    # cap duoc ghep nho bang mapping ten thu cong
    # Dot 6: ket qua lop danh gia AI (Claude API) — doc lap voi score/status
    ai_status: str = ""   # AI_PASS | AI_WARNING | AI_NOT_RUN | "" (chua chay)
    ai_comment: str = ""  # noi dung AI danh gia (tieng Viet)
    # Dot 11: khoa ten bo sung de gom nhom "METHOD LIEN QUAN" trong sheet mo ta
    # (khai bao tach 1-n qua mapping — ten manh tach khac han ten goc)
    related_names: list = field(default_factory=list)

    @property
    def note_text(self) -> str:
        return "; ".join(self.notes)


@dataclass
class ScanResult:
    """Ket qua tong hop mot lan scan."""
    vb_folder: str = ""
    cs_folder: str = ""
    vb_file_count: int = 0
    cs_file_count: int = 0
    comparisons: list = field(default_factory=list)  # list[MethodComparison]
    scanned_at: str = ""
    cs_scan_folder: str = ""   # folder Business Logic phia C# thuc te duoc quet (auto-detect)
    cs_detect_note: str = ""   # mo ta cach tool tim ra folder do
    mapping_file: str = ""     # file mapping ten method thu cong (neu co dung)

    def count_new_arch(self) -> int:
        """So method EXTRA thuoc thanh phan moi cua kien truc (khong phai loi)."""
        return sum(1 for c in self.comparisons if c.is_new_arch)

    def count_frontend_handled(self) -> int:
        """So MISSING la UI event da xac nhan co handler trong .razor (frontend)."""
        return sum(1 for c in self.comparisons if c.has_frontend_handler)

    def count_rule_hits(self) -> int:
        """So method co it nhat 1 ghi chu RULE (rule-based check dot 4)."""
        return sum(1 for c in self.comparisons
                   if any(n.startswith("RULE ") for n in c.notes))

    def count_ai(self) -> dict:
        """Thong ke lop danh gia AI (dot 6): PASS / WARNING / chua danh gia.

        "" (chua chay AI) va AI_NOT_RUN (chay nhung loi) deu dem vao not_run.
        """
        counts = {AI_PASS: 0, AI_WARNING: 0, "not_run": 0}
        for c in self.comparisons:
            if c.ai_status in (AI_PASS, AI_WARNING):
                counts[c.ai_status] += 1
            else:
                counts["not_run"] += 1
        return counts

    def ai_reviewed(self) -> bool:
        """Co it nhat 1 method da duoc AI cham?"""
        return any(c.ai_status in (AI_PASS, AI_WARNING) for c in self.comparisons)

    def count_by_status(self) -> dict:
        counts = {STATUS_PASS: 0, STATUS_WARNING: 0, STATUS_FAIL: 0,
                  STATUS_MISSING: 0, STATUS_EXTRA: 0}
        for c in self.comparisons:
            counts[c.status] = counts.get(c.status, 0) + 1
        return counts

    def average_score(self) -> float:
        scored = [c.score for c in self.comparisons
                  if c.status in (STATUS_PASS, STATUS_WARNING, STATUS_FAIL)]
        return round(sum(scored) / len(scored), 1) if scored else 0.0
