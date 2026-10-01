# ROSS 对本项目的适用性评估（2026-10-01）

状态：**已完成公开资料与仓库源码核对；本轮没有安装 ROSS、运行其脚本或开展仿真/板测。以下是待队友执行的验证方案，不是试用成功报告。**

- 项目核对基线：`0daf92f09ed912635169087b07914b65775ab7ff`
- ROSS 固定版本：`2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de`（上游提交时间 2026-09-30）
- 执行入口：[队友 / Codex 验证手册](codex_ross_validation.md)
- 结果回填：[验证结果模板](../report/templates/ross_validation_result.md)

## 1. 结论与采用边界

**值得小范围试用，优先检查 RTL 仿真、失败日志归因与可复现证据整理是否更可靠。暂不把 ROSS 设为主工程依赖，不为试用升级现有工具链。**

ROSS 是 AMD 发布的 FPGA/SoC 开发辅助技能集合，结合编码助手、Vivado MCP 与文档检索使用；它不是视觉模型、可综合 IP，也不直接给本项目增加检测或识别能力。[上游说明](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/README.md)

本项目仍以 **OV5640 + Zynq** 为主线。STM32 为待评估扩展，双摄仅属探索；本次工具评估不改变架构决定。只处理无生命几何标志，输出屏幕标记、测量和日志。当前硬件操作暂停；这份手册不授权 JTAG 连接、配置位流、ILA/VIO、改引脚/时序/摄像头/网络，也不改变现有板测结论。

可直接帮助的地方：
1. 使用明确输入、顶层和 PASS 条件组织小型 RTL 仿真，避免只看退出码就认定通过。
2. 从 elaboration / simulation 的首个因果错误出发，区分设计、测试、工具、环境问题。
3. 在适用版本上整理 lint / 时序方法学报告，把建议连到真实规则与代码位置。
4. 为后续原创证据核验技能提供参考；仍需团队独立复核。

目前不应指望它解决：暗红纸漏检、曝光/补光与阈值标定、视频物理连接、器件完整料号核验、未完成的 PS/多色功能、实际资源/时序/帧率验收。

## 2. 与现有仓库的对照

以有日期的证据为准，部分早期规划仍保留“初始脚手架”措辞，不据此抹去后续结果。

