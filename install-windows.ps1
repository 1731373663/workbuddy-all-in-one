# install-windows.ps1 - WorkBuddy All-in-One scheduled task installer
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Entry = Join-Path $Root "workbuddy.py"
$Log = Join-Path $Root "run.log"

function Find-Python {
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($py) { return $py }
    $py = (Get-Command py -ErrorAction SilentlyContinue).Source
    if ($py) { return $py }
    foreach ($pat in @("C:\Python3*\python.exe", "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe", "C:\Program Files\Python3*\python.exe")) {
        $hit = Get-ChildItem $pat -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return $null
}

$python = Find-Python
if (-not $python) {
    Write-Host "python not found. Install Python 3 first: https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
Write-Host "python: $python"

$cmd = "/c set PYTHONIOENCODING=utf-8 && `"$python`" `"$Entry`" auto >> `"$Log`" 2>&1"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $cmd -WorkingDirectory $Root
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

# daily full run
$t1 = New-ScheduledTaskTrigger -Daily -At "00:05"
$s1 = New-ScheduledTaskSettingsSet -StartWhenAvailable -Hidden -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "WorkBuddyAllInOne" -Action $action -Trigger $t1 -Settings $s1 -Principal $principal -Description "WorkBuddy all-in-one: daily rewards + task center" -Force | Out-Null

# poll every 4 hours
$triggers = @()
foreach ($hh in @("04:00","08:00","12:00","16:00","20:00")) { $triggers += New-ScheduledTaskTrigger -Daily -At $hh }
$s2 = New-ScheduledTaskSettingsSet -StartWhenAvailable -Hidden -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
Register-ScheduledTask -TaskName "WorkBuddyAllInOnePoll" -Action $action -Trigger $triggers -Settings $s2 -Principal $principal -Description "WorkBuddy all-in-one poll (every 4h)" -Force | Out-Null

Write-Host ""
Write-Host "Scheduled tasks installed:" -ForegroundColor Green
foreach ($n in @("WorkBuddyAllInOne","WorkBuddyAllInOnePoll")) {
    $t = Get-ScheduledTask -TaskName $n
    $i = Get-ScheduledTaskInfo -TaskName $n
    Write-Host ("  {0,-26} {1,-8} next {2}" -f $n, $t.State, $i.NextRunTime)
}
Write-Host ""
Write-Host "Log: $Log"
Write-Host "Uninstall:"
Write-Host '  Unregister-ScheduledTask -TaskName "WorkBuddyAllInOne" -Confirm:$false'
Write-Host '  Unregister-ScheduledTask -TaskName "WorkBuddyAllInOnePoll" -Confirm:$false'
