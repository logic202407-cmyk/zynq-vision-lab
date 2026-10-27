"""Regenerate original SVG wiring diagrams; standard library only."""
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parent
FONT = 'Microsoft YaHei, Noto Sans CJK SC, Arial, sans-serif'

def start(width, height, title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
            f'<title>{escape(title)}</title>',
            '<rect width="100%" height="100%" fill="#f8fafc"/>',
            f'<g font-family="{FONT}" fill="#172033">']

def text(parts, x, y, value, size=19, color='#172033', bold=False, anchor='start'):
    parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}" text-anchor="{anchor}">{escape(value)}</text>')

def box(parts, x, y, w, h, fill='#ffffff', stroke='#cbd5e1'):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')

def wire(parts, points, color, width=3):
    coords=' '.join(f'{x},{y}' for x,y in points)
    parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>')

def dot(parts, x, y, color):
    parts.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"/>')

def save(parts, name):
    parts.extend(['</g>','</svg>'])
    (ROOT/name).write_text('\n'.join(parts)+'\n',encoding='utf-8')

def gimbals():
    p=start(1320,870,'天空星 F407 与两套二维云台：四路 PWM 和独立动力供电')
    text(p,55,48,'天空星 F407 · 两套二维云台接线',30,bold=True)
    text(p,55,82,'普通 PWM 舵机；单独核心板；型号、电源额定值和机构限位待实物确认',18,color='#475569')
    box(p,55,130,390,505,fill='#eef5ff',stroke='#7c9ac5')
    text(p,80,177,'天空星 STM32F407VET6',24,bold=True)
    text(p,80,208,'TIM4 · 四个独立 PWM 通道',18)
    channels=[('D12 / PD12','CH1','云台① · 水平',260,'#2563eb'),
              ('D13 / PD13','CH2','云台① · 俯仰',365,'#7c3aed'),
              ('D14 / PD14','CH3','云台② · 水平',470,'#0284c7'),
              ('D15 / PD15','CH4','云台② · 俯仰',575,'#b45309')]
    for pin,ch,label,y,color in channels:
        text(p,80,y-10,pin,22,bold=True)
        text(p,80,y+18,'TIM4_'+ch,17,color='#475569')
        wire(p,[(445,y),(845,y)],color)
        text(p,565,y-12,'PWM 控制信号',17,color=color)
        box(p,845,y-32,285,92)
        text(p,863,y-5,label,21,bold=True)
        text(p,863,y+26,'PWM        V+ / GND →',17,color='#475569')
        dot(p,445,y,color);dot(p,845,y,color)
        wire(p,[(1130,y+5),(1190,y+5)],'#dc2626')
        wire(p,[(1130,y+38),(1250,y+38)],'#475569')
        dot(p,1190,y+5,'#dc2626');dot(p,1250,y+38,'#475569')
    wire(p,[(1190,265),(1190,715)],'#dc2626',4)
    wire(p,[(1250,298),(1250,770)],'#475569',4)
    text(p,1178,220,'V+',18,color='#dc2626',bold=True)
    text(p,1230,247,'GND',18,color='#475569',bold=True)
    box(p,720,675,410,125,fill='#fff4f2',stroke='#e8a39c')
    text(p,742,713,'外部舵机动力电源',23,bold=True)
    text(p,742,747,'电压按舵机额定值，容量按实际负载',17)
    text(p,742,777,'正极 → V+；负极 → GND',18)
    wire(p,[(1130,715),(1190,715)],'#dc2626',4)
    wire(p,[(1130,770),(1250,770)],'#475569',4)
    text(p,80,620,'侧边 GND',20,bold=True)
    wire(p,[(220,635),(220,770),(700,770),(700,810),(1250,810),(1250,770)],'#475569',4)
    dot(p,220,635,'#475569')
    dot(p,1250,770,'#475569')
    text(p,255,748,'公共信号参考地',18,color='#475569')
    text(p,55,830,'D12-D15 仅接信号；舵机动力电流不经过核心板。图为功能接线，不代表已实测通过。',18,color='#475569')
    save(p,'dual_gimbal_wiring.svg')

def debug():
    p=start(1320,840,'天空星 H1 十针接口：ST-Link SWD 与 USB-TTL 日志接线')
    text(p,45,48,'天空星 H1 · ST-Link 下载 + USB-TTL 日志',29,bold=True)
    text(p,45,82,'按实物 1 脚标记确认针号；以下为逻辑编号，不是实物正反面方向图',19,color='#b45309')
    box(p,410,130,500,405,fill='#eef5ff',stroke='#7c9ac5')
    text(p,435,170,'底部 H1 / 2 × 5 调试接口',23,bold=True)
    rows=[('1  SWO','2  +3.3V'),('3  SWCLK','4  GND'),('5  SWDIO','6  GND'),('7  +5V','8  U1.R / RX'),('9  NRST','10 U1.T / TX')]
    for i,(left,right) in enumerate(rows):
        y=220+i*60
        box(p,430,y-27,215,42,fill='#ffffff')
        box(p,672,y-27,218,42,fill='#ffffff')
        text(p,443,y,left,19,bold=True)
        text(p,685,y,right,19,bold=True)
    box(p,35,165,330,325)
    text(p,57,207,'ST-Link → 天空星',24,bold=True)
    for i,line in enumerate(['SWCLK → H1-3','SWDIO → H1-5','GND → H1-4 或 H1-6','NRST → H1-9（若有）']):
        text(p,57,253+i*51,line,21)
    wire(p,[(365,325),(410,325)],'#2563eb',4)
    box(p,955,165,330,325)
    text(p,977,207,'USB 转 TTL → 天空星',22,bold=True)
    for i,line in enumerate(['RXD ← H1-10 / U1.T','GND → H1-4 或 H1-6','TXD、VCC 不接','115200 / 8N1 / 无流控']):
        text(p,977,253+i*51,line,19)
    wire(p,[(910,325),(955,325)],'#0284c7',4)
    box(p,45,575,1240,205,fill='#ffffff')
    text(p,68,615,'关键对应关系',23,bold=True)
    text(p,68,654,'U1.T = USART1_TX = PA9 = H1-10；U1.R = USART1_RX = PA10 = H1-8。',20)
    text(p,68,692,'PA9 不在两侧普通 GPIO 排针上。两块工具的 GND 可以共用天空星地。',20)
    text(p,68,730,'H1-2 仅按下载器说明作为 VTref 检测参考；不要把电源输出和电压检测输入混接。',19)
    text(p,68,762,'天空星保持原方式供电；H1-7 / +5V 本次不接；下载器端按功能标签接线。',19)
    text(p,45,817,'2026-10-27 · 原创重绘，依据原厂原理图核对；实物接线与烧录结果仍待验证。',18,color='#475569')
    save(p,'debug_uart_wiring.svg')

if __name__=='__main__':
    gimbals();debug()
    print('Generated dual_gimbal_wiring.svg and debug_uart_wiring.svg')
