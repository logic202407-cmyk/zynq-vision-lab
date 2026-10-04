"""Private raw-frame evidence; no networking, image conversion or overlays."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .vendor_udp import Frame, HEIGHT, WIDTH

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "rgb565-frame-evidence/1"
SOURCES = ("live_camera", "synthetic_demo")


def private_output_path(path: Path) -> Path:
    """Raw evidence belongs outside the public tree or in its ignored private/."""
    path = path.resolve()
    if path.is_relative_to(ROOT) and not path.is_relative_to(ROOT / "private"):
        raise ValueError("Evidence must be outside the public repository or in private/")
    return path


def save_frame_bundle(frame: Frame, raw_path: Path, *, source: str) -> dict:
    """Save exact camera-order bytes and a sidecar, refusing either old file.

    Save time is a host timestamp, not exposure time. Source is the UI mode,
    not independently verified camera provenance. No previous-frame PL result
    is copied into the metadata or claimed to describe this snapshot.
    """
    if source not in SOURCES:
        raise ValueError("Unknown frame source")
    if (frame.width, frame.height) != (WIDTH, HEIGHT):
        raise ValueError("Expected a 640x480 frame")
    if len(frame.rgb565_be) != WIDTH * HEIGHT * 2:
        raise ValueError("Expected 614400 RGB565 bytes")
    raw_path = private_output_path(Path(raw_path))
    sidecar = raw_path.with_suffix(raw_path.suffix + ".json")
    if raw_path.exists() or sidecar.exists():
        raise FileExistsError("Raw frame or metadata already exists; use a new name")
    metadata = {
        "schema": SCHEMA, "source": source, "pixel_format": "RGB565_BE",
        "width": WIDTH, "height": HEIGHT, "byte_count": len(frame.rgb565_be),
        "input_sha256": hashlib.sha256(frame.rgb565_be).hexdigest(),
        "frame_seq": frame.frame_seq,
        "host_saved_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "snapshot_not_board_acceptance",
    }
    created = []
    try:
        with raw_path.open("xb") as handle:
            created.append(raw_path)
            handle.write(frame.rgb565_be)
        with sidecar.open("x", encoding="utf-8", newline="\n") as handle:
            created.append(sidecar)
            handle.write(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    return metadata


def read_frame_bundle(raw_path: Path) -> tuple[bytes, dict]:
    """Require this writer's sidecar and verify its input hash before analysis."""
    raw_path = Path(raw_path)
    data = raw_path.read_bytes()
    metadata = json.loads(raw_path.with_suffix(raw_path.suffix + ".json").read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be an object")
    expected = {"schema": SCHEMA, "pixel_format": "RGB565_BE", "width": WIDTH,
                "height": HEIGHT, "byte_count": WIDTH * HEIGHT * 2,
                "scope": "snapshot_not_board_acceptance"}
    if any(type(metadata.get(key)) is not type(value) or metadata[key] != value
           for key, value in expected.items()):
        raise ValueError("Unexpected frame metadata")
    if metadata.get("source") not in SOURCES:
        raise ValueError("Unknown frame source")
    if len(data) != WIDTH * HEIGHT * 2:
        raise ValueError("Expected 614400 RGB565 bytes")
    if metadata.get("input_sha256") != hashlib.sha256(data).hexdigest():
        raise ValueError("Raw input SHA-256 does not match metadata")
    return data, metadata
