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

## 8. 报告证据链与效率对照（待填）

来源口径：依据项目负责人 2026-10-02 转述并标识为赛道官方渠道的消息，理解为应用与报告撰写建议；尚无公开原帖/评分条款依据，不自行填评分值或必装结论。

| 证据项 | 实际值/文件散列/脱敏位置 | 状态 |
|---|---|---|
| 模型版本、任务提示和人工干预摘要 | 待填 | NOT_TESTED |
| 检索方式与实际查询/命中文档章节 | local / hosted / 公开文档阅读 / 未使用，按实际选择 | NOT_TESTED |
| 本地 KB 的资料/索引版本与部署证据 | 未部署就写“未部署”，不以浏览网页替代 | NOT_TESTED |
| 个人 Skill 的作者、版本、散列和原创/借鉴部分 | 候选提案；实际创建与验证待填 | NOT_TESTED |
| 官方 MCP server/version 与调用记录 | 待填调用 ID/时间、tool、参数/Tcl、响应与日志散列 | NOT_TESTED |
| MCP 实际承担的操作 | 仅环境查询 / 实质设计操作 / 未使用，附对应证据 | NOT_TESTED |
| 首错、模型判断、人工修正、最小 diff、复跑 | 未发生写“无”，未跑写 NOT_TESTED | NOT_TESTED |
| 第二人复核与授权/隐私审查 | 待填 | NOT_TESTED |

对照问题：整体流程 / MCP 单独贡献（选一）。冻结任务、样本数、质量标准、计时边界、A/B 顺序及缓存策略：待填。单独研究 MCP 时，必须记录其他组成部分相同的证据；不满足则不能作 MCP 因果归因。

| 组/试验号 | 实际工具路径与版本 | 总耗时/人工时间/工具等待时间 | 干预/失败/重跑次数 | 三例门禁与质量 | 日志散列 |
|---|---|---|---|---|---|
| A / 待填 | 待填 | 未测 / 未测 / 未测 | 未测 | NOT_TESTED | 待填 |
| B / 待填 | 待填 | 未测 / 未测 / 未测 | 未测 | NOT_TESTED | 待填 |

- 安装/初始索引/配置的一次性成本：未测
- 成功率、全部失败成本、重复次数与离散程度：未测
- 相对耗时变化与采用的时间口径：未测；不得预填百分比
- 同等质量是否成立、顺序/熟练度等干扰：待填
- MCP 贡献能否单独识别及理由：未验证
- 不扩大结论：开发效率不等于 FPGA 吞吐、帧率、时序或器件性能提升

## 9. 设计报告段落（占位示例，不能原样当成果提交）

**所有【待填】必须由实际证据替换；未执行的部分保留“未执行/未验证”，不要为了语句完整填假结果。**

本项目选取【待填：模块/固定提交】作为开发辅助案例，使用【待填：模型和客户端版本；未使用则写未使用】整理验证步骤，并通过【待填：本地 KB / hosted 检索 / 公开文档阅读 / 未使用】获得【待填：文档版本、章节和实际查询依据】。个人 Skill 当前状态为【待填：仅提案 / 已编写未验证 / 已完成限定验证】，其原创内容为【待填：项目边界、黄金期望、证据门禁与错误案例】，参考来源为【待填：固定版本官方 Skill】。官方 MCP 实际承担【待填：真实操作；仅版本查询就写仅版本查询】，对应调用记录为【待填：调用编号、Tcl/响应与日志散列】，不能由此推导未执行的仿真或修复。正例、故意错误负例与恢复分别得到【待填：真实结果/未测】，人工发现并纠正【待填：真实错误及 diff；无则写无】。在【待填：可比条件、样本数、计时边界】下，A/B 的【待填：总耗时或人工时间】分别为【待填：真实值或未测】，质量门禁为【待填】；因此目前可支持的结论是【待填：限定结论/尚无效率证据】。本案例仍未验证【待填：局限】，不将开发辅助结果表述为板卡性能提升。

本次文档更新可直接采用的状态句：**“已完成 ROSS 资料核对及候选验证方案整理，正在准备个人 Skill 与可审计证据记录；尚未完成本项目的 ROSS/MCP 实测与效率对照，当前不报告效率提升百分比。”**
