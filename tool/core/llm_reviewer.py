"""Gate danh gia AI (dot 6 — documents/03 muc 12; dot 8 them Google Gemini).

Lop danh gia THU BA, chay SAU scan_folders() va doc lap hoan toan voi:
  - Lop 1: cham diem C1-C5 (comparator)
  - Lop 2: rule-based check (rules/conversion_rules.json)
KHONG sua diem/status cua 2 lop tren — chi ghi vao cac field AI cua
MethodComparison: ai_status ("PASS" | "WARNING" | AI_NOT_RUN), ai_comment,
va (dot 12, chi khi WARNING) ai_suggestion / ai_suggestion_detail /
ai_suggestion_code — AI de xuat giai phap sua.

Ho tro 2 provider (dot 8), tu nhan dien theo dang api_key khi provider="auto":
  - "sk-ant..." -> Anthropic Claude (SDK anthropic, lazy import; tra phi)
  - "AIza..."   -> Google AI Studio / Gemini (REST bang urllib stdlib —
                   khong can cai them package; CO FREE TIER, tu retry khi 429)

Nguyen tac:
  - Duyet TAT CA method, ke ca MISSING (chi co VB) va EXTRA (chi co C#).
  - Tieu chi PASS/WARNING theo nhan dinh tu do cua model, tool khong ap rubric.
  - Moi loi (thieu key, thieu package, timeout, mat mang...) ->
    ai_status = AI_NOT_RUN, KHONG raise ra ngoai, KHONG chan scan.
  - Cache theo hash noi dung method (model + PROMPT_VERSION + ten + body 2 ben)
    de retest khong goi lai API ton token. Doi prompt -> tang PROMPT_VERSION.
  - Test tiem call_fn gia (khong mang, khong can package anthropic).
"""

import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from .models import AI_NOT_RUN, AI_PASS, AI_WARNING

# Doi prompt thi tang version nay de cache cu tu vo hieu
# v2 (dot 12): them 3 truong suggestion_* — AI de xuat giai phap cho cho khong PASS
PROMPT_VERSION = "v2"

# Model mac dinh tung provider (dung khi "model" trong config khong hop provider)
ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-5"
GOOGLE_DEFAULT_MODEL = "gemini-2.5-flash"
_GOOGLE_ENDPOINT = ("https://generativelanguage.googleapis.com"
                    "/v1beta/models/{model}:generateContent")

