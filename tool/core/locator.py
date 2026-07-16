"""Tu tim thu muc Business Logic trong bo source (theo documents/04).

Phia C# (ASP.NET Core / kien truc PCRS): Business Logic nam o project
*Application* (CQRS: Features/[ScreenName]/ + DTOs/ + Common/). Nguoi dung
chi can chon folder goc cua ca solution, tool tu thu hep pham vi quet.

Phia VB: business logic tron trong code-behind cua form (khong co folder
rieng) nen luon quet toan bo *.vb tu folder goc.
"""

from pathlib import Path

# Ten folder Business Logic chap nhan khi khong tim thay project *Application*
_BL_DIR_NAMES = {"features", "businesslogic", "business_logic", "business logic"}


def _has_cs_files(folder: Path) -> bool:
    return any(folder.rglob("*.cs"))


def find_business_logic_folder(root: str):
    """Tim folder Business Logic phia C#. Tra ve (Path, mo_ta_cach_tim).

    Thu tu uu tien:
      1. Folder ten *Application* co folder con Features (kien truc PCRS/CQRS).
      2. Folder ten *Application* chua file .cs.
      3. Folder ten Features / BusinessLogic / Business_Logic chua file .cs.
      4. Khong tim thay -> dung chinh folder goc (quet toan bo).
    """
    base = Path(root)

    app_dirs = sorted(
        (d for d in base.rglob("*") if d.is_dir() and "application" in d.name.lower()),
        key=lambda d: len(d.parts),
    )
    for d in app_dirs:
        if (d / "Features").is_dir() and _has_cs_files(d):
            return d, "kien truc PCRS/CQRS (*Application* chua Features/)"
    for d in app_dirs:
        if _has_cs_files(d):
            return d, "project *Application*"

    bl_dirs = sorted(
        (d for d in base.rglob("*")
         if d.is_dir() and d.name.lower() in _BL_DIR_NAMES and _has_cs_files(d)),
        key=lambda d: len(d.parts),
    )
    if bl_dirs:
        return bl_dirs[0], f"folder ten '{bl_dirs[0].name}'"

    return base, "khong tim thay folder Business Logic rieng — quet toan bo folder da chon"
