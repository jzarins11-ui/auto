@echo off
title YouTube AI Channel - Setup
cls

echo ============================================
echo  YouTube AI Channel - Quick Setup
echo ============================================
echo.

:: --- Python check ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install from https://python.org
    echo        Make sure to check "Add to PATH" during install.
    pause
    exit /b 1
)
echo [OK] Python found

:: --- FFmpeg check + install ---
ffmpeg -version >nul 2>&1
if %errorlevel% equ 0 goto ffmpeg_ok

echo [..] FFmpeg not found. Installing automatically...
set "FFMPEG_DIR=%LOCALAPPDATA%\ffmpeg"
if not exist "%FFMPEG_DIR%" mkdir "%FFMPEG_DIR%"

echo      Downloading (approx 60 MB)...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile '%TEMP%\ffmpeg.zip'}"
if not exist "%TEMP%\ffmpeg.zip" (
    echo [WARN] Download failed. Try manually: https://ffmpeg.org/download.html
    goto after_ffmpeg
)

echo      Extracting...
powershell -Command "& {Expand-Archive -Path '%TEMP%\ffmpeg.zip' -DestinationPath '%TEMP%\ffmpeg_extracted' -Force}"

echo      Installing...
for /d %%i in ("%TEMP%\ffmpeg_extracted\ffmpeg-*") do (
    xcopy /E /I /Y "%%i\bin" "%FFMPEG_DIR%\bin" >nul
)

set "PATH=%PATH%;%FFMPEG_DIR%\bin"
powershell -Command "& {[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';%FFMPEG_DIR%\bin', 'User')}"

del "%TEMP%\ffmpeg.zip" 2>nul
rmdir /S /Q "%TEMP%\ffmpeg_extracted" 2>nul

echo [OK] FFmpeg installed
:ffmpeg_ok
echo [OK] FFmpeg ready

:after_ffmpeg

:: --- Install Python packages ---
echo.
echo Installing Python packages...
pip install -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip install failed. Run: pip install -r requirements.txt
    pause
    exit /b 1
)
echo [OK] Dependencies installed

:: --- Create .env if missing ---
if not exist .env (
    if exist .env.example (
        echo.
        choice /M "Create .env from template"
        if errorlevel 2 goto skip_env
        copy .env.example .env >nul
        echo [INFO] .env created. Opening in Notepad - paste your API keys, save, close.
        start /wait notepad .env
        echo [OK] .env saved
        goto env_done
        :skip_env
        echo [SKIP] You'll need to create .env manually
        :env_done
    )
) else (
    echo [OK] .env found
)

:: --- Test LLM ---
echo.
echo Testing LLM module...
python -c "from scripts.llm import chat; print('[OK] LLM module ready')" 2>nul
if %errorlevel% neq 0 echo [WARN] LLM check failed - check your API keys in .env

:: --- Test YouTube ---
echo.
echo Testing YouTube module...
python -c "from scripts.fetch_top_videos import fetch_top_videos, load_config; print('[OK] YouTube module ready')" 2>nul
if %errorlevel% neq 0 echo [WARN] YouTube check failed - check your YOUTUBE_API_KEY in .env

echo.
echo ============================================
echo  Setup complete
echo ============================================
echo.
echo  Next steps:
echo   1. Edit config\channel_config.json with your channel details
echo   2. Run: python scripts/generate_content_calendar.py
echo   3. Push to GitHub for auto-scheduling
echo.
echo  To upload videos to YouTube:
echo   1. https://console.cloud.google.com -> Enable YouTube Data API v3
echo   2. Credentials -> OAuth 2.0 Client ID -> Desktop app -> Download JSON
echo   3. Save as config\youtube_credentials.json
echo   4. Run: python scripts/upload_to_youtube.py path\to\video.mp4
echo.
pause
