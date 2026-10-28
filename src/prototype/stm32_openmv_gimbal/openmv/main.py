# OpenMV 二维云台追踪 v2 - 多目标从屏幕左侧向右依次锁定
# v1 原始脚本备份: openmv_main_v1.py
# 每个目标对准稳定后停留 2 秒; 完成一轮后保持当前位置。
# 第一帧识别到的目标组成一轮; 再次运行脚本开始新一轮。
# 适用: 相互分开的静止红色目标, 用帧间位置匹配保持顺序。
# 全部目标可见时按左右顺序重新关联, 不受旧坐标和 TRACK_RADIUS 限制。
# 部分目标不可见时按位置匹配并暂停等待; 全部重新出现时自动恢复。
# 硬件: OpenMV H7 Plus
# 分辨率: QQVGA 160x120, 中心 (80, 60)
# 协议: 8字节定长帧
#   0xAA 0xFF | dx(16) | dy(16) | flag | 0xEE
#   dx/dy: int16 有符号, 小端序
#   flag:  0x01=识别到  0x00=丢失
# 串口: UART3, 115200, 8N1
# 接线: OpenMV P4(TX) -> STM32 PA10(RX), 共地
#
# ===== 帧率优化说明 (2026-08 调整) =====
# 之前是 QVGA(320x240) + 每帧绘图 + 5 帧滑动平均, 实测只有 10fps。
# 10fps 意味着两帧之间隔 100ms, 跟踪动态目标时滞后误差无法消除
# (目标 200px/s 时, 光采样间隔就带来 20px 误差)。
# 现在:
#   1. 分辨率降到 QQVGA(160x120) —— find_blobs 是逐像素扫描, 像素少 4 倍就快约 4 倍
#   2. 绘图由 DEBUG_DRAW 开关控制 —— 调试时显示全部目标和当前状态
#   3. 去掉 5 帧滑动平均 —— STM32 侧已有低通滤波, 两层滤波叠加只会增加延迟
# 预期帧率可从 10fps 提到 30~40fps。

import sensor, image, time, ustruct
from pyb import UART

# ===== 优化开关 =====
DEBUG_DRAW = True  # 需要看绿框/红框时改 True; 串口通信本身不受影响
PRINT_FPS  = False      # 需要看帧率时改 True (会占用一点时间)

# ===== 传感器初始化 =====
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQVGA)      # 160x120: 比 QVGA 快约 4 倍
sensor.skip_frames(time=2000)
sensor.set_auto_whitebal(False)
sensor.set_auto_gain(False)

# ===== 阈值 (LAB色彩空间) =====
red_threshold = (7, 49, 13, 45, 8, 33)
# ===== 目标过滤 =====
# 分辨率从 QVGA 降到 QQVGA 后同样目标的像素面积变成 1/4, 所以门限比 QVGA 时代小。
# 这组值(8/8/20)是经过验证能稳定识别的配置, 不要随意调大 ——
# 调到 60 会直接漏掉目标(实测目标丢失)。
PIXELS_THRESHOLD = 8     # find_blobs 的像素门限
AREA_THRESHOLD   = 8     # find_blobs 的面积门限
MIN_BLOB_AREA    = 20    # 小于该面积的色块直接忽略
TRACK_RADIUS     = 30    # 上一帧目标中心允许的最大移动半径(像素)

# ===== 顺序锁定 =====
LOCK_ERR_PX      = 5     # 两轴偏差均不超过该值, 才算对准
STABLE_MS        = 200   # 连续对准 200ms 后开始停留
HOLD_MS          = 2000  # 稳定后停留时间; 改为 1000 就是 1 秒
SWITCH_RESET_MS  = 100   # 切换时持续发送 flag=0, 让 STM32 复位 PID/滤波
MAX_FRAME_GAP_MS = 200   # 拍照卡顿超过该间隔, 重新判断稳定, 不累计停留

# ===== 串口初始化 =====
uart = UART(3, 115200)

# ===== 画面中心 (QQVGA 中心点) =====
CENTER_X = 80    # 160/2
CENTER_Y = 60    # 120/2

clock = time.clock()

