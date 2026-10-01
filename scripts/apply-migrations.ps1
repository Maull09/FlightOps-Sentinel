[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$migrationDirectory = Join-Path $PSScriptRoot "..\sql\migrations"
$containerMigrationDirectory = "/tmp/flightops-migrations"

docker compose exec -T postgres psql -U flightops_admin -d demo -v ON_ERROR_STOP=1 -c `
    "SET ROLE flightops_app; CREATE TABLE IF NOT EXISTS ml.schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());"

if ($LASTEXITCODE -ne 0) {
    throw "Could not create the migration history table."
}

docker compose exec -T postgres mkdir -p $containerMigrationDirectory

if ($LASTEXITCODE -ne 0) {
    throw "Could not create the temporary migration directory in the PostgreSQL container."
}

$appliedVersions = @(
    docker compose exec -T postgres psql -U flightops_admin -d demo -tAc `
        "SELECT version FROM ml.schema_migrations ORDER BY version;"
)

Get-ChildItem -Path $migrationDirectory -Filter "*.sql" | Sort-Object Name | ForEach-Object {
    $migration = $_

    if ($migration.Name -in $appliedVersions) {
        Write-Host "Skipping applied migration $($migration.Name)."
        return
    }

    docker compose cp $migration.FullName "postgres:$containerMigrationDirectory/$($migration.Name)"

    if ($LASTEXITCODE -ne 0) {
        throw "Could not copy migration $($migration.Name) into the PostgreSQL container."
    }

    docker compose exec -T postgres psql -U flightops_admin -d demo -v ON_ERROR_STOP=1 `
        -c "SET ROLE flightops_app;" `
        -f "$containerMigrationDirectory/$($migration.Name)"

    if ($LASTEXITCODE -ne 0) {
        throw "Migration $($migration.Name) failed with exit code $LASTEXITCODE."
    }

    docker compose exec -T postgres psql -U flightops_admin -d demo -v ON_ERROR_STOP=1 -c `
        "SET ROLE flightops_app; INSERT INTO ml.schema_migrations (version) VALUES ('$($migration.Name)');"

    if ($LASTEXITCODE -ne 0) {
        throw "Could not record migration $($migration.Name)."
    }

    Write-Host "Applied migration $($migration.Name)."
}
