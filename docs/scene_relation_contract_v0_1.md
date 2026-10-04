# 场景关系数据契约 v0.1（候选）

状态：候选契约；R0 只实现纯 Python 几何黄金参考及输入一致性校验，未实现关系 RTL、时间状态机、新传输、PS、查询 UI 或模型适配。基于当前 RGB565 包围框/统计契约 [R4] 扩展；具体执行与测试结果单独记录，不从本文推断板测通过。

## 1. 坐标与对象身份

图像为 640×480 RGB565；原点左上，x 向右、y 向下。`bbox=[xmin,ymin,xmax,ymax]` 两端包含，合法有效框满足 `0<=xmin<=xmax<width` 和 `0<=ymin<=ymax<height`。

对象 `marker_id` 首版是颜色槽位 `0/1/2`，不是通过轨迹重识别得到的 ID。首版每色最多一个真实标志；颜色标签与阈值仍须实拍标定。配置 ROI 使用保留 ID `3` 且 `source=configured_roi`，颜色统计使用 `source=pl_color_stats`。同色多区域输入不在保证范围内，不能默称为两个目标。

`centroid_mask_floor=[sum_x//count,sum_y//count]` 是掩膜质心。
`bbox_center_2x=[xmin+xmax,ymin+ymax]` 是二倍包围框中心。
关系引擎使用后者；显示或记录前者时必须明确字段名。

## 2. 帧与配置绑定

一次稳定快照含 `session_id, measurement_frame_seq, config_epoch, width, height, mask_version, frame_complete`。所有对象与边引用同一快照。`session_id` 为非空会话标识；`measurement_frame_seq` 为无符号 32 位整数，`config_epoch` 为非负整数；现有相机链路为 `width=640, height=480`，已知 `mask_version` 为 `1/2`。纯 Python 参考允许显式正整数尺寸以验证数学边界，不修改相机模式或宣称其他硬件分辨率已支持。`session_id` 不假装现有硬件已发送该字段；在新协议实施前由采集端明确维护。设备重启/重新连接需清空缓存与时间状态。

现有传输的视频序号和统计序号不同：视频 N 的首包带 N−1 统计；只能按 `measurement_frame_seq` 配对原始帧。PC 本地 `frame_index` 不是硬件序号。接收时间不是相机曝光时间。[R4]

设备统计帧号缺失、重复、超出配对窗口、配置不一致或序号复位均不得静默对应最近图像。32 位序号回绕策略在实现中单独测试，不能简单使用有符号大小比较。

R0 对帧号只作标签相等比较，允许 uint32 的 `0`，不实现先后排序、接收缓存、回绕或重启检测。当前 UDP 解析器仍将初始 `result_seq=0` 解释为没有前一帧测量；该传输约定不因参考类型接受零标签而改变。R0 的两个快照一致性校验不能代替完整同帧配对或时间状态机。

## 3. 测量合法性

`frame_complete=false` 时整图不可用于确定性查询。
颜色统计 `count=0` 时对象 `measurement_valid=false`，bbox/centroid 为 null。有效颜色统计要求正整数 `count` 和合法 bbox，且 `count<=area_bbox`；包围框面积不等于掩膜 count。面积未达到标定的最小门槛时也可 invalid，但须保留 `invalid_reason`。R0 不自行选择实拍面积门槛，也不重新检查像素颜色。

配置 ROI 独立于颜色像素统计：启用时 `measurement_valid=true`、bbox 合法、`count=null`、`invalid_reason=null`；禁用时 `measurement_valid=false`、bbox 为 null、`count=null`，附非空 `invalid_reason`。ROI 的配置框可以包含零个颜色像素，仍是合法 ROI；禁止将 `count>0` 套到 ROI。

无效颜色对象可保留本帧原始非负 count（如面积过小），但 bbox 为 null，附非空 `invalid_reason`，不保留上一帧的有效坐标。`measurement_valid` 和 `frame_complete` 必须为布尔值；布尔值不作为坐标、count、序号或阈值整数接受。

R0 区分两种失败：非法类型/形状、倒置或越界 bbox、未知掩膜版本、非法 ID/source、无效字段组合、非法阈值及错误谓词用途抛 `ValueError`；合法对象缺测、禁用 ROI、不完整帧或两个快照不一致返回 `unknown` 并保留原因。两个合法对象的会话、测量序号、配置 epoch、尺寸或掩膜版本不一致时，不能生成 true/false 边；关系配置 epoch 与快照不一致同样为 `unknown`。错误数据不通过裁剪、强制类型转换或借用上一帧来修补。

字段合法不代表语义识别正确。`fill_ratio`、面积和接边等是质量指标，不是学习模型置信度。原始字段与平滑显示字段分开保存。

## 4. 空间关系

