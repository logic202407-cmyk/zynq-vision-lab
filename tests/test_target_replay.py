"""Independent fixture checks and host replay rejection behavior."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sim.reference.red_mask import Measurement
from src.pc.target_replay import (check_cases, load_cases, main, make_frame,
                                  make_record, make_sequence_records, read_records,
                                  validate_record, SEQUENCES)


class TargetReplayTests(unittest.TestCase):
    def setUp(self):
        self.cases = load_cases()
        self.record = make_record(self.cases[1], 0, 1)

    def test_analytical_masks_match_current_reference(self):
        result = check_cases(self.cases)
        self.assertTrue(result["passed"], result["results"])
        self.assertEqual(result["cases_compared"], 22)
        self.assertFalse(result["board_verified"])

    def test_reference_mutation_is_detected(self):
        with patch("src.pc.target_replay.measure_red_pixels", return_value=Measurement(0, False, 0, None, None)):
            result = check_cases([self.cases[1]])
        self.assertFalse(result["passed"])
        self.assertIn("count", result["results"][0]["differences"])

    def test_generator_keeps_rgb565_big_endian_and_expected_box(self):
        frame = make_frame(self.cases[1])
        self.assertEqual(len(frame), 614400)
        self.assertEqual(frame[(238 * 640 + 318)*2: (238 * 640 + 318)*2+2], b"\xf8\x00")
        self.assertEqual(frame[:2], b"\x00\x00")
        target = make_record(self.cases[1], 0, 2)["target"]
        self.assertEqual(target["count"], 21)
        self.assertEqual(target["sum_x"], 6720)
        self.assertEqual(target["sum_y"], 5040)

    def test_invalid_measurement_never_reuses_previous_coordinates(self):
        lost = make_record(self.cases[0], 1, 1)
        self.assertIsNone(lost["target"]["bbox"])
        lost["target"]["bbox"] = self.record["target"]["bbox"]
        with self.assertRaises(ValueError):
            validate_record(lost)

    def test_rejects_illegal_fields(self):
        for field, value in (("measurement_frame_seq", True), ("mask_version", 3),
                             ("width", 320), ("frame_complete", False),
                             ("source", "pl_color_stats"), ("timestamp_kind", "camera"),
                             ("timestamp_ms", -1), ("schema_version", "future")):
            with self.subTest(field=field):
                record = copy.deepcopy(self.record)
                record[field] = value
                with self.assertRaises(ValueError):
                    validate_record(record)

    def test_rejects_geometry_and_sum_errors(self):
        for field, value in (("bbox", [-1, 238, 322, 242]),
                             ("bbox", [318, 238, 317, 242]),
                             ("bbox", [318, 238, 640, 242]),
                             ("count", 26), ("sum_x", 0),
                             ("centroid_mask_floor", [320, 241]),
                             ("centroid_mask_floor", [320.0, 240]),
                             ("marker_id", True)):
            with self.subTest(field=field):
                record = copy.deepcopy(self.record)
                record["target"][field] = value
                with self.assertRaises(ValueError):
                    validate_record(record)

    def read(self, records):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "frames.jsonl"
            path.write_text("".join(json.dumps(r)+"\n" for r in records), encoding="utf-8")
            return list(read_records(path))

    def test_rejects_duplicate_gap_and_out_of_order(self):
        for seq in (1, 3, 0):
            with self.subTest(seq=seq):
                following = make_record(self.cases[0], 1, 1)
                following["measurement_frame_seq"] = seq
                with self.assertRaisesRegex(ValueError, "sequence"):
                    self.read([self.record, following])

    def test_rejects_time_reversal(self):
        first = copy.deepcopy(self.record)
        first["timestamp_ms"] = 100
        with self.assertRaisesRegex(ValueError, "timestamp"):
            self.read([first, make_record(self.cases[0], 1, 1)])

    def test_sequence_wrap_and_new_session(self):
        first = copy.deepcopy(self.record)
        first["measurement_frame_seq"] = 0xFFFFFFFF
        following = make_record(self.cases[0], 1, 1)
        following["measurement_frame_seq"] = 0
        restart = make_record(self.cases[1], 0, 2)
        restart["session_id"] = "restarted"
        self.assertEqual(len(self.read([first, following, restart])), 3)

    def test_config_epoch_change_is_preserved_without_claiming_confirmation(self):
        following = make_record(self.cases[0], 1, 2)
        records = self.read([self.record, following])
        self.assertEqual([r["config_epoch"] for r in records], [1, 2])
        self.assertNotIn("confirmed", records[1])

    def test_empty_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty replay"):
            self.read([])

    def test_cli_generated_replay_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "frames.jsonl"
            self.assertEqual(main(["generate", "--output", str(path), "--mask-version", "2"]), 0)
            self.assertEqual(len(list(read_records(path))), 11)

    def test_loss_sequence_clears_then_reacquires(self):
        records = self.read(make_sequence_records("acquire_loss_reacquire", 2))
        self.assertEqual([r["target"]["valid"] for r in records], [True]*4 + [False]*4 + [True]*4)
        for record in records[4:8]:
            self.assertEqual(record["target"]["count"], 0)
            self.assertIsNone(record["target"]["centroid_mask_floor"])
        self.assertEqual(records[8]["target"]["count"], 21)

    def test_pause_replay_uses_timestamps_without_sleeping_in_test(self):
        records = make_sequence_records("receive_pause", 1)
        self.assertEqual(records[3]["timestamp_ms"] - records[2]["timestamp_ms"], 600)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "pause.jsonl"
            path.write_text("".join(json.dumps(r)+"\n" for r in records), encoding="utf-8")
            with patch("src.pc.target_replay.time.sleep") as sleep, patch("builtins.print"):
                main(["replay", "--input", str(path), "--realtime"])
            self.assertEqual([args.args[0] for args in sleep.call_args_list], [0.033, 0.033, 0.6, 0.033])

    def test_session_restart_and_config_change_sequences(self):
        restarted = self.read(make_sequence_records("session_restart", 1))
        self.assertNotEqual(restarted[2]["session_id"], restarted[3]["session_id"])
        self.assertEqual(restarted[3]["measurement_frame_seq"], 1)
        self.assertEqual(restarted[3]["timestamp_ms"], 0)
        changed = self.read(make_sequence_records("config_change", 1))
        self.assertEqual([r["config_epoch"] for r in changed], [1]*3 + [2]*3)
        self.assertEqual([r["target"]["count"] for r in changed], [25]*3 + [21]*3)

    def test_sequence_fixture_rejects_unknown_case_reversal_and_reopened_session(self):
        original = json.loads(SEQUENCES.read_text(encoding="utf-8"))
        mutations = [({"case_id": "unknown"}, KeyError),
                     ({"timestamp_ms": -1}, ValueError),
                     ({"timestamp_ms": 0}, ValueError),
                     ({"session": "b"}, ValueError),
                     ({"mask_version": True}, ValueError)]
        for changes, error in mutations:
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as temp:
                doc = copy.deepcopy(original)
                doc["sequences"][0]["events"][2].update(changes)
                path = Path(temp) / "bad.json"
                path.write_text(json.dumps(doc), encoding="utf-8")
                with self.assertRaises(error):
                    make_sequence_records("acquire_loss_reacquire", 1, path)
        with self.assertRaises(ValueError):
            make_sequence_records("missing", 1)

    def test_sequence_cli_round_trip_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sequence.jsonl"
            args = ["generate", "--sequence", "noise_small", "--mask-version", "2", "--output", str(path)]
            self.assertEqual(main(args), 0)
            records = list(read_records(path))
            self.assertEqual([r["target"]["count"] for r in records], [0, 0, 0, 1, 21, 21, 0])
            before = path.read_bytes()
            with patch("sys.stderr"), self.assertRaises(SystemExit) as raised:
                main(args)
            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
