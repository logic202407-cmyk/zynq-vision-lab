# 帧记录比较器

用帧序号关联硬件结果与独立参考，逐项检查 `count`、`sum_x`、`sum_y`、`bbox`、`valid`。序号允许乱序，但不允许重复；任何缺帧、多余帧或字段差异都会失败。

从仓库根目录运行：

```bash
python tools/compare_frame_records.py --actual skill/frame-result-check/examples/actual.json --reference skill/frame-result-check/examples/reference.json
python -m unittest discover -s tests -p test_frame_records.py -v
```

第一条命令应输出 `passed: true` 和 `matched_frames: 2`。退出码 0 表示完全一致，1 表示结果差异，2 表示输入结构或文件错误。样例是合成数据，不是板测记录。

将另一项目的输出转成相同 JSON 数组即可复用。`bbox` 使用 `[min_x,min_y,max_x,max_y]` 或 `null`，统计量为非负整数，`valid` 为布尔值。两侧必须采用相同分辨率、坐标定义、像素规则、帧序号及有效性语义。

失效条件：两侧共用错误实现、序号跨复位重用、前处理不一致、参考数据缺少独立性、将合成输入冒充板测。此工具不测量延迟、漏检率或控制稳定性。

经验来源：项目曾出现参考计算阻塞 UDP 接收、统计字段与画面跨帧错配的风险，因而将采集与比较分开，并要求以帧序号核对。[原案例](../../report/ai_collaboration/2026-09-27-pl-red-corrections.md)。
