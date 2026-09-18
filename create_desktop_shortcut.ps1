$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcherPath = Join-Path $projectDir "start_all.bat"
$iconPath = Join-Path $projectDir "assets\push-notifications.ico"
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "Smart Meter PUSH Notifications.lnk"

if (-not (Test-Path $launcherPath)) {
    throw "start_all.bat was not found."
}

if (-not (Test-Path $iconPath)) {
    throw "The application icon was not found."
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)

$shortcut.TargetPath = $launcherPath
$shortcut.WorkingDirectory = $projectDir
$shortcut.IconLocation = "$iconPath,0"
$shortcut.Description = "Smart meter PUSH notifications"
$shortcut.Save()

Write-Host "Shortcut created: $shortcutPath"