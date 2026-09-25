# 调研来源与适用边界

检索/阅读日期：2026-09-18（北京时间）。前期规划包只包含调研与规划，不包含下载的第三方源代码、预编译镜像或已验证板级工程。

## S01｜北航教务部：2026 FPGA 创新设计竞赛通知

发布：2026-08-31。  
https://jiaowu.buaa.edu.cn/info/1016/9028.htm

用途：报名/提交/决赛时间、队伍人数、决赛基础编程考核。  
状态：正文已读取。它是高校发布的本届赛事通知；赛事主站本次访问失败，执行前应核对最新组委会公告和校内截止日，不将其当作保证没有变更的证明。

## S02｜团队留存：2026 AMD FPGA 创新设计赛道选题指南

文件：61c0eb3d-7f56-4f5d-ba07-5222f9969879.pdf  
上传日期：2026-09-16。  
主要位置：3.3.1—3.3.7，指南印刷页 19—22；板卡获取章节印刷页 23。

用途：初级组要求、实现方式、工具版本、板测要求、评分权重、工程包、Skill 与可复现性。  
状态：已通过文件检索阅读相关内容。文件是团队留存的指南版本；没有将完整文件纳入本仓库，所以本规划包不附其副本。后续评分细则有更新时，以正式发布版本核对。

## S03｜AMD UG973：器件与订阅级别

https://docs.amd.com/r/en-US/ug973-vivado-release-notes-install-license/Device-Availability-by-Subscription-Tier

阅读版本：2026.1，页面标注发布 2026-06-23。  
用途：新版本表格列示 Zynq-7000 全系列处于 Basic/Core/Pro/Enterprise 支持范围。  
边界：支持表不等于当前电脑已配置许可证、当前 IP 可免费使用或工程必能生成位流；需要实测。

## S04｜AMD UG973：支持器件与许可证说明

https://docs.amd.com/r/en-US/ug973-vivado-release-notes-install-license/Supported-Devices-and-Features

用途：2026.1 启动前有效许可证文件与分级变化。  
边界：不把旧版本规则套入新版；也不据此要求使用最新版而放弃已能复现的原厂工具链。

## S05｜PYNQ 官方：SD 卡镜像与新板卡构建

https://pynq.readthedocs.io/en/latest/pynq_sd_card.html

用途：区分已有板卡镜像与新板移植，理解匹配的启动文件、内核、设备树与软件环境。  
边界：没有确认目标板卡 的匹配镜像。阅读官方文档不等于移植完成。

PYNQ 仓库 README 亦已读取：  
https://github.com/Xilinx/PYNQ/blob/master/README.md

## S06｜AMD/Xilinx Vitis Vision Library

https://github.com/Xilinx/Vitis_Libraries/blob/main/vision/README.md

读取方式：GitHub 连接器读取原始 README。  
用途：L1 单算子 C 仿真、综合、联合仿真、RTL IP 导出；L2/L3 与完整平台流程的区别。主分支阅读时对应 2026.1。  
许可：该 README 声明 Apache-2.0；复用具体版本时仍检查对应许可文件。  
边界：README 所列验证板卡不等于目标板卡；本次没有执行示例、综合或测量。不能拿示例性能当本项目性能。

## S07｜AMD XUP：High-Level-Synthesis Design Flow on ZYNQ

https://xilinx.github.io/xup_high_level_synthesis_design_flow/

用途：分阶段学习 HLS 仿真、综合、性能优化与 IP 集成；Sobel/卷积等项目式案例。  
边界：站点教程注明其板卡与工具版本，包含 2023.2 等历史配套；学习方法可参考，工程配置不能原样套用到未知板卡。

## S08｜obra/superpowers：writing-plans

https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md

用途：任务边界、文件职责、输入输出、独立可验证产物、按任务复核。  
状态：通过 GitHub 连接器阅读原文；没有安装、执行或宣称插件已启用。

## S09｜obra/superpowers：systematic-debugging

https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md

用途：先收集可复现证据，划分故障边界，一次验证一个假设。  
状态：通过 GitHub 连接器阅读原文，借鉴为视频链路排错方法；不是 FPGA 专用驱动或修复工具。

## S10｜obra/superpowers：verification-before-completion

https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md

用途：用实际执行证据支持“完成/通过”的结论。  
状态：通过 GitHub 连接器阅读原文。仓库元数据显示 MIT；本包未复制其完整文本，仅整理方法用于 FPGA 证据分层。

## S11｜FDA：Laser Products and Instruments

https://www.fda.gov/radiation-emitting-products/home-business-and-entertainment-products/laser-products-and-instruments

用途：说明直接照射与不同激光类别的眼部危害，“低功率/可见光”不等于无风险。  
边界：不是对中国场地规范或某一器件的安全认证；具体装置需指导教师/场地安全负责人审核。

## S12｜全国大学生电子设计竞赛培训网：2023 赛题公示

https://www.nuedc-training.com.cn/index/news/details/new_id/310

