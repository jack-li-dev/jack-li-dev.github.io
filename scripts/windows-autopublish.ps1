param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("enable", "disable", "status", "remove")]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$Distro,

    [Parameter(Mandatory = $true)]
    [string]$RepoLinuxPath,

    [ValidateRange(5, 1440)]
    [int]$IntervalMinutes = 5
)

$ErrorActionPreference = "Stop"
$TaskName = "JackLiBlog-AutoPublish"

function Get-BlogTask {
    Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
}

switch ($Action) {
    "status" {
        $task = Get-BlogTask
        if (-not $task) {
            Write-Output "scheduler: not-installed (OFF)"
            exit 0
        }
        $info = Get-ScheduledTaskInfo -TaskName $TaskName
        Write-Output "scheduler: $($task.State)"
        Write-Output "last_run: $($info.LastRunTime)"
        Write-Output "last_result: $($info.LastTaskResult)"
        Write-Output "next_run: $($info.NextRunTime)"
        exit 0
    }

    "disable" {
        $task = Get-BlogTask
        if (-not $task) {
            Write-Output "scheduler: not-installed (already OFF)"
            exit 0
        }
        Disable-ScheduledTask -TaskName $TaskName | Out-Null
        Write-Output "scheduler: disabled"
        exit 0
    }

    "remove" {
        $task = Get-BlogTask
        if (-not $task) {
            Write-Output "scheduler: not-installed"
            exit 0
        }
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Output "scheduler: removed"
        exit 0
    }

    "enable" {
        # The task only wakes WSL and runs the deterministic due-check. Human approval,
        # SHA validation, weekly limits, Git safety, and publishing live in blog_release.py.
        if ($RepoLinuxPath.Contains("'")) {
            throw "RepoLinuxPath must not contain a single quote."
        }
        $bashCommand = "cd '$RepoLinuxPath' && mkdir -p .bin && python3 scripts/blog_release.py run-due >> .bin/autopublish.log 2>&1"
        $wslArguments = "-d `"$Distro`" -- bash -lc `"$bashCommand`""

        $taskAction = New-ScheduledTaskAction -Execute "wsl.exe" -Argument $wslArguments
        $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        $principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive
        $logonTrigger = New-ScheduledTaskTrigger -AtLogOn
        $repeatTrigger = New-ScheduledTaskTrigger `
            -Once `
            -At ((Get-Date).AddMinutes(1)) `
            -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
            -RepetitionDuration (New-TimeSpan -Days 3650)
        $settings = New-ScheduledTaskSettingsSet `
            -StartWhenAvailable `
            -MultipleInstances IgnoreNew `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

        Register-ScheduledTask `
            -TaskName $TaskName `
            -Action $taskAction `
            -Trigger @($logonTrigger, $repeatTrigger) `
            -Principal $principal `
            -Settings $settings `
            -Description "Publish Human-approved jack-li.me release packages when due." `
            -Force | Out-Null

        Enable-ScheduledTask -TaskName $TaskName | Out-Null
        Start-ScheduledTask -TaskName $TaskName
        Write-Output "scheduler: enabled"
        Write-Output "distro: $Distro"
        Write-Output "principal: $currentUser (Interactive)"
        Write-Output "repo: $RepoLinuxPath"
        Write-Output "interval_minutes: $IntervalMinutes"
        Write-Output "catch_up: logon trigger + StartWhenAvailable + due-check"
        exit 0
    }
}
