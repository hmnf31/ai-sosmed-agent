@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

echo === Social Media Assistant - Bot Runner ===
echo.

if not exist ".venv\Scripts\python.exe" (
    echo .venv tidak ditemukan. Membuat virtual environment...
    python -m venv .venv
    echo.
    echo Menginstall dependensi...
    .venv\Scripts\pip install -r requirements.txt
    echo.
)

echo Memulai bot Telegram...
echo Tekan Ctrl+C untuk menghentikan.
echo ========================================
.venv\Scripts\python.exe bot.py

endlocal
