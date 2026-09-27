"""Visible PC viewer for the vendor OV5640-to-UDP FPGA reference design."""

from __future__ import annotations

import queue
import socket
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from .vendor_udp import (
    BOARD_IP,
    FRAME_HEADER,
    HEIGHT,
    PC_IP,
    ROW_BYTES,
    START_COMMAND,
    STOP_COMMAND,
    UDP_PORT,
    WIDTH,
    Frame,
    FrameAssembler,
)


BG = "#10191c"
SURFACE = "#192529"
TEXT = "#e8f0ef"
MUTED = "#a6b9b7"
ACCENT = "#65d6bd"
WARN = "#f0bd75"
UI_POLL_MS = 33


def rgb565_be_to_image(frame: Frame) -> Image.Image:
    """Convert camera-order, big-endian RGB565 bytes into an RGB image."""
    if len(frame.rgb565_be) != frame.width * frame.height * 2:
        raise ValueError("RGB565 frame has an unexpected byte count")
    swapped = bytearray(len(frame.rgb565_be))
    swapped[0::2] = frame.rgb565_be[1::2]
    swapped[1::2] = frame.rgb565_be[0::2]
    return Image.frombytes(
        "RGB", (frame.width, frame.height), bytes(swapped), "raw", "BGR;16"
    )


class CameraReceiver(threading.Thread):
    def __init__(self, bind_ip: str, packets: queue.Queue[Frame]) -> None:
        super().__init__(name="camera-udp-receiver", daemon=True)
        self.packets = packets
        self.stop_event = threading.Event()
        self.assembler = FrameAssembler()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
        self.socket.settimeout(0.25)
        self.socket.bind((bind_ip, UDP_PORT))
        self.error: str | None = None

    def command(self, command: bytes) -> None:
        self.socket.sendto(command, (BOARD_IP, UDP_PORT))

    def close(self, send_stop: bool) -> None:
        if send_stop:
            try:
                self.command(STOP_COMMAND)
            except OSError:
                pass
        self.stop_event.set()
        # Release the UDP port before a new receiver binds it. Waiting for the
        # recv timeout leaves a brief window where an immediate restart fails.
        self.socket.close()

    def run(self) -> None:
        try:
            while not self.stop_event.is_set():
                try:
                    packet, peer = self.socket.recvfrom(2048)
                except socket.timeout:
                    continue
                except OSError as exc:
                    if not self.stop_event.is_set():
                        self.error = str(exc)
                    break
                # In live mode only accept the board's fixed source address.
                if peer[0] != BOARD_IP:
                    continue
                frame = self.assembler.feed(packet)
                if frame is not None:
                    try:
                        self.packets.put_nowait(frame)
                    except queue.Full:
                        try:
                            self.packets.get_nowait()
                        except queue.Empty:
                            pass
                        self.packets.put_nowait(frame)
        finally:
            self.socket.close()