| 项目 | 已找到的仓库证据 | 本次仍未知/未验证 |
|---|---|---|
| Vivado | [工具清单](https://github.com/logic202407-cmyk/zynq-vision-lab/blob/0daf92f09ed912635169087b07914b65775ab7ff/build/toolchain_manifest.md)：2024.2，SW Build 5239630；已有 XSim 和部分本地构建/板测记录 | 队友此刻安装版本、ROSS 与 2024.2 的实际联通及完整兼容性 |
| 主机 | 同一清单历史记录 Windows NT 10.0.26200.0 | 另一台验证机的系统与依赖 |
| Vitis/HLS | 2024.2 安装目录曾存在；版本查询选项不受支持 | 可执行版本、许可证与完整 HLS 流程 |
| 原厂工程 | 元数据为 Vivado 2023.1；不在公开仓库完整分发 | 当前工程跨版本复现和完整时序约束 |
| 器件/相机 | [硬件清单](https://github.com/logic202407-cmyk/zynq-vision-lab/blob/0daf92f09ed912635169087b07914b65775ab7ff/board/hardware_inventory.md)：JTAG 确认 XC7Z100，ATK-MC5640 V1.2；已有视频记录 | 物理封装/速度等级独立确认、广泛场景验收 |
| 现有 RTL | [red_pixel_mask](https://github.com/logic202407-cmyk/zynq-vision-lab/blob/0daf92f09ed912635169087b07914b65775ab7ff/src/rtl/red_pixel_mask.v) 和 [自检 TB](https://github.com/logic202407-cmyk/zynq-vision-lab/blob/0daf92f09ed912635169087b07914b65775ab7ff/sim/red_pixel_mask_tb.v) 已公开，可从固定提交取出 | 用 ROSS 重新验证尚未运行 |
| 场景关系 R0 | [R0 执行说明](https://github.com/logic202407-cmyk/zynq-vision-lab/blob/0daf92f09ed912635169087b07914b65775ab7ff/docs/codex_scene_relation_r0.md) 已入库 | 核对的 main 树中尚无 `sim/reference/spatial_relations.py` 与 `tests/test_spatial_relations.py`；本试验不依赖它们 |

既有 [status.json](https://github.com/logic202407-cmyk/zynq-vision-lab/blob/0daf92f09ed912635169087b07914b65775ab7ff/report/status.json) 继续作为项目状态台账，本次不提高任何 component 的证据等级。未公开的本地文件和其他待交接工作也不算本 PR 的交付物。

## 3. 版本不能一概而论

[FAQ](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/docs/faq.md) 给出 MCP 的总体兼容说明：Vivado 2020.2+，测试基线 2026.1。**这不等于每个 skill 在 2024.2 都可用。**

| 能力 | 固定版本中的具体条件 | 对本项目建议 |
|---|---|---|
| `vivado-simulate-rtl` | [skill](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/skills/vivado-simulate-rtl/SKILL.md) 标为 beta/early access；声明验证于 2025.2、2026.1；live 流程需 Vivado MCP，附带脚本需 Python 3 | 首选试验，但 2024.2 只能写“待实测”；先用已公开的纯 RTL，不加载原厂 IP |
| `vivado-rtl-elaboration-analysis` | [skill](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/skills/vivado-rtl-elaboration-analysis/SKILL.md) 可从 elaboration 日志分析，live MCP 为可选 | 可先用于已脱敏日志；找到解释不等于修复通过 |
| `vivado-rtl-lint` | [skill](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/skills/vivado-rtl-lint/SKILL.md) 依赖 Vivado linter、MCP 与 Python 解析流程；需要按 Vivado 版本选报告格式 | [UG901 2024.2](https://docs.amd.com/r/2024.2-English/ug901-vivado-synthesis/Running-the-Linter) 已记载 `synth_design -lint`，但 ROSS 全流程/解析器仍须验证；不要用 OOC 模式试 linter |
| `vivado-timing-methodology-checks` | [skill](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/skills/vivado-timing-methodology-checks/SKILL.md) 明确 Vivado 2026.1+ | 现有 2024.2 不满足该 skill 声明；本轮跳过，不能由 MCP 总体说明推成兼容 |
| `hls-run-flow` / HLS 优化 | [流程 skill](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/skills/hls-run-flow/SKILL.md) 通过 `v++` / `vitis-run` CLI；基础 HLS 指导不依赖 live MCP | [HLS quickstart](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/docs/getting-started/hls-quickstart.md) 测试于 2026.1，说明可运行于 2025.1+；本项目 2024.2 不获同样保证，Vitis/HLS 实际运行亦未验证；不顺手移植现有 RTL 核心 |
| `hw-ila-debug` | [skill](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/skills/hw-ila-debug/SKILL.md) 明确 Vivado 2026.1+、已配置的 ILA 硬件；其 chipscope-mcp 回退仅用于 Versal | 硬件暂停，本轮绝不执行；Zynq-7000 不能借 Versal-only 回退绕过限制 |
| Vitis AI / AIE / segmented configuration | [上游目录](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/README.md) 面向特定 NPU/AIE/器件工作流 | 不作为 XC7Z100 当前几何标志链路的直接功能，不以名字里有 AI 就引入 |

安装显示成功、skill 能被列出、MCP 能返回版本、仿真正例通过，是四个不同检查项。它们也都不等于实现、板测或独立复现通过。

## 4. 最小采用决策

1. 按手册先完成不含 ROSS 的固定输入基线，再在独立目录完成相同输入的 ROSS 辅助试验。
2. 必须保留正例、故意错误负例、恢复后的正例；负例被漏报是拒绝采用的理由。
3. 硬件保持暂停。即使全部软件试验通过，也只允许结论“该版本、该主机、该小模块的辅助仿真/诊断已验证”。
4. 如果客户端插件命令、MCP 或版本条件不满足，保留现有手工 XSim 工作流，记录 BLOCKED/NOT_TESTED；不要更改主工程工具版本来制造通过。
5. 有实际证据后再决定是否扩大到已有 DVP 配对/帧统计测试。不要先把所有模块重写一遍。

## 5. 许可、数据与来源

ROSS 仓库的 [LICENSE](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/LICENSE) 为 MIT；保留适用版权/许可通知。MIT 不覆盖 Vivado/Vitis 商业软件许可、原厂工程再分发权、相机图片、模型权重或其他依赖。本 PR 只提供原创评估/试验说明与来源链接，不导入上游代码/二进制，因而不把 ROSS 作为已安装依赖登记。

按上游 [安全与隐私说明](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/docs/faq.md#security-privacy-and-the-knowledge-base)，本地 Vivado MCP 与云端文档检索、模型服务是不同层。模型服务是否保留输入由所选服务约定决定，不能因为 MCP 在本地就宣称全流程不出网。检索问题也不要夹带许可证、私有 RTL 或原始相机画面。需要全离线时，另行评估本地知识库与本地模型；这不是本轮安装任务。

公开报告只保留经审查的最小日志摘录、版本、散列与结论；完整日志先存仓库外，去除个人路径、用户名、设备标识、网络细节和凭据再决定是否发布。不要上传原厂 HDL、许可证内容、私有抓帧、`.bit`、`.dcp`、`.wdb`。

## 6. 复核来源

上述链接均固定到本次审查提交（AMD 工具手册另按版本固定）。安装/执行细节见：
- [上游 Codex 插件安装](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/docs/getting-started/install-plugin.md#codex)
- [上游 MCP 配置说明](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/docs/getting-started/vivado-mcp.md)
- [上游 XSim 执行与证据判定](https://github.com/Xilinx/ross-ai-assistant/blob/2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de/skills/vivado-simulate-rtl/references/xsim.md)
- [AMD Vivado 2024.2 仿真手册](https://docs.amd.com/r/2024.2-English/ug900-vivado-logic-simulation)
- [本项目既有 XSim 记录](https://github.com/logic202407-cmyk/zynq-vision-lab/blob/0daf92f09ed912635169087b07914b65775ab7ff/report/experiments/2026-09-27-red-pixel-mask-xsim.md)：旧记录的 24→25 阈值属于当时版本；本手册固定输入已变为 15→16，不照抄旧数值。
