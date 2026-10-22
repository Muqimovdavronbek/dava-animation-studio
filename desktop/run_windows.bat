@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 run.py %*
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python 3.12 kerak: https://www.python.org/downloads/windows/
        echo O'rnatishda "Add python.exe to PATH" ni belgilang.
        pause
        exit /b 1
    )
    python run.py %*
)
if errorlevel 1 (
    echo.
    echo Xato yuz berdi. Yuqoridagi xabarni tekshiring.
    pause
    exit /b 1
)
