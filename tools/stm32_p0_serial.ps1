<#
Send the generated A-I plan to a verified log-only STM32 over one USB-TTL.
Requires Windows PowerShell 7/.NET, Python, and exclusive ownership of the port.
#>
param(
    [Parameter(Mandatory=$true)][string]$Port,
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ([System.IO.Ports.SerialPort]::GetPortNames() -notcontains $Port) {
    throw "Port $Port is not present"
}
$root = Split-Path -Parent $PSScriptRoot
$output = [System.IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $output) { throw 'Use a new output directory for each run' }
[System.IO.Directory]::CreateDirectory($output) | Out-Null
$utf8 = [System.Text.UTF8Encoding]::new($false)
$raw = [System.IO.File]::OpenWrite((Join-Path $output 'mcu-raw.bin'))
$linesFile = [System.IO.StreamWriter]::new((Join-Path $output 'mcu-lines.jsonl'), $false, $utf8)
$sendsFile = [System.IO.StreamWriter]::new((Join-Path $output 'pc-sends.jsonl'), $false, $utf8)
$clock = [System.Diagnostics.Stopwatch]::StartNew()
$state = @{ text=''; latest=$null; lines=0; sequence=0 }
$serial = [System.IO.Ports.SerialPort]::new($Port, 115200,
    [System.IO.Ports.Parity]::None, 8, [System.IO.Ports.StopBits]::One)
$serial.Handshake = [System.IO.Ports.Handshake]::None
$serial.DtrEnable = $false
$serial.RtsEnable = $false
$serial.ReadTimeout = 250
$serial.WriteTimeout = 500

function Pump-Receive {
    while ($serial.BytesToRead -gt 0) {
        $bytes = [byte[]]::new([Math]::Min(8192, $serial.BytesToRead))
        $count = $serial.Read($bytes, 0, $bytes.Length)
        $raw.Write($bytes, 0, $count)
        $state.text += [System.Text.Encoding]::ASCII.GetString($bytes, 0, $count)
        while (($end = $state.text.IndexOf([char]10)) -ge 0) {
            $line = $state.text.Substring(0, $end).TrimEnd([char]13)
            $state.text = $state.text.Substring($end + 1)
            $fields = @{}
            $tokens = $line.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
            if ($tokens.Length -ge 4 -and $tokens[0] -eq 'P0V' -and $tokens[1] -eq '1') {
                for ($i=2; $i+1 -lt $tokens.Length; $i+=2) {
                    $fields[$tokens[$i]] = $tokens[$i+1]
                }
                $state.latest = $fields
            }
            $record = @{ utc=[DateTimeOffset]::UtcNow.ToString('o');
                pc_elapsed_ms=$clock.Elapsed.TotalMilliseconds; line=$line; fields=$fields }
            $linesFile.WriteLine(($record | ConvertTo-Json -Compress -Depth 5))
            $state.lines++
        }
    }
}

function Wait-Until([double]$Deadline) {
    while ($clock.Elapsed.TotalMilliseconds -lt $Deadline) {
        Pump-Receive
        Start-Sleep -Milliseconds 2
    }
    Pump-Receive
}

function Send-Hex([string]$Hex, [string]$Phase) {
    Pump-Receive
    if ($null -eq $state.latest -or $state.latest['OUTPUTS'] -ne '0') {
        throw 'A complete P0V OUTPUTS 0 line is required before every write'
    }
    $bytes = [Convert]::FromHexString($Hex)
    $started = $clock.Elapsed.TotalMilliseconds
    $utc = [DateTimeOffset]::UtcNow.ToString('o')
    $serial.Write($bytes, 0, $bytes.Length)
    $state.sequence++
    $record = @{ sequence=$state.sequence; phase=$Phase; utc=$utc; input_hex=$Hex;
        pc_write_start_ms=$started; pc_write_end_ms=$clock.Elapsed.TotalMilliseconds }
    $sendsFile.WriteLine(($record | ConvertTo-Json -Compress))
    $sendsFile.Flush()
}

try {
    $serial.Open()
    Wait-Until ($clock.Elapsed.TotalMilliseconds + 600)
    if ($null -eq $state.latest -or $state.latest['OUTPUTS'] -ne '0') {
        throw 'Log-only handshake missing: received no complete P0V OUTPUTS 0 line; no packet sent'
    }
    $seed = [uint64]$state.latest['SESSION'] + 1
    if ($seed -ge 4294967295) { throw 'Session exhausted; reset the MCU before testing' }
    $initial = $state.latest.Clone()
    $planOutput = Join-Path $output 'generated-plan'
    Push-Location $root
    try {
        $planCommandOutput = & $Python -m tools.stm32_p0_bench --session $seed --output $planOutput --plan-only
        if ($LASTEXITCODE -ne 0) { throw 'Plan generation failed' }
    } finally { Pop-Location }
    $plan = Get-Content -LiteralPath (Join-Path $planOutput 'plan.json') -Raw | ConvertFrom-Json
    $records = [System.Collections.Generic.List[object]]::new()
    foreach ($phase in $plan) {
        Pump-Receive
        $before = $state.latest.Clone()
        $phaseStart = $clock.Elapsed.TotalMilliseconds
        if ($phase.PSObject.Properties.Name -contains 'packets') {
            $due = $clock.Elapsed.TotalMilliseconds
            foreach ($hex in $phase.packets) {
                Wait-Until $due
                Send-Hex $hex $phase.id
                $due += $phase.interval_ms
            }
            Wait-Until $due
        }
        if ($phase.PSObject.Properties.Name -contains 'prefix') {
            Send-Hex $phase.prefix $phase.id
        }
        if ($phase.PSObject.Properties.Name -contains 'idle_ms') {
            Wait-Until ($clock.Elapsed.TotalMilliseconds + $phase.idle_ms)
        }
        # A 50 ms snapshot plus <37 ms at 115200 must finish; last input is <200 ms old.
        Wait-Until ($clock.Elapsed.TotalMilliseconds + 125)
        $actual = $state.latest.Clone()
        $checks = @{}
        foreach ($property in $phase.expected.PSObject.Properties) {
            $name = $property.Name
            if ($name.EndsWith('_DELTA')) {
                $field = $name.Substring(0, $name.Length-6)
                $checks[$name] = ([uint64]$actual[$field] - [uint64]$before[$field]) -ge [uint64]$property.Value
            } else {
                $checks[$name] = $actual[$name] -eq [string]$property.Value
            }
        }
        $checks['OUTPUTS'] = $actual['OUTPUTS'] -eq '0'
        $passed = @($checks.Values | Where-Object { $_ -ne $true }).Count -eq 0
        $records.Add(@{ id=$phase.id; status=$(if ($passed) {'completed'} else {'failed'});
            expected=$phase.expected; before=$before; actual=$actual; checks=$checks;
            pc_start_ms=$phaseStart; pc_end_ms=$clock.Elapsed.TotalMilliseconds })
    }
    Pump-Receive
    $passed = @($records | Where-Object { $_.status -ne 'completed' }).Count -eq 0
    $result = @{ execution='physical_serial'; port=$Port; baud=115200; data_bits=8;
        parity='none'; stop_bits=1; initial=$initial; received_lines=$state.lines;
        sent_packets=$state.sequence; records=@($records.ToArray()); passed=$passed }
    $result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $output 'results.json') -Encoding utf8
    if (-not $passed) { throw 'One or more physical phases failed; see results.json and raw logs' }
    @{ execution='physical_serial'; port=$Port; verified_phases=$records.Count;
       received_lines=$state.lines; sent_packets=$state.sequence; passed=$passed; output=$output } | ConvertTo-Json
} catch {
    @{ execution='physical_serial'; status='failed'; error=$_.Exception.Message;
       received_lines=$state.lines; sent_packets=$state.sequence;
       utc=[DateTimeOffset]::UtcNow.ToString('o') } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'failure.json') -Encoding utf8
    throw
} finally {
    if ($serial.IsOpen) { $serial.Close() }
    $serial.Dispose()
    $raw.Dispose()
    $linesFile.Dispose()
    $sendsFile.Dispose()
}
