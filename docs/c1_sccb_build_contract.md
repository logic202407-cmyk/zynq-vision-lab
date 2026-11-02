# SCCB 生成时钟的构建合同

本轮以 `128740392376d304b74d00c40cfe126a896b6366` 为基线，复用此前完整厂商工程的时钟实验，将生成时钟纳入正常的只观测候选构建。没有修改厂商 RTL、UART、STM32 控制器、PWM 或任一物理管脚。

## 防止错误复用

`build/build_c1_observation_board.tcl` 在创建工程前调用 `tools/c1_sccb_contract.py`：

- 私有 `i2c_dri.v` 必须与已审查 SHA-256 完全一致；源码不公开，指纹在合同文件中保留。
- 顶层必须只有一个已审查的 `u_i2c_dri` 实例，参数引用、时钟和输出连接必须匹配。
- `CLK_FREQ=50_000_000`、`I2C_FREQ=250_000`，不接受未审查的参数、接线或 defparam 覆盖。
- 任何校验失败都以非零状态终止，不产生时钟合同，不继续创建新工程。

成功后保存 `clock-contract.json`，包括两份私有输入 SHA-256、分频关系和 `measured=false`。执行使用 Python `-I` 隔离 Vivado 的内置 Python 环境。默认解释器为 `D:/Python312/python.exe`；其他主机可设置进程内 `C1_PYTHON`，不修改系统设置。

## 约束与推导

已审查驱动先计算 `(CLK_FREQ/I2C_FREQ)>>2` 为 50，再以其半值计数，每 25 个父时钟边沿翻转一次。因此 driver 时钟周期为 50 个父周期，并不是 SCCB 位速率本身。

| 项目 | 原正常构建 | 新正常构建 |
| --- | --- | --- |
| SCCB driver 时钟 | 没有显式定义 | `c1_sccb_driver` |
| 周期 / 波形 | 未约束 | 1000 ns / `{0 500}`，来源于声明的父周期 |
| source | 未指定 | `u_i2c_dri/dri_clk_reg/C` |
| target | 未指定 | `u_i2c_dri/dri_clk_reg/Q` |

完整约束等价于：

```tcl
create_generated_clock -name c1_sccb_driver -source [get_pins u_i2c_dri/dri_clk_reg/C] -divide_by 50 [get_pins u_i2c_dri/dri_clk_reg/Q]
```

实现位于 `build/c1_sccb_clock.tcl`。它拒绝错误器件、缺失/歧义管脚、非 20 ns 声明父周期，以及已经存在的目标时钟，不覆盖其他约束。约束在综合后写入持久 timing XDC，再进行完整布局布线；最终重新输出 clocks 和 verbose check_timing。

这不是频率或相位实测。外部复位可能影响分频启动相位，仍须复核相关复位与跨域路径；不能根据这条约束宣称实物时钟、电气时序或 MTBF 已验证。没有添加 false path、全异步时钟组或伪造外部 I/O delay。

命令依据：[AMD UG835 2024.2 create_generated_clock](https://docs.amd.com/r/2024.2-English/ug835-vivado-tcl-commands/create_generated_clock)。

## 离线复现与限制

```text
python -m unittest discover -s tests -p test_sccb_contract.py -v
python tools/check_c1_sccb.py --vendor <prepared-private-vendor> --stage <fresh-D-drive-stage>
```

第二条命令复制两份必要私有源码到新目录，执行两个拒绝测试，并用真实私有驱动运行 XSim 波形断言。失败的首轮日志必须保留；驱动源码和波形产物均不得上传。使用已准备好的独立私有目录，按原说明运行完整 `build/build_c1_observation_board.tcl`；不会生成位流或调用硬件接口。

运行结果见[完整构建验收记录](../report/experiments/2026-11-02-sccb-clock-build.md)。这一步只解决缺失的生成时钟覆盖，厂商 FIFO 的两项 CDC Critical、真实 I/O 延迟及跨复位 epoch 提供者仍是独立阻塞项。
