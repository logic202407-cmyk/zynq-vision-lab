"""Offline acceptance cases with hand-counted pixels and no board/network I/O."""

import contextlib
import hashlib
import io
import itertools
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.pc import pl_compare
from src.pc.pl_compare import compare_frames
from src.pc.vendor_udp import (
    BOARD_IP, UDP_PORT, START_COMMAND, STOP_COMMAND, Frame, FrameAssembler,
    PLMeasurement,
)


def image(width, height, points=()):
    red = set(points)
    return b"".join(
        (0xF800 if (x, y) in red else 0).to_bytes(2, "big")
        for y in range(height) for x in range(width)
    )


def measurement(seq, count, sum_x, sum_y, bbox, version=1, complete=True):
    return PLMeasurement(seq, complete, count > 0, count, sum_x, sum_y,
                         bbox, version)


def pair(raw, width, height, result, seq=1):
    return [
        Frame(raw, width, height, frame_seq=seq),
        # Deliberately different pixels: the result belongs to the stored image.
        Frame(image(width, height), width, height, frame_seq=seq + 1,
              previous_measurement=result),
    ]


class CompareFramesTests(unittest.TestCase):
    def assert_failed(self, summary, reason):
        self.assertFalse(summary["passed"])
        self.assertIn(reason, summary["failure_reasons"])

    def test_v1_exact_hand_counted_pair_and_input_identity(self):
        # Four hits at (1,1), (2,1), (1,2), (2,2): sums are 6,6.
        raw = image(4, 4, {(1, 1), (2, 1), (1, 2), (2, 2)})
        result = measurement(1, 4, 6, 6, (1, 1, 2, 2))
        summary = compare_frames(pair(raw, 4, 4, result), required_frames=1,
                                 expected_mask_version=1)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["failure_reasons"], [])
        self.assertEqual(summary["compared"], 1)
        self.assertEqual(summary["mismatch_count"], 0)
        record = summary["comparisons"][0]
        self.assertEqual(record["seq"], 1)
        self.assertEqual(record["mask_version"], 1)
        self.assertEqual(record["input_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertTrue(record["matches"])
        self.assertEqual(record["pl"]["sum_x"], 6)
        self.assertEqual(record["pl"]["sum_y"], 6)
        self.assertEqual(record["software"]["sum_x"], 6)
        self.assertEqual(record["software"]["sum_y"], 6)
        self.assertIsNotNone(summary["first_match"])

    def test_v2_full_red_counts_only_interior_coordinates(self):
        raw = image(4, 4, {(x, y) for y in range(4) for x in range(4)})
        # The excluded border leaves the same four interior coordinates.
        result = measurement(1, 4, 6, 6, (1, 1, 2, 2), version=2)
        summary = compare_frames(pair(raw, 4, 4, result), required_frames=1,
                                 expected_mask_version=2)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["mismatch_count"], 0)

    def test_v2_five_votes_keep_the_center(self):
        raw = image(3, 3, {(0, 0), (1, 0), (2, 0), (0, 1), (1, 1)})
        result = measurement(1, 1, 1, 1, (1, 1, 1, 1), version=2)
        summary = compare_frames(pair(raw, 3, 3, result), required_frames=1,
                                 expected_mask_version=2)
        self.assertTrue(summary["passed"])

    def test_v2_four_votes_produce_a_matched_no_target_result(self):
        raw = image(3, 3, {(0, 0), (1, 0), (2, 0), (0, 1)})
        result = measurement(1, 0, 0, 0, None, version=2)
        summary = compare_frames(pair(raw, 3, 3, result), required_frames=1,
                                 expected_mask_version=2,
                                 compare_raw_mask=True)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["box_variation"]["pl_mask"]["valid_results"], 0)
        self.assertEqual(summary["box_variation"]["pl_mask"]["missing_results"], 1)
        self.assertEqual(summary["box_variation"]["raw_mask"]["valid_results"], 1)

    def test_exact_sum_error_with_unchanged_floor_centroid_is_rejected(self):
        raw = image(4, 4, {(1, 1), (2, 1), (1, 2), (2, 2)})
        for sum_x, sum_y in ((7, 6), (6, 7)):
            with self.subTest(sum_x=sum_x, sum_y=sum_y):
                result = measurement(1, 4, sum_x, sum_y, (1, 1, 2, 2))
                self.assertEqual(result.centroid, (1, 1))
                summary = compare_frames(pair(raw, 4, 4, result),
                                         required_frames=1)
                self.assert_failed(summary, "measurement_mismatch")
                self.assertEqual(summary["mismatch_count"], 1)
                self.assertFalse(summary["comparisons"][0]["matches"])

    def test_old_mask_cannot_pass_a_v2_acceptance_request(self):
        raw = image(3, 3)
        result = measurement(1, 0, 0, 0, None, version=1)
        summary = compare_frames(pair(raw, 3, 3, result), required_frames=1,
                                 expected_mask_version=2,
                                 compare_raw_mask=True)
        self.assert_failed(summary, "mask_version_mismatch")
        self.assertEqual(summary["mask_version_mismatches"], 1)

    def test_unknown_mask_version_is_rejected_without_a_reference_guess(self):
        frames = pair(image(3, 3), 3, 3, measurement(1, 0, 0, 0, None, 3))
        summary = compare_frames(frames, required_frames=1)
        self.assert_failed(summary, "mask_version_mismatch")
        self.assertEqual(summary["compared"], 0)
        self.assertEqual(summary["observed_mask_versions"], {"3": 1})

    def test_result_sequence_zero_is_reserved_even_for_hand_built_frames(self):
        frames = pair(image(3, 3), 3, 3, measurement(0, 0, 0, 0, None), seq=0)
        summary = compare_frames(frames, required_frames=1)
        self.assert_failed(summary, "sequence_gap")
        self.assertEqual(summary["compared"], 0)

    def test_last_pair_before_uint32_rollover_is_accepted(self):
        frames = pair(image(3, 3), 3, 3,
                      measurement(0xFFFFFFFE, 0, 0, 0, None), seq=0xFFFFFFFE)
        summary = compare_frames(frames, required_frames=1)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["compared"], 1)

    def test_uint32_rollover_through_reserved_zero_is_not_accepted(self):
        frames = [
            Frame(image(3, 3), 3, 3, frame_seq=0xFFFFFFFF),
            Frame(image(3, 3), 3, 3, frame_seq=0,
                  previous_measurement=measurement(0xFFFFFFFF, 0, 0, 0, None)),
        ]
        summary = compare_frames(frames, required_frames=1)
        self.assert_failed(summary, "sequence_gap")
        self.assertEqual(summary["compared"], 0)

    def test_restart_at_the_end_fails_after_an_otherwise_good_pair(self):
        frames = pair(image(3, 3), 3, 3, measurement(5, 0, 0, 0, None), seq=5)
        frames.append(Frame(image(3, 3), 3, 3, frame_seq=1,
                            previous_measurement=None))
        summary = compare_frames(frames, required_frames=1)
        self.assert_failed(summary, "sequence_gap")
        self.assertEqual(summary["compared"], 1)

    def test_mixed_versions_fail_even_when_each_measurement_is_correct(self):
        raw = image(3, 3)
        frames = [
            Frame(raw, 3, 3, frame_seq=1),
            Frame(raw, 3, 3, frame_seq=2,
                  previous_measurement=measurement(1, 0, 0, 0, None, 1)),
            Frame(raw, 3, 3, frame_seq=3,
                  previous_measurement=measurement(2, 0, 0, 0, None, 2)),
        ]
        summary = compare_frames(frames, required_frames=2)
        self.assert_failed(summary, "mixed_mask_versions")
        self.assertEqual(summary["mismatch_count"], 0)
        self.assertEqual(summary["compared"], 2)

    def test_empty_input_cannot_pass(self):
        summary = compare_frames([], required_frames=1)
        self.assert_failed(summary, "insufficient_pairs")
        self.assertEqual(summary["compared"], 0)
        self.assertIsNone(summary["first_match"])
        self.assertEqual(summary["comparisons"], [])

    def test_one_complete_image_is_not_a_comparison(self):
        summary = compare_frames([Frame(image(3, 3), 3, 3, frame_seq=1)],
                                 required_frames=1)
        self.assert_failed(summary, "insufficient_pairs")
        self.assertEqual(summary["compared"], 0)

    def test_too_few_matching_pairs_fail_the_requested_sample_count(self):
        raw = image(3, 3)
        result = measurement(1, 0, 0, 0, None)
        summary = compare_frames(pair(raw, 3, 3, result), required_frames=2)
        self.assert_failed(summary, "insufficient_pairs")
        self.assertEqual(summary["compared"], 1)

    def test_missing_measurement_cannot_be_treated_as_no_target(self):
        summary = compare_frames(pair(image(3, 3), 3, 3, None),
                                 required_frames=1)
        self.assert_failed(summary, "sequence_gap")
        self.assertEqual(summary["sequence_gaps"], 1)
        self.assertEqual(summary["compared"], 0)

    def test_other_frame_measurement_is_never_compared_with_identical_pixels(self):
        # Equal pixels must not hide a missing camera frame/incorrect sequence.
        raw = image(3, 3)
        frames = [Frame(raw, 3, 3, frame_seq=1),
                  Frame(raw, 3, 3, frame_seq=3,
                        previous_measurement=measurement(2, 0, 0, 0, None))]
        summary = compare_frames(frames, required_frames=1)
        self.assert_failed(summary, "sequence_gap")
        self.assertEqual(summary["sequence_gaps"], 1)
        self.assertEqual(summary["compared"], 0)

    def test_reversed_sequence_frames_fail(self):
        raw = image(3, 3)
        frames = [Frame(raw, 3, 3, frame_seq=2),
                  Frame(raw, 3, 3, frame_seq=1,
                        previous_measurement=measurement(0, 0, 0, 0, None))]
        summary = compare_frames(frames, required_frames=1)
        self.assert_failed(summary, "sequence_gap")
        self.assertEqual(summary["compared"], 0)

    def test_duplicate_sequence_fails_after_an_otherwise_good_pair(self):
        raw = image(3, 3)
        result = measurement(1, 0, 0, 0, None)
        frames = pair(raw, 3, 3, result)
        frames.append(Frame(raw, 3, 3, frame_seq=2,
                            previous_measurement=result))
        summary = compare_frames(frames, required_frames=1)
        self.assert_failed(summary, "duplicate_sequence")
        self.assertEqual(summary["duplicate_sequences"], 1)

    def test_incomplete_measurement_fails_even_with_all_zero_fields(self):
        raw = image(3, 3)
        result = measurement(1, 0, 0, 0, None, complete=False)
        summary = compare_frames(pair(raw, 3, 3, result), required_frames=1)
        self.assert_failed(summary, "measurement_mismatch")
        self.assertEqual(summary["mismatch_count"], 1)

    def test_target_loss_breaks_adjacent_box_variation(self):
        width, height = 80, 5
        first = image(width, height, {(1, 2)})
        absent = image(width, height)
        third = image(width, height, {(75, 2)})
        frames = [
            Frame(first, width, height, frame_seq=1),
            Frame(absent, width, height, frame_seq=2,
                  previous_measurement=measurement(1, 1, 1, 2, (1, 2, 1, 2))),
            Frame(third, width, height, frame_seq=3,
                  previous_measurement=measurement(2, 0, 0, 0, None)),
            Frame(absent, width, height, frame_seq=4,
                  previous_measurement=measurement(3, 1, 75, 2, (75, 2, 75, 2))),
        ]
        summary = compare_frames(frames, required_frames=3, compare_raw_mask=True)
        self.assertTrue(summary["passed"])
        for name in ("raw_mask", "pl_mask"):
            variation = summary["box_variation"][name]
            self.assertEqual(variation["valid_results"], 2)
            self.assertEqual(variation["missing_results"], 1)
            self.assertEqual(variation["adjacent_valid_pairs"], 0)
            self.assertEqual(variation["edge_jumps_over_50_pixels"], 0)
            self.assertEqual(variation["left_edge_range"], [1, 75])

    def test_sequence_gap_does_not_create_a_box_jump(self):
        width, height = 80, 5
        first = image(width, height, {(1, 2)})
        later = image(width, height, {(75, 2)})
        frames = [
            Frame(first, width, height, frame_seq=1),
            Frame(first, width, height, frame_seq=2,
                  previous_measurement=measurement(1, 1, 1, 2, (1, 2, 1, 2))),
            Frame(later, width, height, frame_seq=4,
                  previous_measurement=measurement(3, 1, 75, 2, (75, 2, 75, 2))),
            Frame(later, width, height, frame_seq=5,
                  previous_measurement=measurement(4, 1, 75, 2, (75, 2, 75, 2))),
        ]
        summary = compare_frames(frames, required_frames=2, compare_raw_mask=True)
        self.assert_failed(summary, "sequence_gap")
        self.assertEqual(summary["compared"], 2)
        for name in ("raw_mask", "pl_mask"):
            variation = summary["box_variation"][name]
            self.assertEqual(variation["valid_results"], 2)
            self.assertEqual(variation["adjacent_valid_pairs"], 0)
            self.assertEqual(variation["edge_jumps_over_50_pixels"], 0)

    def test_consecutive_valid_boxes_record_real_jumps(self):
        width, height = 80, 5
        first = image(width, height, {(1, 2)})
        second = image(width, height, {(75, 2)})
        frames = [
            Frame(first, width, height, frame_seq=1),
            Frame(second, width, height, frame_seq=2,
                  previous_measurement=measurement(1, 1, 1, 2, (1, 2, 1, 2))),
            Frame(second, width, height, frame_seq=3,
                  previous_measurement=measurement(2, 1, 75, 2, (75, 2, 75, 2))),
        ]
        summary = compare_frames(frames, required_frames=2, compare_raw_mask=True)
        self.assertTrue(summary["passed"])
        for name in ("raw_mask", "pl_mask"):
            variation = summary["box_variation"][name]
            self.assertEqual(variation["missing_results"], 0)
            self.assertEqual(variation["adjacent_valid_pairs"], 1)
            self.assertEqual(variation["edge_jumps_over_50_pixels"], 1)


