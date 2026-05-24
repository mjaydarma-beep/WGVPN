# Run after: gh auth login
# Creates private GitHub repo and pushes (no .conf keys — those stay local)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$repoName = "VPN_WG"
Write-Host "Checking GitHub login..."
gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Host "Run: gh auth login"
    Write-Host "Then run this script again."
    exit 1
}

if (git remote get-url origin 2>$null) {
    Write-Host "Remote origin exists. Pushing..."
    git push -u origin master
} else {
    Write-Host "Creating private repo $repoName and pushing..."
    gh repo create $repoName --private --source=. --remote=origin --push
}

Write-Host "Done. View at: gh repo view --web"