class TargetSequence:
    def __init__(self):
        self.targets = []
        self.current_index = 0
        self.stable_since = None
        self.hold_since = None
        self.switch_since = None
        self.last_update = None
        self.done = False
        self.state = "WAIT"

    def _match_targets(self, candidates):
        # 静止目标的左右次序不变。全部可见时用整组顺序更新位置,
        # 避免云台转动后旧坐标跨过匹配半径, 一直卡在 LOST。
        if len(candidates) == len(self.targets):
            ordered = sorted(candidates, key=lambda b: (b.cx, b.cy))
            for target, blob in zip(self.targets, ordered):
                target["cx"], target["cy"] = blob.cx, blob.cy
                target["blob"] = blob
            return self.targets[self.current_index]["blob"]

        # 当前目标按上一帧位置匹配, 不随 candidates 的返回顺序变化。
        for target in self.targets:
            target["blob"] = None
        current = self.targets[self.current_index]
        r2 = TRACK_RADIUS * TRACK_RADIUS
        near = []
        for i, blob in enumerate(candidates):
            distance = ((blob.cx - current["cx"]) ** 2
                        + (blob.cy - current["cy"]) ** 2)
            if distance > r2:
                continue
            # 更靠近其他已有目标的色块, 不能拿来替代丢失的当前目标。
            if any(distance >= (blob.cx - target["cx"]) ** 2
                               + (blob.cy - target["cy"]) ** 2
                   for target_index, target in enumerate(self.targets)
                   if target_index != self.current_index):
                continue
            near.append((i, distance))
        if not near:
            return None
        selected_index, _ = min(near, key=lambda item: item[1])
        selected = candidates[selected_index]

        # 摄像头随云台移动: 用当前目标的帧间位移预测其他静止目标的新位置。
        shift_x = selected.cx - current["cx"]
        shift_y = selected.cy - current["cy"]
        for target in self.targets:
            target["cx"] += shift_x
            target["cy"] += shift_y
        current["blob"] = selected

        # 每个色块最多匹配一个目标; 未出现的目标保留预测位置, 不改变队列顺序。
        pairs = []
        for target_index, target in enumerate(self.targets):
            if target_index == self.current_index:
                continue
            for blob_index, blob in enumerate(candidates):
                if blob_index == selected_index:
                    continue
                distance = ((blob.cx - target["cx"]) ** 2
                            + (blob.cy - target["cy"]) ** 2)
                if distance <= r2:
                    pairs.append((distance, target_index, blob_index))
        pairs.sort()
        matched_targets = {self.current_index}
        matched_blobs = {selected_index}
        for _, target_index, blob_index in pairs:
            if target_index in matched_targets or blob_index in matched_blobs:
                continue
            blob = candidates[blob_index]
            target = self.targets[target_index]
            target["cx"], target["cy"] = blob.cx, blob.cy
            target["blob"] = blob
            matched_targets.add(target_index)
            matched_blobs.add(blob_index)
        return selected

    def update(self, candidates, now):
        if self.done:
            return None
        if (self.last_update is not None
                and time.ticks_diff(now, self.last_update) > MAX_FRAME_GAP_MS):
            self.stable_since = self.hold_since = None
        self.last_update = now
        if not self.targets:
            if not candidates:
                return None
            ordered = sorted(candidates, key=lambda b: (b.cx, b.cy))
            self.targets = [{"cx": b.cx, "cy": b.cy, "blob": b}
                            for b in ordered]

        resetting = (self.switch_since is not None
                     and time.ticks_diff(now, self.switch_since) < SWITCH_RESET_MS)
        if not resetting:
            self.switch_since = None
        selected = self._match_targets(candidates)
        if selected is None:
            self.stable_since = self.hold_since = None
            self.state = "LOST"
            return None
        if resetting:
            self.state = "SWITCH"
            return None

        dx = selected.cx - CENTER_X
        dy = CENTER_Y - selected.cy
        if abs(dx) > LOCK_ERR_PX or abs(dy) > LOCK_ERR_PX:
            self.stable_since = self.hold_since = None
            self.state = "TRACK"
            return selected
        if self.stable_since is None:
            self.stable_since = now
        if time.ticks_diff(now, self.stable_since) < STABLE_MS:
            self.state = "STABLE"
            return selected
        if self.hold_since is None:
            self.hold_since = now
        self.state = "HOLD"
        if time.ticks_diff(now, self.hold_since) < HOLD_MS:
            return selected

        self.stable_since = self.hold_since = None
        self.current_index += 1
        if self.current_index == len(self.targets):
            self.done = True
            self.state = "DONE"
        else:
            self.switch_since = now
            self.state = "SWITCH"
        # 本帧也发送 flag=0; 最后一个目标完成后一直保持该状态。
        return None


sequence = TargetSequence()


while True:
    clock.tick()
    img = sensor.snapshot()

    blobs = img.find_blobs([red_threshold],
                           pixels_threshold=PIXELS_THRESHOLD,
                           area_threshold=AREA_THRESHOLD,
                           merge=False)

    candidates = [b for b in blobs if b.area >= MIN_BLOB_AREA]
    now = time.ticks_ms()
    current_blob = sequence.update(candidates, now)

    if DEBUG_DRAW:
        for blob in candidates:
            img.draw_rectangle(blob.rect, color=(0, 255, 0))

    if current_blob is not None:

        # 直接把原始偏差发出去; 滤波统一在 STM32 侧做, 避免两层滤波叠加延迟
        dx = current_blob.cx - CENTER_X
        dy = CENTER_Y - current_blob.cy

        if DEBUG_DRAW:
            img.draw_rectangle(current_blob.rect, color=(255, 0, 0))
            img.draw_cross((current_blob.cx, current_blob.cy), color=(255, 0, 0))
        if DEBUG_DRAW or PRINT_FPS:
            img.draw_string((2, 14), "dx=%d dy=%d" % (dx, dy), color=(255, 255, 0))

        flag = 0x01
    else:
        dx = dy = 0
        flag = 0x00

    if DEBUG_DRAW:
        if sequence.done or not sequence.targets:
            label = sequence.state
        else:
            label = "T%d/%d %s" % (sequence.current_index + 1,
                                    len(sequence.targets), sequence.state)
            if sequence.hold_since is not None:
                remaining = max(0, HOLD_MS - time.ticks_diff(now, sequence.hold_since))
                label += " %d.%ds" % (remaining // 1000, (remaining % 1000) // 100)
        img.draw_string((2, 2), label, color=(255, 255, 0))

    data = ustruct.pack("<BBhhBB", 0xAA, 0xFF, dx, dy, flag, 0xEE)
    uart.write(data)
