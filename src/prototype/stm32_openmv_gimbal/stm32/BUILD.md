# STM32 P0 构建和依赖

基线为 PR1 的 `d96bc149bc25f0572350c47ed031c0922ec265ad`。
应用控制、解析、命令、队列和驱动支持源码在 `User/`；PID 源/头保持基线字节。
OLED 和 Delay 不参与本 P0 构建：它们不是控制/模拟验证的必要依赖。
毫秒时钟仅由 SysTick_Handler 维护，不调用会重配 SysTick 的旧延时模块。

## 依赖人工准备

1. 从 [ST 官方 STSW-STM32054](https://www.st.com/en/embedded-software/stsw-stm32054.html)
   获取 STM32F10x Standard Peripheral Library V3.5.0，阅读下载包内的原始许可/EULA。
   CMSIS Cortex-M3 V1.30 是该旧依赖集的配套版本；不能用本机安装的 CMSIS 5.0.1 替代。
2. 将 `Libraries/CMSIS/CM3/CoreSupport` 的 `core_cm3.c/.h`，
   `Libraries/CMSIS/CM3/DeviceSupport/ST/STM32F10x` 的设备头、system源/头，
   及其 `startup/arm/startup_stm32f10x_md.s` 放到仓库 `private/stm32-deps/Start/`。
3. 将 `Libraries/STM32F10x_StdPeriph_Driver` 中 misc、gpio、rcc、tim、usart 的
   五对 Src/Inc 文件放到 `private/stm32-deps/Library/`。
   完整16个文件和本次实际字节见 [dependencies.sha256.json](dependencies.sha256.json)。
4. 获取并合法使用 [Keil MDK/Arm Compiler](https://www.keil.com/download/product/)。
   本次实测 MDK Plus 5.24、ARM Compiler 5.06 update5 build528。
   Keil工程声明 STM32F1xx_DFP 2.2.0；命令行构建直接使用上述依赖，不要求调用包管理器。

本次实际依赖取自现有本地工程，头部版本为SPL3.5.0/CMSIS1.30，
没有取得原始下载ZIP及完整EULA的额外证明。哈希固定的是实际使用文件，
不能据此保证任意同名下载包字节一致；匹配失败会停止，不修改清单迎合结果。
没有对厂商源授予MIT或宣称公开再分发权。本仓库只提交获取说明和哈希，
依赖、许可文件、编译器及生成物都不提交。CMSIS旧头的分发条款和ST包条款须保留。

## 真实可用命令

在新ASCII绝对路径克隆，保持Git源码换行字节，并使用自己的分支/提交：

```powershell
git clone --config core.autocrlf=false https://github.com/logic202407-cmyk/zynq-vision-lab.git C:/zynq-p0
Set-Location C:/zynq-p0
git switch work/ikkkkk19-stm32-independent-p0-20261004
```

使用可运行的Python3.10+；本次实际为3.12.14。按上节准备依赖后：

```powershell
python tools/build_stm32_p0.py --deps private/stm32-deps --tool-bin C:/Keil_v5/ARM/ARMCC/bin --output private/build-run-001
```

runner在新目录逐文件调用armcc/armasm、armlink、fromelf，不运行uVision GUI、
调试器或烧录。新目录已存在、缺文件、依赖hash不匹配、非零退出、编译诊断会停止，
保留已产生日志。每条实际命令、UTC、退出码、完整stdout/stderr及日志hash单独存储。
成功时有AXF、Intel HEX、map、完整result.json和源/依赖/产物hash。

日志台架使用独立变体：

```powershell
python tools/build_stm32_p0.py --deps private/stm32-deps --tool-bin C:/Keil_v5/ARM/ARMCC/bin --output private/build-log-001 --log-only
```

该命令定义 P0_LOG_ONLY，排除 servo.c 和 TIM 驱动；完整要求和串口脚本见
[LOG_ONLY.md](LOG_ONLY.md)。普通命令仍生成控制变体，不能用于日志台架。

[Project.uvprojx](Project.uvprojx) 也列出同一组应用和私有依赖，
配置为STM32F103C8、64KiB Flash/20KiB RAM。它是可审查工程配置，
本次验证的是命令行完整构建，未把工程能打开当成uVision重建通过。
继承的HSE=8MHz/SYSCLK=72MHz、TIM2 PA0/PA1、USART1 PA9/PA10、
USART3 PB10/PB11均为原型编译假设，未据此验证新硬件接线、时钟或电气条件。

## Host验证

```powershell
python -m unittest discover -s tests -p test_stm32_p0.py -v
python tools/check_repository.py
python -m unittest discover -s tests -v
git diff --check
```

host测试真实编译同一份pid/control/parser/command/queue C源，
用ctypes调用编译后的库；没有Python替身控制算法。
需要gcc；本次Windows实测TDM64 GCC4.8.1，CI使用runner现有gcc。
可用进程环境变量`P0_HOST_CC`选择编译器；Windows会识别已有Dev-Cpp安装路径。
`STM32_P0_EVIDENCE`可指定一个尚不存在的输出目录，默认新建private目录。
无编译器、编译错误、零测试或skip不算通过。

固定输入与独立手写expected见 [scenarios.json](tests/scenarios.json)。
每个情景的完整输入字节/hash、每步actual及expected保存为replay.json，
编译版本/命令/sourcehash和原始日志另存。当前为66个情景和3个队列测试，
合计69个新增检查；原PR1的40个检查保留，当前完整套件预期109个。

这些结果只证明软件控制状态和逻辑应用值。实际串口、PWM、机械限位、
物理停止/恢复、负载与固定相机闭环均须另行台架验证。
