[CmdletBinding()]
param(
    [string]$ArchivePath = "data/source/demo-20250901-1y.sql.gz"
)

$ErrorActionPreference = "Stop"

$resolvedArchivePath = Join-Path $PSScriptRoot "..\$ArchivePath"

if (-not (Test-Path -LiteralPath $resolvedArchivePath)) {
    throw "Source archive not found at '$resolvedArchivePath'. Run scripts/download-demo-database.ps1 first."
}

$databaseExists = docker compose exec -T postgres psql -U flightops_admin -d postgres -tAc `
    "SELECT 1 FROM pg_database WHERE datname = 'demo';"

if ($null -ne $databaseExists -and $databaseExists.Trim() -eq "1") {
    throw "Database 'demo' already exists. Restore was not run because the source dump recreates that database."
}

docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U flightops_admin -d postgres -c `
    "CREATE DATABASE demo;"

if ($LASTEXITCODE -ne 0) {
    throw "Could not create the empty 'demo' database required by the source dump."
}

$archiveFileName = Split-Path -Leaf $resolvedArchivePath
docker compose cp $resolvedArchivePath "postgres:/tmp/$archiveFileName"

try {
    $restoreCommand = 'set -o pipefail; gzip -dc /tmp/' + $archiveFileName +
        ' | sed ''/^SET transaction_timeout/d'' | psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres'
    docker compose exec -T postgres bash -c $restoreCommand

    if ($LASTEXITCODE -ne 0) {
        throw "Source database restore failed with exit code $LASTEXITCODE."
    }
}
finally {
    docker compose exec -T postgres rm -f "/tmp/$archiveFileName" | Out-Null
}

docker compose exec -T postgres sh -lc @'
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d demo <<SQL
CREATE ROLE "$POSTGRES_PROJECT_USER" LOGIN PASSWORD '$POSTGRES_PROJECT_PASSWORD';
GRANT CONNECT ON DATABASE demo TO "$POSTGRES_PROJECT_USER";
GRANT USAGE ON SCHEMA bookings TO "$POSTGRES_PROJECT_USER";
GRANT SELECT ON ALL TABLES IN SCHEMA bookings TO "$POSTGRES_PROJECT_USER";
CREATE SCHEMA staging AUTHORIZATION "$POSTGRES_PROJECT_USER";
CREATE SCHEMA analytics AUTHORIZATION "$POSTGRES_PROJECT_USER";
CREATE SCHEMA ml AUTHORIZATION "$POSTGRES_PROJECT_USER";
SQL
'@

if ($LASTEXITCODE -ne 0) {
    throw "Project role setup failed with exit code $LASTEXITCODE."
}

Write-Host "Restored database 'demo' and created the restricted project role."
