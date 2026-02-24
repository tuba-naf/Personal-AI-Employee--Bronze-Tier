@echo off
REM ============================================================
REM AI Employee Bronze Tier - Windows Task Scheduler Setup
REM Run once to register all scheduled tasks.
REM ============================================================

REM --- Auto-elevate to Administrator if needed ---
NET SESSION >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

REM --- Configuration ---
SET PYTHON_PATH=C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe
SET PROJECT_DIR=%~dp0
SET WATCHER_SCRIPT=%PROJECT_DIR%Vault\Watchers\scheduled_run.py
SET EMAIL_SCRIPT=%PROJECT_DIR%Vault\Watchers\email_drafts.py

echo.
echo === AI Employee Bronze Tier - Scheduler Setup ===
echo.
echo Python:  %PYTHON_PATH%
echo Project: %PROJECT_DIR%
echo.

REM --- Task 1: Run watchers at 8:00 AM ---
schtasks /create /tn "AIEmployee_Watcher_Morning" /tr "\"%PYTHON_PATH%\" \"%WATCHER_SCRIPT%\"" /sc daily /st 08:00 /f /rl HIGHEST
echo [OK] Morning watcher at 8:00 AM

REM --- Task 2: Run watchers at 1:00 PM ---
schtasks /create /tn "AIEmployee_Watcher_Afternoon" /tr "\"%PYTHON_PATH%\" \"%WATCHER_SCRIPT%\"" /sc daily /st 13:00 /f /rl HIGHEST
echo [OK] Afternoon watcher at 1:00 PM

REM --- Task 3: Run watchers at 6:00 PM ---
schtasks /create /tn "AIEmployee_Watcher_Evening" /tr "\"%PYTHON_PATH%\" \"%WATCHER_SCRIPT%\"" /sc daily /st 18:00 /f /rl HIGHEST
echo [OK] Evening watcher at 6:00 PM

REM --- Task 4: Email News drafts daily at 7:00 PM ---
schtasks /create /tn "AIEmployee_Email_News_Daily" /tr "\"%PYTHON_PATH%\" \"%EMAIL_SCRIPT%\" --platform news" /sc daily /st 19:00 /f /rl HIGHEST
echo [OK] News email daily at 7:00 PM

REM --- Task 5: Email LinkedIn+Instagram every 2 days at 7:30 PM ---
schtasks /create /tn "AIEmployee_Email_Social_2Days" /tr "\"%PYTHON_PATH%\" \"%EMAIL_SCRIPT%\" --platform linkedin instagram" /sc daily /mo 2 /st 19:30 /f /rl HIGHEST
echo [OK] LinkedIn+Instagram email every 2 days at 7:30 PM

echo.
echo === All 5 tasks registered successfully! ===
echo.
echo Schedule Summary:
echo   Watchers (draft generation): 8:00 AM, 1:00 PM, 6:00 PM daily
echo   News email:                  7:00 PM daily
echo   LinkedIn+Instagram email:    7:30 PM every 2 days
echo.
echo Verify with: schtasks /query /fo LIST /tn "AIEmployee_Watcher_Morning"
echo Remove all:  Run remove_scheduler.bat
echo.
pause
