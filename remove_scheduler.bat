@echo off
REM Remove all AI Employee scheduled tasks (old and new names)
echo Removing AI Employee scheduled tasks...

schtasks /delete /tn "AIEmployee_FileWatcher"        /f 2>nul
schtasks /delete /tn "AIEmployee_News_Morning"       /f 2>nul
schtasks /delete /tn "AIEmployee_News_Afternoon"     /f 2>nul
schtasks /delete /tn "AIEmployee_News_Evening"       /f 2>nul
schtasks /delete /tn "AIEmployee_Social"             /f 2>nul
schtasks /delete /tn "AIEmployee_Watcher_Morning"    /f 2>nul
schtasks /delete /tn "AIEmployee_Watcher_Afternoon"  /f 2>nul
schtasks /delete /tn "AIEmployee_Watcher_Evening"    /f 2>nul
schtasks /delete /tn "AIEmployee_Email_News_Daily"   /f 2>nul
schtasks /delete /tn "AIEmployee_Email_Social_2Days" /f 2>nul

echo All AI Employee tasks removed.
pause
