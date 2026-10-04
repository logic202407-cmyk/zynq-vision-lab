# PC/FPGA 独立实验计划：固定 OV5640 与红色几何纸靶

负责人：3331083641-prog。版本 `pc-fpga-plan/2026-10-04-r1`。
依据 [更新任务](3331083641_next_stage_2026-10-03.md) 与
[runbook F](codex_test_runbook.md#f-有-fpga-时另行执行的板测)。
**本轮交付计划和离线留证工具；新板测全部 `not_run`。**
不等待 STM32，不索取队友日志，不冻结双方通信协议。
相机固定；只输出画面、统计与日志，不接执行器或发光模块。

## 来源与现有证据

- PC 基线：PR5 `0c10df7968b4e22dacc8d52f7838c15e9a8904fc`。
  更新任务来源 `091cb7138b89537bffae3557e23a0f2f5d76ae30`，只同步三份任务文档。
  冻结算法 `2a018c4b82e356dee3ca8cb000b520112b624c18`。
  新工具的实际测试提交与文件 SHA 另记在本次交付报告中。
- [来源清单](../report/experiments/2026-10-04-fpga-plan-sources.json)
  记录本地实际位流 SHA/长度及其私有交付清单声明的 RTL 来源。
  v1：RTL `2bfef119a46d1f1e6604d945a58e3896e539113d`，
  2190907 bytes，SHA `2a380055b3fd93049a5a174c0f3e1e7b140117b0df77fb5825b6b2ab6011fdc5`。
  v2：RTL `a9842abe55cf2d7460fa9c09b0ce188a0bd37f14`，
  17416457 bytes，SHA `4b42c32436a0b9ac7e089ed15777536709839eab8b58314c8e3b37031ce7e121`。
  v1 是压缩的红色统计相机位流，不是无统计的纯原厂视频位流。
  交付清单声明 Vivado 2024.2 / SW Build 5239630。
  当前 RTL 与声明的 v2 提交相同；v1 的 red_frame_stats/red_result_header
  本来属于较早版本，来源清单分别按各自 commit 计算 hash，不用当前 v2 文件冒充 v1。
- 本机软件 Python 3.12.4 / Pillow 12.2.0 / Tk 8.6；实际完整版本另存检查日志。
  位流的构建工具版本属于交付声明；现场实际编程工具版本须重新读取。
  未从完整厂商工程独立重建位流，hash 相符不证明其 RTL 构建来源。
  实际板卡封装/速度等级仍需现场核对，不从 die ID 推断。
- PR5 130 项离线结果和历史 xsim 见
  [P0 报告](../report/experiments/2026-10-04-pc-p0-validation.md)。
  更新任务所述 55 项队长额外探测是外部审查记录，本轮未重跑。
  [10 月 3 日 v1 恢复](../report/experiments/2026-10-03-v1-camera-restored.md)
  不属于本轮受控纸靶正例。
  [历史 v2](../report/experiments/2026-09-30-spatial-board-recovery.md)
  有效目标 0/100，不能据此宣称正例或抗闪烁通过。

## 实验前记录与独立预期

第一次硬件动作前创建新 runId/私有目录，保存完整 commit、工作区差异、
此计划文件 SHA、工具版本、位流 SHA、设备身份和本次独占许可记录。
所有已有输出必须保留，文件名不能重用。原始图、报文、硬件序列号、
位流和完整日志仅留私有；公开摘要保留输入 ID/hash、指标和失败原因。
现场条件变化或指标修改必须在采集前另立计划版本；不改既有验收阈值。

拟定环境是室内固定平台、1–2 m、直径约 5–10 cm 静止红色几何纸靶，
哑光不反光背板。它不是最终比赛指标。记录实际距离/直径/拍摄角度、
相机固定位置、背景、灯具/方向、是否自然光、曝光/白平衡锁定状态。
无照度计就记 `lux=unknown`；未知曝光状态记 unknown，不臆称已锁定。
有窗外光变化或灯光调整时另开条件块，不与原块混算。

允许一次明确标为 `pilot_excluded` 的布置检查：调整纸靶颜色/距离/照明，
使其清楚可见；该试拍不计入正式验收。随后人工依据无叠加 PNG 标出
包含式纸靶 bbox/ROI，保存输入 ID/hash 和 ROI JSON，再开始 100 帧采集。
ROI 根据实体靶轮廓确定，不能从 PL 输出或滤波结果反推。
正式采集后不得重画 ROI 来挽救结果。无目标场景保留原相机/背板/照明。
两个版本之间维持标记位置，任何重新安装/参数变化都记录。

| 场景 | 输入定义 | 独立预期与判定 |
|---|---|---|
| P0 中央纸靶 | 单一固定红色圆/方形纸靶；人工 ROI 在采集前固定 | 至少 95/100 有效，且至少 95/100 组同时有效、floored 质心落在 ROI、包含式 bbox 与 ROI 的 IoU ≥ 0.5；无效组计失败，不能只算有效子集 |
| N0 无目标 | 移除纸靶，保留同一背板/光照/相机 | 100/100 `target_valid=false`，count/sum_x/sum_y=0，bbox/centroid=null；发现背景红色误检也保留并判该场景失败 |
| I0 孤立小干扰 | 无目标背板，放置独立小红点；记录其实际像素尺度和间距 | 仅当原始阈值图确认每个红点在所有 3×3 窗口中不足 5 票、且无其他红区域时，预期 v1 有效/v2 无效；无法满足该前提不能宣称该物理噪点验收通过 |
| E0 贴边/小目标（扩展） | 四边、单像素/2×2 等先用既有合成数据；实体目标另开 ID | 合成预期不变；像素尺度由同一原始帧决定，不用纸靶厘米数推断像素数。实体场景尚未纳入 P0/N0 正式门槛 |

表中的 95/100、IoU 0.5 是**个人实验前拟定的新增工程指标**，
不是赛事或团队已冻结标准；原有 100 同帧、零差异门槛保持不变。
数值 count/sum_x/sum_y/bbox/质心的逐帧精确预期来自冻结 RGB565 参考；
语义目标正确性另用人工 ROI/无目标布置判定。两类预期不能互相替代。
不得把真实圆靶的像素统计硬套成理想 5×5 合成矩形常量。

## 顺序、实验单位与失败处理

预先固定版本顺序 v1→v2。每版每场景 3 次独立 START/STOP 窗口：
R1 为 P0→N0，R2 为 N0→P0，R3 为 P0→N0；每版 I0 放在本版三轮之后，
各做 3 个独立 100 组窗口及快照；完成后再切换版本，不在 H6 自动重新配置 v1。
每窗口先做 100 同帧比较，再做单独 30 秒接收统计；两次工具运行分别建 ID。
同一场景每轮保存一份无改写原始快照，明确它不是比较窗口中的全部 100 帧。
版本顺序未随机化，可能有时间/光照漂移，不能把不同时间实拍当配对因果实验。
三轮是工程重复预算，非功效计算；连续 100 帧不是 100 次独立实验。
报告每轮与汇总，不能靠平均值掩盖某轮失败；三轮均需满足本阶段指标。

| 阶段 | 执行/预期 | 失败后的处理 |
|---|---|---|
| H0 当次独占与身份 | 本次许可，JTAG/串口/UDP 1234 无其他任务，核对接线、器件、位流 SHA 与安全范围 | 不 kill 他人、不改驱动/网卡/系统，不自动尝试未知器件；保存问题，后续 not_run |
| H1 v1 临时配置 | 匹配的已审查相机位流，仅易失性 PL；保存日志，startup HIGH，EOS/internal DONE/pin DONE=1 | 配置失败立即停；不 Flash、不 reset 未知设备、不自动换位流 |
| H2 v1 真视频 | 10 s probe 完整帧>0、payload>0、未中断；人工确认固定纸靶实拍且变化，非 demo | 不把 UI 打开或 JTAG ID 可读当视频；失败停 |
| H3 v1 P0/N0/I0 | P0/N0 3 轮各场景 100 精确组+独立 30 s 窗口，再做 I0 3 轮；版本强制 1，独立预期见上表 | 任一轮错配、误检/漏检或窗口失败立即保存并停；其余计划 not_run |
| H4 v2 临时配置/视频 | 正常关闭自己的工具后，重新核对身份/占用/位流并配置 v2；重复 H1/H2 | 不用 v1 的成功状态代替 v2；失败停 |
| H5 v2 P0/N0/I0 | 同条件 P0/N0 3 轮，各场景强制版本 2 的 100 精确组+30 s，再做 I0 3 轮 | 全部无目标只能支持 N0，不能通过 P0；失败停 |
| H6 同原始输入/干扰分析 | 每个私有 RGB565 输入原封不动同时算 v1/v2；H3/H5 的 I0 采集前先核对像素前提 | 无法制造孤立像素条件记前提未满足；不把合成结果或数量下降当板上抗闪烁证明 |

H3/H5 同帧门槛：exit 0、passed=true、required_frames=100、compared≥100，
只观测当前版本，failure_reasons=[]，mismatch_count/sequence_gaps/
duplicate_sequences/mask_version_mismatches 全 0，stop_command_error=null。
完整性/有效性/count/精确总和/bbox/floored 质心全部逐字段相符。
头 N+1 的统计必须与图像 N 配对；不拿 UI 七帧中值框作预期。

30 秒接收窗口拟定门槛：requested=30，elapsed≥30，未 interrupted，
总完整帧/实际 elapsed≥25 FPS，完整帧最大相邻间隔≤0.25 s，
incomplete/(complete+incomplete)≤1%（分母为 0 即失败）。
每个已报告约 10 秒 interval 用 new_frames/实际区间时长≥25 FPS 判定，
最后不足一个 interval 的尾段另记，不补成完整区间。畸形包、orphan rows、
其他源包及全部启动时段也照实记，不悄悄删除。以上也是新增拟定工程指标。
最大相邻间隔不含首尾无帧时段，须同时审查区间/实际 elapsed；
这些数据无法排除逐行静默重复/重排，不能叫完整网络丢包率。

box_variation 的有效覆盖率、缺测、边界范围、相邻有效组数量和 >50 px 跳变
均单列描述，不将其自动判为抗闪烁完成。比较 v1/v2 必须用同一组
raw RGB565；滤波可能填洞，并非 count 必然下降。若 I0 不产生可量化干扰，
记录没有测试到该效应，另设计下一版实验，不由 0 跳变宣称改善。

## 将来获得本次许可后使用的命令（本轮未执行）

先遵照 runbook A 的 Invoke-Recorded 包装保存 UTC、完整参数和退出码，
新 `$evidence` 目录必须存在。每个文件调用前检查不存在；
`bench_probe` 本身会覆盖已有 output，所以包装前置检查不可省略。
不要同时运行 viewer、probe、pl_compare；正常停止/关闭自己的 viewer。
仓库无通用安全下载脚本，配置由现场所有者选择已审查文件，本计划不虚构命令。

```powershell
Invoke-Recorded v1-video-10s $py @('-m','src.pc.bench_probe','--seconds','10','--interval','5','--output',"$evidence/v1-video-10s.json")
& $py -m src.pc.camera_viewer
# 人工开始接收、确认真实纸靶，保存 PNG/原始 RGB565；正常停止并关闭 UI。
# 每场景/每轮设新 ID，确认输出不存在，再运行；此处仅示例 v1/P0/R1。
Invoke-Recorded v1-P0-R1-exact $py @('-m','src.pc.pl_compare','--seconds','30','--frames','100','--expected-mask-version','1','--compare-raw-mask','--output',"$evidence/v1-P0-R1-exact.json")
Invoke-Recorded v1-P0-R1-window $py @('-m','src.pc.bench_probe','--seconds','30','--interval','10','--output',"$evidence/v1-P0-R1-window.json")
# v2 在重新审查配置/视频之后，用 --expected-mask-version 2 和全新 v2 文件名。
```

`pl_compare --seconds 30` 收到 101 帧可能提前结束，不等于连续 30 秒。
STOP 无 ACK：bench 忽略发送错误，exact 的 null 仅证明本机发送未报错，
均不能证明板端已停。结束后检查自己的任务退出，记录端口状态，保持设备协调。

## 原始快照与离线同输入留证

新按钮“保存原始帧 RGB565”保留当前完整 Frame 的 614400 bytes，
不经 RGB888 转换、叠框或显示中值。输出 `.rgb565` 及 `.rgb565.json`，
记录输入 SHA、640×480、RGB565_BE、frame_seq（可为空）和主机保存时间。
source=`live_camera`/`synthetic_demo` 是 UI 来源标签，不是独立硬件鉴定；
保存时间不是曝光时间，停止/清空预览会清除可保存的旧帧。
不得将前一帧头统计放进本快照。文件仅允许 repo/private 或仓库外私有目录，
两份旧文件中的任一已存在即拒绝，模拟快照不能冒称实拍。

```powershell
# 仅离线，不绑定 UDP，不发送 START/STOP；原始输入与 sidecar 必须同时存在。
& $py tools/measure_saved_rgb565.py --input "$evidence/v2-P0-R1.rgb565" --output "$evidence/v2-P0-R1-same-input.json"
```

工具验证 sidecar/输入 hash，再分别调用现有冻结 red_mask，不实现第二个阈值器。
输出两版 valid/count/sums/bbox/质心、输入/hash/来源和 `offline_not_board`。
该输出没有真实 PL 结果，不能替代 100 同帧板测；PNG 无法复原原始 RGB565。
同输入计算仅验证已接收字节，对原始逐行网络完整性和整幅像素掩码无证明。
独立手算预期继续复用 11 场景/22 对照；尤其中心+孤立噪点 26→21、
十字 5→1、中心孔 24→21，均以既有 fixture 为权威，不改常量。

## 阶段报告模板

每个阶段至少记录 `claim, evidence_path, commit, tool_version, input_id,
status, known_limit, reviewer`，附计划版本/hash、runId、UTC 起止、
照明/距离/ROI、位流版本/hash、完整命令/退出码、计数与失败项。
初始台账见 [待执行矩阵](../data/fixtures/fpga_experiment_schedule_2026-10-04.json)。
字段 null 表示未采集，不能写成测得 0；`not_run` 不能写成 PASS。
外部成员复跑与本机重复分开；未由另一人执行不称 reproduced。
公开结论分层为软件、RTL 仿真、临时配置、真视频、精确比较、
纸靶正例、无目标、连续接收和干扰；历史记录保留原日期和限制。
