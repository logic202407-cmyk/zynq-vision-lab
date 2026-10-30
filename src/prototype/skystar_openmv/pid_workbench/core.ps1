# Windows PowerShell 5.1+. No board pins or hardware initialization belong here.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:PidFields = @('PKP', 'PKI', 'PKD', 'TKP', 'TKI', 'TKD')
$script:Invariant = [Globalization.CultureInfo]::InvariantCulture

function Assert-PidGains($Gains) {
    foreach ($key in $script:PidFields) {
        if (-not $Gains.Contains($key)) { throw "缺少参数 $key" }
        $value = 0.0
        if (-not [double]::TryParse([string]$Gains[$key], [Globalization.NumberStyles]::Float,
                $script:Invariant, [ref]$value) -or [double]::IsNaN($value) -or
                [double]::IsInfinity($value) -or $value -lt 0 -or $value -gt 50) {
            throw "$key 必须是 0~50 的有限数值（软件输入范围，不代表机械安全范围）"
        }
        if ([math]::Abs($value - [math]::Round($value, 2)) -gt 0.0000001) {
            throw "$key 最多保留两位小数，与旧协议回读精度一致"
        }
    }
}

function ConvertTo-PidCommand([string]$Key, [double]$Value) {
    if ($Key -cnotin $script:PidFields) { throw '未知 PID 字段' }
    $check = [ordered]@{}
    foreach ($name in $script:PidFields) { $check[$name] = 0.0 }
    $check[$Key] = $Value
    Assert-PidGains $check
    return $Key.ToLowerInvariant() + ' ' + $Value.ToString('0.00', $script:Invariant) + "`n"
}

function ConvertFrom-PidLine([string]$Line, [string]$Protocol) {
    # Parse whole packets only. A circle-console status is never a PID packet.
    $legacy = @('DX','DY','PAN','TLT','PKP','PKI','PKD','TKP','TKI','TKD')
    $p0 = @('P0V','STATE','MODE','VALID','ENABLED','DX','DY','PAN','TLT','REQ_PAN',
        'REQ_TLT','SESSION','FRAME','RX_MS','SOURCE_MS','REJECT','BAD','PARSE_BAD',
        'PKP','PKI','PKD','TKP','TKI','TKD')
    if ($Protocol -eq 'LegacyF103') { $names = $legacy }
    elseif ($Protocol -eq 'P0') { $names = $p0 }
    else { throw '尚无该板卡的协议适配器' }
    $parts = $Line.Trim() -split '\s+'
    if ($parts.Count -ne 2 * $names.Count) { return $null }
    $values = @{}
    for ($i = 0; $i -lt $names.Count; $i++) {
        if ($parts[2 * $i] -cne $names[$i]) { return $null }
        $key = $names[$i]
        $raw = $parts[2 * $i + 1]
        if ($key -in @('STATE','MODE','REJECT')) { $values[$key] = $raw; continue }
        $number = 0L
        if ($raw -notmatch '^-?[0-9]+$' -or -not [long]::TryParse($raw, [ref]$number)) { return $null }
        if ($key -in @('DX','DY')) {
            if ($number -lt -32768 -or $number -gt 32767) { return $null }
        } elseif ($number -lt 0 -or $number -gt 4294967295L) { return $null }
        if ($key -in @('PAN','TLT','REQ_PAN','REQ_TLT') -and $number -gt 65535) { return $null }
        $values[$key] = $number
    }
    $valid = $null; $state = 'unknown'; $mode = 'unknown'; $deviceMs = $null
    if ($Protocol -eq 'P0') {
        if ($values.P0V -ne 1 -or $values.VALID -notin @(0,1) -or $values.ENABLED -notin @(0,1) -or
            $values.STATE -cnotin @('waiting','tracking','no_target','timeout','rejected') -or
            $values.MODE -cnotin @('manual','auto')) { return $null }
        $valid = [bool]$values.VALID; $state = $values.STATE; $mode = $values.MODE
        $deviceMs = $values.RX_MS
    }
    $gains = [ordered]@{}
    foreach ($key in $script:PidFields) { $gains[$key] = $values[$key] / 100.0 }
    return [pscustomobject]@{ Gains = $gains; Dx = $values.DX; Dy = $values.DY;
        Pan = $values.PAN; Tilt = $values.TLT; Valid = $valid; State = $state;
        Mode = $mode; DeviceMs = $deviceMs; Protocol = $Protocol; ReceivedSeconds = 0.0 }
}

