[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$environmentPath = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path -LiteralPath $environmentPath)) {
    throw "Environment file not found at '$environmentPath'. Copy .env.example to .env first."
}

Get-Content -LiteralPath $environmentPath | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2], "Process")
    }
}

function Assert-StatusOk {
    param([string]$Uri)

    $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing
    if ($response.StatusCode -ne 200) {
        throw "Expected HTTP 200 from '$Uri', received $($response.StatusCode)."
    }
}

Assert-StatusOk "http://localhost:$env:MLFLOW_PORT/"
Assert-StatusOk "http://localhost:$env:API_PORT/health/live"
Assert-StatusOk "http://localhost:$env:API_PORT/health/ready"

$sourceCount = docker compose exec -T postgres psql -U $env:POSTGRES_USER -d demo -tAc `
    "SELECT COUNT(*) FROM bookings.flights;"
if ([int]$sourceCount.Trim() -le 0) {
    throw "The DemoDB source has no flights."
}

$featureCount = docker compose exec -T postgres psql -U $env:POSTGRES_USER -d demo -tAc `
    "SELECT COUNT(*) FROM ml.flight_delay_features;"
if ([int]$featureCount.Trim() -le 0) {
    throw "The feature mart has no rows."
}

$championVersion = docker compose exec -T api python -c `
    "from flightops.scoring.model import approved_model_version; print(approved_model_version())"
if ([string]::IsNullOrWhiteSpace($championVersion)) {
    throw "MLflow champion model could not be loaded."
}

$eligibleFlightId = docker compose exec -T postgres psql -U $env:POSTGRES_USER -d demo -tAc `
    "SELECT flight_id FROM ml.flight_delay_features WHERE feature_cutoff <= now() AND scheduled_departure > now() ORDER BY scheduled_departure LIMIT 1;"
if ([string]::IsNullOrWhiteSpace($eligibleFlightId)) {
    throw "No T-24h eligible flight is available for the API smoke test."
}

$predictionResponse = Invoke-WebRequest `
    -Method Post `
    -Uri "http://localhost:$env:API_PORT/v1/predictions/flight-delay?flight_id=$($eligibleFlightId.Trim())" `
    -UseBasicParsing
if ($predictionResponse.StatusCode -ne 200) {
    throw "Expected HTTP 200 from the prediction endpoint, received $($predictionResponse.StatusCode)."
}

Write-Host "Smoke test passed: source=$($sourceCount.Trim()), features=$($featureCount.Trim()), champion=$championVersion."
