param(
    [switch]$BuildOnly
)

$ErrorActionPreference = "Stop"

Push-Location $PSScriptRoot
try {
    if ($BuildOnly) {
        docker compose build
    }
    else {
        docker compose up --build -d
    }
}
finally {
    Pop-Location
}