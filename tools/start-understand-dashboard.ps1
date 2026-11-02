param(
    [string]$ProjectPath = '.',
    [ValidateRange(1024, 65535)]
    [int]$Port = 5173
)

$ErrorActionPreference = 'Stop'
$workspaceRoot = Split-Path -Parent $PSScriptRoot
$pluginCheckout = Join-Path $PSScriptRoot 'understand-anything'
if (-not [System.IO.Path]::IsPathRooted($ProjectPath)) {
    $ProjectPath = Join-Path $workspaceRoot $ProjectPath
}
$projectRoot = (Resolve-Path -LiteralPath $ProjectPath).Path
$dataDir = Join-Path $projectRoot '.ua'
if (Test-Path -LiteralPath (Join-Path $projectRoot '.understand-anything')) {
    $dataDir = Join-Path $projectRoot '.understand-anything'
}
if (-not (Test-Path -LiteralPath (Join-Path $dataDir 'knowledge-graph.json'))) {
    throw "Knowledge graph missing. In Codex run: `$understand $projectRoot --language vi"
}
if (-not (Test-Path -LiteralPath (Join-Path $pluginCheckout 'node_modules'))) {
    throw "Dependencies missing. Run pnpm install --frozen-lockfile in $pluginCheckout"
}
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    throw 'pnpm is required. Install Node.js >=22 and pnpm >=10.'
}

$previousGraphDir = $env:GRAPH_DIR
try {
    $env:GRAPH_DIR = $projectRoot
    Push-Location -LiteralPath $pluginCheckout
    try {
        Write-Host "Viewing: $dataDir\knowledge-graph.json"
        Write-Host 'Open the Dashboard URL printed below, including ?token=... . Stop with Ctrl+C.'
        & pnpm --filter '@understand-anything/dashboard' exec vite --host 127.0.0.1 --port $Port --strictPort
        if ($LASTEXITCODE -ne 0) { throw "Dashboard exited with code $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
} finally {
    $env:GRAPH_DIR = $previousGraphDir
}
