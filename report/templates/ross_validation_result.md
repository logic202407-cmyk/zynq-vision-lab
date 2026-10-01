# ROSS 验证结果模板

> 模板状态：NOT_TESTED。请复制为 `report/experiments/<实际日期>-ross-validation.md` 的候选报告，完成试验后逐项填写。模板不代表任何命令已经执行，也不预先指派队友。
>
> 方案：[评估](../../docs/ross_evaluation_2026-10-01.md)；步骤：[验证手册](../../docs/codex_ross_validation.md)

## 1. 范围与身份

- 实际执行日期/时区：待填
- 执行人/复核人（可用角色）：待填
- 手册所在提交：待填
- 输入项目 SHA：`0daf92f09ed912635169087b07914b65775ab7ff`（实际核验：NOT_TESTED）
- ROSS SHA：`2cdc9eef1b6b5b17fa45f5e4d468e5483a1c92de`（实际加载副本核验：NOT_TESTED）
- 试验编号：待填；隔离目录仅记录脱敏代号，不发布用户名/个人绝对路径
- 硬件暂停边界：是否遵守，是否发生任何越界操作：待填
- 安装/配置/运行授权范围：待填；本模板本身不授权安装或持久访问
- 未公开 R0/原厂源码/私有画面依赖：应为“无”，实际检查待填

## 2. 环境

| 项目 | 实际值与取证方式 | 结论 |
|---|---|---|
| OS / PowerShell / Git / Python | 待填 | NOT_TESTED |
| Codex/其他客户端与模型版本 | 待填，不填写账号信息 | NOT_TESTED |
| 实际加载的 ROSS skill 与缓存副本来源 | 待填，不能只填下载目录 SHA | NOT_TESTED |
| Vivado / XSim 版本及 build | 待填，附版本输出与退出码 | NOT_TESTED |
| Vivado MCP binary 版本/散列 | 待填，不提交二进制 | NOT_TESTED |
| MCP 独立会话版本查询 | 待填真实请求/响应摘要 | NOT_TESTED |
| 适用的版本 caveat | 待填，例如 2024.2 非 simulation skill 声明验证版本 | NOT_TESTED |
| 许可证可用性 | 只填可用/缺失/未知，禁止许可证正文和位置 | NOT_TESTED |
| 文档检索 | 未配置/hosted/local 与实际可用性 | NOT_TESTED |
| Vitis/HLS | 本轮不用；除非另有独立证据，不称已验证 | NOT_TESTED |

## 3. 输入与完整性

| 文件/材料 | 固定来源 | SHA-256 | 核对 |
|---|---|---|---|
| positive RTL | 项目固定提交 red_pixel_mask.v | 待填 | NOT_TESTED |
| positive TB | 项目固定提交 red_pixel_mask_tb.v | 待填 | NOT_TESTED |
| negative RTL | 仅 MIN_R5 15→16 | 待填 | NOT_TESTED |
| recovery RTL | 应与 positive 同散列 | 待填 | NOT_TESTED |
| 三例 TB/guard/bounded.tcl | 各自应相同 | 待填 | NOT_TESTED |
| 实际执行脚本 | 从手册整理，保留实际版本 | 待填 | NOT_TESTED |
| A/B 输入一致性 | B 不复用 A 生成快照 | 待填 | NOT_TESTED |
| 试验前/后 git status | 应为空；禁止覆盖既有工作树 | 脱敏摘要 | NOT_TESTED |

变异 diff（只写真实发生的变化）：待填。

## 4. 分阶段实测

使用 PASS / FAIL / BLOCKED / NOT_TESTED；N/A 仅用于不在范围内的项目。BLOCKED 必须写具体缺失前提，未运行不能写 FAIL 来冒充负例已捕获。

| 试验 | 编译 | 展开 | 仿真功能判定 | 验证门禁判定 | 日志/散列与依据 |
|---|---|---|---|---|---|
| A positive | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | 待填 |
| A negative | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | 预期功能 FAIL、门禁 PASS，实际待填 |
| A recovery | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | 待填 |
| B positive | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | 待填 |
| B negative | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | 预期功能 FAIL、门禁 PASS，实际待填 |
| B recovery | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | 待填 |
| 仅日志诊断（若执行） | N/A | N/A | N/A | NOT_TESTED | 不等于 live skill 或 lint 执行 |
| 第二人独立复跑 | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | 待填 |

每例另记录：
- 真实命令、退出码、开始/结束时间：待填
- top / simulator / mode / runtime：待填
- 完成检查数与终止标记：待填（固定 TB 预期 16 项）
- 首个因果错误、仿真时间、输入/期望/实际值：待填
- 有无意外 ERROR/Fatal/watchdog/超时、完整日志是否读完：待填
- 是否存在编译失败而负例从未运行：待填
- ROSS 所引用的工具结果/来源是否真实：待填
- 查询过的公开 AMD 文档/Answer Record 及适用性：待填；没有则写“未查询”，不得编造
- Workaround、是否改变环境/输入、是否获准、是否真实重跑：待填
- 原始证据目录代号及文件散列：待填

## 5. ROSS 增益与问题

- 是否正确指出 15→16 变异与 7a26 用例：NOT_TESTED
- 是否误把退出 0、MCP 联通或缺失日志当 PASS：NOT_TESTED
- 是否建议改黄金期望、修改原工程或启动硬件：NOT_TESTED
- 实际采纳的建议及人工修正：待填；没有就写“无”
- 如记录耗时/交互次数：A=待填，B=待填，测量边界=待填；不可从一个样例推出普遍加速
- 最小复现问题与下一步：待填
- 建议：暂不采用 / 限定范围试用 / 需修复环境后复验（选一并附证据）

## 6. 未测项与公开审查

- ROSS 以外的 HDL 全回归：NOT_TESTED
- lint / timing-methodology / HLS / ILA：NOT_TESTED，除非另有独立任务与证据
- 综合、实现、时序闭合、CDC、资源/性能、板测：NOT_TESTED
- R0、PS、多色、多摄、项目整体验收：不在本次范围
- 原工作树/硬件状态未被改变：待核对
- 未上传凭据、许可证、原厂 HDL、私有图片、未脱敏日志、生成位流/波形：待核对
- 仓库基础检查与 CI：记录实际结果及提交；即使通过也不是 ROSS/FPGA 验证

公开前先人工审查最小日志摘录；完整原始证据留在仓库外。最终提交需单独授权，不自动修改 `report/status.json` 或合并 PR。

## 7. 独立复核

- 复核人的输入提交/ROSS/工具版本是否相同：待填
- 三例是否在干净目录重新构建：NOT_TESTED
- 复核结论、未决问题：待填
- 远端报告提交/PR 链接：发布并核实后填，不能预填“已提交”