class DemoSource(threading.Thread):
    """Produce a clearly marked synthetic frame for UI/protocol rehearsal."""

    def __init__(self, packets: queue.Queue[Frame]) -> None:
        super().__init__(name="camera-demo-source", daemon=True)
        self.packets = packets
        self.stop_event = threading.Event()
        self.assembler = FrameAssembler()

    def run(self) -> None:
        colors = (0xF800, 0x07E0, 0x001F, 0xFFFF, 0xFFE0, 0x07FF)
        shift = 0
        while not self.stop_event.is_set():
            for y in range(HEIGHT):
                color = colors[((y // 80) + shift) % len(colors)]
                row = color.to_bytes(2, "big") * WIDTH
                packet = FRAME_HEADER + row if y == 0 else row
                frame = self.assembler.feed(packet)
                if frame is not None:
                    try:
                        self.packets.put_nowait(frame)
                    except queue.Full:
                        try:
                            self.packets.get_nowait()
                        except queue.Empty:
                            pass
                        self.packets.put_nowait(frame)
            shift += 1
            self.stop_event.wait(0.5)


class Viewer(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("OV5640 · PC 图像接收")
        self.configure(bg=BG)
        self.geometry("1040x710")
        self.minsize(930, 650)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.frames: queue.Queue[Frame] = queue.Queue(maxsize=1)
        self.worker: CameraReceiver | DemoSource | None = None
        self.mode = "idle"
        self.last_image: Image.Image | None = None
        self.last_arrival = 0.0
        self.render_times: list[float] = []
        self.bind_ip = tk.StringVar(value=PC_IP)
        self.connection = tk.StringVar(value="等待连接")
        self.detail = tk.StringVar(value="JTAG 不传输视频。实机请用网线连接板卡网口与电脑网口。")
        self.stats = tk.StringVar(value="收到帧 0   ·   未完整帧 0   ·   异常包 0   ·   显示 FPS —")
        self._build_ui()
        self.after(UI_POLL_MS, self._poll)

    def _build_ui(self) -> None:
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=28, pady=(16, 8))
        tk.Label(top, text="OV5640 / PC VIEW", fg=ACCENT, bg=BG,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(top, text="摄像头画面", fg=TEXT, bg=BG,
                 font=("Microsoft YaHei UI", 22, "bold")).pack(anchor="w", pady=(3, 0))

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=28)
        left = tk.Frame(body, bg=SURFACE, width=664, height=526)
        left.pack(side="left", fill="both", expand=True)
        left.pack_propagate(False)
        self.canvas = tk.Canvas(left, width=WIDTH, height=HEIGHT, bg="#0b1113",
                                highlightthickness=0)
        self.canvas.pack(padx=12, pady=12, expand=True)
        self.image_item = self.canvas.create_image(0, 0, anchor="nw")
        self.empty_item = self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2, text="尚无摄像头画面\n\n连接网线后点击「开始接收」",
            fill=MUTED, justify="center", font=("Microsoft YaHei UI", 15)
        )
        self.demo_item = self.canvas.create_text(
            WIDTH // 2, 34, text="模拟数据 · 非摄像头画面", fill="#0b1113",
            font=("Microsoft YaHei UI", 14, "bold"), state="hidden"
        )

        panel = tk.Frame(body, bg=BG, width=310)
        panel.pack(side="left", fill="y", padx=(20, 0))
        panel.pack_propagate(False)
        self._heading(panel, "连接")
        tk.Label(panel, textvariable=self.connection, fg=ACCENT, bg=BG,
                 font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w", pady=(1, 12))
        self._label(panel, "电脑有线网卡 IPv4")
        entry = ttk.Entry(panel, textvariable=self.bind_ip, font=("Consolas", 12))
        entry.pack(fill="x", pady=(5, 7))
        self._label(panel, "原厂例程要求电脑设为 192.168.1.102 / 24。")
        self._label(panel, "板端 192.168.1.10 · UDP 1234")
        self._label(panel, "需要用网线连接板卡 GE 网口。")

        self.start_button = tk.Button(panel, text="开始接收", command=self.start_live,
                                      bg=ACCENT, fg="#0d2420", relief="flat",
                                      activebackground="#a3efdc", font=("Microsoft YaHei UI", 12, "bold"),
                                      pady=5)
        self.start_button.pack(fill="x", pady=(6, 3))
        self.stop_button = tk.Button(panel, text="停止", command=self.stop,
                                     bg=SURFACE, fg=TEXT, relief="flat", pady=4,
                                     font=("Microsoft YaHei UI", 11))
        self.stop_button.pack(fill="x", pady=(0, 3))
        tk.Button(panel, text="模拟画面自测", command=self.start_demo,
                  bg=SURFACE, fg=WARN, relief="flat", pady=4,
                  font=("Microsoft YaHei UI", 11)).pack(fill="x", pady=(0, 3))
        tk.Button(panel, text="保存当前帧 PNG", command=self.save_frame,
                  bg=SURFACE, fg=TEXT, relief="flat", pady=4,
                  font=("Microsoft YaHei UI", 11)).pack(fill="x")

        self._heading(panel, "当前数据", top=8)
        tk.Label(panel, textvariable=self.stats, fg=MUTED, bg=BG, justify="left",
                 anchor="w", wraplength=290,
                 font=("Microsoft YaHei UI", 9)).pack(fill="x", pady=(4, 0))
        tk.Label(panel, text="RGB565 · 640 × 480 · 原厂 UDP 格式",
                 fg=MUTED, bg=BG, font=("Microsoft YaHei UI", 9)).pack(anchor="w", pady=(5, 0))

        bottom = tk.Frame(self, bg=BG)
        bottom.pack(fill="x", padx=28, pady=(8, 12))
        tk.Label(bottom, textvariable=self.detail, fg=MUTED, bg=BG, anchor="w",
                 font=("Microsoft YaHei UI", 10)).pack(fill="x")

    @staticmethod
    def _heading(parent: tk.Widget, text: str, top: int = 0) -> None:
        tk.Label(parent, text=text, fg=TEXT, bg=BG,
                 font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w", pady=(top, 4))

    @staticmethod
    def _label(parent: tk.Widget, text: str) -> None:
        tk.Label(parent, text=text, fg=MUTED, bg=BG,
                 font=("Microsoft YaHei UI", 9)).pack(anchor="w", pady=2)

    def start_live(self) -> None:
        self.stop()
        self._clear_preview()
        address = self.bind_ip.get().strip()
        try:
            socket.inet_aton(address)
            worker = CameraReceiver(address, self.frames)
            worker.command(START_COMMAND)
        except (OSError, ValueError) as exc:
            if "worker" in locals():
                worker.close(False)
            self.connection.set("连接失败")
            self.detail.set(f"无法绑定网卡或发送启动命令：{exc}。请检查网线和电脑有线 IP。")
            return
        self.worker = worker
        self.mode = "live"
        self.connection.set("等待板端数据")
        self.detail.set(f"已监听 {address}:{UDP_PORT}，已向 {BOARD_IP}:{UDP_PORT} 发送启动命令。")
        worker.start()

    def start_demo(self) -> None:
        self.stop()
        self._clear_preview()
        worker = DemoSource(self.frames)
        self.worker = worker
        self.mode = "demo"
        self.connection.set("模拟画面自测")
        self.detail.set("当前为本机生成的测试色条，不是 OV5640 实拍画面。")
        worker.start()

    def stop(self) -> None:
        if self.worker is not None:
            if isinstance(self.worker, CameraReceiver):
                self.worker.close(True)
            else:
                self.worker.stop_event.set()
            self.worker = None
        self.mode = "idle"
        self.connection.set("已停止")
        self._clear_preview()
        while not self.frames.empty():
            try:
                self.frames.get_nowait()
            except queue.Empty:
                break

    def _clear_preview(self) -> None:
        self.canvas.itemconfigure(self.image_item, image="")
        self.canvas.itemconfigure(self.empty_item, state="normal")
        self.canvas.itemconfigure(self.demo_item, state="hidden")
        self.last_image = None
        self.photo = None
        self.last_arrival = 0.0
        self.render_times = []

    def _poll(self) -> None:
        now = time.monotonic()
        worker = self.worker
        if worker is not None:
            try:
                frame = self.frames.get_nowait()
            except queue.Empty:
                frame = None
            if frame is not None:
                self.last_image = rgb565_be_to_image(frame)
                self.photo = ImageTk.PhotoImage(self.last_image)
                self.canvas.itemconfigure(self.image_item, image=self.photo)
                self.canvas.itemconfigure(self.empty_item, state="hidden")
                self.canvas.itemconfigure(self.demo_item,
                                          state="normal" if self.mode == "demo" else "hidden")
                self.last_arrival = now
                self.render_times.append(now)
                self.render_times = [t for t in self.render_times if now - t < 2.0]
                if self.mode == "live":
                    self.connection.set("接收中 · 实时画面")
            a = worker.assembler
            fps = len(self.render_times) / 2 if len(self.render_times) > 1 else 0
            self.stats.set(
                f"收到包 {a.datagrams}   ·   完整帧 {a.completed}\n"
                f"未完整帧 {a.incomplete}   ·   异常包 {a.malformed}\n"
                f"显示 FPS {fps:.1f}   ·   当前帧行数 {a.rows_received}/{HEIGHT}"
            )
            if isinstance(worker, CameraReceiver) and worker.error:
                self.connection.set("网络接收错误")
                self.detail.set(worker.error)
            elif self.mode == "live" and a.completed and now - self.last_arrival > 3:
                self.connection.set("画面中断")
                self.detail.set("超过 3 秒无完整帧；检查网线、板卡配置及丢包计数。")
        self.after(UI_POLL_MS, self._poll)

    def save_frame(self) -> None:
        if self.last_image is None:
            messagebox.showinfo("没有图像", "收到完整帧后才能保存。", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".png", filetypes=[("PNG image", "*.png")],
            initialfile=time.strftime("ov5640_%Y%m%d_%H%M%S.png")
        )
        if path:
            self.last_image.save(path)
            self.detail.set(f"已保存当前帧：{path}")

    def on_close(self) -> None:
        self.stop()
        self.destroy()


def main() -> None:
    Viewer().mainloop()


if __name__ == "__main__":
    main()
