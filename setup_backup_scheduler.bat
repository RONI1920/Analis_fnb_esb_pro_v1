@echo off
REM ============================================================
REM setup_backup_scheduler.bat
REM Daftarkan backup otomatis ke Windows Task Scheduler
REM Jalankan SEKALI sebagai Administrator
REM ============================================================

set "APP_DIR=%~dp0"
set "PYTHON_CMD=python"
set "TASK_NAME=FnB_Database_Backup"

echo [INFO] Mendaftarkan backup otomatis...
echo [INFO] Folder app: %APP_DIR%
echo.

REM Hapus task lama jika ada
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

REM Buat task baru — backup setiap hari jam 02:00
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "%PYTHON_CMD% \"%APP_DIR%backup.py\"" ^
    /sc DAILY ^
    /st 02:00 ^
    /ru SYSTEM ^
    /f

if %errorlevel%==0 (
    echo [OK] Backup otomatis berhasil didaftarkan!
    echo [OK] Backup akan berjalan setiap hari jam 02:00
    echo [OK] Hasil backup: %APP_DIR%backups\
) else (
    echo [ERROR] Gagal mendaftarkan task. Jalankan sebagai Administrator!
)

echo.
pause
