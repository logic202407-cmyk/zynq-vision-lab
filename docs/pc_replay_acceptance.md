# 电脑端样例、回放和独立验收

日期：2026-10-03。负责人：`3331083641-prog`。

本轮任务是电脑端输入与核对。队长已说明 R0 几何参考和验收修复已在另一台
电脑完成，93 项测试通过但尚未提交。本轮基线 `main@0daf92f09ed912635169087b07914b65775ab7ff`
没有这批源码；只复核实际可取得的代码，不重复实现 R0，不把本机检查当成
队长 93 项测试的独立复跑。最新用户说明作为当前硬件工作安排，历史恢复
日志不证明本次开发板已恢复。

新增工具：[target_replay.py](../src/pc/target_replay.py)，
样例：[pc_target_cases.json](../data/fixtures/pc_target_cases.json)，
测试：[test_target_replay.py](../tests/test_target_replay.py)，
格式提案：[pc_target_format_candidate.md](pc_target_format_candidate.md)。

## 输入、预期和判定

全部使用纯红 `0xf800` 和黑色 `0x0000`，RGB565 大端、640×480。
原始阈值和五票滤波逐场景分别核对 valid、count、sum_x、sum_y、包含式
bbox 和向下取整质心。明确的 expected 常量来自矩形计数/对称性与人工
枚举窗口，不调用被测参考生成 expected。

| 场景 | 输入 | 原始 count / 滤波 count | 判定重点 |
|---|---|---|---|
| 无目标 | 全黑 | 0 / 0 | 坐标必须 null，不保留上一帧 |
| 居中 | (318,238)—(322,242) 的 5×5 色块 | 25 / 21 | 四角各四票被删，中心对称 |
| 左贴边 | x=0…4,y=238…242 | 25 / 18 | x=0 不输出；远侧两角删除 |
| 右贴边 | x=635…639,y=238…242 | 25 / 18 | 左贴边镜像，含右边界 |
| 上贴边 | x=318…322,y=0…4 | 25 / 18 | y=0 不输出 |
| 下贴边 | x=318…322,y=475…479 | 25 / 18 | 上贴边镜像 |
| 单像素 | (320,240) | 1 / 0 | 小目标滤除是算法定义，不是故障 |
| 2×2 小块 | (320,240)—(321,241) | 4 / 0 | 任意窗口最多四票 |
| 色块加远处噪点 | 居中色块加 (30,20) | 26 / 21 | 原始 box 被拉偏；滤波应与居中色块相同 |
| 五像素十字 | 中心及四邻居 | 5 / 1 | 恰好五票留下中心，四票不留下 |
| 色块中心孔洞 | 5×5 删除中心 | 24 / 21 | 中心被填回；去噪不是只删像素 |

本轮有 11 场景×2 模式，共 22 组像素对照。只使用同一份输入字节比较，
不把显示中值滤波加入精确 expected。已有颜色阈值边界测试继续复跑，
人工降低阈值去迎合暗红纸不属于此任务。

## 运行命令

在仓库根目录执行，以下输出目录位于仓库外。文件已存在时生成器拒绝覆盖，
换一个输出名即可；每次验收使用新的目录。

```powershell
python -m src.pc.target_replay generate --mask-version 1 --output D:\嵌入式比赛资料\task_outputs\replay-v1.jsonl
python -m src.pc.target_replay generate --mask-version 2 --output D:\嵌入式比赛资料\task_outputs\replay-v2.jsonl
python -m src.pc.target_replay replay --input D:\嵌入式比赛资料\task_outputs\replay-v2.jsonl
python -m src.pc.target_replay replay --input D:\嵌入式比赛资料\task_outputs\replay-v2.jsonl --realtime
python tools/run_pc_acceptance.py --output-dir D:\嵌入式比赛资料\task_outputs\acceptance-new-run
```

默认回放尽快写 stdout，`--realtime` 仅按合成间隔等待，不保证实时调度；
33ms 不表示相机实测帧率。可以把 stdout 重定向到文件供原型离线读取，
尚未连接 STM32 串口。生成器不输出运动命令。

验收目录包含每条命令的真实日志、退出码、日志散列、源文件散列、提交、
工作树状态、Python 版本和像素对照结果。工作树不干净时不能只凭 HEAD
声明源码一致，使用 `source_sha256` 复核。

## 队长新增代码同步后的复跑

先取得队长提交/分支和涉及文件的 SHA-256，特别是 R0、pl_compare、
vendor_udp、red_mask 与新增测试。不要仅复制一个 .py 文件或根据“93”猜版本。
确认原有工作已保存，按 PR 审查后的提交进行集成；不 reset/clean 或覆盖文件。

```powershell
git fetch origin
git status --short --branch
git log -5 --oneline
python tools/run_pc_acceptance.py --require-r0 --output-dir D:\嵌入式比赛资料\task_outputs\acceptance-after-team-sync
```

`--require-r0` 缺少 R0 源码或测试时最终退出 1，记录 NOT_TESTED，不跳过后
声称全通过。文件存在只说明可以审查和执行，不代表与队长源码相同；核对
实际散列、检查日志与测试发现范围。后续总测试数可能因为本轮样例增加而
超过 93，不通过删测试来凑数。

R0 同步后使用它已经冻结的关系 API/边界表，补独立适配用例：左/右、上/下、
同中心、斜对角、交集为零、单像素框、包含 ROI、距离等号、缺测、帧号/
配置不一致。方向、面积 +1 和距离平方的人工计算作为预期依据；真实参数
和 unknown 模糊区以冻结契约为准，本轮不另建关系判定器。

## 硬件与实拍后续

本轮未运行 Vivado/JTAG、未下载位流、未改网络设置或 UDP，未板测。
电脑只读状态看到 USB Serial Converter 为 OK；不能据此认定下载器型号或
JTAG 成功。有线网口为 Disconnected，UDP 接收条件未齐。

真实板测由队长统一协调，先确认 GE/PL 网线、电源、相机、下载器和正确
位流版本，再由已同步的验收工具对有目标/无目标做同帧对照。无目标的
全零一致不能代替红纸检出验收。

实拍需独立采集静止/运动/光照/相似背景/遮挡素材，记录失败和丢帧。
合成小目标不等同于 1–2m 距离的 5–10cm 实物目标；像素尺寸由相机视场
与拍摄实测决定。当前不报告角度定位精度、距离误差或抗干扰增益。
