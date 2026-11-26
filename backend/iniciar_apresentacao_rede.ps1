# Script para iniciar o SIGA Web Admin em rede local (Wi-Fi / Hotspot) na apresentacao
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  SIGA Web Admin - Modo Apresentacao em Rede Local (0.0.0.0:8000)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*"
}

Write-Host "Enderecos detectados neste computador (digite no App Mobile):" -ForegroundColor Yellow
foreach ($ip in $ips) {
    Write-Host ("  - [{0}]  http://{1}:8000" -f $ip.InterfaceAlias, $ip.IPAddress) -ForegroundColor Green
}

Write-Host ""
Write-Host "Caso o celular nao conecte, libere a porta 8000 no Firewall (PowerShell como Admin, 1x):" -ForegroundColor DarkYellow
Write-Host '  New-NetFirewallRule -DisplayName "SIGA Django 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow' -ForegroundColor Gray
Write-Host ""

Write-Host "[1/3] Aplicando migracoes do banco..." -ForegroundColor Cyan
& ".\venv\Scripts\python.exe" manage.py migrate

Write-Host "[2/3] Garantindo dados de demonstracao (usuarios e catalogo da IA)..." -ForegroundColor Cyan
& ".\venv\Scripts\python.exe" manage.py popular_dados

Write-Host "[3/3] Subindo servidor Django em 0.0.0.0:8000..." -ForegroundColor Cyan
& ".\venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000
