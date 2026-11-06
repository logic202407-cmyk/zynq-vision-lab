# 3331083641 软件任务补齐与干净检出复跑

执行日期：2026-10-03；负责人：3331083641-prog。
输入基线 `7dc3966b089abea3a21b7d0ebf0d066a5e24bdff`，main/远端main仍为
`0daf92f09ed912635169087b07914b65775ab7ff`；队长未提交的 R0/验收修复仍缺。
任务在 `work/3331083641-pc-replay-20261003` 继续，通过 PR #3 交付。

## 修改与证据

增加六种连续输入组合：丢失/重获、贴边、小目标/噪点、600ms接收空窗、
会话重启、配置切换。复用已有11种独立像素预期，新增5项行为/负例测试，
包含错误场景名、时间倒退、重开旧会话、错误版本和拒绝覆盖文件。
命令行默认生成11场景保持兼容，`--sequence` 为可选项；现有JSONL字段未改。
实际生成12个文件（两种默认模式），84条记录均经现有校验读取。
配置切换序列固定v1→v2，不受默认模式覆盖。

用户本次确认已与 ikkkkk19 约定当前JSONL作为软件输入，记录进格式说明。
没有发送串口数据、控制指令或改现有UDP/RTL，没有重复实现R0。
另补16项R0独立数学核对输入，等号/unknown需要队长冻结表后适配执行。

四种机构SKU的当天报价/截图沿用之前实际采集；晚间淘宝要求登录，未重新
读取淘宝价格。补官方DRI0043和Pololu#2133报价/截图，明确它们不是淘宝价。
DRI0043当前页面注明芯片TB67S109AFTG，不能套通用“TB6600”参数。
完整型号、尺寸/孔位、精度、接口、限位及LED配套仍有外部资料缺项。

## 实际执行

在干净本地克隆、关闭Git自动换行转换后检出提交
`49cfc5c04195abfc2f71aefe4b83809928b901f8`。运行前工作树为空，Python3.12.4。
测试临时文件使用D盘任务临时目录，验收输出在仓库外。

```powershell
python tools/run_pc_acceptance.py --require-r0 --output-dir <new-directory-outside-repository>
```

| 内部命令 | 实际结果 |
|---|---|
| python tools/check_repository.py | 退出0，仓库/链接/证据检查通过 |
| python -m unittest discover -s tests -v | 退出0，57项通过，15.721秒 |
| python -m src.pc.target_replay check --output pixel_comparison.json | 退出0，22组相符，board_verified=false |
| git diff --check | 退出0，无输出 |

总命令退出1，acceptance.json 的 passed=false，原因是指定了 `--require-r0`
而 `sim/reference/spatial_relations.py` 与 `tests/test_spatial_relations.py` 未取得，
状态 `NOT_TESTED_MISSING_SOURCE`。四项基础检查通过不代表R0整体验收通过。
测试数40+12+5=57，不能冒充队长93项独立复跑。

日志、输入/源文件SHA-256、命令、Git提交和工作树状态由工具实际保存；

| 干净检出文件 | 实际SHA-256 |
|---|---|
| data/fixtures/pc_replay_sequences.json | `0c8a6c85e18ec738ca81e36859ef8f3eb15d6d5e15ee19475e09f1c50ab89d9e` |
| src/pc/target_replay.py | `bc1f0dd5826b84953ddac85ab4f3a26d6b9f127c22eaebd62330bc5c441f58e9` |
| tests/test_target_replay.py | `842c8f963605f662de4a5eff4c1791d1c4abb679f1d6c4e9612467f647688de1` |

详见本地交付目录的 acceptance-task-completion-clean。行尾不同会改变原始
字节散列，来源核对需记录Git配置，不只对比散列而忽略换行。

## 板卡边界与下一步

本次补齐未操作JTAG或下载位流。前一轮v1显示恢复与10秒290帧实测见
[v1恢复记录](2026-10-03-v1-camera-restored.md)；不把这次57项离线通过升级为
滤波v2、R0、STM32或整机闭环板测。控制参数、串口封包和采购仍未验收。

下一步依次取得队长完整源码/冻结边界、原型日志约定、商家BOM和LED规格。
先审查已有实现和测试覆盖再补缺项，复跑版本、命令、差异全部留档。
当前任务入口：[进度与交付](../../docs/3331083641_task_delivery_2026-10-03.md)。
