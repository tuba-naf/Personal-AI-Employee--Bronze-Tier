@echo off
cd /d "C:\Users\user\AI Employee-Bronze\Vault\Watchers"
"C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe" scheduled_run.py --platform linkedin instagram
"C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe" email_drafts.py --platform linkedin instagram