function New-PidSession {
    return @{ Connected = $false; Transport = $null; Protocol = 'Unknown';
        Clock = [Diagnostics.Stopwatch]::StartNew(); Buffer = ''; Dropping = $false;
        Latest = $null; Frames = [Collections.Generic.List[object]]::new();
        Events = [Collections.Generic.List[string]]::new(); Pending = $null;
        ReadPending = $false; ReadDeadline = 0.0; ReadVersion = 0;
        WriteStatus = '未写入'; Inhibit = $false; Csv = $null; RawLog = $null;
        LogDirectory = ''; InvalidLines = 0; NextMock = 0.0 }
}

function Write-PidEvent($Session, [string]$Message) {
    $line = [DateTimeOffset]::Now.ToString('o') + ' ' + $Message
    $Session.Events.Add($line)
    if ($Session.Events.Count -gt 300) { $Session.Events.RemoveAt(0) }
    if ($null -ne $Session.RawLog) { $Session.RawLog.WriteLine($line) }
}

function Start-PidLog($Session, [string]$Directory) {
    if ($null -ne $Session.Csv) { throw '日志已打开' }
    [void][IO.Directory]::CreateDirectory($Directory)
    $folder = Join-Path $Directory ((Get-Date -Format 'yyyyMMdd_HHmmss_fff') + '_' + [guid]::NewGuid().ToString('N').Substring(0,6))
    [void][IO.Directory]::CreateDirectory($folder)
    try {
        $Session.Csv = [IO.StreamWriter]::new((Join-Path $folder 'telemetry.csv'), $false, [Text.UTF8Encoding]::new($true))
        $Session.RawLog = [IO.StreamWriter]::new((Join-Path $folder 'session.log'), $false, [Text.UTF8Encoding]::new($true))
        $Session.Csv.AutoFlush = $true; $Session.RawLog.AutoFlush = $true
        $Session.Csv.WriteLine('host_time,elapsed_s,protocol,dx_px,dy_px,pan_us,tilt_us,valid,state,mode,device_rx_ms,pkp,pki,pkd,tkp,tki,tkd')
        $Session.LogDirectory = $folder
        Write-PidEvent $Session '日志开始；横轴是 PC 接收时间，不是控制周期'
    } catch { Close-PidLog $Session; throw }
}

function Close-PidLog($Session) {
    foreach ($name in @('Csv','RawLog')) {
        if ($null -ne $Session[$name]) {
            try { $Session[$name].Dispose() }
            catch { $Session.Events.Add('日志关闭失败：' + $_.Exception.Message) }
            finally { $Session[$name] = $null }
        }
    }
}

function New-PidTransport([string]$Kind, [string]$Port, [int]$Baud) {
    if ($Kind -eq 'Mock') {
        return @{ Kind = 'Mock'; Gains = [ordered]@{PKP=3.0;PKI=0.5;PKD=0.0;TKP=5.0;TKI=0.8;TKD=0.0};
            Stopped = $false; Writes = [Collections.Generic.List[string]]::new() }
    }
    if ($Kind -ne 'Serial' -or $Port -notmatch '^COM[0-9]+$' -or $Baud -le 0) { throw '请选择 COM 端口和有效波特率' }
    $serial = [IO.Ports.SerialPort]::new($Port, $Baud, [IO.Ports.Parity]::None, 8, [IO.Ports.StopBits]::One)
    $serial.Handshake = [IO.Ports.Handshake]::None
    $serial.DtrEnable = $false; $serial.RtsEnable = $false
    $serial.ReadTimeout = 100; $serial.WriteTimeout = 200
    try { $serial.Open() } catch { $serial.Dispose(); throw }
    return @{ Kind = 'Serial'; Serial = $serial }
}