_SYSTEM_PROMPT = """Bạn là senior reviewer chuyên thẩm định chất lượng migration hệ thống \
từ VB.NET/.NET Framework 4.8/Oracle 19c (ứng dụng PC WinForms) sang \
ASP.NET Core/.NET/PostgreSQL (Web, kiến trúc CQRS/MediatR).

Nhiệm vụ: đánh giá MỘT method được convert có đảm bảo chất lượng hay không, \
theo nhận định chuyên môn của chính bạn (không bị ràng buộc bởi kết quả chấm \
điểm tự động kèm theo — chúng chỉ là thông tin tham khảo).

Các thay đổi CÓ CHỦ ĐÍCH của kiến trúc mới, KHÔNG được coi là lỗi:
- Async hóa (hậu tố Async, Task<T>), Result pattern (Boolean/Sub -> Result/Result<T>)
- DataTable/DataSet -> List<DTO>, ADO.NET -> EF Core/LINQ
- DELETE vật lý -> soft delete (IsDeleted = true)
- SQL Oracle viết lại cho PostgreSQL, MessageBox -> Result.Failure(message)
- Method tách sang Handler/Validator theo CQRS/MediatR

Những điểm cần soi kỹ (kinh nghiệm bẫy VB -> C#):
- CInt (banker's rounding) vs (int), chia nguyên \\ vs /, IIf tính cả 2 vế,
  On Error Resume Next nuốt lỗi, And/Or không short-circuit, "" vs Nothing
- Mất điều kiện loại trừ chính record khi check trùng, mất message nghiệp vụ,
  thiếu OrderBy khi thay ROWNUM bằng First/Take, sync-over-async (.Result/.Wait),
  fire-and-forget (_ = XxxAsync()), logic nghiệp vụ bị thiếu/nhầm nhánh

Trả lời bằng JSON đúng schema. Quy ước:
- status = "PASS"  : bạn nhận định method convert đạt, không thấy rủi ro đáng kể.
- status = "WARNING": có điểm nghi ngờ/rủi ro/thiếu thông tin cần người review tay.
- comment: tiếng Việt, ngắn gọn (tối đa ~3 câu), nêu đúng trọng tâm nhận định.

Khi status = "PASS": để cả 3 trường suggestion_overview / suggestion_detail /
suggestion_code là chuỗi rỗng "".

Khi status = "WARNING": BẮT BUỘC đề xuất giải pháp sửa, điền đủ 3 trường:
- suggestion_overview: tiếng Việt, TỐI ĐA 2 câu, tóm tắt hướng sửa để đọc nhanh
  trên bảng tổng hợp (nêu sửa CÁI GÌ và theo hướng NÀO — không dán code vào đây).
- suggestion_detail: tiếng Việt, giải thích đầy đủ để dev sửa được ngay:
  (1) Nguyên nhân gốc — chỉ đích danh đoạn code/điều kiện/nhánh nào sai lệch so
      với bản VB (trích ngắn dòng liên quan nếu cần);
  (2) Rủi ro nghiệp vụ nếu giữ nguyên (sai số liệu, mất message, nuốt lỗi...);
  (3) Các bước sửa cụ thể, đánh số 1. 2. 3.
  Nếu bạn thiếu thông tin để chắc chắn (ví dụ không thấy Validator/Handler liên
  quan), ghi rõ cần người review kiểm tra tay điều gì, ở đâu.
- suggestion_code: method C# HOÀN CHỈNH SAU KHI SỬA (đủ chữ ký + toàn bộ body,
  biên dịch được), là code thuần — KHÔNG bọc markdown ``` hay giải thích lẫn vào.
  Nguyên tắc:
  + Sửa TỐI THIỂU trên code C# hiện có; giữ nguyên style, tên biến, kiến trúc
    CQRS/MediatR/Result pattern/async của hệ thống mới.
  + MỌI dòng bạn thêm hoặc sửa phải kết thúc bằng comment "// FIX: <lý do ngắn>"
    để người review nhận ra ngay chỗ thay đổi.
  + Method MISSING (chưa có bản C#): viết bản convert C# đề xuất hoàn chỉnh theo
    kiến trúc mới, mỗi phần logic chính kèm "// FIX: convert từ VB".
  + Method EXTRA (code mới): sửa trực tiếp trên chính code C# đó.
  + Nếu vấn đề KHÔNG nằm ở code (chỉ cần xác nhận nghiệp vụ/kiểm tra tay), để
    suggestion_code = "" và nói rõ lý do trong suggestion_detail."""

_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["PASS", "WARNING"]},
        "comment": {"type": "string"},
        # Dot 12: de xuat giai phap — rong khi PASS (xem _SYSTEM_PROMPT)
        "suggestion_overview": {"type": "string"},
        "suggestion_detail": {"type": "string"},
        "suggestion_code": {"type": "string"},
    },
    "required": ["status", "comment",
                 "suggestion_overview", "suggestion_detail", "suggestion_code"],
    "additionalProperties": False,
}


# ---------- Dung payload cho 1 method ----------

def build_payload(comp) -> str:
    """Noi dung user message gui cho model (1 method / 1 request)."""
    lines = [f"# Method: {comp.name}", f"Trang thai tool cham: {comp.status}"]
    if comp.notes:
        lines.append("Ghi chu cua tool (tham khao, khong bat buoc theo):")
        lines.extend(f"- {n}" for n in comp.notes)
    if comp.vb and comp.cs:
        lines.append("\n## Code VB.NET (he thong cu)")
        lines.append(comp.vb.signature)
        lines.append(comp.vb.body or "(body rong)")
        lines.append("\n## Code C# (he thong moi)")
        lines.append(comp.cs.signature)
        lines.append(comp.cs.body or "(body rong)")
    elif comp.vb:
        lines.append("\n## Method CHI TON TAI phia VB (MISSING — chua thay ban convert C#)")
        lines.append(comp.vb.signature)
        lines.append(comp.vb.body or "(body rong)")
        lines.append("\nHay danh gia rui ro viec method nay khong co ban C# tuong ung "
                     "(da chuyen frontend hop le? nghiep vu bi bo sot?).")
    else:
        lines.append("\n## Method CHI TON TAI phia C# (EXTRA — viet moi, khong co ban VB)")
        lines.append(comp.cs.signature)
        lines.append(comp.cs.body or "(body rong)")
        lines.append("\nHay danh gia chat luong/rui ro cua code moi nay "
                     "(dung kien truc? co bay async/logic nao khong?).")
    return "\n".join(lines)


