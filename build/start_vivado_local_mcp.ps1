param(
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [string]$Vivado = 'D:\Vivado\Vivado\2024.2\bin\vivado.bat',
    [ValidateRange(1024,65535)][int]$Port = 18883
)
# Windows fallback for a Vivado MCP proxy that cannot launch .bat correctly.
# Local Tcl/webserver only: never opens Hardware Manager or a hardware target.
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Vivado -PathType Leaf)) { throw 'Vivado not found' }
if ($OutputDirectory -match '[^\x00-\x7F]' -or $OutputDirectory -match '[\s{}"]') {
    throw 'Use an ASCII staging path without spaces/braces/quotes, outside Git'
}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $Port is already listening; connect to the existing session or choose another port"
}
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$stage = (Get-Item -LiteralPath $OutputDirectory).FullName
$script = Join-Path $stage 'mcp_local.tcl'
if (Test-Path -LiteralPath $script) { throw 'Use a fresh output directory' }
@"
webserver -start -port $Port -key none
puts "VIVADO_LOCAL_MCP_READY"
vwait ::local_mcp_exit
"@ | Set-Content -LiteralPath $script -Encoding ascii
$process = Start-Process -FilePath $Vivado -ArgumentList '-mode batch -nojournal -log mcp_local.log -source mcp_local.tcl' -WorkingDirectory $stage -WindowStyle Hidden -PassThru
[pscustomobject]@{LauncherPid=$process.Id; Url="http://localhost:$Port"; Log=(Join-Path $stage 'mcp_local.log')}
# Connect with vivado_connect after the log reports Started webserver.
# This startup receipt does NOT claim successful connection or compatibility.
