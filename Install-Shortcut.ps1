# User-level shortcut only. No admin access, registry changes or new software.
$projectPath = $PSScriptRoot
$pythonPath = Join-Path $projectPath '.venv\Scripts\pythonw.exe'
$appPath = Join-Path $projectPath 'local_app.py'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Python environment missing. See README.md.'
}
$desktopPath = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktopPath 'Bilal Voice Translator.lnk'
$shortcutShell = New-Object -ComObject WScript.Shell
if (Test-Path -LiteralPath $shortcutPath) {
    $previousShortcut = $shortcutShell.CreateShortcut($shortcutPath)
    if ($previousShortcut.TargetPath -ne $pythonPath -or $previousShortcut.Arguments -ne ('"' + $appPath + '"')) {
        throw 'A different shortcut uses this name. It has not been overwritten.'
    }
}
$shortcut = $shortcutShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonPath
$shortcut.Arguments = '"' + $appPath + '"'
$shortcut.WorkingDirectory = $projectPath
$shortcut.Description = 'Personal Urdu-English voice translator'
$shortcut.IconLocation = $pythonPath + ',0'
$shortcut.Save()
Write-Output ('Shortcut ready: ' + $shortcutPath)
