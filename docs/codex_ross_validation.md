# 队友 / Codex：ROSS 最小验证手册

先读[适用性评估](ross_evaluation_2026-10-01.md)。本轮只验证工具辅助开发是否可靠，**不恢复硬件测试**。本文包含可执行试验步骤，但编写时未执行；所有结果默认 NOT_TESTED。

## 0. 任务卡与不可越过的边界

- 输入：本仓库固定提交 `0daf92f09ed912635169087b07914b65775ab7ff` 的 `src/rtl/red_pixel_mask.v` 与 `sim/red_pixel_mask_tb.v`
- ROSS：`2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de`，完整克隆，不只复制 SKILL.md
- 输出：仓库外原始证据目录 + 填妥的[结果模板](../report/templates/ross_validation_result.md)
- 执行人/复核人：队友执行前填名或角色，不默认任何人已接受任务
- 范围：纯组合像素谓词的 behavioral XSim 仿真、故意错误检测、恢复与日志诊断
- 禁止：打开原厂/日常 Vivado 工程，改现有 RTL/测试期望/阈值，改 XDC、IP、相机与网络，综合/实现/生成位流，JTAG/hw_server/ILA/VIO/板卡连接，自动提交、推送、合并或发布日志
- 不安装、不升级任何工具或持久配置，除非执行者另行明确同意；文档并不是安装授权
- 不依赖 R0、本地未发布材料或私有图像。发现既有工作树有未提交工作只记录，不 reset/clean/stash/覆盖
- 未满足某项前提即在该项记 BLOCKED；独立的只读分析可继续。不得把省略的环节计为通过

只在**新建、仓库外、ASCII 路径**操作。下述代码是文档提供的试验脚本，允许的 RTL 变异只发生在临时 negative 副本；黄金测试不变。所有文件仅处理无生命几何标志对应的像素数值。

## 1. 先记录环境，不按路径猜版本

1. 核对当前 AGENTS.md、README、工具清单与状态台账。记录手册所在提交和实际主机信息；项目历史 Vivado 是 2024.2，不等于验证机当前版本。
2. 记录 Git、Python、编码助手及模型的真实版本。检查 Vivado/XSim 可执行文件来自同一安装；记录版本输出和退出码。历史上 `vivado.bat -version` 打印版本却返回 1，因此版本查询与可运行能力分开判定。
3. 使用已有、获准的 Vivado 安装与许可证；不公开许可证值、不扩大目录扫描。若不存在，报告缺失，不下载或安装。
4. Vitis/HLS、本轮不使用的 IP 与其他模拟器均标 N/A 或 NOT_TESTED，不凭安装文件夹声称可用。
5. 若需要新装 ROSS/MCP，先完成第 2 节的许可与安装确认；基线 A 本身不需要 ROSS/MCP。
6. 小例每次仿真最多 100 ns，并有 watchdog；每个工具阶段建议给 5 分钟主机超时。超时保存日志和该子进程信息，停止该试验，不结束别人已开的 Vivado 会话。

## 2. ROSS 安装与 MCP：需另行获准后执行

