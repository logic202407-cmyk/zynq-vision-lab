# Codex 测试流程：离线复现与有板验收

初稿日期：2026-09-30；源码交付复核：2026-10-03。本文提供下一位成员明确请求测试后执行的流程；本次源码发布的软件复跑结果见 [发布记录](../report/experiments/2026-10-03-r0-acceptance-publication.md)。先读 [AGENTS.md](../AGENTS.md) 及其中的必读文件，再读仓库候选技能 [evidence-gates](../skill/evidence-gates/SKILL.md)，按其证据字段记录结果。该技能仍是候选流程，不是已认证的板测工具。

9 月 30 日 21:50 后已有 [成功配置/视频及 v2 无目标比较](../report/experiments/2026-09-30-spatial-board-recovery.md)；v2 正例与抗闪烁仍未验收。10 月 3 日队员另报告 v1 恢复，属于队员记录而非本次板测。本次发布不操作硬件。无板条件执行 A–E；F 仅在实际板卡所有者授权一次测试并满足前置条件后执行。下一阶段分工见 [两人任务索引](team_next_stage_2026-10-03.md)；PR1 的 STM32/OpenMV 快照尚缺完整支持源，本文不虚构其干净构建或固定 OV5640 全流程命令。

## A. 干净克隆、版本与工作区

以下是 Windows PowerShell 命令，均从仓库根目录执行。选一个可写的 **ASCII 绝对路径**；不要复用别人正在工作的目录。Vivado 的完整帧 runner 会拒绝含中文的绝对输出路径，即使末级文件夹是英文。

```powershell
git clone --config core.autocrlf=false https://github.com/logic202407-cmyk/zynq-vision-lab.git D:/zynq-repro
if ($LASTEXITCODE -ne 0) { throw 'Clone failed; stop here' }
Set-Location D:/zynq-repro
git log -1 --format='%H'
git status --short
git remote -v
```

本次源码通过独立分支 `codex/r0-exact-acceptance-20261003` 的 draft PR 交付，尚未合并 main；不能默认 main 已包含 R0。干净克隆后，在修改文件前执行以下步骤固定本次源码提交。PR 页面给出的完整 head SHA 是权威版本，不能用 PR3 的 SHA 代替。

```powershell
git fetch origin codex/r0-exact-acceptance-20261003
if ($LASTEXITCODE -ne 0) { throw 'Source branch unavailable; stop' }
$sourceCommit = Read-Host 'Full 40-character source commit from the draft PR'
if ($sourceCommit -notmatch '^[0-9a-fA-F]{40}$') { throw 'A full commit SHA is required' }
git switch --detach $sourceCommit
if ($LASTEXITCODE -ne 0) { throw 'Cannot check out the requested commit' }
git rev-parse HEAD
```

保存实际完整 commit。克隆参数仅为新仓库设置 `core.autocrlf=false`，保持 Git 中源码字节以核对 SHA-256，不修改全局 Git 设置。工作区若已有修改，先辨明归属并记录差异；不要 reset、clean、stash、覆盖、合并或提交他人的修改。上述检出步骤只用于干净克隆；已有工作目录不能自动切换分支。后续开发使用自己的分支和 PR；复现固定提交时不要顺手升级代码或阈值。

发布快照应包含下面的文件。**缺文件立即停止**；`unittest discover` 找不到文件时可能出现 `Ran 0 tests / OK`，不能算通过。

```powershell
$required = @(
  'sim/reference/spatial_relations.py', 'tests/test_spatial_relations.py',
  'sim/reference/red_mask.py', 'src/pc/pl_compare.py', 'tests/test_pl_compare.py',
  'tools/compare_red_frame_xsim.py', 'docs/scene_relation_contract_v0_1.md'
)
foreach ($file in $required) {
  if (-not (Test-Path -LiteralPath $file)) { throw "Missing required file: $file" }
}
```

先为这次测试进程设置可写临时目录，**再**创建 venv/安装项目依赖，避免工具继承不可写的 TEMP/TMP。新建输出目录，保留所有旧结果，不用 `-Force` 覆盖。

