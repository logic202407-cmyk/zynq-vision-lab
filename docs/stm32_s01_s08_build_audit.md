# S03：ARM 命令行与 µVision 工程静态审计

输入固定为PR7 `04ba0db3e1a4f67cee7efa7b941d69ce281bffa2` 的
[Project.uvprojx](../src/prototype/stm32_openmv_gimbal/stm32/Project.uvprojx)、
[firmware.sct](../src/prototype/stm32_openmv_gimbal/stm32/firmware.sct) 与
[已有ARM记录](../report/experiments/stm32-p0-2026-10-04/firmware.json)。
本批未重跑ARM工具、未打开GUI；旧0错误/0警告只归属旧命令行构建。

## 逐编译单元

工程与实际记录的18个编译单元集合相等，均无FileOption覆盖。
C宏统一为 `USE_STDPERIPH_DRIVER,STM32F10X_MD`，包含目录归一化为
User/Start/Library。CLI使用实际私有依赖目录；GUI用工程相对目录。
GUI配置Cortex-M3、C99和调试；实际C命令均为 `--cpu Cortex-M3 --c99 -O1 -g`。
每一单元的原始路径、宏、包含目录与实际参数由只读工具输出保存。

| 编译单元 | 类型 | 共享参数与需保留的差异 |
|---|---|---|
| command.c | C | C组：宏/包含目录相同；优化枚举、section与interwork差异见下表 |
| control.c | C | C组 |
| main.c | C | C组 |
| pid.c | C | C组 |
| rx_queue.c | C | C组 |
| servo.c | C | C组 |
| stm32f10x_it.c | C | C组 |
| usart3_config.c | C | C组 |
| usart_config.c | C | C组 |
| uart_parser.c | C | C组 |
| core_cm3.c | C | C组 |
| system_stm32f10x.c | C | C组 |
| misc.c | C | C组 |
| stm32f10x_gpio.c | C | C组 |
| stm32f10x_rcc.c | C | C组 |
| stm32f10x_tim.c | C | C组 |
| stm32f10x_usart.c | C | C组 |
| startup_stm32f10x_md.s | 汇编 | Cortex-M3、调试、interwork；GUI汇编宏/包含目录单独保存在审计JSON |

## 等价范围和差异

| 项目 | GUI XML | 实际CLI记录 | 审计结论 |
|---|---|---|---|
| C源码集合、目标CPU | 17个C + 1个启动汇编；Cortex-M3 | 同集合；Cortex-M3 | 此范围一致 |
| C宏/目录、C99/调试 | 上述宏与3目录；uC99=1、DebugInformation=1 | -D/-I；--c99、-g | 配置一致；未验证GUI实际展开的全部控制串 |
| 优化 | Optim=1原始枚举 | -O1 | 尚无GUI实际控制串证明数字映射，不把枚举1直接写成-O1 |
| 每函数section | OneElfS=1 | C命令没有--split_sections | 差异；Keil说明One ELF Section启用--split_sections |
| C interwork | interw=1 | C命令未显式--apcs=interwork；汇编有 | 显式参数差异，默认行为未在本批证明 |
| enum/char/告警 | EnumInt=0、PlainCh=0、wLevel=2 | 未显式设置；成功且0告警 | 原始配置有记录，不由0告警推出全部等价 |
| 自动包含/设备包 | uSurpInc=0；工程设备配置 | 只声明3包含目录 | GUI可能自动加入头路径/版本宏，未取得实际控制串 |
| 链接布局 | umfTarg=1、useFile=0、ScatterFile空 | 显式firmware.sct、RESET/+First/root sections | GUI生成布局与手工scatter不等价证明 |
| ROM/RAM范围 | 0x08000000/0x10000；0x20000000/0x5000 | scatter同起点/大小 | 范围一致，不证明对象/section放置相同 |
| 用户hooks | 六个RunUserProg均为0 | 没有调用GUI hooks | 未启用；没有运行任何hook |

选项含义仅依据[Keil C/C++选项](https://www.keil.com/support/man/docs/uv4/uv4_dg_adscc.asp)
和[Keil Linker选项](https://www.keil.com/support/man/docs/uv4/uv4_dg_adsld.asp)。
未自行更改工程或CLI参数来“修成等价”。GUI实际重建、map逐对象比较与工具版本锁定
仍为后续任务；本批交付审计差异，GUI执行为 `not_run`。
