# Run after: gh auth login
# Creates private GitHub repo and pushes (no .conf keys — those stay local)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$remoteUrl = "https://github.com/mjaydarma-beep/WGVPN.git"
Write-Host "Checking GitHub login..."
gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Host "Run: gh auth login"
    Write-Host "Then run this script again."
    exit 1
}

if (-not (git remote get-url origin 2>$null)) {
    git remote add origin $remoteUrl
}
Write-Host "Pushing to $remoteUrl ..."
git push -u origin master

Write-Host "Done. View at: gh repo view --web"