官方入口：
- [AMD 下载页](https://www.amd.com/en/support/downloads/ross-agentic-ai.html)
- [固定版本插件安装说明](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/docs/getting-started/install-plugin.md#codex)
- [固定版本 Codex MCP 说明](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/docs/getting-started/vivado-mcp.md)
- [隐私与许可证边界](ross_evaluation_2026-10-01.md#5-许可数据与来源)

先检查客户端 `codex --version` 及其 `codex plugin --help`、`codex mcp --help` 是否支持上游指令。未知子命令即停止安装并记录版本，不臆造替代命令，不自行升级。插件与 MCP 是两项独立安装；Codex CLI 使用官方 standalone MCP binary，别再同时安装 IDE extension。

以下 PowerShell 片段中的路径均须由执行者替换为已批准的实际路径；不在现有同名目录执行。这里列出的是已核对上游文档的命令，**本 PR 没有执行这些安装**。

```powershell
$Ross = 'C:\fpga-scratch\ross-pinned' # 示例；先换成批准的空目录
$RossSha = '2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de'
if (Test-Path $Ross) { throw 'Use a fresh directory; do not overwrite.' }
git clone https://github.com/Xilinx/ross-ai-assistant $Ross
if ($LASTEXITCODE -ne 0) { throw 'Ross clone failed' }
git -C $Ross checkout --detach $RossSha
if ($LASTEXITCODE -ne 0) { throw 'Ross checkout failed' }
if ((git -C $Ross rev-parse HEAD).Trim() -ne $RossSha) {
    throw 'Ross SHA mismatch'
}
codex plugin marketplace add $Ross
if ($LASTEXITCODE -ne 0) { throw 'Marketplace registration failed' }
codex plugin add amd-ross-agentic-ai-assistant@amd-ross-agentic-ai-assistant
if ($LASTEXITCODE -ne 0) { throw 'Plugin installation failed' }
```

在 Codex 的 `/plugins` 查看插件和目标 skill。Codex 会复制到缓存：记录实际加载副本与安装源，不仅记录克隆 SHA；若缓存已有另一版本，停止并按官方卸载/重装流程处理，不能声称新 clone 已生效。不与 `npx skills add` 或另一份手工 skills 重复安装。

MCP binary 只从 AMD 官方下载页取得，记录文件版本及 SHA-256，并审阅其单独许可。配置会赋予助手调用 Vivado Tcl 的能力，必须由执行者确认。上游详细页给出的命令结构如下，实际可执行路径需核实：

```text
codex mcp add vivado-mcp --env VIVADO_PATH=/actual/path/to/vivado -- /actual/path/to/vivado-mcp-server --stdio-bridge
```

Windows 请按上游说明使用真实、正确引用的 Windows 路径。不要照抄未展开的 `{{ mcp_version }}`；上游 preflight 页还含旧配置片段，应以详细安装页及当前客户端 help 为准。无须为本试验新增远程服务器、开放网络端口或配置密钥。

获准后通过 MCP 新建独立 Tcl 会话，只查询 `version -short` 等环境信息，保留请求/响应与实际 server/tool 前缀。**MCP 版本查询通过只记“MCP 联通 PASS”。**不得连接已有硬件会话。文档检索是独立 `amd-doc-search` 服务；未配置时明确缺失，不声称可搜索，也不要把私有日志整段发给检索服务。

## 3. A：人工命令基线（不使用 ROSS）

使用已有 Windows Vivado 命令环境和 PowerShell。以下准备与运行代码应在同一会话分段执行。Linux 队友可按同样源清单转换调用方式，但须记录转换后的脚本与工具版本，不能把 Windows 步骤当成 Linux 实测。

### 3.1 取固定输入，保留原工作树

```powershell
$ErrorActionPreference = 'Stop'
$ProjectSha = '0daf92f09ed912635169087b07914b65775ab7ff'
$ScratchRoot = 'C:\fpga-scratch' # 示例；换成批准的仓库外 ASCII 路径
$VivadoBin = 'F:\Vivado\2024.2\bin' # 历史示例；先核对本机，不能照猜
if ($ScratchRoot -match '[^\x00-\x7F]') { throw 'ASCII path required' }
$Trial = Join-Path $ScratchRoot ('ross-trial-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $Trial | Out-Null
$Source = Join-Path $Trial 'source'
git clone https://github.com/logic202407-cmyk/zynq-vision-lab $Source
if ($LASTEXITCODE -ne 0) { throw 'Project clone failed' }
git -C $Source checkout --detach $ProjectSha
if ($LASTEXITCODE -ne 0) { throw 'Project checkout failed' }
if ((git -C $Source rev-parse HEAD).Trim() -ne $ProjectSha) {
    throw 'Project SHA mismatch'
}
foreach ($name in @('vivado.bat','xvlog.bat','xelab.bat','xsim.bat')) {
    if (-not (Test-Path (Join-Path $VivadoBin $name))) { throw "Missing $name" }
}
& (Join-Path $VivadoBin 'vivado.bat') -version 2>&1 |
    Set-Content (Join-Path $Trial 'vivado-version.txt')
$LASTEXITCODE | Set-Content (Join-Path $Trial 'vivado-version-exit.txt')
```

记录版本后人工核对预期版本；若与计划不符，暂停并修正记录/范围，不继续混用。只查询版本时发现异常退出不能单独推断“无法仿真”或“许可可用”。

### 3.2 为正例、负例、恢复各建独立目录

```powershell
$Cases = @('positive','negative','recovery')
foreach ($case in $Cases) {
    $dir = Join-Path $Trial $case
    New-Item -ItemType Directory -Path $dir | Out-Null
    Copy-Item (Join-Path $Source 'src/rtl/red_pixel_mask.v') $dir
    Copy-Item (Join-Path $Source 'sim/red_pixel_mask_tb.v') $dir
    @'
`timescale 1ns / 1ps
module ross_guard_tb;
    red_pixel_mask_tb checks();
    initial begin
        #100;
        $fatal(1, "ROSS_WATCHDOG_TIMEOUT");
    end
endmodule
'@ | Set-Content (Join-Path $dir 'ross_guard_tb.v') -Encoding ascii
    "run 100 ns`nquit" |
        Set-Content (Join-Path $dir 'bounded.tcl') -Encoding ascii
}
$NegativeRtl = Join-Path $Trial 'negative/red_pixel_mask.v'
$before = [IO.File]::ReadAllText($NegativeRtl)
$old = "MIN_R5 = 5'd15"
$new = "MIN_R5 = 5'd16"
if ([regex]::Matches($before, [regex]::Escape($old)).Count -ne 1) {
    throw 'Unexpected RTL; do not guess a mutation'
}
[IO.File]::WriteAllText($NegativeRtl, $before.Replace($old, $new),
    [Text.Encoding]::ASCII)
foreach ($case in $Cases) {
    Get-ChildItem (Join-Path $Trial $case) -File |
        Get-FileHash -Algorithm SHA256 |
        Select-Object Hash,Path |
        Export-Csv (Join-Path $Trial ($case + '-inputs.csv')) -NoTypeInformation
}
```

这一变异只将 red 的包含阈值从 15 提高到 16，不改 TB。固定 TB 的 `{5'd15, 6'd17, 5'd6}` 即 `16'h7a26`，应仍期望 1；变异后 DUT 返回 0。此预期由位域和比较关系直接推得，不从变异 DUT 反算答案。当前 TB 共 16 个确定性检查，正常在 16 ns 附近结束；watchdog 只防挂起，不新增 DUT 功能。

### 3.3 编译、展开、运行并保存完整输出

以下是文档自带的测试调度代码，不属于已运行结果。XSim 三阶段采用[仓库既有命令](https://github.com/logic202407-cmyk/zynq-vision-lab/blob/0daf92f09ed912635169087b07914b65775ab7ff/report/experiments/2026-09-27-red-pixel-mask-xsim.md)；有限运行使用 [UG900 2024.2 的 -tclbatch 选项](https://docs.amd.com/r/2024.2-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87/ug900-vivado-logic-simulation/xsim-%E5%8F%AF%E6%89%A7%E8%A1%8C%E6%96%87%E9%80%89%E9%A1%B9)。新脚本本身也需要执行者验证，不因写在文档里就假定可用。

```powershell
function Invoke-MaskCase([string]$CaseName) {
    # Native stderr must be logged, including the deliberately failing case.
    # This preference is local to the function; explicit throws still stop it.
    $ErrorActionPreference = 'Continue'
    $dir = Join-Path $Trial $CaseName
    Push-Location $dir
    try {
        & (Join-Path $VivadoBin 'xvlog.bat') red_pixel_mask.v red_pixel_mask_tb.v ross_guard_tb.v 2>&1 |
            Tee-Object -FilePath compile-console.txt
        $compileRc = $LASTEXITCODE
        "compile=$compileRc" | Set-Content exits.txt
        if ($compileRc -ne 0) { throw "$CaseName compile failed" }

        & (Join-Path $VivadoBin 'xelab.bat') ross_guard_tb -s ross_mask_sim 2>&1 |
            Tee-Object -FilePath elaborate-console.txt
        $elabRc = $LASTEXITCODE
        "elaborate=$elabRc" | Add-Content exits.txt
        if ($elabRc -ne 0) { throw "$CaseName elaboration failed" }

        & (Join-Path $VivadoBin 'xsim.bat') ross_mask_sim -tclbatch bounded.tcl 2>&1 |
            Tee-Object -FilePath simulation-console.txt
        $simRc = $LASTEXITCODE
        "simulate=$simRc" | Add-Content exits.txt

        $log = Get-Content simulation-console.txt -Raw -ErrorAction Stop
        $passCount = [regex]::Matches($log, '(?m)^\s*RED_PIXEL_MASK_TB_PASS\s*$').Count
        $hasPass = $passCount -gt 0
        $hasFail = $log -match 'RED_PIXEL_MASK_TB_FAIL'
        $hasTimeout = $log -match 'ROSS_WATCHDOG_TIMEOUT'
        $hasUnexpected = $log -match '(?im)^\s*(ERROR|FATAL|Fatal)[: ]'
        if ($CaseName -eq 'negative') {
            if ($hasPass -or -not $hasFail -or $hasTimeout -or
                $log -notmatch 'FAIL pixel=7a26 expected=1 actual=0' -or
                $log -notmatch 'RED_PIXEL_MASK_TB_FAIL count=1\b') {
                throw 'Negative control was not correctly detected'
            }
            'EXPECTED_FAILURE_DETECTED; inspect full logs for unrelated errors' |
                Set-Content verdict-candidate.txt
        } else {
            if ($simRc -ne 0 -or $passCount -ne 1 -or $hasFail -or
                $hasTimeout -or $hasUnexpected) {
                throw "$CaseName did not meet the positive gates"
            }
            'POSITIVE_PASS_CANDIDATE; inspect full logs before final verdict' |
                Set-Content verdict-candidate.txt
        }
    } finally {
        Pop-Location
    }
}
Invoke-MaskCase 'positive'
Invoke-MaskCase 'negative'
Invoke-MaskCase 'recovery'
$sourceStatus = git -C $Source status --porcelain
if ($LASTEXITCODE -ne 0 -or $sourceStatus) { throw 'Source checkout changed' }
```

自动解析只给出 candidate，人工仍要读三个阶段完整日志：所有 16 个检查结束、正常终止、无意外错误。负例的预期结果是仿真功能 FAIL + 验证门禁成功捕获；不要把 Fatal 当作运行器故障后删除该测试，也不要通过改期望让负例变绿。XSim 可能在 $fatal 后返回 0，退出码不能代替标记。负例有语法错误/许可证故障而没运行到指定像素时，属于无效负例，必须记 FAIL/BLOCKED。

recovery 的 RTL 和 TB 应与 positive 文件 SHA-256 相同；negative 只允许一个阈值差异，TB/guard/bounded.tcl 三者散列应在三个目录相同。`git status --porcelain` 应为空。所有快照/编译缓存分目录，不能复用负例的旧 snapshot 冒充恢复。

## 4. B：相同输入的 ROSS 辅助试验

只有安装授权、实际 skill 加载版本核对和 MCP 联通检查都完成后，才给 B 填 PASS/FAIL。否则标 BLOCKED/NOT_TESTED，并可以继续将 A 的脱敏日志作为“仅阅读辅助分析”；后者不算 ROSS live 流程通过。

在另一个新建 `ross-trial-<id>` 目录重复第 3 节固定输入及变异；不复用 A 的生成文件。在启用固定版本插件的 Codex 会话中给出下面的任务。实际路径由执行者提供，不能用生产工程路径替换试验目录。

```text
阅读本仓库 docs/codex_ross_validation.md 和实际 AGENTS.md。
这次仅在我指定的仓库外 ASCII scratch 目录验证 ROSS，硬件仍暂停。
先确认加载的 ROSS 来源为 2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de，
并核对实际 Vivado/XSim、Python、客户端版本与 MCP 工具是否可用。
不要安装/升级任何东西；缺少安装或权限就报告具体阻塞。

请显式使用 vivado-simulate-rtl，先读它的 SKILL.md 和 xsim reference。
MCP 仅启动新的独立 Tcl 会话做环境核验，不能连板或接管已有工程。
本任务采用明确的非工程源清单：
red_pixel_mask.v、red_pixel_mask_tb.v、ross_guard_tb.v；
顶层 ross_guard_tb，XSim behavioral，100 ns 上限。
按手册在各自干净目录运行 positive、negative、recovery，
使用已批准的本机 XSim 三阶段命令，不生成器件工程、不猜完整 part。
如果当前 skill/client 不能在这些限制内工作，停在该环节并记录原因；
不要静默改用另一个 simulator、升级工具或越过权限。

保留所有实际命令、退出码、输入散列和完整日志。
从日志说明每次结果、首个因果错误、输入/期望/实际值，
区分 expected negative FAIL 与运行器错误，恢复必须重新编译。
不要改变黄金测试和原工作树；只允许 negative 的 15→16 变异。
不修 RTL，不改 XDC/IP，不综合/实现/生成位流，不调用任何 hw_* 功能。
不自动提交、推送、合并或上传原始日志。
填写结果模板，列出实测通过、失败、未测和阻塞，
不得从仿真或 MCP 联通推导板测、时序、性能、R0 或项目整体完成。
```

若 ROSS 的默认步骤提出修 RTL、写 XDC 或进一步实现，必须受本任务边界约束。对工具/环境失败，查询对应版本的公开 AMD 文档，保留已验证原因/未验证假设；未经许可不打补丁、不换后端。只有取得公开链接或适用命令证据才给出处，不能虚构 Answer Record。

可追加一项不改设计的诊断对照：让 ROSS 只读负例日志和两份 scratch RTL 差异，指出 `MIN_R5` 变异、`7a26` 用例及不该修改 TB 的理由。此项单列“日志诊断”，不能冒充完整 elaboration skill 或 lint 已运行。

## 5. 通过标准与停止条件

| 项目 | PASS | FAIL / BLOCKED / NOT_TESTED |
|---|---|---|
| 输入/版本 | 两个固定提交、实际加载副本、工具版本、散列均有记录 | 版本混用或无法确认则阻塞 |
| A 正例 | compile/elaborate 成功，16 项检查结束，唯一终止 PASS 标记，无意外错误/超时 | 仅退出 0、缺标记或未运行均不通过 |
| A 负例 | 编译/展开成功，实际跑到 7a26 的预期失败；无 PASS 标记；错误未被隐藏 | 误报通过、改 TB、语法错代替功能错均失败 |
| A 恢复 | 原始输入散列恢复，新目录重建后正例通过 | 复用旧 snapshot 不算 |
| B ROSS | 安装/加载与 MCP 各自验证；同样三例正确判定，引用实际日志，遵守边界 | 未满足 MCP/版本/安装前提记阻塞；只读日志单列，不充当 live PASS |
| 复核 | 第二人能复跑并核对证据 | 尚无第二人复跑则“独立复现 NOT_TESTED” |

本轮采用条件是 A/B 的可执行部分均有真实证据，且 ROSS 没有漏报负例、伪造工具执行、削弱检查或越界修改。若只有 A 通过，则保留 A 工作流，ROSS 暂不采用。即使 B 通过，也不能宣称有性能提升；想比较时间/人工干预量，必须同机同输入、分别记录实际耗时与交互次数，再扩大样本。

以下情况立即停止相应步骤：试验路径非隔离、固定 SHA 不符、权限未获准、版本条件不满足、开始接触原工程/硬件、需要私有数据外传。保留失败现场，不为了结果好看换门槛。

## 6. 回填、复核与后续

复制[结果模板](../report/templates/ross_validation_result.md)为 `report/experiments/<实际日期>-ross-validation.md` 的候选报告；先在本地填写、脱敏审查，经授权后通过单独分支/PR 提交。不要把模板里的 NOT_TESTED 自动改 PASS，不更改现有 `report/status.json`。

原始日志、WDB、生成目录继续保留在仓库外。公开报告给出输入/脚本/日志的 SHA-256、最小可公开摘录和复核人；报告链接与远端提交核实后才能称“已提交”。

后续候选按需求再开小任务：已发布红色帧统计/DVP 仿真；适用版本的 lint；独立的 HLS 环境核验。ILA 只在用户明确恢复硬件、确认工具版本/匹配 bitstream 与 .ltx、明确探针/时钟/触发方案之后另行评估，不在本手册执行。
