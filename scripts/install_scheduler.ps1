$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$bat = Join-Path $root 'scripts\run_daily_briefing.bat'
$action = New-ScheduledTaskAction -Execute "$env:WINDIR\System32\cmd.exe" -Argument "/c `"$bat`""
$trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName 'CareerOS Daily Briefing' -Action $action -Trigger $trigger -Settings $settings -Description 'Run CareerOS daily job discovery and refresh local briefing.' -Force
Write-Host 'Installed CareerOS daily task for 9:00 AM. Keep the laptop powered on and logged in.'
