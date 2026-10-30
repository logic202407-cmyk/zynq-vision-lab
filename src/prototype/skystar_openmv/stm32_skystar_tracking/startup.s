; Original minimal Cortex-M4 startup; no vendor SDK dependency.
                PRESERVE8
                THUMB
                AREA STACK, NOINIT, READWRITE, ALIGN=3
Stack_Mem       SPACE 0x1000
__initial_sp
                AREA HEAP, NOINIT, READWRITE, ALIGN=3
__heap_base
Heap_Mem        SPACE 0x400
__heap_limit
                EXPORT __initial_sp
                EXPORT __heap_base
                EXPORT __heap_limit
                AREA RESET, DATA, READONLY, ALIGN=9
                EXPORT __Vectors
__Vectors
                DCD __initial_sp
                DCD Reset_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD 0
                DCD 0
                DCD 0
                DCD 0
                DCD Default_Handler
                DCD Default_Handler
                DCD 0
                DCD Default_Handler
                DCD SysTick_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD USART1_IRQHandler
                DCD USART2_IRQHandler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                DCD Default_Handler
                AREA |.text|, CODE, READONLY
                EXPORT Reset_Handler
                EXPORT Default_Handler
                IMPORT __main
                IMPORT SysTick_Handler
                IMPORT USART1_IRQHandler
                IMPORT USART2_IRQHandler
Reset_Handler   PROC
                LDR R0, =__main
                BX R0
                ENDP
Default_Handler PROC
                LDR R0, =0x40000820
                MOVS R1, #0
                STR R1, [R0]
fault_loop      B fault_loop
                ENDP
                END
