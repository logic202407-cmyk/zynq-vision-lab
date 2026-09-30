# 场景关系数据契约 v0.1（候选）

状态：设计提案，未实现；基于当前 RGB565 包围框/统计契约 [R4] 扩展。

## 1. 坐标与对象身份

图像为 640×480 RGB565；原点左上，x 向右、y 向下。`bbox=[xmin,ymin,xmax,ymax]` 两端包含，合法有效框满足 `0<=xmin<=xmax<width` 和 `0<=ymin<=ymax<height`。

对象 `marker_id` 首版是标定颜色槽位，不是通过轨迹重识别得到的 ID。首版每色最多一个真实标志。配置 ROI 使用保留 ID 且 `source=configured_roi`。同色多区域输入不在保证范围内，不能默称为两个目标。

`centroid_mask_floor=[sum_x//count,sum_y//count]` 是掩膜质心。
`bbox_center_2x=[xmin+xmax,ymin+ymax]` 是二倍包围框中心。
关系引擎使用后者；显示或记录前者时必须明确字段名。

## 2. 帧与配置绑定

一次稳定快照含 `session_id, measurement_frame_seq, config_epoch, width, height, mask_version`。所有对象与边引用同一快照。`session_id` 是本次采集会话标识，不假装现有硬件已发送该字段；在新协议实施前由采集端明确维护。设备重启/重新连接需清空缓存与时间状态。

现有传输的视频序号和统计序号不同：视频 N 的首包带 N−1 统计；只能按 `measurement_frame_seq` 配对原始帧。PC 本地 `frame_index` 不是硬件序号。接收时间不是相机曝光时间。[R4]

设备统计帧号缺失、重复、超出配对窗口、配置不一致或序号复位均不得静默对应最近图像。32 位序号回绕策略在实现中单独测试，不能简单使用有符号大小比较。

## 3. 测量合法性

`frame_complete=false` 时整图不可用于确定性查询。
`count=0` 时对象 `measurement_valid=false`，bbox/centroid 为 null。
面积未达到标定的最小门槛时也可 invalid，但须保留 `invalid_reason`。

字段合法不代表语义识别正确。`fill_ratio`、面积和接边等是质量指标，不是学习模型置信度。原始字段与平滑显示字段分开保存。

## 4. 空间关系

首版谓词：`left_of/right_of/above/below/bbox_overlap/bbox_within_roi/near_2d`。
`left_of(A,B)` 表示 A 的 bbox 中心在 B 左侧；`above(A,B)` 表示 A 中心 y 更小。关系是图像二维定义，不支持由此推断真实远近、遮挡前后或物体实体接触。

每条 raw edge 含 `subject_id, predicate, object_id, truth, evidence`。
`truth` 为 `true/false/unknown`。端点缺测、快照不完整或阈值模糊区依约定返回 unknown。不得将 unknown 写成 false。

时间管理另行记录 `pending/confirmed/stale/lost`，不能用 `confirmed` 覆盖当前原始 invalid。任何当前无效、过期关系都不得驱动高亮选择。

相反关系不得同时确认为真；左/上可以同时为真。禁止通过“每目标对只留一条边”删掉另一条真实几何关系。自关系默认不枚举。

## 5. 纯整数运算

面积使用包含式宽高 `xmax-xmin+1`、`ymax-ymin+1`。
比较 p/q 交并比使用交叉乘法，限制 `0<=p<=q`、`q>0` 并计算乘法位宽。
二维距离使用二倍中心平方距离 `dx2*dx2+dy2*dy2`；像素半径 r 对应 `4*r*r`。

首版所有阈值属于 `config_epoch`，仅帧边界切换。PS/PC 参考与 PL 核的舍入、比较符号和有效状态完全一致。随机测试要包含恰好等于阈值的情况。

## 6. 时间与选择

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