function Connect-PidSession($Session, [string]$Kind, [string]$Protocol, [string]$Port = '',
        [int]$Baud = 115200, [bool]$HardwareConfirmed = $false) {
    if ($Session.Connected) { throw '请先断开现有连接' }
    if ($Protocol -notin @('LegacyF103','P0')) { throw '天空星固件协议尚未确认：仅可使用模拟连接' }
    if ($Kind -eq 'Serial' -and -not $HardwareConfirmed) { throw '必须先核对实物及所选固件协议' }
    $Session.Transport = New-PidTransport $Kind $Port $Baud
    $Session.Protocol = $Protocol; $Session.Connected = $true
    $Session.Buffer = ''; $Session.Dropping = $false; $Session.Latest = $null
    $Session.Frames.Clear(); $Session.Pending = $null; $Session.ReadPending = $false
    $Session.Inhibit = $false; $Session.WriteStatus = '未写入'; $Session.InvalidLines = 0
    $Session.Clock.Restart(); $Session.NextMock = 0.0
    Write-PidEvent $Session "连接 $Kind / $Protocol / $Port / $Baud 8N1 / DTR=0 RTS=0；未自动写入参数"
}

function Disconnect-PidSession($Session) {
    if ($null -ne $Session.Pending) { $Session.WriteStatus = '已中断，部分参数可能已生效；请重新读取' }
    $Session.Pending = $null; $Session.ReadPending = $false
    $Session.Connected = $false; $Session.Latest = $null; $Session.Buffer = ''; $Session.Dropping = $false
    if ($null -ne $Session.Transport -and $Session.Transport.Kind -eq 'Serial') { $Session.Transport.Serial.Dispose() }
    $Session.Transport = $null
    Write-PidEvent $Session '已断开；断开 PC 通信不会停止设备闭环或切断执行器电源'
}

function Send-PidWire($Session, [string]$Command) {
    if (-not $Session.Connected) { throw '尚未连接' }
    try {
        Write-PidEvent $Session ('TX ' + $Command.Trim())
        if ($Session.Transport.Kind -eq 'Mock') {
            $Session.Transport.Writes.Add($Command)
            if ($Command -match '^(pkp|pki|pkd|tkp|tki|tkd) ([0-9]+\.[0-9]{2})\n$') {
                $Session.Transport.Gains[$Matches[1].ToUpperInvariant()] = [double]::Parse($Matches[2], $script:Invariant)
            }
        } else { $Session.Transport.Serial.Write($Command) }
    } catch {
        $Session.Pending = $null; $Session.ReadPending = $false; $Session.Inhibit = $true
        $Session.WriteStatus = '发送或日志失败：已锁定后续写入，部分参数可能已生效'
        throw
    }
}

function Request-PidRead($Session) {
    if ($null -ne $Session.Pending) { throw '正在逐项写入，请等待回读或取消' }
    Send-PidWire $Session "st`n"
    $Session.ReadPending = $true; $Session.ReadDeadline = $Session.Clock.Elapsed.TotalSeconds + 2.0
    Write-PidEvent $Session '读取请求已发送，等待完整状态帧'
}

function Start-PidWrite($Session, $Gains) {
    if (-not $Session.Connected) { throw '尚未连接' }
    if ($Session.Inhibit) { throw '本次连接已锁定写入，请核查设备并重新连接' }
    if ($null -ne $Session.Pending -or $Session.ReadPending) { throw '已有操作正在等待回读' }
    if ($null -eq $Session.Latest -or ($Session.Clock.Elapsed.TotalSeconds - $Session.Latest.ReceivedSeconds) -gt 2) {
        throw '没有新鲜的协议匹配回包，请先读取参数'
    }
    Assert-PidGains $Gains
    $copy = [ordered]@{}
    foreach ($key in $script:PidFields) { $copy[$key] = [double]$Gains[$key] }
    $Session.Pending = @{ Gains = $copy; Index = 0; Deadline = 0.0; Waiting = $false }
    $Session.WriteStatus = '等待逐项发送'
    Send-PidNext $Session
}