首版谓词：`left_of/right_of/above/below/bbox_overlap/bbox_within_roi/near_2d`。
`left_of(A,B)` 表示 A 的 bbox 中心在 B 左侧；`above(A,B)` 表示 A 中心 y 更小。关系是图像二维定义，不支持由此推断真实远近、遮挡前后或物体实体接触。

每条 raw edge 含 `subject_id, predicate, object_id, truth, evidence`。
`truth` 为 `true/false/unknown`。端点缺测、快照不完整或阈值模糊区依约定返回 unknown。不得将 unknown 写成 false。

时间管理另行记录 `pending/confirmed/stale/lost`，不能用 `confirmed` 覆盖当前原始 invalid。任何当前无效、过期关系都不得驱动高亮选择。

相反关系不得同时确认为真；左/上可以同时为真。禁止通过“每目标对只留一条边”删掉另一条真实几何关系。自关系默认不枚举。

### R0 原始关系边界表

本次源码交付冻结版本：`r0-boundaries/2026-10-03`。以下原始数学边界与 9 月 30 日已检查实现一致，本次不修改比较符号、阈值语义或测试期望。变更须在独立提交中同时说明契约版本及边界测试；冻结不表示颜色阈值已实拍标定，也不冻结后续时间/传输/模型功能。

下表仅在两个对象当前有效、帧完整、快照相同且配置 epoch 匹配时判定；否则按上一节返回 `unknown`。全部阈值由调用方显式提供，属于候选实验配置，未声称实拍标定。判定不读取上一帧，不实现时间迟滞。

方向阈值 `margin` 为非负整数像素。对 `left_of/above`，`d` 分别是 `cx2(B)-cx2(A)`、`cy2(B)-cy2(A)`；`right_of/below` 取相应差值的负号。令 `I` 为包含式框交集面积、`U=areaA+areaB-I`，IoU 的低/高阈值为 `p_false/q_false`、`p_true/q_true`；令 `D=dx2*dx2+dy2*dy2`，距离半径 `r_true/r_false` 为非负整数像素。

| 谓词 | true | false | unknown 与等号 |
|---|---|---|---|
| `left_of/right_of/above/below` | `d>2*margin` | `d<=0` | `0<d<=2*margin`；正阈值等号为 unknown，同中心为 false；`margin=0` 时无模糊区 |
| `bbox_overlap` | `I>0` 且 `q_true*I>=p_true*U` | `I=0` 优先；或未达到 true 且 `q_false*I<p_false*U` | 其余；低阈值等号 unknown，高阈值等号 true；阈值相等时该等号 true，无模糊区 |
| `bbox_within_roi` | A 的四条 bbox 边均在 B 的配置 ROI 内，允许边相等 | A 任一边超出 ROI | 只有缺测/快照等前置失效为 unknown，无几何模糊区 |
| `near_2d` | `D<=4*r_true*r_true` | `D>4*r_false*r_false` | 中间范围；内半径等号 true，外半径等号 unknown；两半径相等时该等号 true，无模糊区 |

IoU 阈值各自满足 `0<=p<=q`、`q>0`，且交叉比较满足 `p_false*q_true<=p_true*q_false`；允许两阈值相等及零阈值。零交集始终 false，包括两阈值均为零时；相邻但不共享像素的包含式框交集为零，共享一个边界像素的框交集可为正。半径满足 `0<=r_true<=r_false`。

方向、距离和交叠支持颜色对象或启用 ROI。`bbox_within_roi(A,B)` 的 A 必须是颜色对象，B 必须为 `configured_roi`；错误用途抛 `ValueError`。R0 的单关系 API 对相同 ID 的端点抛 `ValueError`，不实现整图或对象对枚举；后续非自身有序对枚举须保留每对所有适用谓词，不通过挑选单条边来处理左上等复合方向。

原始边 `source=geometry_rule`，输出 `reason`、`config` 与整数 `evidence`（方向差、面积、交集/并集、二倍中心平方距离），阈值保留在 `config`，以便独立核对。合法输入但无法评估时 evidence 为 null；两个端点的完整 Snapshot 相同时保留该 snapshot，不同时为 null。`unknown` 的原因可为快照/配置不一致、帧不完整、端点无效或 `threshold_band`。

R0 入口为 `sim/reference/spatial_relations.py` 的 `evaluate(predicate, subject, object, config)`，显式数据类型为 `BBox`、`Snapshot`、`Region`、`Ratio`、`RelationConfig`、`GeometryEvidence` 和 `RelationResult`；三值类型为 `Truth`。配置字段为 `config_epoch`、`direction_margin_px`、`iou_false`、`iou_true`、`near_true_radius_px`、`near_false_radius_px`，其中 IoU 使用 `Ratio(numerator, denominator)`。仅接受调用方提供的测量快照，不直接连接相机 UDP、显示平滑或未来模型输出；参考中没有颜色阈值、最小面积阈值、质心计算或配置生效管理。

