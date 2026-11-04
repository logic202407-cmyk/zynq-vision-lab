# red_static_steady

状态：historical single red static steady test, later stopped。这是历史源码快照，不是当前板上固件。

接线及红1/黄2/蓝3身份以[最终接线表](../../../../../board/skystar_f407/three_gimbal_wiring.md)为准；历史注释不覆盖最新映射。当前运行的是 `laser123_static` 静止测试版。

使用 `tools/build_bench_profile.py --profile red_static_steady --stage <外部生成目录>` 仅构建，不自动烧录、复位或使能。对应历史测试源码保存在 `tests/`（如有），本次是否重跑见[完整进度清单](../../../../../report/evidence/full-progress-20261104/manifest.json)。
