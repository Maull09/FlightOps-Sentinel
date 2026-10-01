[CmdletBinding()]
param(
    [string]$OutputPath = "data/source/demo-20250901-1y.sql.gz"
)

$ErrorActionPreference = "Stop"

$sourceUrl = "https://edu.postgrespro.ru/demo-20250901-1y.sql.gz"
$resolvedOutputPath = Join-Path $PSScriptRoot "..\$OutputPath"
$outputDirectory = Split-Path -Parent $resolvedOutputPath

if (Test-Path -LiteralPath $resolvedOutputPath) {
    throw "Source archive already exists at '$resolvedOutputPath'. It was not overwritten."
}

New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
Invoke-WebRequest -Uri $sourceUrl -OutFile $resolvedOutputPath

Write-Host "Downloaded source archive to '$resolvedOutputPath'."
