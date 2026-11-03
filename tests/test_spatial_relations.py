"""Independent geometry oracle and boundary checks for the offline R0 reference.

These tests do not establish RTL, protocol, board, temporal-manager or model
behavior.  The randomized expectations use Fraction arithmetic and inclusive
pixel-set areas, rather than helpers from the implementation under test.
"""

from dataclasses import replace
from fractions import Fraction
import random
import unittest

from sim.reference.spatial_relations import (
    BBox,
    PREDICATES,
    Ratio,
    Region,
    RelationConfig,
    Snapshot,
    Truth,
    evaluate,
)


RANDOM_SEED = 0x5CE0_2026
RANDOM_PAIRS = 10_000


def snapshot(**changes):
    fields = dict(session_id="synthetic-r0", measurement_frame_seq=100,
                  config_epoch=7, mask_version=2)
    fields.update(changes)
    return Snapshot(**fields)


def config(**changes):
    # Explicit synthetic parameters; these are not calibrated scene thresholds.
    fields = dict(config_epoch=7, direction_margin_px=0,
                  iou_false=Ratio(0, 1), iou_true=Ratio(1, 1),
                  near_true_radius_px=0, near_false_radius_px=0)
    fields.update(changes)
    return RelationConfig(**fields)


def marker(box, marker_id=0, snap=None, count=1):
    return Region(marker_id, snap or snapshot(), "pl_color_stats", True,
                  BBox(*box), count)


def roi(box, snap=None):
    return Region(3, snap or snapshot(), "configured_roi", True,
                  BBox(*box), None)


