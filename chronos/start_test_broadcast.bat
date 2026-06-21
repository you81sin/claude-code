@echo off
cd /d "C:\Users\you81\Desktop\Chronos"

REM Read config
if exist chronos_config.txt (
    for /f "tokens=1,* delims==" %%a in (chronos_config.txt) do (
        if "%%a"=="SBV2_DIR" set SBV2_DIR=%%b
        if "%%a"=="LLM_PROVIDER" set LLM_PROVIDER=%%b
    )
) else (
    set SBV2_DIR=C:\VITS2
    set LLM_PROVIDER=gemini
)

set PYTHONUTF8=1
set CHRONOS_LLM_PROVIDER=%LLM_PROVIDER%

echo.
echo ========================================
echo  CHRONOS Test Broadcast Start
echo ========================================
echo.

REM Start SBV2 Server (TTS)
echo [1/4] Starting SBV2 Server (TTS)...
start "SBV2" cmd /k "cd /d "%SBV2_DIR%" && Server.bat"
timeout /t 5 /nobreak > nul

REM Start Web Server
echo [2/4] Starting Web Server...
start /B cmd /k "cd apps\pon && python -m http.server 8001"
timeout /t 2 /nobreak > nul

REM Open Browser
echo [3/4] Opening Browser...
start http://localhost:8001/viewer.html
timeout /t 1 /nobreak > nul

REM Start CHRONOS
echo [4/4] Starting CHRONOS...
echo.
echo ========================================
echo  Ready - pon is running
echo ========================================
echo.
echo Web Viewer: http://localhost:8001/viewer.html
echo Type messages and pon will respond with voice
echo (Ctrl+C to stop)
echo.

REM Start with pon character
python main.py pon

pause
