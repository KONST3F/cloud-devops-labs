$ErrorActionPreference = 'Stop'
$openssl = (Get-Command openssl.exe -ErrorAction Stop).Source
$utf8 = [System.Text.UTF8Encoding]::new($false)
$envFile = Join-Path (Get-Location) '.env'

function New-LocalPassword {
    $bytes = New-Object byte[] 24
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return -join ($bytes | ForEach-Object { $_.ToString('x2') })
}

if (-not (Test-Path -LiteralPath $envFile)) {
    $dbPassword = New-LocalPassword
    $adminPassword = New-LocalPassword
    [System.IO.File]::WriteAllText($envFile, "DB_PASSWORD=$dbPassword`nADMIN_PASSWORD=$adminPassword`n", $utf8)
}

$settings = @{}
foreach ($line in Get-Content -LiteralPath $envFile) {
    if ($line -match '^(DB_PASSWORD|ADMIN_PASSWORD)=([0-9a-f]{48})$') {
        $settings[$Matches[1]] = $Matches[2]
    }
}
if (-not $settings.DB_PASSWORD -or -not $settings.ADMIN_PASSWORD) {
    throw '.env должен содержать DB_PASSWORD и ADMIN_PASSWORD в формате 48 шестнадцатеричных символов.'
}

New-Item -ItemType Directory -Force -Path 'certs', 'auth' | Out-Null
if (-not ((Test-Path -LiteralPath 'certs/local.key') -and (Test-Path -LiteralPath 'certs/local.crt'))) {
    & $openssl req -x509 -newkey rsa:2048 -nodes -days 30 -keyout certs/local.key -out certs/local.crt -subj '/CN=notes.local' -addext 'subjectAltName=DNS:notes.local,DNS:second.local'
    if ($LASTEXITCODE -ne 0) { throw 'Не удалось создать сертификат' }
}
& python tools/create_auth.py
if ($LASTEXITCODE -ne 0) { throw 'Не удалось создать пароль' }
Write-Output 'Локальные файлы .env, certs и auth подготовлены.'