## 5. 纯整数运算

面积使用包含式宽高 `xmax-xmin+1`、`ymax-ymin+1`。
比较 p/q 交并比使用交叉乘法，限制 `0<=p<=q`、`q>0` 并计算乘法位宽。
二维距离使用二倍中心平方距离 `dx2*dx2+dy2*dy2`；像素半径 r 对应 `4*r*r`。

首版所有阈值属于 `config_epoch`，仅帧边界切换。未来 PS/PC 参考与 PL 核须采用同一舍入、比较符号和有效状态；R0 只实现 PC/Python 参考，不宣称已有 PL 一致性结果。随机测试之外必须有手工构造的阈值等号测试。

## 6. 时间与选择

本节是后续任务契约，R0 不实现时间状态机或选择界面。原始空间模糊区与进入/保持迟滞不同，不能把上一帧的 confirmed 当作本帧 raw true。

三次确认要求测量序号连续、配置不变、对象有效。缺帧不是否定证据，也不计入连续命中。失效立即停止当前选择，历史图最多按可配置 TTL 显示为 stale。

查询“参考标志左侧最近对象”只在参考标志和候选均当前有效时执行。无候选返回 `no_match`；等距离或在预定差值容差内的候选返回 `ambiguous`；端点失效返回 `invalid_input`。不在并列时暗用颜色 ID 选一个。

## 7. 模型适配

模型输入必须绑定同帧 image+boxes。模型框索引到 marker_id 的映射随该次请求保存，禁止拿新一帧目标排列解释旧模型索引。

包含式像素框到连续边界框的候选变换为 `[xmin,ymin,xmax+1,ymax+1]`；适配器须依据所选上游 API 验证并测试边界，不直接把规范文字当成已验证实现。缩放/裁剪由唯一的适配层管理并记 `image_transform_id`，不可重复缩放。

模型建议记录 `source=relateanything, model_revision, score, inference_ms`；确定性几何边记录 `source=geometry_rule`。二者的分数/真假语义不同，不合并成“总置信度”。历史模型结果仅允许显示在其对应历史帧，过期输出不影响当前查询。

## 8. 示例（虚构数据，仅用于说明契约）

```json
{
  "schema_version": "scene-relation/0.1",
  "session_id": "example-session",
  "measurement_frame_seq": 100,
  "config_epoch": 1,
  "width": 640,
  "height": 480,
  "mask_version": 2,
  "frame_complete": true,
  "manager_backend": "pc_reference",
  "objects": [
    {"marker_id": 0, "label": "red", "source": "pl_color_stats", "measurement_valid": true, "bbox": [80, 120, 159, 199], "bbox_center_2x": [239, 319]},
    {"marker_id": 2, "label": "blue", "source": "pl_color_stats", "measurement_valid": true, "bbox": [300, 120, 379, 199], "bbox_center_2x": [679, 319]}
  ],
  "edges": [
    {"subject_id": 0, "predicate": "left_of", "object_id": 2, "truth": "true", "source": "geometry_rule", "evidence": {"delta_cx2": 440}}
  ]
}
```

实际统计传输还需 count、sum_x、sum_y 等字段。此 JSON 是应用层候选，不是已经冻结的 UDP 二进制布局，也不是模型或板测输出。

## 9. 传输兼容

保留当前 8 字节头和 40 字节扩展的解码测试；当前字节 17 的 1/2 属于已有掩膜语义，不能直接覆写。[R4] 新布局须区分传输格式版本、场景 schema 版本和各算法版本。先检查真实包生成器与最大包长，再冻结二进制偏移；默认不改造所有视频行包。

新格式检查 magic/头长/版本/目标数/序号/范围；未知格式明确拒绝。不声明当前协议能发现所有静默行重复或乱序。

## 10. 必需测试矩阵

基本几何：四方向、斜对角、同中心、接边、包含、交叠、无交叠、单像素、全帧。
整数边界：最大坐标、阈值等号、面积乘法上界、差值符号、二倍中心半像素。
对象有效性：空色、面积过小、参考缺失、同色多区域限制、多色阈值冲突。
时间：连续确认、单帧缺测、长时间缺测、缺序号、旧结果晚到、重启、回绕、配置切换。
协议：旧格式、滤波版本1/2、新格式长度不足、非法坐标、未知版本。
模型：框顺序改变、帧不匹配、过期、超时、空输出、框坐标边界。
跨时钟：快照更新与读取交错、复位、参数生效时刻、过载。

<!-- Version-pinned source links -->
[R4]: https://github.com/logic202407-cmyk/zynq-vision-lab/blob/a7423ab96f25dbda3e58fd6439b8b8bcc3b416cd/src/interface_contract.md