def oracle_geometry(a, b):
    """Use ordinary coordinates in pixels, not the implementation's center2."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    acx, acy = Fraction(ax0 + ax1, 2), Fraction(ay0 + ay1, 2)
    bcx, bcy = Fraction(bx0 + bx1, 2), Fraction(by0 + by1, 2)
    area_a = (ax1 - ax0 + 1) * (ay1 - ay0 + 1)
    area_b = (bx1 - bx0 + 1) * (by1 - by0 + 1)
    # Inclusive one-dimensional pixel sets intersect at a shared endpoint.
    iw = max(0, min(ax1, bx1) - max(ax0, bx0) + 1)
    ih = max(0, min(ay1, by1) - max(ay0, by0) + 1)
    intersection = iw * ih
    union = area_a + area_b - intersection
    return dict(dx=bcx - acx, dy=bcy - acy, area_a=area_a, area_b=area_b,
                intersection=intersection, union=union,
                iou=Fraction(intersection, union),
                distance_sq=(bcx - acx) ** 2 + (bcy - acy) ** 2,
                within=(bx0 <= ax0 <= ax1 <= bx1 and
                        by0 <= ay0 <= ay1 <= by1))


def oracle_truth(predicate, geometry, cfg):
    if predicate in ("left_of", "right_of", "above", "below"):
        delta = geometry["dx" if predicate in ("left_of", "right_of") else "dy"]
        if predicate in ("right_of", "below"):
            delta = -delta
        if delta > cfg.direction_margin_px:
            return Truth.TRUE
        if delta <= 0:
            return Truth.FALSE
        return Truth.UNKNOWN
    if predicate == "bbox_overlap":
        if geometry["intersection"] == 0:
            return Truth.FALSE
        if geometry["iou"] >= Fraction(cfg.iou_true.numerator,
                                        cfg.iou_true.denominator):
            return Truth.TRUE
        if geometry["iou"] < Fraction(cfg.iou_false.numerator,
                                       cfg.iou_false.denominator):
            return Truth.FALSE
        return Truth.UNKNOWN
    if predicate == "near_2d":
        if geometry["distance_sq"] <= cfg.near_true_radius_px ** 2:
            return Truth.TRUE
        if geometry["distance_sq"] > cfg.near_false_radius_px ** 2:
            return Truth.FALSE
        return Truth.UNKNOWN
    if predicate == "bbox_within_roi":
        return Truth.TRUE if geometry["within"] else Truth.FALSE
    raise AssertionError("oracle predicate was not explicitly implemented")


class SpatialRelationsTests(unittest.TestCase):
    def assert_truth(self, predicate, a, b, expected, cfg=None):
        result = evaluate(predicate, a, b, cfg or config())
        self.assertEqual(result.truth, expected)
        self.assertEqual(result.reason,
                         "threshold_band" if expected is Truth.UNKNOWN else "evaluated")
        self.assertEqual(result.predicate, predicate)
        self.assertEqual(result.subject_id, a.marker_id)
        self.assertEqual(result.object_id, b.marker_id)
        self.assertEqual(result.source, "geometry_rule")
        self.assertEqual(result.snapshot, a.snapshot)
        self.assertEqual(result.config, cfg or config())
        self.assertIsNotNone(result.evidence)
        return result

    def test_public_predicates_and_truth_values_are_explicit(self):
        self.assertEqual(set(PREDICATES), {
            "left_of", "right_of", "above", "below", "bbox_overlap",
            "bbox_within_roi", "near_2d",
        })
        self.assertEqual({truth.value for truth in Truth}, {"true", "false", "unknown"})

    def test_single_pixel_and_full_frame_inclusive_area_and_center(self):
        self.assertEqual(BBox(0, 0, 0, 0).area, 1)
        self.assertEqual(BBox(639, 479, 639, 479).area, 1)
        full = BBox(0, 0, 639, 479)
        self.assertEqual(full.area, 307_200)
        self.assertEqual(full.center_2x, (639, 479))
        self.assertEqual(BBox(2, 4, 3, 7).center_2x, (5, 11))
        a = marker((0, 0, 639, 479), count=307_200)
        b = roi((0, 0, 639, 479))
        result = self.assert_truth("bbox_within_roi", a, b, Truth.TRUE)
        self.assertEqual(result.evidence.subject_area, 307_200)
        self.assertEqual(result.evidence.intersection, 307_200)
        self.assertEqual(result.evidence.union, 307_200)

    def test_direction_margin_equality_and_reverse_false(self):
        a = marker((0, 0, 0, 0))
        cfg = config(direction_margin_px=2)
        for point, expected in ((0, Truth.FALSE), (1, Truth.UNKNOWN),
                                (2, Truth.UNKNOWN), (3, Truth.TRUE)):
            b = marker((point, point, point, point), 1)
            with self.subTest(point=point):
                self.assert_truth("left_of", a, b, expected, cfg)
                self.assert_truth("above", a, b, expected, cfg)
                self.assert_truth("right_of", a, b, Truth.FALSE, cfg)
                self.assert_truth("below", a, b, Truth.FALSE, cfg)

    def test_half_pixel_centers_are_not_rounded_to_integer_pixels(self):
        a = marker((0, 0, 0, 0))
        b = marker((0, 0, 1, 1), 1)
        result = self.assert_truth("left_of", a, b, Truth.TRUE)
        self.assert_truth("above", a, b, Truth.TRUE)
        self.assertEqual(result.evidence.delta_cx2, 1)
        self.assertEqual(result.evidence.delta_cy2, 1)
        self.assertEqual(result.evidence.distance_sq_center2, 2)
        self.assert_truth("near_2d", a, b, Truth.FALSE)
        self.assert_truth("near_2d", a, b, Truth.TRUE,
                          config(near_true_radius_px=1, near_false_radius_px=1))

    def test_same_center_is_false_for_all_directions_and_near_at_zero(self):
        a = marker((1, 1, 3, 3))
        b = marker((2, 2, 2, 2), 1)
        for predicate in ("left_of", "right_of", "above", "below"):
            self.assert_truth(predicate, a, b, Truth.FALSE)
        self.assert_truth("near_2d", a, b, Truth.TRUE)

    def test_diagonal_relations_can_both_be_true(self):
        a = marker((0, 0, 1, 1))
        b = marker((10, 10, 11, 11), 1)
        self.assert_truth("left_of", a, b, Truth.TRUE)
        self.assert_truth("above", a, b, Truth.TRUE)

    def test_shared_inclusive_endpoint_has_one_pixel_of_intersection(self):
        a = marker((0, 0, 1, 0))
        b = marker((1, 0, 2, 0), 1)
        cfg = config(iou_true=Ratio(1, 3))
        result = self.assert_truth("bbox_overlap", a, b, Truth.TRUE, cfg)
        self.assertEqual(result.evidence.intersection, 1)
        self.assertEqual(result.evidence.union, 3)
        adjacent = marker((2, 0, 3, 0), 1)
        self.assert_truth("bbox_overlap", a, adjacent, Truth.FALSE, cfg)

    def test_overlap_threshold_equality_and_band(self):
        # Independent hand calculation: I=1, U=3, IoU=1/3 exactly.
        a = marker((0, 0, 1, 0))
        b = marker((1, 0, 2, 0), 1)
        self.assert_truth("bbox_overlap", a, b, Truth.TRUE,
                          config(iou_false=Ratio(0, 1), iou_true=Ratio(1, 3)))
        self.assert_truth("bbox_overlap", a, b, Truth.UNKNOWN,
                          config(iou_false=Ratio(1, 3), iou_true=Ratio(2, 3)))
        self.assert_truth("bbox_overlap", a, b, Truth.FALSE,
                          config(iou_false=Ratio(1, 2), iou_true=Ratio(2, 3)))
        self.assert_truth("bbox_overlap", a, b, Truth.UNKNOWN,
                          config(iou_false=Ratio(1, 4), iou_true=Ratio(1, 2)))

    def test_zero_intersection_is_false_even_with_zero_true_threshold(self):
        cfg = config(iou_false=Ratio(0, 1), iou_true=Ratio(0, 1))
        for b in ((1, 0, 1, 0), (0, 1, 0, 1), (639, 479, 639, 479)):
            with self.subTest(box=b):
                self.assert_truth("bbox_overlap", marker((0, 0, 0, 0)),
                                  marker(b, 1), Truth.FALSE, cfg)

    def test_full_frame_single_pixel_iou_and_large_exact_ratio_products(self):
        a = marker((0, 0, 639, 479), count=307_200)
        b = marker((639, 479, 639, 479), 1)
        scale = 10 ** 40
        cfg = config(iou_false=Ratio(0, 1),
                     iou_true=Ratio(scale, 307_200 * scale))
        self.assert_truth("bbox_overlap", a, b, Truth.TRUE, cfg)

    def test_near_uses_square_distance_and_inclusive_true_boundary(self):
        # The 3/4/5 triangle fixes the radius equality without sqrt rounding.
        a = marker((0, 0, 0, 0))
        b = marker((3, 4, 3, 4), 1)
        self.assert_truth("near_2d", a, b, Truth.TRUE,
                          config(near_true_radius_px=5, near_false_radius_px=8))
        self.assert_truth("near_2d", a, b, Truth.UNKNOWN,
                          config(near_true_radius_px=4, near_false_radius_px=5))
        self.assert_truth("near_2d", a, b, Truth.FALSE,
                          config(near_true_radius_px=3, near_false_radius_px=4))

    def test_roi_includes_equal_edges_and_rejects_each_outside_edge(self):
        boundary = roi((1, 1, 4, 4))
        for box in ((1, 1, 4, 4), (1, 1, 1, 1), (4, 4, 4, 4), (2, 2, 3, 3)):
            with self.subTest(box=box):
                self.assert_truth("bbox_within_roi", marker(box), boundary, Truth.TRUE)
        for box in ((0, 1, 4, 4), (1, 0, 4, 4), (1, 1, 5, 4),
                    (1, 1, 4, 5), (8, 8, 8, 8)):
            with self.subTest(box=box):
                self.assert_truth("bbox_within_roi", marker(box), boundary, Truth.FALSE)

    def test_roi_does_not_require_visual_count(self):
        boundary = roi((0, 0, 639, 479))
        self.assertIsNone(boundary.count)
        self.assert_truth("bbox_within_roi", marker((12, 20, 12, 20)), boundary, Truth.TRUE)
        with self.assertRaises(ValueError):
            replace(boundary, count=0)

    def test_missing_measurement_is_unknown_and_keeps_reason(self):
        valid = marker((1, 1, 2, 2), 1)
        for count, reason in ((0, "no_pixels"), (2, "below_min_area")):
            missing = Region(0, snapshot(), "pl_color_stats", False, None, count, reason)
            for a, b, expected_reason in (
                    (missing, valid, "subject_invalid:" + reason),
                    (valid, missing, "object_invalid:" + reason)):
                with self.subTest(count=count, subject=a.marker_id):
                    result = evaluate("left_of", a, b, config())
                    self.assertEqual(result.truth, Truth.UNKNOWN)
                    self.assertEqual(result.reason, expected_reason)
                    self.assertIsNone(result.evidence)
        missing_roi = Region(3, snapshot(), "configured_roi", False, None,
                             None, "roi_not_configured")
        result = evaluate("bbox_within_roi", marker((1, 1, 2, 2)), missing_roi, config())
        self.assertEqual(result.truth, Truth.UNKNOWN)
        self.assertEqual(result.reason, "object_invalid:roi_not_configured")

    def test_incomplete_frame_cannot_produce_relation(self):
        for side in ("subject", "object"):
            a, b = marker((0, 0, 0, 0)), marker((10, 10, 10, 10), 1)
            if side == "subject":
                a = replace(a, snapshot=replace(a.snapshot, frame_complete=False))
            else:
                b = replace(b, snapshot=replace(b.snapshot, frame_complete=False))
            with self.subTest(side=side):
                result = evaluate("left_of", a, b, config())
                self.assertEqual(result.truth, Truth.UNKNOWN)
                self.assertEqual(result.reason, "frame_incomplete")
                self.assertIsNone(result.evidence)

    def test_each_snapshot_or_config_mismatch_is_unknown(self):
        a = marker((0, 0, 0, 0))
        cases = (
            ({"session_id": "another-session"}, "session_mismatch"),
            ({"measurement_frame_seq": 99}, "measurement_frame_mismatch"),
            ({"measurement_frame_seq": 101}, "measurement_frame_mismatch"),
            ({"config_epoch": 8}, "config_epoch_mismatch"),
            ({"width": 639}, "dimensions_mismatch"),
            ({"height": 479}, "dimensions_mismatch"),
            ({"mask_version": 1}, "mask_version_mismatch"),
        )
        for change, reason in cases:
            b = marker((10, 10, 10, 10), 1, snapshot(**change))
            with self.subTest(change=change):
                result = evaluate("left_of", a, b, config())
                self.assertEqual(result.truth, Truth.UNKNOWN)
                self.assertEqual(result.reason, reason)
                self.assertIsNone(result.evidence)
                self.assertIsNone(result.snapshot)
        result = evaluate("left_of", a, marker((10, 10, 10, 10), 1),
                          config(config_epoch=8))
        self.assertEqual(result.truth, Truth.UNKNOWN)
        self.assertEqual(result.reason, "config_epoch_mismatch")
        self.assertIsNone(result.evidence)

    def test_uint32_frame_extremes_are_valid_but_wrap_pair_does_not_match(self):
        for seq in (0, 0xFFFF_FFFF):
            snap = snapshot(measurement_frame_seq=seq)
            self.assert_truth("left_of", marker((0, 0, 0, 0), snap=snap),
                              marker((2, 0, 2, 0), 1, snap), Truth.TRUE)
        result = evaluate("left_of", marker((0, 0, 0, 0),
                          snap=snapshot(measurement_frame_seq=0xFFFF_FFFF)),
                          marker((2, 0, 2, 0), 1, snapshot(measurement_frame_seq=0)),
                          config())
        self.assertEqual(result.truth, Truth.UNKNOWN)
        self.assertEqual(result.reason, "measurement_frame_mismatch")

    def test_rejects_malformed_bbox_types_and_order(self):
        for values in ((-1, 0, 1, 1), (0, -1, 1, 1), (2, 0, 1, 1),
                       (0, 2, 1, 1), (0.0, 0, 1, 1), (False, 0, 1, 1),
                       (0, "0", 1, 1), (0, 0, None, 1)):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    BBox(*values)
        for box in ((640, 0, 640, 0), (0, 480, 0, 480), (0, 0, 640, 479)):
            with self.subTest(box=box):
                with self.assertRaises(ValueError):
                    marker(box)

    def test_rejects_malformed_snapshot_values(self):
        bad = (
            {"session_id": ""}, {"session_id": None}, {"session_id": 1},
            {"measurement_frame_seq": -1}, {"measurement_frame_seq": 2 ** 32},
            {"measurement_frame_seq": True}, {"measurement_frame_seq": 1.0},
            {"config_epoch": -1}, {"config_epoch": False}, {"config_epoch": "7"},
            {"width": 0}, {"width": True}, {"width": 640.0},
            {"height": -1}, {"height": None},
            {"mask_version": 0}, {"mask_version": 3}, {"mask_version": True},
            {"frame_complete": 1}, {"frame_complete": "true"},
        )
        for changes in bad:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    snapshot(**changes)

    def test_rejects_malformed_ratios_and_config_values(self):
        for numerator, denominator in ((-1, 2), (3, 2), (0, 0), (1, -1),
                                       (True, 2), (0, False), (0.5, 1), (0, "1")):
            with self.subTest(ratio=(numerator, denominator)):
                with self.assertRaises(ValueError):
                    Ratio(numerator, denominator)
        self.assertEqual(Ratio(0, 1).numerator, 0)
        self.assertEqual(Ratio(1, 1).denominator, 1)
        bad = (
            {"config_epoch": -1}, {"config_epoch": True},
            {"direction_margin_px": -1}, {"direction_margin_px": 1.5},
            {"direction_margin_px": False}, {"iou_false": (0, 1)},
            {"iou_true": 1},
            {"iou_false": Ratio(2, 3), "iou_true": Ratio(1, 3)},
            {"near_true_radius_px": -1}, {"near_false_radius_px": -1},
            {"near_true_radius_px": True}, {"near_false_radius_px": 1.0},
            {"near_true_radius_px": 2, "near_false_radius_px": 1},
        )
        for changes in bad:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    config(**changes)

    def test_rejects_malformed_region_fields_and_validity_combinations(self):
        valid = marker((0, 0, 1, 1))
        bad = (
            {"marker_id": -1}, {"marker_id": 3}, {"marker_id": True},
            {"marker_id": "0"}, {"snapshot": None}, {"source": "other"},
            {"source": "configured_roi"}, {"measurement_valid": 1},
            {"bbox": (0, 0, 1, 1)}, {"bbox": None},
            {"count": None}, {"count": 0}, {"count": -1}, {"count": 5},
            {"count": True}, {"count": 1.0}, {"invalid_reason": "no_pixels"},
            {"measurement_valid": False},
        )
        for changes in bad:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    replace(valid, **changes)
        for changes in ({"invalid_reason": None}, {"invalid_reason": ""},
                        {"invalid_reason": 1}, {"count": -1},
                        {"count": True}, {"bbox": BBox(0, 0, 0, 0)}):
            fields = dict(marker_id=0, snapshot=snapshot(), source="pl_color_stats",
                          measurement_valid=False, bbox=None, count=0,
                          invalid_reason="no_pixels")
            fields.update(changes)
            with self.subTest(invalid_changes=changes):
                with self.assertRaises(ValueError):
                    Region(**fields)
        with self.assertRaises(ValueError):
            replace(roi((0, 0, 1, 1)), marker_id=2)

    def test_rejects_bad_evaluate_arguments_self_pair_and_roi_roles(self):
        a, b = marker((0, 0, 0, 0)), marker((2, 2, 2, 2), 1)
        for predicate, subject, obj, cfg in (
                ("unsupported", a, b, config()), (None, a, b, config()),
                (1, a, b, config()), ("left_of", None, b, config()),
                ("left_of", a, {}, config()), ("left_of", a, b, None),
                ("left_of", a, a, config()),
                ("left_of", a, replace(b, marker_id=0), config()),
                ("bbox_within_roi", a, b, config()),
                ("bbox_within_roi", roi((0, 0, 10, 10)), a, config())):
            with self.subTest(predicate=predicate, subject=subject, obj=obj):
                with self.assertRaises(ValueError):
                    evaluate(predicate, subject, obj, cfg)

    def test_10000_fixed_seed_pairs_against_fraction_oracle_and_invariants(self):
        rng = random.Random(RANDOM_SEED)
        truths_seen = {predicate: set() for predicate in PREDICATES}
        for case in range(RANDOM_PAIRS):
            width, height = rng.randint(1, 640), rng.randint(1, 480)

            def random_box():
                x0, x1 = sorted((rng.randrange(width), rng.randrange(width)))
                y0, y1 = sorted((rng.randrange(height), rng.randrange(height)))
                return x0, y0, x1, y1

            box_a, box_b = random_box(), random_box()
            geometry = oracle_geometry(box_a, box_b)
            snap = snapshot(width=width, height=height,
                            measurement_frame_seq=case, mask_version=rng.choice((1, 2)))
            a = marker(box_a, snap=snap, count=rng.randint(1, geometry["area_a"]))
            b = marker(box_b, 1, snap, rng.randint(1, geometry["area_b"]))
            ratios = []
            for _ in range(2):
                denominator = rng.randint(1, 64)
                ratios.append((rng.randint(0, denominator), denominator))
            ratios.sort(key=lambda pair: Fraction(*pair))
            near_true, near_false = sorted((rng.randint(0, 800), rng.randint(0, 800)))
            cfg = config(direction_margin_px=rng.randint(0, max(width, height)),
                         iou_false=Ratio(*ratios[0]), iou_true=Ratio(*ratios[1]),
                         near_true_radius_px=near_true, near_false_radius_px=near_false)
            results = {}
            with self.subTest(case=case, seed=RANDOM_SEED, a=box_a, b=box_b):
                for predicate in PREDICATES:
                    obj = roi(box_b, snap) if predicate == "bbox_within_roi" else b
                    expected = oracle_truth(predicate, geometry, cfg)
                    result = self.assert_truth(predicate, a, obj, expected, cfg)
                    results[predicate] = result.truth
                    truths_seen[predicate].add(result.truth)
                    evidence = result.evidence
                    self.assertEqual(evidence.subject_area, geometry["area_a"])
                    self.assertEqual(evidence.object_area, geometry["area_b"])
                    self.assertEqual(evidence.intersection, geometry["intersection"])
                    self.assertEqual(evidence.union, geometry["union"])
                    self.assertEqual(evidence.delta_cx2, 2 * geometry["dx"])
                    self.assertEqual(evidence.delta_cy2, 2 * geometry["dy"])
                    self.assertEqual(evidence.distance_sq_center2,
                                     4 * geometry["distance_sq"])
                # Independent symmetry and direction consistency constraints.
                self.assertEqual(results["left_of"], evaluate("right_of", b, a, cfg).truth)
                self.assertEqual(results["above"], evaluate("below", b, a, cfg).truth)
                for predicate in ("bbox_overlap", "near_2d"):
                    self.assertEqual(results[predicate], evaluate(predicate, b, a, cfg).truth)
                self.assertFalse(results["left_of"] is Truth.TRUE and
                                 results["right_of"] is Truth.TRUE)
                self.assertFalse(results["above"] is Truth.TRUE and
                                 results["below"] is Truth.TRUE)
                self.assertEqual(evaluate("bbox_within_roi", a,
                                          roi((0, 0, width - 1, height - 1), snap),
                                          cfg).truth, Truth.TRUE)
        for predicate, seen in truths_seen.items():
            expected = {Truth.TRUE, Truth.FALSE}
            if predicate != "bbox_within_roi":
                expected.add(Truth.UNKNOWN)
            self.assertEqual(seen, expected, predicate)


if __name__ == "__main__":
    unittest.main()
