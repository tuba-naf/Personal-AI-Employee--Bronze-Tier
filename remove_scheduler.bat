@echo off
REM Remove all AI Employee scheduled tasks
echo Removing AI Employee scheduled tasks...

schtasks /delete /tn "AIEmployee_Watcher_Morning" /f 2>nul
schtasks /delete /tn "AIEmployee_Watcher_Afternoon" /f 2>nul
schtasks /delete /tn "AIEmployee_Watcher_Evening" /f 2>nul
schtasks /delete /tn "AIEmployee_Email_News_Daily" /f 2>nul
schtasks /delete /tn "AIEmployee_Email_Social_2Days" /f 2>nul

echo All AI Employee tasks removed.
pause
