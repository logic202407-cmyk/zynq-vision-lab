# 赛事要求与仓库位置

依据团队留存的《2026 FPGA 创新设计赛道选题指南（AMD）》3.3 节，并于 2026-09-22 对照 AMD 企业赛道 Gitee 仓库提交 `e47e4a8` 的 `TRACK_GUIDE_2026.md` 与 `tracks/open-topic/GUIDE.md`；出处与版本限制见 [sources.md](sources.md)。不套用 3.1 本地智能体或 3.2 具身智能赛道的硬件要求。

| 要求/交付 | 仓库位置 | 当前状态 |
|---|---|---|
| GitHub/Gitee 公开与允许再分发的协议，推荐 MIT/Apache-2.0 | `README.md`、`LICENSE`、`THIRD_PARTY.md` | 2026-09-24 已回读公开 GitHub 仓库和 MIT 许可；当前仅规划文件，完整工程尚未发布 |
| 声明具体器件、板卡与工具版本 | `board/hardware_inventory.md`、`build/toolchain_manifest.md` | 待实物与工具核验 |
| 源码、仿真、接口和可重建工程 | `src/`、`sim/`、`build/` | 目录已建，工程未实现 |
| 板上运行、实测输出及资源/性能对照 | `report/experiments/`、`report/templates/experiment.md` | 未完成 |
| 大模型协作交互、自我纠错记录 | `report/ai_collaboration/` | 仅初始化记录与后续模板 |
| 可复用 Skill 与适用边界 | `skill/evidence-gates/SKILL.md` | 候选，未完成 FPGA 开发中的复用验证 |
| 报告、演示、复现和参考材料 | `report/submission_checklist.md`、`docs/reproduction.md` | 清单已建，最终材料未完成 |
| 英文/ASCII 文件与目录命名 | 基础检查工具与 CI | ASCII 检查已配置；官方指南对小写的文字要求与其 `README.md` 示例存在歧义，最终提交前确认 |
| 决赛英文单页海报等额外材料 | `report/submission_checklist.md` | 未制作；以届时模板和公告为准 |
| 2026.1/2025.2 推荐工具版本，其他版本说明并保证复现 | `build/toolchain_manifest.md`、`docs/reproduction.md` | 本机发现 2024.2；尚未构建，后续须记录选择依据与复现结果 |
| 初级组 PYNQ 为推荐方向，通用 PYNQ Skill 单独加分 | `docs/decisions.md`、`skill/` | 维持条件分支；未验证匹配镜像，不据加分项提前移植 |

“已建立目录/模板”不等于“满足最终提交要求”。最终以组委会最新评分细则、提交格式和实际验收结果为准。

公开仓库的工程交付差距、入库节奏和最终验收见 [repository_submission.md](repository_submission.md)。
