param(
    [string]$ServerAddress = '192.168.70.5',
    [switch]$AllowFirewall
)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$address = [System.Net.IPAddress]::Parse($ServerAddress)
if ($address.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) { throw 'Use the PC IPv4 address.' }
$serverUrl = 'http://' + $address.ToString() + ':8000'
$envPath = Join-Path $project '.env'
if (-not (Test-Path -LiteralPath $envPath)) { Copy-Item -LiteralPath (Join-Path $project '.env.example') -Destination $envPath }
$settings = [IO.File]::ReadAllText($envPath)
if ($settings -match '(?m)^PUBLIC_BASE_URL=') { $settings = [regex]::Replace($settings, '(?m)^PUBLIC_BASE_URL=.*$', ('PUBLIC_BASE_URL=' + $serverUrl)) }
else { $settings += "`nPUBLIC_BASE_URL=$serverUrl`n" }
[IO.File]::WriteAllText($envPath, $settings, [Text.UTF8Encoding]::new($false))
if ($AllowFirewall) {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run this script as Administrator to add the narrow phone-test firewall rule.' }
    $rule = Get-NetFirewallRule -Name 'GivingFlow-Phone-Test' -ErrorAction SilentlyContinue
    if ($rule) { $rule | Remove-NetFirewallRule }
    New-NetFirewallRule -Name 'GivingFlow-Phone-Test' -DisplayName 'GivingFlow phone test - local subnet only' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -LocalAddress $address.ToString() -RemoteAddress LocalSubnet -Profile Any | Out-Null
    Write-Output 'Phone access allowed: TCP 8000, this PC address, local subnet only. PostgreSQL remains private.'
}
Write-Output ('App server: ' + $serverUrl)
Write-Output ('Phone install page: ' + $serverUrl + '/android')
Write-Output 'Restart the app with docker compose up -d after changing the URL. Existing database records are preserved.'
