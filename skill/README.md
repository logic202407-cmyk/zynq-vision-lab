# 可复用技能包

## 帧测量与独立参考的逐字段核对

[使用说明](frame-result-check/README.md) · [技能定义](frame-result-check/SKILL.md) · [命令行工具](../tools/compare_frame_records.py)

输入为带唯一帧序号的两组 JSON 测量，输出为匹配数量、缺失帧、多余帧和字段差异。适用于 FPGA、CPU 或其他处理器的图像统计输出，不绑定相机型号或开发板。

本次验证采用可公开的确定性样例和故障注入回归，覆盖乱序、坐标和错误、缺帧、重复帧、空输入、缺字段及错误类型。它验证比较器的行为，不自动证明输入参考独立或来自真实硬件。

`evidence-gates/SKILL.md` 保留为历史方法说明，不列入本次已验证工具的效果结论。AI 协作案例见 [协作记录索引](../report/ai_collaboration/README.md)。