搜索条目发布：2023-08-02。条目列出 E 题“运动目标控制与自动追踪系统”。  
用途：确认该类题目有既有竞赛背景，避免将基础视觉跟踪叙述为首次出现。  
限制：本次搜索返回了题目条目，但进一步打开正文失败；没有据此核验细项指标、获奖方案或现成工程可复现性。没有用其他团队声称的结果来推断本项目能力。

## S13｜2026 FPGA 创新设计赛道 AMD 企业赛道仓库

仓库：https://gitee.com/Vickyiii/fpgachina26-amd  
读取日期：2026-09-22（北京时间）。  
读取分支/提交：`master` / `e47e4a81c2a6a35dbd0b25dcaa4d2edef9daf643`（提交时间 2026-09-21T09:51:31Z）。  
主要位置：`TRACK_GUIDE_2026.md`、`tracks/open-topic/GUIDE.md`、`README.md`。

用途：直接核对 AMD 自主选题初级/高级组资格、器件范围、工具版本、PYNQ 定位、板测与开源要求、工程包/Skill/报告提交内容及评分权重。仓库说明自身是赛道入口与指南索引；自主选题不提供参考工程，参赛队自行组织工程包。

核对结论：Z100 属于允许的 Zynq 路线；PYNQ 为初级组推荐而非强制，通用 PYNQ Skill 另有加分；Vivado/Vitis 2026.1 或 2025.2 为推荐版本，其他版本可用但须说明并保证复现；作品必须板上跑通并提供实测输出。评分为创新与应用价值 30、性能与资源优化 20、功能正确性与完整性 20、大模型协作与 Skill 15、文档与复现 15。

许可边界：该 Gitee 仓库页面与检出内容未发现 `LICENSE` 文件，页面也提示未指定许可证。因此本项目只引用其要求，不复制其指南全文、图片或文件并纳入本仓库 MIT 许可。赛事提交作品本身须使用允许再分发的许可证。

待澄清项：指南正文要求路径使用小写英文、数字、下划线或连字符，但同一指南的推荐结构使用 `README.md`，官方仓库自身也使用大写文件名。当前仓库先保证 ASCII 路径，不据此立即批量重命名；最终提交前向赛道支持渠道确认大小写口径。

## 2026-09-26 方案讨论补充来源

以下来源用于判断实现复杂度与接口约束，不构成目标板卡可用性或实际性能证明。

### S14｜AMD Vitis Vision：颜色检测示例与函数范围

颜色检测示例：https://docs.amd.com/r/2023.2-English/Vitis_Libraries/vision/overview.html_3_2

2024.2 函数说明：https://docs.amd.com/r/2024.2-English/Vitis_Libraries/vision/api-reference.html_1

用途：颜色分割和形态学处理作为可参考的 FPGA 视觉路径；2024.2 函数说明明确 `Bounding box` 为内存映射实现之一，不能假设直接调用就是本项目所需的全流式区域统计。实际函数适配、资源和性能待目标工程验证。

### S15｜AMD UG934：AXI4-Stream Video 信号

https://docs.amd.com/r/en-US/ug934_axi_videoIP/AXI4-Stream-Signaling-Interface

用途：若后续封装 AXI4-Stream Video 接口，按文档区分 `VALID/READY` 握手、`TUSER` 帧首与 `TLAST` 行末。本地原厂例程可能采用其他同步信号，是否转换须按选定版本实查。

### S16｜Mori 等：FPGA 视觉传感器案例

https://onlinelibrary.wiley.com/doi/10.1155/2012/148190

用途：参考可解释图像处理硬件与处理器分工的研究案例；研究对象和硬件与本项目不同，不能照搬其性能结论。

### S17｜Kowalczyk 等：4K 视频流连通域实现

https://link.springer.com/article/10.1007/s11265-021-01636-4

用途：流式连通域是同色多目标的后续研究方向，也体现相对单一颜色矩累加更高的设计复杂度。本项目 V1 不需要实现 CCL。

## 本次没有完成的事项

没有上板；没有运行 Vivado/HLS；没有下载位流；没有安装 GitHub Skill；没有验证目标板卡的 PYNQ 镜像；没有获得采购报价；没有确认赛事主站是否另有最新调整；没有为光学装置出具安全结论。S13 的读取是指南核对，不是赛事仓库身份的独立组织方认证；具体日期及后续评分细则仍以大赛官方公告为准。


## 仓库初始化补充来源

以下文档在初始化时核对，用于发布与仓库配置，不作为硬件实现证据：

- GitHub CLI 创建仓库：https://cli.github.com/manual/gh_repo_create
- GitHub CLI 浏览器登录：https://cli.github.com/manual/gh_auth_login
- GitHub CLI 查看仓库：https://cli.github.com/manual/gh_repo_view
- actions/checkout 固定版本：https://github.com/actions/checkout/tree/11bd71901bbe5b1630ceea73d27597364c9af683 （v4.2.2，已核对官方标签；不是“最新版本”声明）

本文件保留前期调研的日期与适用限制。创建仓库没有重新执行 FPGA 示例，也没有将任何建议指标转为实测结果。
