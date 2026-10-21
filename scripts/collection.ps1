param(
    [ValidateSet('Start','Pause','Resume','Status')][string]$Action = 'Status',
    [string]$StartAt,
    [int]$Days = 0
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$taskName = 'AircraftProject-MainCollection'
$rawFolder = Join-Path $projectRoot 'data\raw'
$scheduleFile = Join-Path $rawFolder 'main_schedule.json'
$historyFolder = Join-Path $rawFolder 'schedules'
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Record-Control($kind, $details) {
    New-Item -ItemType Directory -Path $rawFolder -Force | Out-Null
    $entry = [ordered]@{ action=$kind; task_name=$taskName; event_utc=[DateTimeOffset]::UtcNow.ToString('o'); details=$details }
    [IO.File]::AppendAllText((Join-Path $rawFolder 'collection_control.jsonl'), (($entry | ConvertTo-Json -Depth 6 -Compress) + "`n"), $utf8)
}

function Preserve-Task {
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        New-Item -ItemType Directory -Path $historyFolder -Force | Out-Null
        $path = Join-Path $historyFolder ((Get-Date -Format 'yyyyMMddTHHmmssfff') + '-main.xml')
        Export-ScheduledTask -TaskName $taskName | Set-Content -LiteralPath $path -Encoding Unicode
    }
}

function Register-Window([DateTimeOffset]$begin, [DateTimeOffset]$end) {
    $pythonPath = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Install .venv first.' }
    $scriptPath = Join-Path $projectRoot 'src\collect.py'
    $arguments = '"{0}" snapshot --scheduled --until-utc "{1}"' -f $scriptPath, $end.UtcDateTime.ToString('o')
    $actionObject = New-ScheduledTaskAction -Execute $pythonPath -Argument $arguments -WorkingDirectory $projectRoot
    $trigger = New-ScheduledTaskTrigger -Once -At $begin.LocalDateTime -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ($end - $begin)
    $trigger.EndBoundary = $end.ToString('yyyy-MM-ddTHH:mm:sszzz')
    $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    # WakeToRun remains false; no power plan, sleep, shutdown or battery settings are changed.
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
    $task = New-ScheduledTask -Action $actionObject -Trigger $trigger -Settings $settings -Principal $principal -Description 'Bounded university aircraft research collection; five-minute current snapshots; normal laptop sleep; no backfill.'
    Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null
}

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($Action -eq 'Status') {
    foreach ($name in @('AircraftProject-CollectionPilot', $taskName)) {
        $currentTask = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
        if ($currentTask) {
            $info = Get-ScheduledTaskInfo -TaskName $name
            [pscustomobject]@{Task=$name;State=[string]$currentTask.State;LastRun=$info.LastRunTime;Result=$info.LastTaskResult;NextRun=$info.NextRunTime} | Format-List
        } else { Write-Output "$name is not registered." }
    }
    return
}
if ($Action -eq 'Pause') {
    if (-not $existing) { throw 'Main collection is not registered.' }
    Preserve-Task
    Disable-ScheduledTask -TaskName $taskName | Out-Null
    Stop-ScheduledTask -TaskName $taskName
    Record-Control 'pause' @{}
    Write-Output 'Main collection paused. Originals and schedule deadline are preserved.'
    return
}
if ($Action -eq 'Start') {
    if (-not $StartAt -or $Days -lt 1 -or $Days -gt 60) { throw 'Provide -StartAt with timezone offset and -Days from 1 to 60.' }
    if ($StartAt -notmatch '(Z|[+-]\d{2}:\d{2})$') { throw 'StartAt must include a timezone offset, e.g. +02:00.' }
    $begin = [DateTimeOffset]::Parse($StartAt, [Globalization.CultureInfo]::InvariantCulture)
    $end = $begin.AddDays($Days)
    if ($begin -le [DateTimeOffset]::Now) { throw 'Choose a future StartAt.' }
    if ($existing -and $existing.State -ne 'Disabled') { throw 'Main collection is already enabled. Pause or resume it instead of adding a second collector.' }
    if ($existing -and (Test-Path -LiteralPath $scheduleFile)) {
        $previous = Get-Content -LiteralPath $scheduleFile -Raw | ConvertFrom-Json
        if ([DateTimeOffset]::Parse($previous.end_utc) -gt [DateTimeOffset]::Now) { throw 'A paused window is still valid. Use Resume to preserve its deadline.' }
    }
    $pilot = Get-ScheduledTask -TaskName 'AircraftProject-CollectionPilot' -ErrorAction SilentlyContinue
    if ($pilot -and $pilot.State -ne 'Disabled') { throw 'Disable the pilot before starting main collection.' }
    Preserve-Task
    New-Item -ItemType Directory -Path $rawFolder -Force | Out-Null
    Register-Window $begin $end
    $details = [ordered]@{start_utc=$begin.UtcDateTime.ToString('o');end_utc=$end.UtcDateTime.ToString('o');interval_seconds=300;days=$Days}
    [IO.File]::WriteAllText($scheduleFile, ($details | ConvertTo-Json), $utf8)
    Record-Control 'start' $details
} else {
    if (-not $existing -or -not (Test-Path -LiteralPath $scheduleFile)) { throw 'Start a chosen collection window first.' }
    if ($existing.State -ne 'Disabled') { Write-Output 'Main collection is already enabled; no second task started.'; return }
    $details = Get-Content -LiteralPath $scheduleFile -Raw | ConvertFrom-Json
    $end = [DateTimeOffset]::Parse($details.end_utc)
    $begin = [DateTimeOffset]::Now.AddMinutes(5)
    if ($begin -ge $end) { throw 'This window has expired or has fewer than five minutes remaining. Choose a new Start date and duration.' }
    if ($begin -lt [DateTimeOffset]::Parse($details.start_utc)) { $begin = [DateTimeOffset]::Parse($details.start_utc) }
    Preserve-Task
    Register-Window $begin $end
    Record-Control 'resume' @{next_start_utc=$begin.UtcDateTime.ToString('o');end_utc=$end.UtcDateTime.ToString('o')}
}
Write-Output ("$taskName enabled. First tick: {0}; end: {1}." -f $begin.ToString('o'), $end.ToString('o'))
