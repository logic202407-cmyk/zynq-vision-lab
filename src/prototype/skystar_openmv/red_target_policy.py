"""Single-target observation policy. No sensor, UART, PWM or filesystem access.

The caller supplies already thresholded blobs. This is a quality gate, not
cross-camera identity or mechanical calibration. One instance per camera.
"""


def blob_value(blob, name):
    value = getattr(blob, name)
    return value() if callable(value) else value


class RedTargetPolicy:
    def __init__(self, min_area=20, border=1, stable_frames=3):
        if min_area < 1 or border < 1 or stable_frames < 1:
            raise ValueError('Positive observation policy required')
        self.min_area = min_area
        self.border = border
        self.stable_frames = stable_frames
        self.good_frames = 0
        self.reason = 'MISSING'

    def choose(self, blobs, width=160, height=120):
        candidates = [b for b in blobs if blob_value(b, 'area') >= self.min_area]
        reason = 'MISSING' if not candidates else 'AMBIGUOUS' if len(candidates) != 1 else None
        blob = candidates[0] if reason is None else None
        if blob is not None:
            x, y, w, h = blob_value(blob, 'rect')
            cx, cy = blob_value(blob, 'cx'), blob_value(blob, 'cy')
            if (w <= 0 or h <= 0 or x < 0 or y < 0 or x+w > width or y+h > height or
                    not x <= cx < x+w or not y <= cy < y+h):
                reason = 'GEOMETRY'
            elif (x < self.border or y < self.border or
                  x+w > width-self.border or y+h > height-self.border):
                reason = 'EDGE'
        if reason is not None:
            self.good_frames = 0
            self.reason = reason
            return None
        self.good_frames = min(self.good_frames+1, self.stable_frames)
        self.reason = 'VALID' if self.good_frames == self.stable_frames else 'WARMUP'
        return blob if self.reason == 'VALID' else None


def target_offsets(blob, width=160, height=120):
    if blob is None:
        return 0, 0, 0
    return blob_value(blob, 'cx')-width//2, height//2-blob_value(blob, 'cy'), 1
