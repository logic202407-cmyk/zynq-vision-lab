# R0 与精确同帧验收源码发布

日期：2026-10-03。用户明确批准将原创 R0、测试、精确验收修复及相关文档提交到独立分支并创建 draft PR。基线为 `0daf92f09ed912635169087b07914b65775ab7ff`；发布分支为 `codex/r0-exact-acceptance-20261003`，尚未合并 main。完整源码提交号以该 PR 的 head SHA 和检出后 `git rev-parse HEAD` 为准，不能用本报告基线代替源码发布提交。

## 源码范围与冻结接口

- 新增 `sim/reference/spatial_relations.py`、`tests/test_spatial_relations.py`：七个纯几何关系、输入合法性/一致性及独立边界/10,000 对随机框测试；不实现状态型回放、关系 RTL、PS、多色采集或模型推理。
- 更新 `sim/reference/red_mask.py`、`src/pc/pl_compare.py`，新增 `tests/test_pl_compare.py`：精确坐标和、严格版本与序号配对、输出保护及错误退出；保持现有 Measurement API、RGB565 颜色规则、RTL 和 UDP 布局。
- [冻结边界表](../../docs/scene_relation_contract_v0_1.md#r0-原始关系边界表) 标识为 `r0-boundaries/2026-10-03`；保持先前已检查的比较符号、包含式坐标、半像素中心和未知态语义。配置阈值须显式提供，不假装已实拍标定。
- 更新 [Codex runbook](../../docs/codex_test_runbook.md)、入口/状态及交接记录；CI 安装现有 PC requirements 并检查 Pillow/Tk，避免 UI 回归因依赖缺失而静默 skip。

原共享 worktree 的无关规划/报告修改保留，本次在独立 worktree 定向交付。没有收录厂家 HDL/IP/XDC、位流、检查点、私有输出、画面、硬件标识或凭据。没有访问 JTAG、烧写 Flash、控制云台/光源、合并 main 或修改 PR3。

## 复跑命令与证据

从干净克隆获取上述发布分支，按 runbook 固定 PR head 的完整 SHA，设置进程级可写 TEMP/TMP。Python 3.12 环境另需 PC requirements 和 Tk，记录实际 patch 版本。每一步保存 stdout/stderr 与退出码；缺文件/工具、零测试或 skip 不等于完整复现通过。

```powershell
python -m unittest discover -s tests -p test_spatial_relations.py -v
python -m unittest discover -s tests -p test_pl_compare.py -v
python -m unittest discover -s tests -v
python tools/check_repository.py
git diff --check
```

实际环境：Windows、Python **3.12.14**、Pillow **12.3.0**、Tk **8.6**，使用已有解释器和依赖，没有安装软件。2026-10-03 UTC 在独立 worktree 执行；[完整脱敏 stdout/stderr 与退出码](2026-10-03-r0-acceptance-checks.txt) 记录每条命令及起始时间。

| 检查 | 实际结果 |
|---|---|
| R0 定向测试 | 23 项，OK，退出 0；包含固定 seed 的 10,000 对随机框 |
| 同帧验收定向测试 | 30 项，OK，退出 0；包含错误总和、错误 v1、空输入和 STOP 失败的负控制 |
| 完整 Python 套件 | 93 项，OK，退出 0，无 skip/failure/error |
| 仓库结构、链接与状态检查 | 明确 PASS，退出 0 |
| Runbook 的 PowerShell 静态解析 | 14 个代码块，0 个语法错误；只解析，没有执行硬件命令 |

`git diff --check` 在最终文档更新后运行并记录。远端完整 commit、draft PR 和该 head 的 CI 结果由 PR 页面绑定，不能用本地 93 项通过代替远端 CI；未合并 main。

## 源码身份

[源码 SHA-256 清单](2026-10-03-r0-acceptance-source-sha256.txt) 随 PR 完整提交交付，覆盖五份实现/测试、冻结契约及未修改的 UDP/仿真 runner/依赖表。现有五份实现/测试的字节保持先前检查版本；契约增加冻结版本说明，参数文档更新历史恢复范围。复现者对照 `git rev-parse HEAD` 及清单核对实际字节，不使用另一个 PR 的 SHA。

## 板测和队员接口限制

本次只复跑软件与仓库检查，未复跑 xsim 或板测。先前 v1/v2 合成全红 xsim 的八字段一致证据见 [历史交付说明](2026-09-30-test-delivery.md)，不能写成本次新仿真。

9 月 30 日 [恢复记录](2026-09-30-spatial-board-recovery.md) 的旧相机和 v2 配置成功，EOS/内部 DONE/引脚 DONE 均为 1。v2 100 同帧精确匹配但有效滤波目标 **0/100**；正例与抗闪烁未验收，不能把软件通过写成该板测门槛关闭。

10 月 3 日 `3331083641-prog` 在 [PR3](https://github.com/logic202407-cmyk/zynq-vision-lab/pull/3) 报告 v1 恢复：10 秒 290 完整帧、7 不完整帧、1 异常报文；该报告不是本次复测。核对时 PR3 head 为 `7a638ac8a332f17951b45200fa3e13c41c7150d7`，其 57 测试/22 对照仅覆盖队员分支，R0 原先因缺源码未测试。

JSONL 会话 `A→B→A` 连续性风险仍须在队员适配层单独核对；R0 不保存历史输入流，Snapshot 相等只用于本次关系两端绑定，不代表检测过旧会话复活。此次交付补齐可独立复跑的源码，不修改队员回放接口或分支。
