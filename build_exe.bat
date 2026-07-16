@echo off
REM Build file exe GUI (Windows) — ket qua: dist\MigrationChecker.exe
REM Yeu cau: pip install openpyxl pyinstaller (+ anthropic neu muon dung gate AI dot 6)
REM Luu y: --add-data phai dung duong dan tuyet doi (%~dp0) vi PyInstaller moi
REM resolve duong dan tuong doi theo --specpath (build\) -> se khong tim thay file.
cd /d "%~dp0"
python -m PyInstaller --noconfirm --onefile --windowed --name MigrationChecker ^
  --paths tool --distpath dist --workpath build --specpath build ^
  --add-data "%~dp0rules\conversion_rules.json;rules" ^
  --exclude-module numpy --exclude-module PIL --exclude-module lxml ^
  --exclude-module charset_normalizer ^
  tool\main.py
echo.
echo Xong: dist\MigrationChecker.exe
pause
