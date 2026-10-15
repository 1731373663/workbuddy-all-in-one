# install-windows.ps1 - WorkBuddy All-in-One scheduled task installer (Windows)
#
# Triggers (run whenever the machine is awake and the user is present):
#   1) At logon              - machine just started / user logged in
#   2) On workstation unlock - fires every time the screen is unlocked
#   3) Daily 11:00 and 19:00 - fallback if the machine stayed unlocked all day
#
# All triggers run the same command. workbuddy.py enforces the guard rules
# (3 successes/day, 5 attempts/day, 3h between successes, 15m retry gap,
# network probe) so frequent unlocks do not spam the API.

$ErrorActionPreference = "Stop"

$Root  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Entry = Join-Path $Root "workbuddy.py"
$Log   = Join-Path $Root "run.log"
$TaskName = "WorkBuddyAllInOne"


# ---- self-elevate: registering the unlock trigger needs administrator ----
$identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
$wp        = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin   = $wp.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Elevation required for the unlock trigger; relaunching as administrator..." -ForegroundColor Yellow
    Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File","`"$PSCommandPath`"") -Verb RunAs
    exit 0
}

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

$user = "$env:USERDOMAIN\$env:USERNAME"
$escLog = [System.Security.SecurityElement]::Escape($Log)
$escEntry = [System.Security.SecurityElement]::Escape($Entry)
$escPy = [System.Security.SecurityElement]::Escape($python)
$escWork = [System.Security.SecurityElement]::Escape($Root)
$args = '/c set PYTHONIOENCODING=utf-8 &amp;&amp; "' + $escPy + '" "' + $escEntry + '" auto &gt;&gt; "' + $escLog + '" 2&gt;&amp;1'

$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>WorkBuddy all-in-one: daily rewards + task center (logon / unlock / daily)</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>$user</UserId>
    </LogonTrigger>
    <SessionStateChangeTrigger>
      <Enabled>true</Enabled>
      <StateChange>SessionUnlock</StateChange>
    </SessionStateChangeTrigger>
    <CalendarTrigger>
      <StartBoundary>2026-10-16T11:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>
    <CalendarTrigger>
      <StartBoundary>2026-10-16T19:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$user</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>cmd.exe</Command>
      <Arguments>$args</Arguments>
      <WorkingDirectory>$escWork</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

foreach ($old in @("WorkBuddyAllInOnePoll","WorkBuddyAutoSignin","WorkBuddyGrowthPoll","WorkBuddyTaskRunner","WorkBuddyTaskRunnerPoll")) {
    if (Get-ScheduledTask -TaskName $old -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $old -Confirm:$false
        Write-Host "removed old task: $old"
    }
}

Register-ScheduledTask -TaskName $TaskName -Xml $xml -Force | Out-Null

Write-Host ""
Write-Host "Task installed:" -ForegroundColor Green
$t = Get-ScheduledTask -TaskName $TaskName
$i = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host ("  {0}  state={1}  next={2}" -f $TaskName, $t.State, $i.NextRunTime)
Write-Host ("  triggers: {0}" -f ($t.Triggers.Count))
$t.Triggers | ForEach-Object { Write-Host ("    - {0}" -f $_.CimClass.CimClassName) }
Write-Host ""
Write-Host "Log: $Log"
Write-Host "Uninstall:"
Write-Host ("  Unregister-ScheduledTask -TaskName `"$TaskName`" -Confirm:`$false")
