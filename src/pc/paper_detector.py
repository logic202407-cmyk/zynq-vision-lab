"""Independent PC red-paper proposal; never substitutes for PL measurements."""

from dataclasses import dataclass

VERSION = "pc-red-paper-hsv/1"


@dataclass(frozen=True)
class PaperDetection:
    bbox: tuple[int, int, int, int]
    centroid: tuple[int, int]
    pixel_area: int
    rectangularity: float
    candidate_count: int
    version: str = VERSION


class RedPaperDetector:
    """Search the whole current RGB image for a dominant red rectangle.

    Hue is brightness-independent; saturation/value gates suppress neutral and
    near-black pixels. Morphology removes isolated dots before component
    selection. No fixed ROI, previous-frame box, or PL result is used.
    Dependencies are loaded only when this optional PC feature is instantiated.
    """

    def __init__(self):
        import cv2
        import numpy as np
        self.cv = cv2
        self.np = np
        self.open_kernel = np.ones((3, 3), dtype=np.uint8)
        self.close_kernel = np.ones((5, 5), dtype=np.uint8)

    def detect(self, image) -> PaperDetection | None:
        cv, np = self.cv, self.np
        rgb = np.asarray(image.convert("RGB"))
        height, width = rgb.shape[:2]
        if width < 12 or height < 12:
            return None
        hsv = cv.cvtColor(rgb, cv.COLOR_RGB2HSV)
        hue, saturation, value = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        mask = (((hue <= 10) | (hue >= 170))
                & (saturation >= 65) & (value >= 25)).astype(np.uint8) * 255
        mask = cv.morphologyEx(mask, cv.MORPH_OPEN, self.open_kernel)
        mask = cv.morphologyEx(mask, cv.MORPH_CLOSE, self.close_kernel)
        count, _, stats, centers = cv.connectedComponentsWithStats(
            mask, connectivity=8)
        minimum_area = max(150, int(width * height * 0.0005))
        candidates = []
        for index in range(1, count):
            x, y, w, h, area = (int(v) for v in stats[index])
            if area < minimum_area or min(w, h) < 12:
                continue
            fill = area / (w * h)
            if not (1 / 3 <= w / h <= 3) or fill < 0.82:
                continue
            candidates.append((area * fill, index, x, y, w, h, area, fill))
        if not candidates:
            return None
        _, index, x, y, w, h, area, fill = max(candidates)
        return PaperDetection(
            (x, y, x + w - 1, y + h - 1),
            (int(centers[index][0]), int(centers[index][1])),
            area, fill, len(candidates))


def draw_paper_result(image, detection):
    """Draw a labelled PC overlay on a copy; saved camera pixels stay intact."""
    if detection is None:
        return image
    from PIL import ImageDraw
    shown = image.copy()
    draw = ImageDraw.Draw(shown)
    x0, y0, x1, y1 = detection.bbox
    cx, cy = detection.centroid
    color = "#42c7ff"
    draw.rectangle(detection.bbox, outline=color, width=3)
    draw.line((cx - 7, cy, cx + 7, cy), fill=color, width=2)
    draw.line((cx, cy - 7, cx, cy + 7), fill=color, width=2)
    draw.text((x0 + 3, max(0, y0 - 13)), "PC PAPER", fill=color)
    return shown
