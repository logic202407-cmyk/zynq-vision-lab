# 独立任务索引（2026-10-04 扩展版）

两人各自推进，当前不互相联调，不需要等另一人的输入、回放或日志。本文只安排后续工作；本轮没有执行这些新工作包、测试或硬件操作。保留原实现和验收阈值，已交付功能不再从零布置。

| 负责人 | 任务单 | 必做 | 进阶 | 条件储备 | 合计 | 第一批 |
|---|---|---:|---:|---:|---:|---|
| `3331083641-prog` | [PC/FPGA](3331083641_next_stage_2026-10-03.md) | 20 | 20 | 10 | 50 | F01–F08，离线 |
| `ikkkkk19` | [STM32](ikkkkk19_next_stage_2026-10-03.md) | 31 | 29 | 10 | 70 | S01–S08，离线 |

## 计数依据与开始方式

上一版固定提交 [091cb7138b89537bffae3557e23a0f2f5d76ae30](https://github.com/logic202407-cmyk/zynq-vision-lab/commit/091cb7138b89537bffae3557e23a0f2f5d76ae30) 的独立交付物为文 5 包、吴 7 包。吴除五个软件主任务，还包括台架行为和候选电气复核，不能从分母漏掉。本版按独立目的、交付物和验收边界计文 50、吴 70，均为原包数的 10 倍；不声称工时正好 10 倍。标题、句子、测试向量、实验计划的 42 条测量记录、一般提交/安全说明及已经完成的功能不另计数。W1–W7 是旧任务映射，不是本版执行依赖；本版依赖使用 F/S 编号。

| 旧包 | 本版相应增量范围 |
|---|---|
| 文 W1 计划与版本输入 | F01、F18、F20–F27 |
| 文 W2 准备/独占/停止 | F02、F03、F12、F19、F28、F35、F46–F48 |
| 文 W3 v1 正例/无目标/稳定 | F04–F08、F13、F16–F17、F29–F33 |
| 文 W4 v2 同输入/滤波 | F09–F11、F14–F15、F34、F36–F45 |
| 文 W5 分层结论/失败账 | F40、F49–F50 |
| 吴 W1 可重建工程/依赖 | S01–S04、S35–S36、S41、S51–S54、S64、S66 |
| 吴 W2 本地输入/夹具 | S05、S07–S10、S15、S17–S18、S33–S34、S55–S59 |
| 吴 W3 失效/恢复 | S06、S13–S16、S19–S20、S22、S29、S63 |
| 吴 W4 单轴/解析 | S11–S12、S17–S18、S21、S23–S28、S30–S32、S37–S38、S60、S67–S69 |
| 吴 W5 软件结果 | S39–S40、S50、S61–S62、S65、S70 |
| 吴 W6 条件台架 | S42–S46 |
| 吴 W7 候选电气/负载 | S42、S49；S47–S48 是接口规划增量 |

映射允许一包对应多个旧目的，合计按唯一 F01–F50 / S01–S70 去重。全体新包起始为 `planned / not_run`。每次只选一个可审查的小包；先做第一批，随后在同类任务中按依赖推进。若已有对应成果，引用精确版本和证据标为 covered，不重复实现或重跑已完成工作。缺输入时阻塞该包，可做本人的其他无依赖离线包；不要向另一人索要材料作为启动前置。

## 已有交付与固定来源

以下是本轮读取的固定 head；引用报告不代表本轮再次执行，也不表示已合并 main。除 PR5 的下述软件复核，作者记录不自动提升为非作者独立复现。

| PR | 固定 head | 已有状态及限制 |
|---|---|---|
| [1](https://github.com/logic202407-cmyk/zynq-vision-lab/pull/1) | `d96bc149bc25f0572350c47ed031c0922ec265ad` | STM32/OpenMV 历史原型，后续源码看 PR7 |
| [3](https://github.com/logic202407-cmyk/zynq-vision-lab/pull/3) | `7a638ac8a332f17951b45200fa3e13c41c7150d7` | PC 回放历史原型，P0 扩展看 PR5 |
| [4](https://github.com/logic202407-cmyk/zynq-vision-lab/pull/4) | 更新前 `091cb7138b89537bffae3557e23a0f2f5d76ae30` | R0/精确验收/runbook 文档分支，本次仍仅更新这三个任务文档 |
| [5](https://github.com/logic202407-cmyk/zynq-vision-lab/pull/5) | `0c10df7968b4e22dacc8d52f7838c15e9a8904fc` | 独立软件复核：130 项无 skip、22 像素对照、16 组/31 项 R0、55 额外探测；9 份冻结 hash 一致。xsim 仅核对日志，本轮未重跑 |
| [6](https://github.com/logic202407-cmyk/zynq-vision-lab/pull/6) | `cc58615f34d90e7cd1da9bd9d9dffa455c1d19ae` | 作者 141 测试；raw+sidecar/离线测量与 r1 实验计划已交付，42 条是计划测量记录 |
| [7](https://github.com/logic202407-cmyk/zynq-vision-lab/pull/7) | `04ba0db3e1a4f67cee7efa7b941d69ce281bffa2` | 作者 109 项无 skip（40+66+3）及 ARM 命令行 0 错误/0 警告构建；非 uVision GUI、串口/PWM/实物验收 |
| [8](https://github.com/logic202407-cmyk/zynq-vision-lab/pull/8) | `96270ce56fba15ac896f4f6dfdd6ea41a107406f` | v1 部分实测与失败记录，不能替代完整场景/时长验收 |
| [9](https://github.com/logic202407-cmyk/zynq-vision-lab/pull/9) | `f616f866e275835689528ee12514fec40dc6c4b3` | 作者 158 测试；两轮 v1 各 100 精确匹配，但语义 P0 0/100、85/100 均失败，3.375 秒均不是 30 秒 |

PR9 最后固定报告中一次配置 startup HIGH、EOS/internal DONE/pin DONE=1/1/1，随后两张试拍，再 10.12 秒零包零帧；事后仅下载器 target 可见而板器件缺失。配置成功、视频出现和持续场景通过是不同证据；这不是现在设备状态的读取，也不能仅凭零包认定板坏。原帧覆盖不足、条件混杂和 ROI 独立复核尚待补齐。历史 v2 100 精确匹配有效目标 0/100，仍不证明有效正例或抗干扰。

各人按自己的固定 PR/提交获取实际源码，不能假定 PR4、main 或另一人的分支已经含 PR6/7/9 代码。原 R0 冻结源码 [2a018c4b82e356dee3ca8cb000b520112b624c18](https://github.com/logic202407-cmyk/zynq-vision-lab/commit/2a018c4b82e356dee3ca8cb000b520112b624c18)、[hash 清单](../report/experiments/2026-10-03-r0-acceptance-source-sha256.txt)、[数学边界](scene_relation_contract_v0_1.md#r0-原始关系边界表)及 [Codex runbook](codex_test_runbook.md) 保持不变。

## 执行门与停止边界

| 门 | 含义 | 需要的额外条件 |
|---|---|---|
| O | 离线档案、源码/host 测试或文档规划 | 用户明确请求该阶段、依赖已有且合法；本轮只写文档 |
| H0 | 当次 FPGA 配置/只读枚举准备 | 板卡所有者当次许可、正确相机位流来源、安全接线、JTAG/UDP 无并发占用 |
| H2 | 真实相机帧与 PC 收包 | H0 通过，区分配置、相机帧、UDP、持续场景结果，原始证据可归属 |
| E1 | 可选新算法/协议/采集修改 | 先提交版本化方案，再获用户批准；保护原参考、验收及 RTL/UDP 协议 |
| B | STM32 GUI/串口/PWM/台架 | 工具依赖许可、型号/电平/接线核实及当次具体许可；烧录/供电/运动各自协调 |

“必做/进阶”是优先级，不绕过执行门；条件储备目前只规划。FPGA 板测不要求 STM32；STM32 host 工作不要求 FPGA。文档阅读不授权设备接管、系统改动、驱动安装、Flash、运动或光源。失败保存原始结果并停止该阶段，后续记 `not_run`；不反复烧写/复位直到碰巧通过，不降低阈值，不把跳过、退出 0、构建成功或一段视频当板测通过。

最终相机仍为现有 OV5640→FPGA/Zynq，镜头固定。最终 PS/STM32 架构未定；OpenMV/回放仅为独立原型输入，不替换最终相机，也不算 Zynq 验收。未来双对象观测属于另行讨论的规划，不在本次独立任务中实现；不采用“目标偏离图像中心就转云台”的相机随动逻辑、不把像素线性换角度。本仓库研发限几何纸靶、屏幕测量和日志；不加入移动发射器协同或自动照射。参见 [AGENTS](../AGENTS.md)、[安全边界](safety.md)。

## 每包交付证据

每包单独记录 `id / claim / priority / gate / status / commit / tool_version / input_id+hash / utc_start+end / command / independent_expected / actual / exit_code / counts+skip / evidence_path+hash / known_limit / reviewer`。状态区分 planned、implemented、simulated、implemented_on_device、board_verified、reproduced；参见 [候选 evidence-gates 技能](../skill/evidence-gates/SKILL.md)。完整原始图像、串口档案和工具私有资料留私有目录，公开仅提交授权源码与脱敏摘要；不得包含私人邮箱、系统个人路径、机器标识、凭据和未授权厂商源。

以自己的分支/PR 交付，不重写作者分支、不合并现有 PR、不采购、不联系另一人代办。本阶段分别复核成果后，再由用户安排字段差异、共同协议和联调。新实现完成后才写验证过的命令；以下任务清单没有伪造尚不存在的测试入口。
