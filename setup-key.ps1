<#
.SYNOPSIS
  Writes the local .env for Watcher, asking for the key with a masked prompt.

.DESCRIPTION
  The key is typed into a SecureString, so it never lands in the terminal
  scrollback, in PSReadLine history, or in a screen recording. It is written to
  .env (gitignored) and the script then verifies it against the endpoint that
  will actually be called, reporting only a verdict and a fingerprint.

  Nothing here ever prints the key.

.EXAMPLE
  ./setup-key.ps1
  ./setup-key.ps1 -Provider anthropic
#>
[CmdletBinding()]
param(
    [ValidateSet('mnemosyne', 'anthropic')]
    [string]$Provider = 'mnemosyne',

    # Only used for the mnemosyne provider.
    [string]$ProxyUrl = 'http://127.0.0.1:7439/v1'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$envPath = Join-Path $root '.env'

function Get-Fingerprint([string]$value) {
    # Same shape as the host's keyFingerprint: sha256, first 8 hex chars. Lets
    # you match what you pasted against what the cartridge shows, without
    # either side ever displaying the key.
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($value))
    -join ($bytes | ForEach-Object { $_.ToString('x2') }) | ForEach-Object { $_.Substring(0, 8) }
}

if ($Provider -eq 'mnemosyne') {
    Write-Host ''
    Write-Host '  Mnemosyne brain proxy' -ForegroundColor Cyan
    Write-Host '  Open the MnemoHermes cartridge, brain proxy section, and copy the key.'
    Write-Host "  It will be checked against $ProxyUrl"
    $varName = 'MNEMO_PROXY_KEY'
} else {
    Write-Host ''
    Write-Host '  Anthropic API' -ForegroundColor Cyan
    Write-Host '  Paste an API key from console.anthropic.com.'
    $varName = 'ANTHROPIC_API_KEY'
}

Write-Host '  Nothing you type will be shown or logged.' -ForegroundColor DarkGray
Write-Host ''

$secure = Read-Host -Prompt "  $varName" -AsSecureString
$key = [System.Net.NetworkCredential]::new('', $secure).Password

if ([string]::IsNullOrWhiteSpace($key)) {
    Write-Host ''
    Write-Host '  Nothing entered. No file written.' -ForegroundColor Yellow
    exit 1
}

# An existing .env is preserved, never silently replaced.
if (Test-Path $envPath) {
    $backup = "$envPath.bak"
    Copy-Item $envPath $backup -Force
    Write-Host ''
    Write-Host "  Existing .env kept as $(Split-Path -Leaf $backup)" -ForegroundColor DarkGray
}

$lines = @("MODEL_PROVIDER=$Provider", "$varName=$key")
if ($Provider -eq 'mnemosyne') { $lines += "MNEMO_PROXY_URL=$ProxyUrl" }

# UTF8 without BOM: a BOM would end up inside the first variable name.
[System.IO.File]::WriteAllLines($envPath, $lines, [System.Text.UTF8Encoding]::new($false))

Write-Host ''
Write-Host "  .env written  (provider $Provider, key fingerprint $(Get-Fingerprint $key))" -ForegroundColor Green

# ── Verify against the endpoint that will actually be called ────────────────
if ($Provider -ne 'mnemosyne') {
    Write-Host '  Not verified: the Anthropic path is checked on the first real call.' -ForegroundColor DarkGray
    Write-Host ''
    Write-Host '  Next:  .venv\Scripts\python.exe -m watcher'
    exit 0
}

Write-Host '  Checking the key against the proxy...' -ForegroundColor DarkGray
try {
    $res = Invoke-WebRequest -Uri "$ProxyUrl/models" `
        -Headers @{ Authorization = "Bearer $key" } `
        -TimeoutSec 10 -SkipHttpErrorCheck
    $code = [int]$res.StatusCode
} catch {
    # A proxy that is not listening and a key that is refused are two different
    # problems with two different fixes, so they get two different sentences.
    Write-Host ''
    Write-Host '  Could not reach the proxy at all.' -ForegroundColor Red
    Write-Host '  Is Mnemosyne OS running, and is the brain proxy switched on in MnemoHermes?'
    Write-Host "  ($($_.Exception.Message))" -ForegroundColor DarkGray
    exit 3
}

switch ($code) {
    200 {
        Write-Host '  Key accepted. The proxy answered /v1/models.' -ForegroundColor Green
        Write-Host ''
        Write-Host '  Next:  .venv\Scripts\python.exe -m watcher'
        exit 0
    }
    401 {
        Write-Host ''
        Write-Host '  The proxy is up but refused this key (401).' -ForegroundColor Red
        Write-Host '  The brain-proxy key is regenerated on each boot of the app.'
        Write-Host '  Re-copy it from MnemoHermes and run this script again.'
        exit 4
    }
    default {
        # An unexpected code is reported as itself, never rounded to "it works".
        Write-Host ''
        Write-Host "  Unexpected answer from the proxy: HTTP $code" -ForegroundColor Yellow
        Write-Host '  The key was written, but nothing here proves it is the right one.'
        exit 5
    }
}