def cache_key(comp, model: str) -> str:
    """Hash noi dung method — trung thi khoi goi API (tiet kiem token)."""
    vb_body = comp.vb.body if comp.vb else ""
    cs_body = comp.cs.body if comp.cs else ""
    raw = "\x1f".join([model, PROMPT_VERSION, comp.name, vb_body, cs_body])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------- Cache file ----------

def default_cache_path() -> Path:
    """llm_cache.json canh exe (dong goi) hoac goc repo/cwd."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "llm_cache.json"
    return Path(__file__).parent.parent.parent / "llm_cache.json"


def load_cache(path: Path) -> dict:
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                return data
    except (OSError, ValueError):
        pass  # cache hong -> coi nhu rong, se ghi de
    return {}


def save_cache(path: Path, cache: dict):
    try:
        path.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    except OSError:
        pass  # khong ghi duoc cache khong lam hong ket qua review


# ---------- Provider & model ----------

def resolve_api_key(cfg) -> str:
    """api_key trong config uu tien; rong -> bien moi truong api_key_env."""
    key = (cfg.llm("api_key") or "").strip()
    if key:
        return key
    import os
    return (os.environ.get(cfg.llm("api_key_env") or "", "") or "").strip()


def resolve_provider(cfg, api_key: str = None) -> str:
    """"auto" -> nhan dien theo dang key: AIza=Google, con lai=Anthropic."""
    provider = (cfg.llm("provider") or "auto").strip().lower()
    if provider != "auto":
        return provider
    key = resolve_api_key(cfg) if api_key is None else api_key
    return "google" if key.startswith("AIza") else "anthropic"


def effective_model(cfg, provider: str) -> str:
    """Model thuc dung: model trong config khong hop provider -> model mac dinh."""
    model = (cfg.llm("model") or "").strip()
    if provider == "google":
        return model if model and not model.lower().startswith("claude") \
            else GOOGLE_DEFAULT_MODEL
    return model if model and not model.lower().startswith("gemini") \
        else ANTHROPIC_DEFAULT_MODEL


# ---------- Caller: Anthropic Claude (SDK, tra phi) ----------

def _make_anthropic_caller(cfg, api_key: str):
    try:
        import anthropic  # lazy import — tool van chay khi khong cai package
    except ImportError as e:
        raise RuntimeError("chua cai package 'anthropic' (pip install anthropic)") from e

    client = anthropic.Anthropic(
        api_key=api_key,
        timeout=float(cfg.llm("timeout_seconds")),
        max_retries=int(cfg.llm("max_retries")),
    )
    model = effective_model(cfg, "anthropic")
    max_tokens = int(cfg.llm("max_output_tokens"))
    auth_error = anthropic.AuthenticationError

    def call_fn(payload: str):
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=_SYSTEM_PROMPT,
            output_config={"format": {"type": "json_schema", "schema": _OUTPUT_SCHEMA}},
            messages=[{"role": "user", "content": payload}],
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        return json.loads(text)  # dict day du (status/comment/suggestion_*)

    call_fn.auth_error_type = auth_error
    return call_fn


# ---------- Caller: Google Gemini (REST stdlib, co free tier) ----------

def _google_request_body(payload: str, model: str, max_tokens: int) -> dict:
    generation_config = {
        "responseMimeType": "application/json",
        "responseSchema": {
            "type": "OBJECT",
            "properties": {
                "status": {"type": "STRING", "enum": ["PASS", "WARNING"]},
                "comment": {"type": "STRING"},
                # Dot 12: de xuat giai phap — rong khi PASS
                "suggestion_overview": {"type": "STRING"},
                "suggestion_detail": {"type": "STRING"},
                "suggestion_code": {"type": "STRING"},
            },
            "required": ["status", "comment", "suggestion_overview",
                         "suggestion_detail", "suggestion_code"],
        },
        "maxOutputTokens": max_tokens,
    }
    if model.startswith("gemini-2.5-flash"):
        # Flash cho phep tat thinking -> moi call nhanh hon han va do ton quota
        # free tier (Pro khong cho tat nen chi ap cho Flash)
        generation_config["thinkingConfig"] = {"thinkingBudget": 0}
    return {
        "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": payload}]}],
        "generationConfig": generation_config,
    }


def _parse_google_response(data: dict) -> dict:
    """Trich dict ket qua (status/comment/suggestion_*) tu response generateContent."""
    if "error" in data:
        raise RuntimeError(data["error"].get("message", str(data["error"])))
    candidates = data.get("candidates") or []
    if not candidates:
        block = (data.get("promptFeedback") or {}).get("blockReason", "khong ro")
        raise RuntimeError(f"Gemini khong tra candidate (blockReason={block})")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts)
    return json.loads(text)


def _google_retry_delay(detail: str, attempt: int) -> float:
    """Free tier tra 429 kem retryDelay (vd '18s') — doc ra, khong co thi tang dan."""
    m = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', detail)
    if m:
        return min(float(m.group(1)) + 1.0, 65.0)
    return 15.0 * (attempt + 1)


def _make_google_caller(cfg, api_key: str):
    model = effective_model(cfg, "google")
    url = _GOOGLE_ENDPOINT.format(model=model)
    timeout = float(cfg.llm("timeout_seconds"))
    max_retries = int(cfg.llm("max_retries"))
    max_tokens = int(cfg.llm("max_output_tokens"))

    def call_fn(payload: str):
        body = json.dumps(_google_request_body(payload, model, max_tokens)).encode("utf-8")
        last_detail = ""
        for attempt in range(max_retries + 1):
            req = urllib.request.Request(
                url, data=body, method="POST",
                headers={"Content-Type": "application/json",
                         "x-goog-api-key": api_key})  # key trong header, khong nam tren URL
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return _parse_google_response(json.loads(resp.read().decode("utf-8")))
            except urllib.error.HTTPError as e:
                last_detail = e.read().decode("utf-8", "replace")[:400]
                if e.code == 429 and "credit" in last_detail.lower():
                    # het credit tra truoc (khac rate-limit) — retry vo ich
                    raise RuntimeError(f"HTTP 429: {last_detail}") from None
                if e.code == 429 and attempt < max_retries:
                    # free tier gioi han so request/phut — cho roi goi lai
                    time.sleep(_google_retry_delay(last_detail, attempt))
                    continue
                if e.code >= 500 and attempt < max_retries:
                    time.sleep(5.0 * (attempt + 1))
                    continue
                raise RuntimeError(f"HTTP {e.code}: {last_detail}") from None
        raise RuntimeError(f"HTTP 429 sau {max_retries + 1} lan thu: {last_detail}")

    return call_fn


def make_api_caller(cfg):
    """Tao call_fn that theo provider. Raise neu thieu key/package/provider la —
    caller (review_result) chiu trach nhiem bat va chuyen thanh AI_NOT_RUN."""
    api_key = resolve_api_key(cfg)
    if not api_key:
        raise RuntimeError(
            "chua co API key (dien llm.api_key trong config.json hoac set bien "
            f"moi truong {cfg.llm('api_key_env')})")
    provider = resolve_provider(cfg, api_key)
    if provider == "google":
        return _make_google_caller(cfg, api_key)
    if provider == "anthropic":
        return _make_anthropic_caller(cfg, api_key)
    raise RuntimeError(f"llm.provider khong ho tro: '{provider}' "
                       "(chi nhan auto / anthropic / google)")


# ---------- Review toan bo ket qua scan ----------

def _normalize_reply(reply) -> dict:
    """Dua ket qua call_fn ve dict chuan.

    call_fn moi (dot 12) tra dict {status, comment, suggestion_*}; van chap nhan
    dang tuple (status, comment) cu — test/integration cu khong phai sua."""
    if isinstance(reply, dict):
        return reply
    status, comment = reply
    return {"status": status, "comment": comment}


def _apply_suggestions(comp, data: dict):
    """Gan 3 truong suggestion vao comparison — PASS thi ep ve rong (chi cho
    khong PASS moi can giai phap)."""
    if comp.ai_status == AI_PASS:
        comp.ai_suggestion = comp.ai_suggestion_detail = comp.ai_suggestion_code = ""
        return
    comp.ai_suggestion = (data.get("suggestion_overview") or "").strip()
    comp.ai_suggestion_detail = (data.get("suggestion_detail") or "").strip()
    comp.ai_suggestion_code = _strip_code_fence(data.get("suggestion_code") or "")


def _strip_code_fence(code: str) -> str:
    """Phong thu: model boc code trong ``` du prompt cam — go bo cho sach."""
    code = code.strip()
    if code.startswith("```"):
        lines = code.splitlines()
        lines = lines[1:]  # bo dong ```csharp / ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines).strip("\n")
    return code


