# PC 离线 P0：连续性修复与冻结源码独立核对

负责人：3331083641-prog；执行日期2026-10-04。
来源：PR3 `7a638ac8a332f17951b45200fa3e13c41c7150d7`；队长交付快照
`55447b9ff1afac0e7d718be5873325c2d0cf6614`，算法冻结
`2a018c4b82e356dee3ca8cb000b520112b624c18`。
独立集成分支 `work/3331083641-p0-r0-20261004`。
正式干净检出、实际测试提交 `ed98fdccc7985eeca8f07edf71da8d3c818d40ee`。
未改main、现有RTL/UDP、五份冻结实现/测试或原有22组预期。

## 问题与修复

旧版read_records只与紧邻的同session记录比较。在内存只读复现中，
A(seq3,t66)→B(seq1,t0)→A(seq3,t0)被错误接受；生成器自己的旧会话检查
不能保护外部JSONL。

修复为文件内session占一个连续区段，切换离开即关闭；旧ID重入一律拒绝，
包括倒退、重复及看似连续的seq/time。新ID允许时间/序号重启；同session
连续uint32回绕及非倒退时间保留。CLI先整文件校验，失败前无stdout、无等待。
4项新增回归覆盖旧ID重入、多级历史、合法新会话/回绕和全文件原子拒绝。
旧11像素场景、六种回放序列继续复用，不改变字段或硬件协议。

## 独立预期和实际结果

手工G01-G16的输入、配置、几何事实、truth/reason预期写入
[fixture](../../data/fixtures/pc_r0_independent_cases.json)。
[适配工具](../../tools/check_pc_r0_cases.py)只构造冻结API对象和逐字段比对，
没有第二套几何判定器，也不调用evaluate生成expected。
16组共31检查通过；非法框2检查为ValueError，缺测/帧/配置/session不一致
为明确原因的unknown。G01-G13的面积、方向差、交/并集和平方距离亦精确核对。
临时mock把G01左关系错误返回false，独立常量成功检测差异；未修改冻结源码。

| 实际命令/阶段 | 数量及结果 |
|---|---|
| unittest discover -s tests -p test_target_replay.py -v | 21项通过 |
| unittest discover -s tests -p test_pc_r0_independent.py -v | 16项通过 |
| tools/check_pc_r0_cases.py --output <new-json> | 16组/31检查，相符 |
| unittest discover -s tests -p test_spatial_relations.py -v | 23项通过，含固定10000框对 |
| R0测试 -k test_10000_fixed_seed_pairs_against_fraction_oracle_and_invariants | 1项通过，seed=0x5CE0_2026，10000对 |
| unittest discover -s tests -p test_pl_compare.py -v | 30项通过 |
| 四项runbook负控制，各指定-k测试 | 每项1测试通过，内部错误CLI均返回1/passed=false |
| tools/run_pc_acceptance.py --require-r0 --output-dir <new-outside-dir> | 退出0，四项内部检查通过，22像素对照相符 |
| 内部unittest discover -s tests -v | **130项通过，无skip** |
| 内部仓库检查、git diff --check | 退出0 |

130=冻结93＋PC回放21＋独立几何16；不机械沿用原93作为新分支预期。
SOURCE_PRESENT_REVIEW_RESULTS只是存在性提示，本次另有独立16组及实际
R0/验收运行日志，不用该提示冒充核对完成。

8项附加控制保存完整预期/实际：外部A→B→A的倒退、重复、看似连续三种
CLI均退出2且stdout空，stderr为line 3 closed session_id；错误总和、版本、
空输入、STOP失败四种mock CLI均退出1；另有独立预期mutation敏感性检查。
四种精确失败原因为measurement_mismatch、mask_version_mismatch、
insufficient_pairs、stop_command_failed。mock接收器从未绑定真实UDP。

## 环境、时间和源码

Windows；Python3.12.4、Pillow12.2.0、Tk8.6，满足已有依赖范围；与队长/CI
补丁版本不同，未升级安装。ASCII干净检出用core.autocrlf=false保留源码字节，
不改全局Git/系统设置。五份冻结工作文件SHA-256与来源清单全部一致。

正式步骤UTC起止：`2026-10-04T01:51:01.366902+00:00` 至
`2026-10-04T01:52:02.001054+00:00`；附加控制另有每项UTC起止。
每一步保存命令、stdout/stderr、退出码、数量/skip、源码/输入和日志散列。
完整本地记录与公开脱敏摘要分开；不提交私有原图、设备标识、位流或凭据。
脱敏步骤/日志见 [JSON摘要](2026-10-04-pc-p0-validation.json) 和
[检查日志](2026-10-04-pc-p0-checks.txt)。

## 同输入完整帧仿真（独立于板测）

Vivado/xsim2024.2，SW Build5239630，原有runner未改；两个新build目录。
输入是F8 00重复307200次，640×480大端RGB565，614400字节，SHA-256
`82764ed06ca9dd3c9c9caaa0ade5318aa135abbd2f11cad36f9aa1e2aa944440`。
人工expected使用runbook表；同输入软件及RTL结果八项完全一致，各退出0并
输出FRAME_COMPARE_PASS，xsim日志无Fatal/error。

| 模式 | valid/count/sx/sy | inclusive bbox |
|---|---|---|
| v1 | 1 / 307200 / 98150400 / 73574400 | [0,0,639,479] |
| v2 | 1 / 304964 / 97435998 / 73038878 | [1,1,638,478] |

命令是现有tools/compare_red_frame_xsim.py：同一frame、不同--build-dir、
--vivado-bin，v2另加--spatial-filter。全红仿真不是实际纸靶或抗干扰板测。

## 未完成项与交付

[串口契约提案](../../docs/pc_stm32_serial_contract_draft_2026-10-04.md)覆盖封包/
校验/版本、有效零误差、session/帧/配置、坐标/误差中心、时钟、超时、
失联/恢复和输出日志。尚未经双方复核，未实现或运行串口适配；STM32日志
和实测由ikkkkk19提供，不能用本次PC通过代替。Z01-Z04列缺失样例与预期。
保持OV5640固定，单红槽位不能冒充已具备双对象观测，未定义实体控制行为。

四个原云台候选沿用10月3日报价/来源，未新增采购或对外消息；电气、移动
负载和限位交接ikkkkk19复核。完整商家BOM/图纸、LED规格仍未取得。
本次没有JTAG、网络改动、板测、执行器或光源动作。P1未运行，不提升
v2正例/抗干扰、STM32、PS–PL或整机闭环证据。
