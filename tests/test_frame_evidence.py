"""Evidence must preserve bytes/provenance and reject misleading or old inputs."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.pc.frame_evidence import ROOT, read_frame_bundle, save_frame_bundle
from src.pc.vendor_udp import Frame
from tools.measure_saved_rgb565 import measure_bundle


class FrameEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "input.rgb565"
        self.frame = Frame(b"\xf8\x00" * (640 * 480), frame_seq=42)

    def test_exact_bytes_and_demo_provenance_survive_round_trip(self):
        metadata = save_frame_bundle(self.frame, self.path, source="synthetic_demo")
        data, loaded = read_frame_bundle(self.path)
        self.assertEqual(data, self.frame.rgb565_be)
        self.assertEqual(metadata, loaded)
        self.assertEqual(loaded["source"], "synthetic_demo")
        self.assertEqual(loaded["frame_seq"], 42)
        self.assertEqual(loaded["input_sha256"], hashlib.sha256(data).hexdigest())
        self.assertIn("host_saved_at_utc", loaded)
        self.assertNotIn("pl_measurement", loaded)

    def test_refuses_either_existing_file_without_modification(self):
        for occupied in (self.path, self.path.with_suffix(".rgb565.json")):
            with self.subTest(occupied=occupied.suffix):
                occupied.write_bytes(b"old evidence")
                with self.assertRaises(FileExistsError):
                    save_frame_bundle(self.frame, self.path, source="live_camera")
                self.assertEqual(occupied.read_bytes(), b"old evidence")
                occupied.unlink()
                self.assertFalse(self.path.exists())
                self.assertFalse(self.path.with_suffix(".rgb565.json").exists())

    def test_sidecar_race_preserves_other_writer_and_removes_own_raw(self):
        original_open = Path.open
        sidecar = self.path.with_suffix(".rgb565.json")

        def raced_open(path, *args, **kwargs):
            if path == sidecar and args[0] == "x":
                with original_open(path, "w", encoding="utf-8") as handle:
                    handle.write("other writer")
                raise FileExistsError("sidecar race")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", raced_open), self.assertRaises(FileExistsError):
            save_frame_bundle(self.frame, self.path, source="live_camera")
        self.assertFalse(self.path.exists())
        self.assertEqual(sidecar.read_text(), "other writer")

    def test_invalid_size_dimensions_source_and_public_path_rejected(self):
        cases = [(Frame(b"\x00"), self.path, "live_camera"),
                 (Frame(self.frame.rgb565_be, width=320, height=960), self.path, "live_camera"),
                 (self.frame, self.path, "unknown"),
                 (self.frame, ROOT / "data/forbidden-evidence.rgb565", "live_camera")]
        for frame, path, source in cases:
            with self.subTest(source=source, width=frame.width), self.assertRaises(ValueError):
                save_frame_bundle(frame, path, source=source)
        self.assertFalse(self.path.exists())

    def test_changed_bytes_or_metadata_rejected_before_analysis(self):
        save_frame_bundle(self.frame, self.path, source="live_camera")
        self.path.write_bytes(b"\x00\x00" + self.frame.rgb565_be[2:])
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            measure_bundle(self.path)
        self.path.write_bytes(self.frame.rgb565_be)
        sidecar = self.path.with_suffix(".rgb565.json")
        data = json.loads(sidecar.read_text())
        data["width"] = 640.0
        sidecar.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "metadata"):
            measure_bundle(self.path)

    def test_cli_same_input_all_red_matches_hand_calculated_both_masks(self):
        save_frame_bundle(self.frame, self.path, source="synthetic_demo")
        output = self.path.parent / "measurements.json"
        process = subprocess.run([sys.executable, str(ROOT / "tools/measure_saved_rgb565.py"),
                                  "--input", str(self.path), "--output", str(output)],
                                 capture_output=True, text=True, check=False)
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(output.read_text())
        self.assertEqual(report["scope"], "offline_not_board")
        self.assertEqual(report["source"], "synthetic_demo")
        self.assertEqual(report["input_sha256"], "82764ed06ca9dd3c9c9caaa0ade5318aa135abbd2f11cad36f9aa1e2aa944440")
        self.assertEqual(report["masks"]["1"], {
            "valid": True, "count": 307200, "sum_x": 98150400, "sum_y": 73574400,
            "bbox": [0, 0, 639, 479], "centroid_mask_floor": [319, 239]})
        self.assertEqual(report["masks"]["2"], {
            "valid": True, "count": 304964, "sum_x": 97435998, "sum_y": 73038878,
            "bbox": [1, 1, 638, 478], "centroid_mask_floor": [319, 239]})

    def test_cli_bad_input_preserves_existing_outputs_and_creates_no_report(self):
        output = self.path.parent / "result.json"
        command = [sys.executable, str(ROOT / "tools/measure_saved_rgb565.py"),
                   "--input", str(self.path), "--output", str(output)]
        process = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(process.returncode, 2)
        self.assertFalse(output.exists())
        output.write_text("old report")
        process = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(output.read_text(), "old report")


class ViewerEvidenceTests(unittest.TestCase):
    def test_dialog_poll_does_not_change_saved_snapshot_or_source(self):
        from src.pc.camera_viewer import Viewer
        first = Frame(b"first")
        viewer = SimpleNamespace(last_raw_frame=first, last_raw_source="synthetic_demo", detail=Mock())

        def dialog(**kwargs):
            viewer.last_raw_frame = Frame(b"newer")
            viewer.last_raw_source = "live_camera"
            return "D:/snapshot.rgb565"

        with patch("src.pc.camera_viewer.filedialog.asksaveasfilename", side_effect=dialog), \
             patch("src.pc.camera_viewer.save_frame_bundle") as save:
            Viewer.save_raw_frame(viewer)
        save.assert_called_once_with(first, Path("D:/snapshot.rgb565"), source="synthetic_demo")

    def test_no_frame_and_cancel_do_not_write(self):
        from src.pc.camera_viewer import Viewer
        viewer = SimpleNamespace(last_raw_frame=None, last_raw_source=None, detail=Mock())
        with patch("src.pc.camera_viewer.messagebox.showinfo") as info, \
             patch("src.pc.camera_viewer.filedialog.asksaveasfilename", return_value="") as dialog, \
             patch("src.pc.camera_viewer.save_frame_bundle") as save:
            Viewer.save_raw_frame(viewer)
            info.assert_called_once()
            dialog.assert_not_called()
            viewer.last_raw_frame, viewer.last_raw_source = Frame(b"raw"), "live_camera"
            Viewer.save_raw_frame(viewer)
            save.assert_not_called()

    def test_clear_preview_discards_previous_raw_source(self):
        from src.pc.camera_viewer import Viewer
        viewer = SimpleNamespace(canvas=Mock(), image_item=1, empty_item=2, demo_item=3,
                                 last_raw_frame=Frame(b"raw"), last_raw_source="live_camera")
        Viewer._clear_preview(viewer)
        self.assertIsNone(viewer.last_raw_frame)
        self.assertIsNone(viewer.last_raw_source)

    def test_write_error_visible_and_no_success_message(self):
        from src.pc.camera_viewer import Viewer
        viewer = SimpleNamespace(last_raw_frame=Frame(b"raw"), last_raw_source="live_camera", detail=Mock())
        with patch("src.pc.camera_viewer.filedialog.asksaveasfilename", return_value="D:/snapshot.rgb565"), \
             patch("src.pc.camera_viewer.save_frame_bundle", side_effect=FileExistsError("old evidence")), \
             patch("src.pc.camera_viewer.messagebox.showerror") as error:
            Viewer.save_raw_frame(viewer)
        error.assert_called_once()
        viewer.detail.set.assert_not_called()