def review_result(result, cfg, call_fn=None, progress=None) -> dict:
    """Cham AI cho TAT CA comparison trong ScanResult (ke ca MISSING/EXTRA).

    call_fn : (payload_str) -> dict {status, comment, suggestion_overview,
              suggestion_detail, suggestion_code} (hoac tuple (status, comment)
              kieu cu). None -> tao caller that qua AI API theo config.
              Test tiem ham gia vao day.
    progress: callback (i, total, cached) de GUI/CLI bao tien do (tuy chon).

    Tra ve thong ke: {"reviewed", "cached", "not_run", "error": str|None}.
    Ham nay KHONG BAO GIO raise — moi loi chuyen thanh AI_NOT_RUN.
    """
    stats = {"reviewed": 0, "cached": 0, "not_run": 0, "error": None}
    comparisons = result.comparisons
    if not comparisons:
        return stats

    fatal_reason = None
    if call_fn is None:
        try:
            call_fn = make_api_caller(cfg)
        except Exception as e:  # thieu key / thieu package -> khong goi gi ca
            fatal_reason = str(e)

    cache_file = (cfg.llm("cache_file") or "").strip()
    cache_path = Path(cache_file) if cache_file else default_cache_path()
    cache = load_cache(cache_path) if fatal_reason is None else {}
    cache_dirty = False
    auth_error_type = getattr(call_fn, "auth_error_type", None) if call_fn else None
    # cache key theo model THUC dung (dot 8: model config co the bi thay bang
    # model mac dinh cua provider — vd key Google + model claude -> gemini)
    model = effective_model(cfg, resolve_provider(cfg))

    for i, comp in enumerate(comparisons):
        if fatal_reason is not None:
            comp.ai_status = AI_NOT_RUN
            comp.ai_comment = f"Khong goi duoc AI API: {fatal_reason}"
            stats["not_run"] += 1
            if progress:
                progress(i + 1, len(comparisons), False)
            continue

        key = cache_key(comp, model)
        hit = cache.get(key)
        if isinstance(hit, dict) and hit.get("status") in (AI_PASS, AI_WARNING):
            comp.ai_status = hit["status"]
            comp.ai_comment = hit.get("comment", "")
            _apply_suggestions(comp, hit)
            stats["cached"] += 1
            stats["reviewed"] += 1
            if progress:
                progress(i + 1, len(comparisons), True)
            continue

        try:
            data = _normalize_reply(call_fn(build_payload(comp)))
            status = (data.get("status") or "").strip().upper()
            comment = (data.get("comment") or "").strip()
            if status not in (AI_PASS, AI_WARNING):
                # phong thu: model tra ngoai quy uoc -> ep ve WARNING de review tay
                comment = f"[status model tra ve: '{status}'] {comment}".strip()
                status = AI_WARNING
            comp.ai_status = status
            comp.ai_comment = comment
            _apply_suggestions(comp, data)
            cache[key] = {"status": comp.ai_status, "comment": comp.ai_comment,
                          "suggestion_overview": comp.ai_suggestion,
                          "suggestion_detail": comp.ai_suggestion_detail,
                          "suggestion_code": comp.ai_suggestion_code}
            cache_dirty = True
            stats["reviewed"] += 1
        except Exception as e:
            msg_lower = str(e).lower()
            if auth_error_type is not None and isinstance(e, auth_error_type):
                # sai key -> cac method sau chac chan cung loi, dung goi tiep
                fatal_reason = f"API key khong hop le ({e.__class__.__name__})"
            elif "api key not valid" in msg_lower or "api_key_invalid" in msg_lower:
                # sai key Google -> dung goi tiep
                fatal_reason = ("API key Google khong hop le — kiem tra lai key "
                                "lay tu aistudio.google.com")
            elif "credit balance" in msg_lower:
                # het credit API Anthropic -> dung goi tiep
                fatal_reason = ("tai khoan het credit API — nap credit tai "
                                "platform.claude.com -> Billing roi scan lai")
            elif "credits are depleted" in msg_lower:
                # het credit tra truoc Google -> dung goi tiep
                fatal_reason = ("project Google AI Studio het credit tra truoc — "
                                "vao aistudio.google.com tao API key tren project "
                                "free tier (khong gan billing), hoac nap credit "
                                "tai ai.studio/projects")
            comp.ai_status = AI_NOT_RUN
            comp.ai_comment = f"Loi khi goi AI API: {e.__class__.__name__}: {e}"
            stats["not_run"] += 1
        if progress:
            progress(i + 1, len(comparisons), False)

    if cache_dirty:
        save_cache(cache_path, cache)
    if fatal_reason is not None:
        stats["error"] = fatal_reason
    return stats
