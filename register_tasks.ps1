$watchers = 'C:\Users\user\AI Employee-Bronze\Vault\Watchers'
$logs     = 'C:\Users\user\AI Employee-Bronze\Vault\Logs'

# Remove old tasks
@(
  'AIEmployee_Watcher_Morning','AIEmployee_Watcher_Afternoon','AIEmployee_Watcher_Evening',
  'AIEmployee_Email_News_Daily','AIEmployee_Email_Social_2Days','AIEmployee_FileWatcher',
  'AIEmployee_News_Morning','AIEmployee_News_Afternoon','AIEmployee_News_Evening','AIEmployee_Social'
) | ForEach-Object { Unregister-ScheduledTask -TaskName $_ -Confirm:$false -ErrorAction SilentlyContinue }
Write-Host '[OK] Old tasks cleared.' -ForegroundColor Yellow

# Shared settings for one-shot tasks (generate + email)
$s = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
$s.DisallowStartIfOnBatteries = $false
$s.StopIfGoingOnBatteries     = $false

# Settings for filesystem watcher (continuous process, no time limit)
$fw = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)
$fw.DisallowStartIfOnBatteries = $false
$fw.StopIfGoingOnBatteries     = $false

# Task 1 — FileWatcher: at logon, continuous process
$a = New-ScheduledTaskAction `
    -Execute 'cmd.exe' `
    -Argument "/c `"$watchers\run_filesystem_watcher.bat`"" `
    -WorkingDirectory $watchers
$t = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$p = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
Register-ScheduledTask -TaskName 'AIEmployee_FileWatcher' -Action $a -Trigger $t -Settings $fw -Principal $p -Force | Out-Null
Write-Host '[OK] AIEmployee_FileWatcher     — at logon, runs continuously'

# Task 2 — News 8 AM
$a = New-ScheduledTaskAction `
    -Execute 'cmd.exe' `
    -Argument "/c `"$watchers\run_news.bat`" >> `"$logs\news_morning.log`" 2>&1" `
    -WorkingDirectory $watchers
$t = New-ScheduledTaskTrigger -Daily -At '08:00AM'
Register-ScheduledTask -TaskName 'AIEmployee_News_Morning' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] AIEmployee_News_Morning    — daily 8:00 AM  (generate + email news)'

# Task 3 — Social every 2 days 9 AM
$a = New-ScheduledTaskAction `
    -Execute 'cmd.exe' `
    -Argument "/c `"$watchers\run_social.bat`" >> `"$logs\social.log`" 2>&1" `
    -WorkingDirectory $watchers
$t = New-ScheduledTaskTrigger -Daily -At '09:00AM' -DaysInterval 2
Register-ScheduledTask -TaskName 'AIEmployee_Social' -Action $a -Trigger $t -Settings $s -Force | Out-Null
Write-Host '[OK] AIEmployee_Social          — every 2 days 9:00 AM  (generate + email LinkedIn/Instagram)'

# Start the FileWatcher immediately
Start-ScheduledTask -TaskName 'AIEmployee_FileWatcher'
Write-Host ''
Write-Host '[OK] FileWatcher started now.' -ForegroundColor Green

# Verification
Write-Host ''
Write-Host 'Registered tasks:' -ForegroundColor Cyan
Get-ScheduledTask | Where-Object { $_.TaskName -like 'AIEmployee_*' } |
    ForEach-Object {
        $info = $_ | Get-ScheduledTaskInfo
        '{0,-32} State: {1,-10} Next: {2}' -f $_.TaskName, $_.State, $info.NextRunTime
    }
Write-Host ''
Write-Host 'Done.' -ForegroundColor Cyan
