[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$contractFiles = @(
    "001_source_data_contract.sql",
    "002_staging_label_contract.sql",
    "003_feature_mart_contract.sql"
)
$sourceDirectory = Join-Path $PSScriptRoot "..\sql\checks"

foreach ($contractFile in $contractFiles) {
    $sourcePath = Join-Path $sourceDirectory $contractFile
    $containerPath = "/tmp/$contractFile"

    docker compose cp $sourcePath "postgres:$containerPath"

    if ($LASTEXITCODE -ne 0) {
        throw "Could not copy contract $contractFile into the PostgreSQL container."
    }

    try {
        docker compose exec -T postgres psql -U flightops_admin -d demo -v ON_ERROR_STOP=1 `
            -c "SET ROLE flightops_app;" `
            -f $containerPath

        if ($LASTEXITCODE -ne 0) {
            throw "Data contract $contractFile failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        docker compose exec -T postgres rm -f $containerPath | Out-Null
    }
}

$failedCheckCount = docker compose exec -T postgres psql -U flightops_admin -d demo -tAc `
    "SELECT COUNT(*) FROM (SELECT DISTINCT ON (check_name) passed FROM ml.data_quality_results ORDER BY check_name, checked_at DESC, id DESC) AS latest_checks WHERE NOT passed;"

if ([int]$failedCheckCount.Trim() -ne 0) {
    throw "$failedCheckCount latest data contract checks failed."
}
