param([Security.SecureString]$Password)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
$envFile = Join-Path $projectRoot '.env'
if (-not (Test-Path -LiteralPath $envFile)) {
    throw 'Create .env from .env.example and start the Docker app first.'
}
if (-not $Password) { $Password = Read-Host 'Admin deletion password' -AsSecureString }
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
$previousOutputEncoding = $OutputEncoding
Push-Location $projectRoot
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    if ([string]::IsNullOrWhiteSpace($plainPassword)) { throw 'The password cannot be empty.' }
    $OutputEncoding = New-Object Text.UTF8Encoding($false)
    # Pass the password through stdin, never as a Docker/Python command-line argument.
    $passwordHash = $plainPassword | docker compose exec -T app python -c "import sys; from backend.app import password_hash; print(password_hash(sys.stdin.buffer.read().decode('utf-8').rstrip('\r\n')))"
    if ($LASTEXITCODE -ne 0 -or $passwordHash -notmatch '^[0-9a-f]{32}\$[0-9a-f]{64}$') {
        throw 'Could not generate the password hash. Check that the Docker app is running.'
    }
    $configuration = [IO.File]::ReadAllText($envFile)
    $configuration = [regex]::Replace($configuration, '(?m)^ADMIN_DELETE_PASSWORD_HASH=.*(?:\r?\n)?', '')
    # Single quotes stop Compose interpreting the literal dollar sign in the hash.
    $configuration = $configuration.TrimEnd() + "`r`nADMIN_DELETE_PASSWORD_HASH='" + $passwordHash.Trim() + "'`r`n"
    [IO.File]::WriteAllText($envFile, $configuration, (New-Object Text.UTF8Encoding($false)))
    Write-Output 'Admin deletion password configured locally. The password and hash were not printed.'
    Write-Output 'Apply the setting with: docker compose up -d app'
} finally {
    $plainPassword = $null
    $passwordHash = $null
    $OutputEncoding = $previousOutputEncoding
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    Pop-Location
}
