# SkyStar wiring preparation: resource semantics

The older wiring document proposed USART3 for a camera and UART4 on PC10/PC11 for the FPGA. The current integration source and recorded FPGA connection use USART3 on PC10/PC11; the old candidate must not be presented as current wiring.

The approved preparation keeps USART3 for the FPGA and assigns USART6 PC7 / UART5 PD2 to the two additional inputs. PWM resources are PD14/PD15 and PE9/PE11. Multiple pin alternatives of one UART peripheral are not independent UARTs.

The third-gimbal registry formerly used UNKNOWN. Replacing this with selected pins only records a plan. `mapped` and `confirmed_for_preparation` do not mean installed, measured or enabled. The registry keeps IDs 1/2 uninstalled, and C regression checks reject observation ingestion for them. Actual new drivers and board tests are separate work.
