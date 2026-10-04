# FPGA 实验准备与原始帧留证工具：离线检查

日期 2026-10-04；负责人 3331083641-prog。
测试固定提交 `07fcb34cdaac02da67a09eb359beb233a6d29269`，由 PR5
`0c10df7968b4e22dacc8d52f7838c15e9a8904fc` 建个人后续分支，另建干净检出。
正式 UTC 03:51:11.606048–03:51:30.102452，工作区干净。
Python 3.12.4 / Pillow 12.2.0 / Tk 8.6。
完整日志和命令留私有目录；[JSON 摘要](2026-10-04-fpga-plan-validation.json)
保存日志/hash、源码/hash、真实提交与来源限制。

## 结果与范围

| 实际执行 | 结果 |
|---|---|
| tools/run_pc_acceptance.py --require-r0 --output-dir 新私有目录 | exit 0 / passed=true；SOURCE_PRESENT_REVIEW_RESULTS 仅为源码存在门槛 |
| runner 内 tools/check_repository.py | exit 0，基础/链接/台账通过 |
| runner 内 python -m unittest discover -s tests -v | 141 项，0 failure/error/skip，exit 0；PR5 130 + 新留证回归 11 |
| runner 内 python -m src.pc.target_replay check | 原有 11 场景/22 像素对照通过，不改预期 |
| runner 内 git diff --check | exit 0 |
| tools/check_pc_r0_cases.py --output 新私有 JSON | 原有 16 组/31 检查通过，exit 0 |
| 9 份保护文件 SHA 核对 | 冻结 R0/参考/精确验收/UDP 与三份既有 fixture 不变 |
| 私有 v1/v2 位流实际 bytes/hash | 与交付清单相符；不证明独立 RTL 构建或现场可运行 |

原始导出新增按钮和 `.rgb565.json` sidecar；保存精确 614400 字节，
无 RGB888 转换/叠框/显示中值，来源分 live_camera 与 synthetic_demo。
两文件拒绝覆盖，sidecar 冲突保留另一写者文件并删除本调用创建的 raw，
对话框处理新帧时仍保存事先固定的 frame/source，停止清空旧证据候选。
离线工具要求 sidecar/hash/dimensions/format 相符，再调用同一冻结参考的两版。
输入篡改、文件冲突、非法来源/长度/路径和保存失败均有拒绝回归。
未启动真实 UI 做外观验证；Tk 回调由 mock 驱动，未建立 UDP 接收器。

合成全红输入 SHA
`82764ed06ca9dd3c9c9caaa0ade5318aa135abbd2f11cad36f9aa1e2aa944440`：
v1 count 307200 / sum_x 98150400 / sum_y 73574400 / bbox [0,0,639,479]；
v2 count 304964 / sum_x 97435998 / sum_y 73038878 / bbox [1,1,638,478]。
两版 valid=true、floored 质心 [319,239]，由手算常量验证，非实拍输入。

## 已准备与尚未执行

[实验计划](../../docs/fpga_experiment_plan_2026-10-04.md) 预先定义
正例/无目标、人工 ROI、窗口指标、三次独立窗口、版本顺序、干扰前提和失败停止。
新增数值门槛标个人实验前拟定；没有修改既有 100 同帧/零差异等阈值。
[矩阵](../../data/fixtures/fpga_experiment_schedule_2026-10-04.json) 的 42 条采集记录
均 not_run，实际值 null；[来源清单](2026-10-04-fpga-plan-sources.json)
分别列 v1/v2 声明 commit 和 RTL hash，v1 历史差异不冒充当前源码。
私有交付清单中“R0 未提交”是其包装时旧状态，现在已发布，不作为当前阻塞。
旧串口契约提案已注明后置，当前不等待 STM32/采购或索取另一方日志。

本轮没有 JTAG 连接/配置、UDP START/STOP、网卡/驱动变更、光源/执行器动作、
真实图像采集或新的 xsim 运行。临时配置、真视频、100 同帧、纸靶正例、
无目标、30 秒连续统计与物理干扰均 not_run。历史日志不转为本轮完成。
软件/同输入 golden 工具通过不能提升到 board_verified 或 reproduced；
实际板测须按 AGENTS/runbook 另获本次许可和设备独占后执行。

## CI 路径注入修正后的追加复跑

首次 [CI 失败](https://github.com/logic202407-cmyk/zynq-vision-lab/actions/runs/37175393043)
保留：141 项中的 sidecar 故障注入未触发。临时路径别名是原因推断；
注入器改为比较两边 resolve 后的路径，原异常/文件保留/清理断言不变。
产品实现和全部既有门槛未变。固定提交
`e3ca20df8da6ff627f2f06fa5ddf288996247766` 干净检出重新执行同一 runner：
141 项无 skip、22 对照、16 组/31 检查和基础/diff 全通过。
追加 UTC、日志/hash 和测试文件 hash 见 JSON 的 ci_followup；首轮证据保留。
[push CI](https://github.com/logic202407-cmyk/zynq-vision-lab/actions/runs/37175489549)
与 [PR CI](https://github.com/logic202407-cmyk/zynq-vision-lab/actions/runs/37175491698)
也通过。两次本机运行和远端 CI 均是软件证据，不提升为新板测。
