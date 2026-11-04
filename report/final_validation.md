# 最终交付检查

本次检查针对最终源码整理与交付内容，不连接或操作开发板。

| 检查 | 结果 |
|---|---|
| 仓库结构、相对链接、证据账本 | 通过 |
| Python 全量回归 | 124 项通过 |
| 三云台引脚与资源元数据 | 通过 |
| GCC 主机注册表回归 | C1_REGISTRY_PASS |
| 帧记录 Skill 正例 | 2 组一致，退出码 0 |
| 帧记录 Skill 坐标和错误负例 | 返回字段差异，退出码 1 |

Python 命令为 `python tools/check_repository.py`、`python -m unittest discover -s tests -v`、`python tools/check_skystar_wiring.py`。Skill 命令和输入见 [使用说明](../skill/frame-result-check/README.md)。GCC 使用 `-std=c99 -Wall -Wextra -Werror -O2` 编译 `sim/c1/registry_checks.c` 与当前小写 user 路径下的相关源文件，覆盖隔离、象限、缺测、边界、超时和六路资源表。

报告沿用已检查的 v11 文档，海报沿用已检查的中英文 v03 文件；仅以统一英文名称打包，不重新改写内容。下载后的附件以 Release 中 `SHA256SUMS.txt` 校验。

本次未重新执行 Vivado 全工程构建、STM32 交叉编译、位流下载或板级测试；已有硬件结论和各自配置见 [结果索引](../docs/results.md)。历史记录原样保留，源码路径整理不把历史构建自动标记为当前版本重新验收。
