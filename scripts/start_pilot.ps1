param([int]$Hours = 24)
$ErrorActionPreference = 'Stop'
if ($Hours -lt 1 -or $Hours -gt 24) { throw 'Pilot duration must be 1 to 24 hours.' }
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$pythonPath = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
$scriptPath = Join-Path $projectRoot 'src\collect.py'
$taskName = 'AircraftProject-CollectionPilot'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Set up .venv first.' }
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    throw "Task $taskName already exists. Inspect it before replacing or starting another collector."
}
$start = (Get-Date).AddMinutes(5)
$duration = New-TimeSpan -Hours $Hours
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument ('"{0}" snapshot' -f $scriptPath) -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Once -At $start -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration $duration
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Bounded 24-hour aircraft research pilot; anonymous OpenSky snapshots every five minutes while awake, online and signed in. No catch-up or parallel collectors.'
Register-ScheduledTask -TaskName $taskName -InputObject $task | Out-Null
$evidence = [ordered]@{
    task_name = $taskName
    first_scheduled_local = $start.ToString('o')
    repetition_ends_local = ($start.Add($duration)).ToString('o')
    interval_seconds = 300
    duration_hours = $Hours
    user = $identity
    python = $pythonPath
    script = $scriptPath
    working_directory = $projectRoot
}
$outputFolder = Join-Path $projectRoot 'outputs\pilot'
New-Item -ItemType Directory -Path $outputFolder -Force | Out-Null
$evidence | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputFolder 'schedule.json') -Encoding utf8
$evidence | ConvertTo-Json