function Send-PidNext($Session) {
    $pending = $Session.Pending
    $key = $script:PidFields[$pending.Index]
    Send-PidWire $Session (ConvertTo-PidCommand $key $pending.Gains[$key])
    $pending.Waiting = $true; $pending.Deadline = $Session.Clock.Elapsed.TotalSeconds + 2.0
    $Session.WriteStatus = "等待 $key 回读匹配（$($pending.Index)/6）"
}

function Add-PidFrame($Session, [string]$Line) {
    $frame = ConvertFrom-PidLine $Line $Session.Protocol
    if ($null -eq $frame) { $Session.InvalidLines++; Write-PidEvent $Session ('RX 未识别 ' + $Line); return }
    $frame.ReceivedSeconds = $Session.Clock.Elapsed.TotalSeconds
    $Session.Latest = $frame; $Session.Frames.Add($frame)
    if ($Session.Frames.Count -gt 1200) { $Session.Frames.RemoveAt(0) }
    if ($null -ne $Session.RawLog) { $Session.RawLog.WriteLine([DateTimeOffset]::Now.ToString('o') + ' RX ' + $Line) }
    if ($null -ne $Session.Csv) {
        $validText = if ($null -eq $frame.Valid) { 'unknown' } else { [int]$frame.Valid }
        $cols = @([DateTimeOffset]::Now.ToString('o'), $frame.ReceivedSeconds.ToString('F3',$script:Invariant),
            $Session.Protocol, $frame.Dx, $frame.Dy, $frame.Pan, $frame.Tilt, $validText, $frame.State, $frame.Mode, $frame.DeviceMs)
        foreach ($key in $script:PidFields) { $cols += $frame.Gains[$key].ToString('F2',$script:Invariant) }
        $Session.Csv.WriteLine(($cols -join ','))
    }
    if ($Session.ReadPending) {
        $Session.ReadPending = $false; $Session.ReadVersion++
        Write-PidEvent $Session '读取完成（状态快照；旧协议无请求序号）'
    }
    if ($null -ne $Session.Pending -and $Session.Pending.Waiting) {
        $pending = $Session.Pending; $key = $script:PidFields[$pending.Index]
        if ([math]::Abs($frame.Gains[$key] - $pending.Gains[$key]) -le 0.000001) {
            $pending.Index++; $pending.Waiting = $false
            if ($pending.Index -eq 6) {
                $allMatch = $true
                foreach ($name in $script:PidFields) {
                    if ([math]::Abs($frame.Gains[$name] - $pending.Gains[$name]) -gt 0.000001) { $allMatch = $false }
                }
                if ($allMatch) { $Session.WriteStatus = '6 项回读匹配（无事务 ACK；仅 RAM，不代表掉电保存）' }
                else {
                    $Session.WriteStatus = '最终整组回读不匹配，设备可能部分更新；请核查并重新连接'
                    $Session.Inhibit = $true
                }
                Write-PidEvent $Session $Session.WriteStatus
                $Session.Pending = $null
            }
        }
    }
}

function Add-PidBytes($Session, [string]$Text) {
    # Bounded incremental framer: discard an oversized line THROUGH its newline.
    foreach ($char in $Text.ToCharArray()) {
        if ($char -eq "`n") {
            if (-not $Session.Dropping -and $Session.Buffer.Length -gt 0) { Add-PidFrame $Session $Session.Buffer.TrimEnd("`r") }
            $Session.Buffer = ''; $Session.Dropping = $false
        } elseif (-not $Session.Dropping) {
            if ($Session.Buffer.Length -ge 4096) {
                $Session.Buffer = ''; $Session.Dropping = $true; $Session.InvalidLines++
                Write-PidEvent $Session 'RX 超长行已丢弃，等待下一行重新同步'
            } else { $Session.Buffer += $char }
        }
    }
}

