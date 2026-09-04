@echo off
setlocal enabledelayedexpansion
title FnB Dashboard

echo ============================================
echo  FnB Analyst Dashboard — Starting...
echo ============================================
echo.

REM ── Load .env ke environment Windows ──────────────────────────
if not exist ".env" (
    echo [WARN] File .env tidak ditemukan. Pastikan ada di folder ini.
    goto :start
)

echo [INFO] Loading .env...
for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
    set "_key=%%A"
    set "_val=%%B"
    REM Skip baris kosong
    if not "!_key!"=="" (
        if not "!_val!"=="" (
            REM Trim whitespace dari key
            for /f "tokens=* delims= " %%C in ("!_key!") do set "_key=%%C"
            set "!_key!=!_val!"
        )
    )
)
echo [INFO] Environment loaded.

:start
echo [INFO] Starting Streamlit on port 8501...
echo [INFO] Buka browser: http://localhost:8501
echo.

streamlit run app.py --server.port 8501 --server.headless false

echo.
echo [INFO] Streamlit berhenti.
pause