```powershell
$repoPath = (Get-Location).Path
if ($repoPath -match '[^\x00-\x7F]') { throw 'Use an ASCII absolute clone path' }
$runId = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8)
$evidence = Join-Path $repoPath "private/$runId"
New-Item -ItemType Directory -Path $evidence -ErrorAction Stop | Out-Null
$env:TEMP = $evidence
$env:TMP = $evidence
$env:ZYNQ_OFFLINE_EVIDENCE = $evidence
git rev-parse HEAD | Set-Content "$evidence/commit.txt"
git status --short | Set-Content "$evidence/worktree.txt"
```

软件参考与测试使用 Python 3.10+ 标准库；已保存通过记录来自 **Python 3.12.14**。完整 UI 回归另需 Tk 和 `Pillow>=10,<13`，当时 Pillow 为 12.1.1。优先复用已有 Python 3.12；WindowsApps 别名或 `py` 启动器不能启动时，显式选择已安装解释器，不能把启动失败算测试通过。不要自动安装 Python/Vivado、改驱动或系统设置。

```powershell
$pythonBase = (Get-Command python -ErrorAction Stop).Source
& $pythonBase --version
if ($LASTEXITCODE -ne 0) { throw 'Select a working installed Python interpreter' }
if (Test-Path .venv) { throw 'Existing venv: review or use a fresh clone' }
& $pythonBase -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'venv creation failed' }
$py = (Resolve-Path .venv/Scripts/python.exe).Path
& $py -m pip install -r src/pc/requirements.txt 2>&1 | Tee-Object -FilePath "$evidence/dependencies.txt"
if ($LASTEXITCODE -ne 0) { throw 'Dependency setup failed' }
& $py -c "import sys, tkinter, PIL; print(sys.version); print('Pillow', PIL.__version__); print('Tk', tkinter.TkVersion)" 2>&1 | Tee-Object -FilePath "$evidence/python-version.txt"
if ($LASTEXITCODE -ne 0) { throw 'UI dependencies unavailable; full-suite claim is blocked' }
```

下面的 PowerShell 包装只记录真实命令、stdout/stderr 和退出码；它不提供新的项目测试接口。任一意外非零退出立即抛错，保留结果，停止后续步骤。每一步只执行一次；修复后使用新的 runId，不无限重试。

```powershell
function Invoke-Recorded {
  param([string]$Name, [string]$Executable, [string[]]$ArgumentList)
  if (Test-Path "$evidence/$Name.txt") { throw "Existing evidence: $Name" }
  @{ executable=$Executable; args=$ArgumentList } | ConvertTo-Json -Depth 3 | Set-Content "$evidence/$Name.command.json"
  & $Executable @ArgumentList 2>&1 | Tee-Object -FilePath "$evidence/$Name.txt"
  $code = $LASTEXITCODE
  "exit_code=$code" | Add-Content "$evidence/$Name.txt"
  if ($code -ne 0) { throw "$Name failed ($code); preserve evidence and stop" }
}
```

## B. Python 基础、R0 与同帧验收回归

```powershell
Invoke-Recorded foundation $py @('tools/check_repository.py')
Invoke-Recorded r0 $py @('-m','unittest','discover','-s','tests','-p','test_spatial_relations.py','-v')
Invoke-Recorded acceptance $py @('-m','unittest','discover','-s','tests','-p','test_pl_compare.py','-v')
Invoke-Recorded full-suite $py @('-m','unittest','discover','-s','tests','-v')
Invoke-Recorded whitespace git @('diff','--check')
```

本交付代码的通过条件：foundation 输出 `PASS: repository foundations, local links, and claim-ledger checks.`；R0 **23**、acceptance **30**、完整套件 **93** 个测试均 `OK`，退出 0，且没有 failure/error/skip。少于预期、`OK (skipped=...)`、零测试、依赖缺失，均不构成完整复现通过。后续提交增加测试时记录新提交与预期变化，不为通过删测试或修改阈值。基础检查不证明 RTL/板卡功能。

