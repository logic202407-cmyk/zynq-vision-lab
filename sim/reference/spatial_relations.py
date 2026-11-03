"""Original integer geometry reference; no transport, tracking or model runtime.

The candidate semantics are in docs/scene_relation_contract_v0_1.md. All
thresholds are explicit experiment configuration, not camera calibration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


PREDICATES = (
    "left_of", "right_of", "above", "below", "bbox_overlap",
    "bbox_within_roi", "near_2d",
)


def _integer(name: str, value: object, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def _text(name: str, value: object) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


class Truth(str, Enum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class BBox:
    """Inclusive image coordinates, with frame bounds checked by Region."""

    xmin: int
    ymin: int
    xmax: int
    ymax: int

    def __post_init__(self) -> None:
        for name in ("xmin", "ymin", "xmax", "ymax"):
            _integer(name, getattr(self, name))
        if self.xmin > self.xmax or self.ymin > self.ymax:
            raise ValueError("bbox minima must not exceed maxima")

    @property
    def area(self) -> int:
        return (self.xmax - self.xmin + 1) * (self.ymax - self.ymin + 1)

    @property
    def center_2x(self) -> tuple[int, int]:
        return self.xmin + self.xmax, self.ymin + self.ymax


@dataclass(frozen=True)
class Snapshot:
    """Caller-supplied binding, not a claim that UDP carries these fields.

    Sequence numbers are uint32 labels here. This module neither orders them
    nor manages reboot, wraparound, pairing windows or temporal confirmation.
    """

    session_id: str
    measurement_frame_seq: int
    config_epoch: int
    mask_version: int
    width: int = 640
    height: int = 480
    frame_complete: bool = True

    def __post_init__(self) -> None:
        _text("session_id", self.session_id)
        _integer("measurement_frame_seq", self.measurement_frame_seq)
        if self.measurement_frame_seq > 0xFFFFFFFF:
            raise ValueError("measurement_frame_seq must fit uint32")
        _integer("config_epoch", self.config_epoch)
        _integer("mask_version", self.mask_version)
        if self.mask_version not in (1, 2):
            raise ValueError("mask_version must be 1 or 2")
        _integer("width", self.width, 1)
        _integer("height", self.height, 1)
        if type(self.frame_complete) is not bool:
            raise ValueError("frame_complete must be bool")


@dataclass(frozen=True)
class Region:
    """Three color slots and a separate configured ROI slot.

    Invalid measurements carry no current bbox. A rejected color observation
    may retain its raw count and reason; the count does not imply validity.
    ROI validity depends on configuration and bounds, never mask count.
    """

    marker_id: int
    snapshot: Snapshot
    source: str
    measurement_valid: bool
    bbox: BBox | None
    count: int | None = None
    invalid_reason: str | None = None

    def __post_init__(self) -> None:
        _integer("marker_id", self.marker_id)
        if not isinstance(self.snapshot, Snapshot):
            raise ValueError("snapshot must be Snapshot")
        if type(self.measurement_valid) is not bool:
            raise ValueError("measurement_valid must be bool")
        if self.source == "pl_color_stats":
            if self.marker_id not in (0, 1, 2):
                raise ValueError("color marker_id must be 0, 1 or 2")
            _integer("count", self.count)
            if self.count > self.snapshot.width * self.snapshot.height:
                raise ValueError("count exceeds the frame area")
            if self.measurement_valid and self.count == 0:
                raise ValueError("valid color measurement needs positive count")
        elif self.source == "configured_roi":
            if self.marker_id != 3 or self.count is not None:
                raise ValueError("configured ROI uses marker_id 3 and count=None")
        else:
            raise ValueError("unsupported region source")
        if self.measurement_valid:
            if not isinstance(self.bbox, BBox) or self.invalid_reason is not None:
                raise ValueError("valid region needs BBox and no invalid_reason")
            if self.bbox.xmax >= self.snapshot.width or self.bbox.ymax >= self.snapshot.height:
                raise ValueError("bbox exceeds snapshot dimensions")
            if self.count is not None and self.count > self.bbox.area:
                raise ValueError("count exceeds bbox area")
        else:
            if self.bbox is not None:
                raise ValueError("invalid region must not retain a current bbox")
            _text("invalid_reason", self.invalid_reason)


@dataclass(frozen=True)
class Ratio:
    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        _integer("numerator", self.numerator)
        _integer("denominator", self.denominator, 1)
        if self.numerator > self.denominator:
            raise ValueError("ratio must be within [0, 1]")


@dataclass(frozen=True)
class RelationConfig:
    """Raw three-valued boundaries; temporal hysteresis is a later task."""

    config_epoch: int
    direction_margin_px: int
    iou_false: Ratio
    iou_true: Ratio
    near_true_radius_px: int
    near_false_radius_px: int

    def __post_init__(self) -> None:
        for name in ("config_epoch", "direction_margin_px", "near_true_radius_px", "near_false_radius_px"):
            _integer(name, getattr(self, name))
        if not isinstance(self.iou_false, Ratio) or not isinstance(self.iou_true, Ratio):
            raise ValueError("IoU thresholds must be Ratio")
        if (self.iou_false.numerator * self.iou_true.denominator >
                self.iou_true.numerator * self.iou_false.denominator):
            raise ValueError("iou_false must not exceed iou_true")
        if self.near_true_radius_px > self.near_false_radius_px:
            raise ValueError("near_true_radius_px must not exceed near_false_radius_px")


@dataclass(frozen=True)
class GeometryEvidence:
    delta_cx2: int
    delta_cy2: int
    subject_area: int
    object_area: int
    intersection: int
    union: int
    distance_sq_center2: int


@dataclass(frozen=True)
class RelationResult:
    subject_id: int
    predicate: str
    object_id: int
    truth: Truth
    reason: str
    snapshot: Snapshot | None
    config: RelationConfig
    evidence: GeometryEvidence | None
    source: str = "geometry_rule"


def evaluate(
    predicate: str, subject: Region, object: Region, config: RelationConfig
) -> RelationResult:
    """Evaluate one ordered pair without reusing stale or mismatched inputs.

    Invalid types/field combinations raise ValueError. Legal but unavailable
    or incompatible observations return UNKNOWN with an explicit reason.
    No self edges are supported. Relations involving ROI are geometric;
    bbox_within_roi specifically requires a color subject and ROI object.
    """
    if not isinstance(predicate, str) or predicate not in PREDICATES:
        raise ValueError("unsupported predicate")
    if not isinstance(subject, Region) or not isinstance(object, Region):
        raise ValueError("endpoints must be Region")
    if not isinstance(config, RelationConfig):
        raise ValueError("config must be RelationConfig")
    if subject.marker_id == object.marker_id:
        raise ValueError("self relations are not supported")
    if predicate == "bbox_within_roi" and (
        subject.source != "pl_color_stats" or object.source != "configured_roi"
    ):
        raise ValueError("bbox_within_roi requires a color subject and ROI object")

    a, b = subject.snapshot, object.snapshot
    binding = a if a == b else None

    def result(truth: Truth, reason: str, evidence: GeometryEvidence | None = None) -> RelationResult:
        return RelationResult(subject.marker_id, predicate, object.marker_id,
                              truth, reason, binding, config, evidence)

    for mismatch, differs in (
        ("session_mismatch", a.session_id != b.session_id),
        ("measurement_frame_mismatch", a.measurement_frame_seq != b.measurement_frame_seq),
        ("config_epoch_mismatch", a.config_epoch != b.config_epoch or a.config_epoch != config.config_epoch),
        ("dimensions_mismatch", (a.width, a.height) != (b.width, b.height)),
        ("mask_version_mismatch", a.mask_version != b.mask_version),
    ):
        if differs:
            return result(Truth.UNKNOWN, mismatch)
    if not a.frame_complete or not b.frame_complete:
        return result(Truth.UNKNOWN, "frame_incomplete")
    if not subject.measurement_valid:
        return result(Truth.UNKNOWN, f"subject_invalid:{subject.invalid_reason}")
    if not object.measurement_valid:
        return result(Truth.UNKNOWN, f"object_invalid:{object.invalid_reason}")

    box_a, box_b = subject.bbox, object.bbox
    ax2, ay2 = box_a.center_2x
    bx2, by2 = box_b.center_2x
    dx2, dy2 = bx2 - ax2, by2 - ay2
    iw = max(0, min(box_a.xmax, box_b.xmax) - max(box_a.xmin, box_b.xmin) + 1)
    ih = max(0, min(box_a.ymax, box_b.ymax) - max(box_a.ymin, box_b.ymin) + 1)
    intersection = iw * ih
    union = box_a.area + box_b.area - intersection
    distance = dx2 * dx2 + dy2 * dy2
    evidence = GeometryEvidence(dx2, dy2, box_a.area, box_b.area, intersection, union, distance)

    if predicate in ("left_of", "right_of", "above", "below"):
        delta = {"left_of": dx2, "right_of": -dx2, "above": dy2, "below": -dy2}[predicate]
        truth = (Truth.TRUE if delta > 2 * config.direction_margin_px else
                 Truth.FALSE if delta <= 0 else Truth.UNKNOWN)
    elif predicate == "bbox_overlap":
        high, low = config.iou_true, config.iou_false
        truth = (Truth.FALSE if intersection == 0 else
                 Truth.TRUE if high.denominator * intersection >= high.numerator * union else
                 Truth.FALSE if low.denominator * intersection < low.numerator * union else
                 Truth.UNKNOWN)
    elif predicate == "near_2d":
        truth = (Truth.TRUE if distance <= 4 * config.near_true_radius_px ** 2 else
                 Truth.FALSE if distance > 4 * config.near_false_radius_px ** 2 else Truth.UNKNOWN)
    else:
        inside = (box_b.xmin <= box_a.xmin and box_b.ymin <= box_a.ymin and
                  box_a.xmax <= box_b.xmax and box_a.ymax <= box_b.ymax)
        truth = Truth.TRUE if inside else Truth.FALSE
    return result(truth, "threshold_band" if truth is Truth.UNKNOWN else "evaluated", evidence)
