---
name: frame-result-check
description: Compare frame-keyed integer measurement records against independently generated reference records.
---

# 同帧测量核对

1. 确认两份输入来自同一组原始帧，帧号没有跨复位复用。
2. 统一字段、坐标定义、颜色规则及有效性语义，参考由独立实现生成。
3. 按 [README](README.md) 运行 `tools/compare_frame_records.py`，保存输入与 JSON 输出。
4. 先运行正常样例，再注入一个坐标和错误，确认工具返回差异而非成功。
5. 用缺帧、重复帧和空输入检测验收脚本，避免零样本通过。
6. 报告匹配数量及错误类型，分开标注合成、仿真和板测来源。

适用范围、命令、失效条件及验证用例见 README。本技能只进行离线数据核对，不连接或配置硬件。