R0 的固定数学边界以 [候选契约的边界表](scene_relation_contract_v0_1.md#r0-原始关系边界表) 和 [独立测试](../tests/test_spatial_relations.py) 为准：包含式 bbox、半像素中心、方向阈值等号、IoU 上下阈值、零交集、距离内外半径等号、ROI 等边、单像素/全帧、缺测、不完整帧及会话/帧/配置一致性。非法输入应抛 `ValueError`；合法缺测/错帧应返回 `unknown`，不能复用旧框。

需要单独留存随机框证据时，执行现有测试名：

```powershell
Invoke-Recorded r0-random $py @('-m','unittest','discover','-s','tests','-p','test_spatial_relations.py','-k','test_10000_fixed_seed_pairs_against_fraction_oracle_and_invariants','-v')
```

预期 **1** 个测试通过；其内部固定 seed `0x5CE0_2026`，检查 **10,000** 对合法框、七个谓词、独立 `fractions.Fraction` oracle 及逆向/对称/ROI 不变量。随机输入不是实拍标定；不要换 seed、减少数量或用被测实现生成期望值。

## C. 现有错误注入与预期失败

以下均调用 [test_pl_compare.py](../tests/test_pl_compare.py) 的现有测试，socket/接收器/时钟使用 mock，**不会连接板卡**。每条 unittest 自身应退出 0、执行 1 个测试并 `OK`；测试内部要求故意错误的 CLI 返回 1、`passed=false` 和对应失败原因。

```powershell
Invoke-Recorded reject-sum $py @('-m','unittest','discover','-s','tests','-p','test_pl_compare.py','-k','test_cli_exact_sum_error_sets_failure_exit_code','-v')
Invoke-Recorded reject-v1 $py @('-m','unittest','discover','-s','tests','-p','test_pl_compare.py','-k','test_cli_v2_request_rejects_v1_with_failure_exit_code','-v')
Invoke-Recorded reject-empty $py @('-m','unittest','discover','-s','tests','-p','test_pl_compare.py','-k','test_cli_no_data_sets_failure_exit_code','-v')
Invoke-Recorded reject-stop $py @('-m','unittest','discover','-s','tests','-p','test_pl_compare.py','-k','test_stop_command_error_cannot_leave_a_success_exit_code','-v')
```

| 注入 | 必须拒绝的原因 |
|---|---|
| 四像素 `sum_x` 从 6 改为 7，floored centroid 仍不变 | `measurement_mismatch` |
| 要求 v2，却收到 v1 | `mask_version_mismatch` |
| 没有收到任何帧 | `insufficient_pairs` |
| 正确数据后 STOP 发送失败 | `stop_command_failed` |

完整 acceptance 的 30 个测试另覆盖错帧、缺结果、不完整结果、重复/乱序、混合版本、保留零序号/回绕、覆盖旧输出和 bind 失败。**不要**用 live `python -m src.pc.pl_compare` 做离线错误注入；该 CLI 真实绑定 UDP 并发送 START/STOP。R0 历史内存 mutation 记录不提供公开 runner，不能编造 `--mutation` 参数；该历史敏感性检查见 [交付证据](../report/experiments/2026-09-30-test-delivery.md)。

## D. 可公开重建的完整帧与 golden

没有相机也能生成同一个合成输入。`red_mask.py` 没有 CLI，下面通过其真实 `measure_red_statistics` API 获取 v1/v2 golden；输出文件只在新的 ignored `private/` 目录。

```powershell
@'
import hashlib, os
from pathlib import Path
from sim.reference.red_mask import measure_red_statistics
root = Path(os.environ["ZYNQ_OFFLINE_EVIDENCE"]).resolve()
assert root.is_dir() and str(root).isascii()
raw = b"\xf8\x00" * (640 * 480)
with (root / "all-red.rgb565").open("xb") as stream:
    stream.write(raw)
lines = [f"BYTES={len(raw)} SHA256={hashlib.sha256(raw).hexdigest()}"]
for version in (1, 2):
    lines.append(f"GOLDEN v{version}: {measure_red_statistics(raw, 640, 480, spatial_filter=version == 2)}")
with (root / "golden.txt").open("x", encoding="utf-8") as stream:
    stream.write("\n".join(lines) + "\n")
print("\n".join(lines))
'@ | & $py -
if ($LASTEXITCODE -ne 0) { throw 'Input/golden preparation failed' }
```

输入：640×480、row-major、RGB565 **大端**，`F8 00` 重复 307200 次，共 **614400** 字节；SHA-256 必须为 `82764ed06ca9dd3c9c9caaa0ade5318aa135abbd2f11cad36f9aa1e2aa944440`。

| 模式 | valid | count | sum_x | sum_y | inclusive bbox | floored centroid |
|---|---:|---:|---:|---:|---|---|
| v1 阈值 | true | 307200 | 98150400 | 73574400 | `(0,0,639,479)` | `(319,239)` |
| v2 5-of-9 | true | 304964 | 97435998 | 73038878 | `(1,1,638,478)` | `(319,239)` |

不一致就停止，不修期望值来适配结果。该输入没有私人相机像素；全红通过不代表其他场景通过。

## E. v1/v2 RTL 仿真与同输入 golden 对比

需已安装且可运行的 **Vivado 2024.2，SW Build 5239630**；这是既有记录版本，其他版本须单列环境差异。无 Vivado 时写 `not_run: Vivado unavailable`，仍可完成 A–D，不能声称 RTL 通过。下面 runner 只启动 xvlog/xelab/xsim，不启动 JTAG、不综合或烧写。

```powershell
$vivadoBin = Read-Host 'Installed Vivado 2024.2 bin absolute path'
foreach ($exe in @('xvlog.bat','xelab.bat','xsim.bat')) {
  if (-not (Test-Path (Join-Path $vivadoBin $exe))) { throw "Missing simulator: $exe" }
}
if ((Test-Path "$evidence/xsim-v1") -or (Test-Path "$evidence/xsim-v2")) { throw 'Use fresh xsim directories' }
Invoke-Recorded xsim-v1 $py @('tools/compare_red_frame_xsim.py',"$evidence/all-red.rgb565",'--build-dir',"$evidence/xsim-v1",'--vivado-bin',$vivadoBin)
Invoke-Recorded xsim-v2 $py @('tools/compare_red_frame_xsim.py',"$evidence/all-red.rgb565",'--build-dir',"$evidence/xsim-v2",'--vivado-bin',$vivadoBin,'--spatial-filter')
```

参数与源码来自 [compare_red_frame_xsim.py](../tools/compare_red_frame_xsim.py)。v2 只通过 `--spatial-filter` 选择；没有 `--golden`、`--v2`、`--error-injection` 等参数。每次保留独立 build 目录及工具日志，禁止复用旧生成结果。

每个模式须同时满足：退出码 0；输出 `FRAME_COMPARE_PASS`；`REFERENCE` 与 `PL_XSIM` 的 **valid/count/sx/sy/minx/miny/maxx/maxy 八项逐项完全相等**，并符合 D 表。发现 `FRAME_COMPARE_FAIL`、`Fatal`、runner 报 `no FRAME_RESULT` 或工具启动失败时停止。`FRAME_RESULT` 在详细 xsim 日志内，由 runner 解析，成功摘要不直接打印它。历史上 xsim 的 `$fatal` 曾返回进程码 0，不能只看退出码。现有 [v1](../report/experiments/2026-09-30-red-v1-xsim.txt)/[v2](../report/experiments/2026-09-30-red-v2-xsim.txt) 是既有摘要，不能冒充队友的新结果。

更细的小场景/复位/间隙/四票与五票/帧头版本已有 [testbench](../sim/README.md) 和 [历史记录](../report/experiments/2026-09-30-red-spatial-filter.md)。完整帧 runner 只验证调用者提供的字节；没有一键运行所有 testbench 的公开脚本。需要扩展时，先核对 bench 的实际依赖及 PASS/Fatal 判定，再另开可复核任务；不要把旧像素阈值 mutation 步骤套到当前已变化的颜色规则。

## F. 有 FPGA 时另行执行的板测

此节不随 A–E 自动执行；以成员当前实际板卡条件为准，不凭队员文字授权加载硬件。离线结果不能标为板测通过。最终相机固定为现有 **OV5640 接 FPGA，镜头固定不随云台转**。

前置条件：所有者授权本次测试；没有其他会话占用 JTAG、串口或 UDP 1234；明确接线/板卡身份；已审查的匹配相机位流及其 SHA-256 在本地可用。位流与原厂 HDL 不在公开仓库，干净克隆不能自动重建或取得它们。仅允许不含激光/运动的相机位流做**易失性 JTAG 配置**；禁止自动 Flash/EEPROM/eFuse 写入、驱动/系统/网络安全修改、重启、kill 别人的进程、启动运动或光源。

1. 按 [视频基线](../board/video_baseline.md) 核对相机、GE 网线、有线地址 `192.168.1.102/24` 与板端 `192.168.1.10:1234`；这是一套已测配置，不能自动给队友电脑改网卡。USB/JTAG 必须稳定识别，不以曾读到 ID 代替当前配置成功。
2. 先通过 Vivado Hardware Manager 将**匹配且 hash 已核对的相机基线**临时加载到实际识别的器件，保存编程日志及位流 hash。必须有配置完成、startup `HIGH`，并核对 EOS/DONE 状态；不能从“ID 可读”或“下载命令已发出”推断配置成功。仓库没有通用安全下载脚本，本步骤由所有者选择已审查文件完成，不编造下载命令。失败保存日志并停止。
3. 单独验证真实相机画面与 PC UDP 接收。先运行下方 10 秒 headless probe；退出码 0 仍必须检查 JSON：`complete_frames>0`、`received_payload_bytes>0`、未 interrupted。再启动 viewer，人工点击「开始接收」，确认无生命纸靶/实际场景可见且画面有变化。窗口打开不自动接收；**模拟画面自测不算相机帧。** 保存脱敏观察和统计；原厂纯视频基线尚无 PL 统计，不运行它的同帧算法验收。

```powershell
Invoke-Recorded video-10s $py @('-m','src.pc.bench_probe','--seconds','10','--interval','5','--output',"$evidence/video-10s.json")
& $py -m src.pc.camera_viewer
```

4. 用户正常关闭本次 viewer 后，审查并临时加载待验收的 **v2 相机/滤波位流**，重新确认配置完成和真实视频。不能用纯原厂或 v1 位流代替 v2。确认 UDP 端口空闲，用新 JSON 执行强制版本的 100 同帧验收：

```powershell
Invoke-Recorded filter-100 $py @('-m','src.pc.pl_compare','--seconds','30','--frames','100','--expected-mask-version','2','--compare-raw-mask','--output',"$evidence/filter-100.json")
```

同帧统计一致的通过条件：退出 0，JSON `passed=true`、`required_frames=100`、`compared>=100`、`expected_mask_version=2`、仅有观测版本 2；`failure_reasons=[]`，`mismatch_count=sequence_gaps=duplicate_sequences=mask_version_mismatches=0`，`stop_command_error=null`，100 组精确 count/sum_x/sum_y/bbox/centroid/有效性与本组原始图像一致。视频 N+1 携带 N 的结果，必须按硬件序号配对；不以显示平滑框作黄金参考。若有效滤波目标为 0/100，只记录无目标统计一致，不能称为纸靶正例检测通过。正例门槛和抗干扰场景需在后续实验前冻结；不得降低颜色/票数阈值来让本次结果通过。

5. 再做**独立**连续接收统计：

```powershell
Invoke-Recorded video-30s $py @('-m','src.pc.bench_probe','--seconds','30','--interval','10','--output',"$evidence/video-30s.json")
```

`pl_compare --seconds 30` 是接收超时上限，够 101 个视频帧可能提前结束，不能称为连续 30 秒。连续 probe 必须读取实际 elapsed、每个 interval 新帧、完整/不完整/畸形包和最大间隔；报告测量值与已冻结场景阈值，不从 exit 0 推断稳定。协议没有逐行序号/checksum，无法排除所有静默行重复/重排。`box_variation` 只是描述统计，100 组一致也不自动证明滤波降低抖动、时序闭合、更多场景或独立重建通过。

STOP 是无 ACK 的单向命令：bench_probe 忽略 STOP 发送错误，`pl_compare.stop_command_error=null` 也只说明本机发送未报错，不能证明板端已经停止。关闭本次工具并检查自己的接收任务已退出；不要因此操作别人的进程。

## G. 保存、复核与结果交付

每次按 [候选 evidence-gates](../skill/evidence-gates/SKILL.md) 记录 `claim, evidence_path, commit, tool_version, input_id, status, known_limit, reviewer`，另附 runId/UTC 起止、完整命令、实际退出码、测试数与 skip、输入/源码 SHA-256。失败保存 stdout/stderr、失败阶段与原因，后续项写 `not_run`；不用跳过代替通过。

证据分层：B/C 为软件检查；E 为 `simulated`；F 的配置完成、真实相机、PC 接收、v2 100 同帧、连续运行分别记录。A–E 通过不能提升板测状态，原型通过不能提升 Zynq 状态。历史证据入口见 [交付说明](../report/experiments/2026-09-30-test-delivery.md)。

原始日志、私有图像、位流、账号/个人路径及设备序列号保留 ignored `private/`。对外只提交脱敏摘要与获准公开的合成输入定义；用独立分支/PR 交付测试样例和报告，不自动 merge/deploy。用户没有要求开始测试时，读完流程后停止。
