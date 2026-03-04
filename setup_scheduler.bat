@echo off
REM ============================================================
REM AI Employee Bronze Tier - Windows Task Scheduler Setup
REM Run once (as Administrator) to register all scheduled tasks.
REM
REM Fixes vs original:
REM   - Uses PowerShell for registration (handles spaces in paths)
REM   - Calls .bat files that set correct working dir (loads .env)
REM   - Runs on battery (DisallowStartIfOnBatteries = false)
REM   - Adds filesystem watcher at logon
REM   - Consolidates generate + email into single .bat per platform
REM ============================================================

REM --- Auto-elevate to Administrator if needed ---
NET SESSION >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo === AI Employee - Scheduler Setup ===
echo.

REM --- Remove old broken tasks ---
schtasks /delete /tn "AIEmployee_Watcher_Morning"    /f >nul 2>&1
schtasks /delete /tn "AIEmployee_Watcher_Afternoon"  /f >nul 2>&1
schtasks /delete /tn "AIEmployee_Watcher_Evening"    /f >nul 2>&1
schtasks /delete /tn "AIEmployee_Email_News_Daily"   /f >nul 2>&1
schtasks /delete /tn "AIEmployee_Email_Social_2Days" /f >nul 2>&1
schtasks /delete /tn "AIEmployee_FileWatcher"        /f >nul 2>&1
echo [OK] Old tasks removed.

REM --- Register all tasks via PowerShell (handles spaces in paths correctly) ---
powershell -ExecutionPolicy Bypass -Command ^
  "$watchers = 'C:\Users\user\AI Employee-Bronze\Vault\Watchers';" ^
  "$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 15) -DisallowHardTerminate $false;" ^
  "$settings.DisallowStartIfOnBatteries = $false;" ^
  "$settings.StopIfGoingOnBatteries = $false;" ^
  "" ^
  "# Task 1: Filesystem Watcher - runs at logon, restarts if it crashes" ^
  "$fwSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 0) -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 2);" ^
  "$fwSettings.DisallowStartIfOnBatteries = $false;" ^
  "$fwSettings.StopIfGoingOnBatteries = $false;" ^
  "$a1 = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c \"' + $watchers + '\run_filesystem_watcher.bat\"') -WorkingDirectory $watchers;" ^
  "$t1 = New-ScheduledTaskTrigger -AtLogOn;" ^
  "Register-ScheduledTask -TaskName 'AIEmployee_FileWatcher' -Action $a1 -Trigger $t1 -Settings $fwSettings -RunLevel Highest -Force | Out-Null;" ^
  "Write-Host '[OK] AIEmployee_FileWatcher - runs at logon, auto-restarts';" ^
  "" ^
  "# Task 2: News - 8:00 AM daily (generate + email)" ^
  "$a2 = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c \"' + $watchers + '\run_news.bat\" >> \"' + $watchers + '\..\Logs\news_morning.log\" 2>&1') -WorkingDirectory $watchers;" ^
  "$t2 = New-ScheduledTaskTrigger -Daily -At '08:00AM';" ^
  "Register-ScheduledTask -TaskName 'AIEmployee_News_Morning' -Action $a2 -Trigger $t2 -Settings $settings -RunLevel Highest -Force | Out-Null;" ^
  "Write-Host '[OK] AIEmployee_News_Morning - daily 8:00 AM';" ^
  "" ^
  "# Task 3: News - 1:00 PM daily (retry if morning failed)" ^
  "$a3 = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c \"' + $watchers + '\run_news.bat\" >> \"' + $watchers + '\..\Logs\news_afternoon.log\" 2>&1') -WorkingDirectory $watchers;" ^
  "$t3 = New-ScheduledTaskTrigger -Daily -At '01:00PM';" ^
  "Register-ScheduledTask -TaskName 'AIEmployee_News_Afternoon' -Action $a3 -Trigger $t3 -Settings $settings -RunLevel Highest -Force | Out-Null;" ^
  "Write-Host '[OK] AIEmployee_News_Afternoon - daily 1:00 PM';" ^
  "" ^
  "# Task 4: News - 6:00 PM daily (retry if earlier runs failed)" ^
  "$a4 = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c \"' + $watchers + '\run_news.bat\" >> \"' + $watchers + '\..\Logs\news_evening.log\" 2>&1') -WorkingDirectory $watchers;" ^
  "$t4 = New-ScheduledTaskTrigger -Daily -At '06:00PM';" ^
  "Register-ScheduledTask -TaskName 'AIEmployee_News_Evening' -Action $a4 -Trigger $t4 -Settings $settings -RunLevel Highest -Force | Out-Null;" ^
  "Write-Host '[OK] AIEmployee_News_Evening - daily 6:00 PM';" ^
  "" ^
  "# Task 5: Social - every 2 days at 9:00 AM (generate + email LinkedIn + Instagram)" ^
  "$a5 = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c \"' + $watchers + '\run_social.bat\" >> \"' + $watchers + '\..\Logs\social.log\" 2>&1') -WorkingDirectory $watchers;" ^
  "$t5 = New-ScheduledTaskTrigger -Daily -At '09:00AM' -DaysInterval 2;" ^
  "Register-ScheduledTask -TaskName 'AIEmployee_Social' -Action $a5 -Trigger $t5 -Settings $settings -RunLevel Highest -Force | Out-Null;" ^
  "Write-Host '[OK] AIEmployee_Social - every 2 days 9:00 AM';" ^
  "" ^
  "Write-Host ''; Write-Host 'All 5 tasks registered.' -ForegroundColor Green"

echo.
echo Starting FileWatcher now...
schtasks /run /tn "AIEmployee_FileWatcher" >nul 2>&1
echo [OK] FileWatcher started.

echo.
echo === Schedule Summary ===
echo   FileWatcher:    Runs at every login (monitors Inbox folder)
echo   News drafts:    8:00 AM daily (generate + email, 1 per day)
echo   Social drafts:  Every 2 days at 9:00 AM (generate + email)
echo   Logs saved to:  Vault\Logs\news_morning.log etc.
echo.
echo Remove all tasks: run remove_scheduler.bat
echo.
pause
