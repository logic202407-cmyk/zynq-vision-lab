# 离线核对已保存的 100 组场景结果

`tools/check_board_scene.py` 读取现有 `src.pc.pl_compare` 输出。
它不接收视频、不发送 START/STOP，也不改变 RTL、UDP 或冻结参考。
阈值固定为 [实验计划 r1](fpga_experiment_plan_2026-10-04.md) 中的 P0/N0 指标。
3 米长方形布置另见 [采集前条件补充](fpga_experiment_condition_3m_2026-10-04.md)。
每次只处理完整的 100 组窗口，不截取有效子集、不合并不同轮次。

P0 要求至少 95/100 有效，并至少 95/100 **同时**满足有效、floored
质心在人工 ROI 的包含式边界内、bbox 与 ROI 的包含式 IoU ≥ 0.5。
无效组计失败。IoU 临界值用整数交集/并集判断，单像素框仍有正面积。
N0 要求 100/100 valid=false、count/sums=0、bbox/centroid=null。
既有精确比较门槛必须同时通过，逐组检查记录与汇总的版本、序号及相符标志。

P0 的人工 ROI JSON 在采集前另存私有，示例结构如下；坐标和输入 hash
须来自真实无叠加 PNG/原始侧车，不能将本示例用作实拍预期：

```json
{
  "schema": "manual-paper-roi/1",
  "origin": "manual_unmodified_png",
  "width": 640,
  "height": 480,
  "bbox": [100, 100, 149, 149],
  "input_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "frozen_at_utc": "2026-10-04T08:00:00+00:00",
  "plan_sha256": "3301785371b6da99926aa1468c0217bbe2baa50c1e7f593413dcb98e7a084b6a"
}
```

记录额外保存标注人、操作者确认、条件文档 SHA、距离/尺寸、照明未知项。
`frozen_at_utc` 必须早于比较窗口的 `started_at_utc`，时间均须带时区。
工具只核对声明的来源/时间/hash格式，不鉴定人工标注真实性、源图内容或物理布置；
原始 PNG、RGB565、侧车、人工确认与冻结动作日志仍需独立留证。

用真实比较命令退出码执行，输出必须为新文件：

```text
python tools/check_board_scene.py --exact <private-exact.json> --capture-exit-code 0 --scene P0 --mask-version 1 --roi <private-roi.json> --output <new-private-scene.json>
python tools/check_board_scene.py --exact <private-exact.json> --capture-exit-code 0 --scene N0 --mask-version 2 --output <new-private-scene.json>
```

工具核对比较报告记录的三份源码 hash 与当前本地文件。
退出 0 表示本离线核对通过，退出 1 表示门槛失败，退出 2 表示输入/文件错误。
缺组、旧输出或 hash 不符不会创建成功结果；失败 stderr 与原报告也应保留。
报告含全部 100 组场景判定和缺测计数，另记录输入报告、ROI 文件和核对器 SHA。
`passed` 仅涵盖这份报告的精确/声明场景指标，不代表物理条件已核验、
30 秒稳定性、三轮实验、v2 实际加载、干扰效果或另一成员复现。
