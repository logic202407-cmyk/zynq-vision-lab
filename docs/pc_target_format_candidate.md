# 电脑端目标回放格式（已确认用于软件联测）

日期：2026-10-03。负责人：`3331083641-prog`。

2026-10-03，3331083641 在本次任务中明确回复：与 ikkkkk19 已确认使用当前
JSONL 提案。本文件记录该确认，范围是软件测试输入。保留
`target-replay/0.1-candidate` 字符串以兼容已经生成的文件，不新增字段。
这不是已约定的串口封包，不改变 RGB565/UDP、RTL、PS 或 OpenMV 八字节帧。
串口适配、校验、ACK、超时与字段映射仍需单独确认。本次工具只写文件和
stdout，不打开串口、不发送网络命令、不驱动电机。

依据：[现有像素契约](../src/interface_contract.md)、
[场景关系候选契约](scene_relation_contract_v0_1.md)、
[R0 任务](codex_scene_relation_r0.md)。R0 不在本轮重复实现。

## 数据定义

编码 UTF-8，每行一个完整 JSON 对象，以 LF 分隔。当前只接受固定 640×480、
红色槽位 `marker_id=0`，不声称支持三色检测或通用对象跟踪。

| 字段 | 软件联测含义 |
|---|---|
| `schema_version` | `target-replay/0.1-candidate`，与相机包版本分开 |
| `source` | 固定 `synthetic_expected`；禁止伪装 PL 或真实相机结果 |
| `session_id` | 软件回放会话；换会话清空接收端旧状态 |
| `case_id` | 对应测试场景，不是物体身份 |
| `measurement_frame_seq` | uint32 软件测量帧号；允许 0 和模 2^32 回绕 |
| `config_epoch` | 配置版本；当前 1/2 对应两种测试掩膜版本 |
| `timestamp_ms` | 合成的会话内相对毫秒时间，不是曝光、接收或 Unix 时间 |
| `timestamp_kind` | 固定 `synthetic_relative_ms` |
| `width,height` | 640,480；原点左上，x 向右，y 向下 |
| `mask_version` | 1：现有颜色阈值；2：排除外边圈的 3×3 五票多数滤波 |
| `frame_complete` | 当前这份测量对应的合成帧是否完整 |
| `target.marker_id` | 0：红色槽位，不是重识别 ID |
| `target.valid` | 有效测量；无效必须清空当前坐标 |
| `target.count,sum_x,sum_y` | 掩膜面积与坐标和，整数，不是 bbox 面积 |
| `target.bbox` | 两端包含 `[xmin,ymin,xmax,ymax]`，无效时 null |
| `target.centroid_mask_floor` | `[sum_x//count,sum_y//count]`，无效时 null |

例如中心 5×5 色块的阈值结果是 count=25、sum_x=8000、sum_y=6000、
bbox=[318,238,322,242]、掩膜质心=[320,240]；这是假数据。
关系引擎的二倍 bbox 中心为 [640,480]，与上述质心字段不能混用。

## 接收与错误行为

字段类型、坐标范围、count 上限、坐标和范围和质心一致性都要检查。
`valid=false` 时 count/sums 全零，bbox/centroid 为 null；
`frame_complete=false` 不得与有效目标组合。

同会话连续帧号按 uint32 回绕检查，重复、缺帧、乱序或时间倒退都拒绝。
错误显式报告行号；CLI 在完整验证输入后才输出，防止先发送半份非法回放。
新的会话可重新从 1 开始，不能把新旧会话数据混在同一个当前状态里。

配置变更会保留在记录中。回放工具不会实现或声称已经通过三帧确认、
pending/confirmed/stale/lost 状态机；这些由接收端后续单独实现和验证。

无目标场景表示完整帧未检出目标，不表示“数据包没来”；接收超时须通过
停止回放来测试，不能通过重发旧的有效坐标替代。真实采集未来仍须匹配
视频 N 的头部所携带的 N−1 测量，不使用本地序号冒充板端序号。

## 剩余接收端约定

1. 已确认以当前 JSONL 为测试输入；文件/stdin 如何送入具体 STM32 原型仍需联调。
2. 模拟误差以掩膜质心还是 bbox 中心为输入；确认前不隐式转换。
3. 接收超时、控制限幅和目标丢失行为的阈值，需独立配置。
4. 串口波特率、二进制布局、校验、反馈和重连策略；尚未冻结。
5. 合成相对时间与设备单调时间的映射；不同设备时钟不得直接相减。

后续确认继续记录。JSONL 确认不等于串口、真实 PS–PL 接口或整机闭环通过。