class CompareCommandTests(unittest.TestCase):
    def run_command(self, frames, *extra_args, stop_error=None):
        receiver = Mock()
        receiver.recvfrom.side_effect = (
            [(b"local-fixture", (BOARD_IP, UDP_PORT)) for _ in frames]
            if frames else socket.timeout
        )
        if stop_error is not None:
            receiver.sendto.side_effect = [1, stop_error]
        assembler = Mock(spec=FrameAssembler)
        assembler.feed.side_effect = frames
        assembler.completed = len(frames)
        assembler.datagrams = len(frames)
        assembler.incomplete = 0
        assembler.malformed = 0
        assembler.orphan_rows = 0
        capture = io.StringIO()
        with patch.object(pl_compare.socket, "socket", return_value=receiver), \
                patch.object(pl_compare, "FrameAssembler", return_value=assembler), \
                patch.object(pl_compare.time, "monotonic",
                             side_effect=itertools.count(step=0.2)), \
                contextlib.redirect_stdout(capture):
            code = pl_compare.main(["--frames", "1", "--seconds", "1", *extra_args])
        receiver.close.assert_called_once_with()
        self.assertEqual(receiver.sendto.call_args_list[0].args,
                         (START_COMMAND, (BOARD_IP, UDP_PORT)))
        self.assertEqual(receiver.sendto.call_args_list[1].args,
                         (STOP_COMMAND, (BOARD_IP, UDP_PORT)))
        return code, json.loads(capture.getvalue())

    def test_cli_exact_sum_error_sets_failure_exit_code(self):
        raw = image(4, 4, {(1, 1), (2, 1), (1, 2), (2, 2)})
        frames = pair(raw, 4, 4, measurement(1, 4, 7, 6, (1, 1, 2, 2)))
        code, summary = self.run_command(frames)
        self.assertEqual(code, 1)
        self.assertFalse(summary["passed"])
        self.assertIn("measurement_mismatch", summary["failure_reasons"])

    def test_cli_v2_request_rejects_v1_with_failure_exit_code(self):
        frames = pair(image(3, 3), 3, 3, measurement(1, 0, 0, 0, None, 1))
        code, summary = self.run_command(frames, "--expected-mask-version", "2",
                                         "--compare-raw-mask")
        self.assertEqual(code, 1)
        self.assertIn("mask_version_mismatch", summary["failure_reasons"])

    def test_cli_no_data_sets_failure_exit_code(self):
        code, summary = self.run_command([])
        self.assertEqual(code, 1)
        self.assertEqual(summary["compared"], 0)
        self.assertIn("insufficient_pairs", summary["failure_reasons"])

    def test_cli_success_saves_exact_statistics_and_input_hash(self):
        raw = image(4, 4, {(x, y) for y in range(4) for x in range(4)})
        frames = pair(raw, 4, 4, measurement(1, 4, 6, 6, (1, 1, 2, 2), 2))
        with tempfile.TemporaryDirectory(prefix="pl_compare_test_") as directory:
            output = Path(directory) / "acceptance.json"
            code, summary = self.run_command(frames, "--expected-mask-version", "2",
                                             "--output", str(output))
            saved = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertTrue(summary["passed"])
        self.assertEqual(saved, summary)
        record = saved["comparisons"][0]
        self.assertEqual(record["input_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(record["pl"]["sum_x"], 6)
        self.assertEqual(record["pl"]["sum_y"], 6)
        self.assertEqual(record["software"]["sum_x"], 6)
        self.assertEqual(record["software"]["sum_y"], 6)
        self.assertEqual(record["mask_version"], 2)
        self.assertNotIn("rgb565_be", record)
        self.assertEqual(set(saved["source_files_sha256"]), {
            "src/pc/pl_compare.py", "src/pc/vendor_udp.py",
            "sim/reference/red_mask.py",
        })

    def test_existing_output_is_preserved_before_socket_creation(self):
        with tempfile.TemporaryDirectory(prefix="pl_compare_test_") as directory:
            output = Path(directory) / "previous.json"
            output.write_text("retain this earlier evidence\n", encoding="utf-8")
            with patch.object(pl_compare.socket, "socket") as constructor, \
                    contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit) as error:
                pl_compare.main(["--output", str(output)])
            self.assertEqual(error.exception.code, 2)
            constructor.assert_not_called()
            self.assertEqual(output.read_text(encoding="utf-8"),
                             "retain this earlier evidence\n")

    def test_stop_command_error_cannot_leave_a_success_exit_code(self):
        frames = pair(image(3, 3), 3, 3, measurement(1, 0, 0, 0, None))
        code, summary = self.run_command(frames, stop_error=OSError("mock stop failure"))
        self.assertEqual(code, 1)
        self.assertFalse(summary["passed"])
        self.assertIn("stop_command_failed", summary["failure_reasons"])
        self.assertEqual(summary["stop_command_error"], "mock stop failure")

    def test_bind_failure_closes_socket_without_sending_commands(self):
        receiver = Mock()
        receiver.bind.side_effect = OSError("mock bind failure")
        with patch.object(pl_compare.socket, "socket", return_value=receiver), \
                self.assertRaisesRegex(OSError, "mock bind failure"):
            pl_compare.main([])
        receiver.close.assert_called_once_with()
        receiver.sendto.assert_not_called()


if __name__ == "__main__":
    unittest.main()
