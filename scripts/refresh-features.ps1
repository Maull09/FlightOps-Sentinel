[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$sourcePath = Join-Path $PSScriptRoot "..\sql\ml\001_refresh_flight_delay_features.sql"
$containerPath = "/tmp/001_refresh_flight_delay_features.sql"

docker compose cp $sourcePath "postgres:$containerPath"

if ($LASTEXITCODE -ne 0) {
    throw "Could not copy the feature refresh SQL into the PostgreSQL container."
}

try {
    docker compose exec -T postgres psql -U flightops_admin -d demo -v ON_ERROR_STOP=1 `
        -c "SET ROLE flightops_app;" `
        -f $containerPath

    if ($LASTEXITCODE -ne 0) {
        throw "Feature refresh failed with exit code $LASTEXITCODE."
    }
}
finally {
    docker compose exec -T postgres rm -f $containerPath | Out-Null
}