function Update-PidSession($Session) {
    if (-not $Session.Connected) { return }
    $seconds = $Session.Clock.Elapsed.TotalSeconds
    if ($Session.Transport.Kind -eq 'Mock') {
        if ($seconds -ge $Session.NextMock) {
            $Session.NextMock = $seconds + 0.05
            $dx = [int](20 * [math]::Sin($seconds * 1.5)); $dy = [int](12 * [math]::Cos($seconds))
            $state = if ($Session.Transport.Stopped) { 'waiting' } else { 'tracking' }
            $valid = if ($Session.Transport.Stopped) { 0 } else { 1 }
            $line = "DX $dx DY $dy PAN 1450 TLT 1500"
            if ($Session.Protocol -eq 'P0') {
                $ms = [int]($seconds * 1000)
                $line = "P0V 1 STATE $state MODE manual VALID $valid ENABLED 0 $line REQ_PAN 1450 REQ_TLT 1500 SESSION 1 FRAME $ms RX_MS $ms SOURCE_MS $ms REJECT none BAD 0 PARSE_BAD 0"
            }
            foreach ($key in $script:PidFields) { $line += ' ' + $key + ' ' + [int][math]::Round(100 * $Session.Transport.Gains[$key]) }
            Add-PidBytes $Session ($line + "`r`n")
        }
    } else {
        $serial = $Session.Transport.Serial
        if (-not $serial.IsOpen) { throw '串口已关闭，请检查连接' }
        $count = [math]::Min(16384, $serial.BytesToRead)
        if ($count -gt 0) {
            $bytes = [byte[]]::new($count)
            $read = $serial.Read($bytes,0,$count)
            Add-PidBytes $Session ([Text.Encoding]::ASCII.GetString($bytes,0,$read))
        }
    }
    if ($Session.ReadPending -and $seconds -gt $Session.ReadDeadline) {
        $Session.ReadPending = $false
        Write-PidEvent $Session '读取超时：未收到所选协议的完整回包；检查模式/协议/接线'
    }
    if ($null -ne $Session.Pending) {
        if ($Session.Pending.Waiting -and $seconds -gt $Session.Pending.Deadline) {
            $Session.WriteStatus = '写入回读超时：已取消剩余发送，部分参数可能已生效'
            $Session.Pending = $null; $Session.Inhibit = $true
            Write-PidEvent $Session $Session.WriteStatus
        } elseif (-not $Session.Pending.Waiting) { Send-PidNext $Session }
    }
}

function Stop-PidLocal($Session) {
    $Session.Pending = $null; $Session.ReadPending = $false; $Session.Inhibit = $true
    $Session.WriteStatus = '本次连接已锁定写入；已发送的参数可能仍生效'
    if ($Session.Connected -and $Session.Transport.Kind -eq 'Mock') {
        $Session.Transport.Stopped = $true
        $message = '模拟数据源已标记停止。真实设备仍需独立确认停止。'
    } else { $message = '未发送设备急停：已取消上位机后续写入。该协议无可靠停止命令，请立即使用现场确认过的硬件停止方式。断开通信不会停止设备。' }
    Write-PidEvent $Session $message
    return $message
}

function Save-PidPreset([string]$Path, [string]$Protocol, $Gains, [string]$Note = '',
        [string]$ConnectionKind = 'Unspecified') {
    Assert-PidGains $Gains
    $data = [ordered]@{ schema = 'pid-workbench-preset-v1'; protocol = $Protocol;
        created_at = [DateTimeOffset]::Now.ToString('o'); source = 'editor'; note = $Note;
        gains = $Gains; device_flash_saved = $false; connection_kind = $ConnectionKind }
    [IO.File]::WriteAllText($Path, ($data | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($true))
}

function Read-PidPreset([string]$Path, [string]$Protocol, [string]$ConnectionKind = 'Unspecified') {
    $data = [IO.File]::ReadAllText($Path) | ConvertFrom-Json
    if ($data.schema -ne 'pid-workbench-preset-v1' -or $data.protocol -ne $Protocol) {
        throw '参数文件格式或协议不匹配；不可直接跨协议恢复'
    }
    if ($ConnectionKind -ne 'Unspecified' -and $data.connection_kind -ne $ConnectionKind) {
        throw '参数文件的模拟/串口来源与当前连接不匹配'
    }
    $gains = [ordered]@{}
    foreach ($key in $script:PidFields) { $gains[$key] = $data.gains.$key }
    Assert-PidGains $gains
    return $gains
}
