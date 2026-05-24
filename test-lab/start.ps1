# Start VPN router + LAN test lab
$ErrorActionPreference = "Stop"

Write-Host "Checking Docker..."
$ready = $false
for ($i = 1; $i -le 36; $i++) {
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        Write-Host "Docker is ready."
        break
    }
    Write-Host "Waiting for Docker Desktop... ($i/36)"
    Start-Sleep -Seconds 5
}

if (-not $ready) {
    Write-Host ""
    Write-Host "Docker is not running. Open Docker Desktop, wait until it says Running, then run:"
    Write-Host "  cd d:\VPN_WG\test-lab"
    Write-Host "  .\start.ps1"
    exit 1
}

Set-Location $PSScriptRoot
docker compose up -d --build

Write-Host ""
Write-Host "Lab started. Check routers:"
Write-Host "  docker exec wg-site1-router wg show"
Write-Host "  docker exec wg-site2-router wg show"
Write-Host ""
Write-Host "On PC: import ..\peers\phone.conf in WireGuard, then:"
Write-Host "  ping 192.168.10.100"
Write-Host "  ping 192.168.20.100"
